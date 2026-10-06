"""auto-context-reset — detecte la saturation de contexte et agit sans intervention humaine.

Probleme traite
---------------
Quand le contexte sature, la compression d'historique peut echouer ou s'etouffer (modele
auxiliaire qui ne rend rien). Sans surveillance, l'utilisateur doit lui-meme faire /new.

Ce que fait le plugin
---------------------
1. ``post_auxiliary_call`` (``aux_task == "compression"``) : un appel de compression qui
   sort en erreur, qui ne rend AUCUN texte, ou qui depasse ``duree_suspecte_s`` sans rien
   produire est un incident de saturation.
2. ``api_request_error`` : une erreur de debordement de fenetre (context length / too long /
   maximum context) est aussi un incident (saturation dure, pas seulement etouffement).
3. A chaque incident : une ligne JSONL dans ``auto-reset.log``, et au seuil
   ``seuil_echecs`` l'ecriture d'un **handoff durable** :
   ``<HERMES_HOME>/handoffs/<session>_<horodatage>.md`` — metadonnees de session lues en
   lecture seule dans ``state.db`` (titre, modele, cwd, compteurs de compression) plus les
   derniers messages actifs. Le travail en cours n'est donc pas perdu.
4. ``pre_llm_call`` : au tour suivant, un bloc ``<auto_context_reset>`` est injecte dans le
   contexte du modele. L'agent sait alors qu'il doit cloturer proprement, completer le
   handoff, et donner a l'utilisateur la commande de reprise — sans que celui-ci ait a
   diagnostiquer quoi que ce soit.

Ce que le plugin ne peut PAS faire
----------------------------------
Forcer ``/new`` : ``VALID_HOOKS`` (hermes_cli/plugins.py) ne contient aucune directive de
reinitialisation de session ; seuls ``pre_tool_call`` (blocage) et ``pre_llm_call``
(injection) transforment quoi que ce soit. Le plugin fait donc la seule chose possible :
detecter, preserver le travail, et rendre l'action evidente pour l'agent et l'utilisateur.

Tout est fail-open : une erreur interne ne casse jamais un tour.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

COMMAND = "auto-context-reset"
HOOKS = ("post_auxiliary_call", "api_request_error", "pre_llm_call")
AUX_TASK = "compression"
SUSPECT_FINISH = {"length", "error", "content_filter"}
# Signatures de debordement de fenetre cote fournisseur (saturation dure).
MOTIFS_SATURATION = (
    "context length", "maximum context", "context_length_exceeded", "context window",
    "too many tokens", "reduce the length", "prompt is too long", "input is too long",
    "exceeds the maximum", "tokens in the messages",
)

_CTX = None
_LOCK = threading.Lock()
_STATE: dict = {}   # session_id -> {n, premier, dernier, genres, handoff, avis, notifie_a}


# --------------------------------------------------------------------------- socle

def _hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def _norm_mode(v) -> str:
    """Normalise le mode : YAML 1.1 lit `on`/`true`/`yes` comme des booleens, et
    `hermes config set ... on` ecrit `true`. On accepte donc les deux graphies."""
    if isinstance(v, bool):
        return "on" if v else "off"
    s = str(v or "").strip().strip('"').strip("'").strip().lower()
    if s in ("", "on", "true", "1", "yes", "oui", "enabled", "actif", "active"):
        return "on"
    if s in ("off", "false", "0", "no", "non", "disabled", "inactif"):
        return "off"
    return s


def _settings(ctx) -> dict:
    """Lit les reglages du plugin. Ne leve jamais."""

    def num(cle, defaut, cast):
        try:
            return cast(ctx.get_config(cle, defaut))
        except (TypeError, ValueError):
            return defaut

    def booleen(cle, defaut):
        v = ctx.get_config(cle, defaut)
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() not in ("0", "false", "non", "no", "off", "")

    try:
        handoff_dir = str(ctx.get_config("handoff_dir", "") or "")
    except Exception:  # noqa: BLE001
        handoff_dir = ""
    try:
        log_path = str(ctx.get_config("log_path", "") or "")
    except Exception:  # noqa: BLE001
        log_path = ""
    return {
        "mode": _norm_mode(ctx.get_config("mode", "on")),
        "seuil_echecs": max(1, num("seuil_echecs", 1, int)),
        "duree_suspecte_s": num("duree_suspecte_s", 120.0, float),
        "notify_every_s": num("notify_every_s", 600.0, float),
        "dernieres_messages": max(0, num("dernieres_messages", 12, int)),
        "message_chars": max(80, num("message_chars", 400, int)),
        "ecrire_handoff": booleen("ecrire_handoff", True),
        "handoff_dir": handoff_dir,
        "log_path": log_path,
    }


def log_file(settings: dict) -> Path:
    return (Path(settings["log_path"]).expanduser() if settings["log_path"]
            else _hermes_home() / "logs" / "auto-reset.log")


def handoff_dir(settings: dict) -> Path:
    return (Path(settings["handoff_dir"]).expanduser() if settings["handoff_dir"]
            else _hermes_home() / "handoffs")


def journaliser(settings: dict, entree: dict) -> None:
    """Une ligne JSONL dans auto-reset.log. Ne leve jamais."""
    try:
        p = log_file(settings)
        p.parent.mkdir(parents=True, exist_ok=True)
        ligne = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entree}
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ligne, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.debug("auto-context-reset: journal illisible: %s", exc)


# ------------------------------------------------------------------- lecture state.db

def _etat_session(session_id: str) -> dict:
    """Lecture seule de state.db : ligne de session + derniers messages actifs."""
    out = {"session": {}, "messages": []}
    try:
        db = _hermes_home() / "state.db"
        if not db.exists():
            return out
        con = sqlite3.connect("file:%s?mode=ro" % str(db).replace("\\", "/"), uri=True, timeout=4)
        try:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cols = ("id", "title", "model", "cwd", "started_at", "ended_at", "end_reason",
                    "message_count", "tool_call_count", "compression_failure_cooldown_until",
                    "compression_failure_error", "compression_fallback_streak",
                    "compression_ineffective_count", "compression_overload_streak",
                    "compression_recovery_deadline")
            cur.execute("SELECT %s FROM sessions WHERE id=?" % ",".join(cols), (session_id,))
            r = cur.fetchone()
            if r is not None:
                out["session"] = {c: r[c] for c in cols}
            cur.execute("SELECT role, content, timestamp FROM messages WHERE session_id=? "
                        "AND active=1 ORDER BY id DESC LIMIT ?", (session_id, 200))
            out["messages"] = [dict(m) for m in cur.fetchall()]
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        logger.debug("auto-context-reset: state.db illisible: %s", exc)
    return out


def _ts(v) -> str:
    try:
        return datetime.fromtimestamp(float(v)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return str(v)


# ------------------------------------------------------------------------ handoff

def ecrire_handoff(settings: dict, session_id: str, incidents: list, avis: str) -> str:
    """Ecrit le handoff durable. Retourne le chemin, ou "" en cas d'echec."""
    if not settings["ecrire_handoff"]:
        return ""
    try:
        dossier = handoff_dir(settings)
        dossier.mkdir(parents=True, exist_ok=True)
        horo = datetime.now().strftime("%Y%m%d_%H%M%S")
        chemin = dossier / ("%s_%s.md" % (session_id or "session-inconnue", horo))
        info = _etat_session(session_id) if session_id else {"session": {}, "messages": []}
        s = info["session"]
        L = []
        L.append("# Handoff automatique — saturation de contexte")
        L.append("")
        L.append("Ecrit par le plugin `auto-context-reset` apres %d incident(s) de compression."
                 % len(incidents))
        L.append("Aucune intervention humaine n'a ete necessaire pour le produire ; il reste a"
                 " COMPLETER la section « Etat du travail » par l'agent (ou l'utilisateur).")
        L.append("")
        L.append("## Session")
        L.append("")
        L.append("- session_id : `%s`" % (session_id or "?"))
        for cle, lib in (("title", "titre"), ("model", "modele"), ("cwd", "cwd"),
                         ("started_at", "debut"), ("message_count", "messages"),
                         ("tool_call_count", "appels d'outil"), ("end_reason", "fin")):
            if s.get(cle) not in (None, ""):
                v = _ts(s[cle]) if cle in ("started_at",) else s[cle]
                L.append("- %s : %s" % (lib, v))
        L.append("")
        L.append("## Etat de compression (lu dans state.db)")
        L.append("")
        for cle, lib in (("compression_failure_error", "derniere erreur"),
                         ("compression_fallback_streak", "serie de repli"),
                         ("compression_ineffective_count", "compressions sans effet"),
                         ("compression_overload_streak", "serie de surcharge"),
                         ("compression_failure_cooldown_until", "blocage jusqu'a"),
                         ("compression_recovery_deadline", "limite de retablissement")):
            v = s.get(cle)
            if v not in (None, "", 0):
                if cle == "compression_failure_cooldown_until":
                    v = "%s (%s)" % (_ts(v), v)
                L.append("- %s : %s" % (lib, v))
        L.append("")
        L.append("## Incidents detectes")
        L.append("")
        for i, inc in enumerate(incidents, 1):
            L.append("%d. `%s` — %s" % (i, inc.get("genre", "?"), inc.get("detail", "")))
        L.append("")
        L.append("## Derniers messages actifs")
        L.append("")
        msgs = info["messages"][: settings["dernieres_messages"]]
        if not msgs:
            L.append("(aucun message lisible dans state.db pour cette session)")
        for m in reversed(msgs):
            texte = (m.get("content") or "").replace("\r", " ").strip()
            if len(texte) > settings["message_chars"]:
                texte = texte[: settings["message_chars"]] + " […]"
            texte = texte.replace("\n", "\n  ")
            L.append("- **%s** (%s) : %s" % (m.get("role"), _ts(m.get("timestamp")), texte or "(vide)"))
        L.append("")
        L.append("## Etat du travail — A COMPLETER PAR L'AGENT")
        L.append("")
        L.append("1. Ce qui est fait et verifie (avec les chemins absolus des livrables)")
        L.append("2. Ce qui reste a faire, dans l'ordre")
        L.append("3. Les mesures / verdicts a ne pas refaire")
        L.append("4. Les commandes exactes de reprise")
        L.append("")
        L.append("## Reprise")
        L.append("")
        L.append("- reprendre la session : `hermes -c` (ou `/resume` dans le CLI)")
        L.append("- relire l'historique  : `session_search(query='<mot-cle>', session_id='%s')`" % session_id)
        L.append("- base d'etat          : `%s`" % (_hermes_home() / "state.db"))
        L.append("- journal du plugin    : `%s`" % log_file(settings))
        L.append("")
        L.append("## Avis injecte au modele au tour suivant")
        L.append("")
        L.append("```")
        L.append(avis.strip())
        L.append("```")
        L.append("")
        chemin.write_text("\n".join(L) + "\n", encoding="utf-8")
        return str(chemin)
    except Exception as exc:  # noqa: BLE001
        logger.debug("auto-context-reset: handoff non ecrit: %s", exc)
        return ""


# -------------------------------------------------------------------------- avis

def texte_avis(session_id: str, incidents: list, handoff: str, seuil: int) -> str:
    dernier = incidents[-1] if incidents else {}
    lignes = [
        "<auto_context_reset>",
        "ALERTE SATURATION — plugin auto-context-reset.",
        "%d incident(s) de compression de contexte (seuil de declenchement : %d)."
        % (len(incidents), seuil),
        "Dernier incident : [%s] %s" % (dernier.get("genre", "?"), dernier.get("detail", "")),
    ]
    if handoff:
        lignes.append("Handoff durable ecrit : %s" % handoff)
    lignes += [
        "A FAIRE MAINTENANT, sans attendre que l'utilisateur diagnostique :",
        "1. terminer proprement le travail en cours ;",
        "2. completer la section « Etat du travail » du handoff (chemins, restes, mesures) ;",
        "3. dire a l'utilisateur que la compression a echoue et qu'un /new est conseille"
        " (aucun hook Hermes ne permet de forcer /new) ;",
        "4. donner la commande de reprise : `hermes -c` ou `session_search(session_id='%s')`."
        % session_id,
        "Procedure detaillee : skill `auto-context-reset`.",
        "</auto_context_reset>",
    ]
    return "\n".join(lignes)


# ----------------------------------------------------------------------- incidents

def _est_echec_compression(kw: dict, seuil_duree: float) -> tuple:
    """(est_incident, genre, detail) pour un appel auxiliaire de compression."""
    err = kw.get("error") or kw.get("error_type")
    duree = kw.get("api_duration") or 0
    try:
        duree = float(duree)
    except (TypeError, ValueError):
        duree = 0.0
    chars = kw.get("assistant_content_chars")
    try:
        chars = int(chars)
    except (TypeError, ValueError):
        chars = -1
    fin = str(kw.get("finish_reason") or "")
    modele = kw.get("model") or kw.get("response_model") or "?"
    if err:
        return True, "erreur", "erreur %s : %s (modele %s, %.0f s)" % (
            type(err).__name__ if not isinstance(err, str) else "provider",
            str(err)[:180], modele, duree)
    # Reponse en flux : auxiliary_hooks.py:153 la rend NON consommee, donc
    # assistant_content_chars=0 et finish_reason=None sont normaux — aucun signal.
    if kw.get("streaming"):
        return False, "", ""
    if chars == 0:
        return True, "sortie_vide", "aucun texte rendu par le modele de compression %s (%.0f s, finish=%s)" % (
            modele, duree, fin or "?")
    if duree >= seuil_duree:
        return True, "etouffement", "compression sans progres : %.0f s >= seuil %.0f s (modele %s, finish=%s)" % (
            duree, seuil_duree, modele, fin or "?")
    if fin in SUSPECT_FINISH:
        return True, "fin_anormale", "fin de generation anormale (%s, modele %s, %.0f s)" % (fin, modele, duree)
    return False, "", ""


def _est_saturation_dure(kw: dict) -> tuple:
    """(est_incident, genre, detail) pour une erreur d'appel API = fenetre depassee."""
    texte = " ".join(str(kw.get(k) or "") for k in
                     ("error_message", "error_body", "error_type", "error_code")).lower()
    if not texte.strip():
        return False, "", ""
    for motif in MOTIFS_SATURATION:
        if motif in texte:
            return True, "fenetre_depassee", "erreur de fenetre (%s) : %s" % (
                kw.get("status_code") or "?", str(kw.get("error_message") or "")[:160])
    return False, "", ""


def _incident(ctx, settings: dict, session_id: str, genre: str, detail: str) -> None:
    """Enregistre un incident, journalise, et au seuil ecrit le handoff + arme l'avis."""
    if settings["mode"] != "on":
        return
    maintenant = time.time()
    handoff, avis = "", ""
    with _LOCK:
        st = _STATE.setdefault(session_id or "-", {"n": 0, "premier": maintenant, "dernier": 0,
                                                   "genres": [], "handoff": "", "avis": "",
                                                   "notifie_a": 0.0})
        st["n"] += 1
        st["dernier"] = maintenant
        st["genres"].append(genre)
        franchi = st["n"] == settings["seuil_echecs"] or (
            st["n"] > settings["seuil_echecs"]
            and maintenant - (st["notifie_a"] or 0.0) >= settings["notify_every_s"])
        incident = {"genre": genre, "detail": detail, "ts": maintenant}
        duels = st.setdefault("incidents", [])
        duels.append(incident)
        if franchi:
            st["notifie_a"] = maintenant
    journaliser(settings, {"outcome": "incident", "session": session_id, "genre": genre,
                           "detail": detail, "n": st["n"], "franchi": bool(franchi)})
    if not franchi:
        return
    with _LOCK:
        incidents = list(st.get("incidents") or [])
    avis = texte_avis(session_id or "?", incidents, "", settings["seuil_echecs"])
    handoff = ecrire_handoff(settings, session_id, incidents, avis)
    if handoff:
        avis = texte_avis(session_id or "?", incidents, handoff, settings["seuil_echecs"])
    with _LOCK:
        st["handoff"] = handoff
        st["avis"] = avis
    journaliser(settings, {"outcome": "handoff", "session": session_id, "chemin": handoff,
                           "incidents": len(incidents)})
    logger.warning("auto-context-reset: %d incident(s) de compression sur %s — handoff %s",
                   len(incidents), session_id, handoff or "(non ecrit)")


# --------------------------------------------------------------------------- hooks

def make_hooks(ctx):
    def on_post_auxiliary_call(**kw):
        try:
            settings = _settings(ctx)
            if settings["mode"] != "on":
                return None
            if str(kw.get("aux_task") or "") != AUX_TASK:
                return None
            incident, genre, detail = _est_echec_compression(kw, settings["duree_suspecte_s"])
            if incident:
                _incident(ctx, settings, str(kw.get("session_id") or ""), genre, detail)
            return None
        except Exception as exc:  # noqa: BLE001 — fail-open
            logger.debug("auto-context-reset: post_auxiliary_call: %s", exc)
            return None

    def on_api_request_error(**kw):
        try:
            settings = _settings(ctx)
            if settings["mode"] != "on":
                return None
            incident, genre, detail = _est_saturation_dure(kw)
            if incident:
                _incident(ctx, settings, str(kw.get("session_id") or ""), genre, detail)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("auto-context-reset: api_request_error: %s", exc)
            return None

    def on_pre_llm_call(**kw):
        """Injecte l'avis une seule fois par franchissement. Ne leve jamais."""
        try:
            settings = _settings(ctx)
            if settings["mode"] != "on":
                return None
            sid = str(kw.get("session_id") or "")
            texte = kw.get("user_message")
            if isinstance(texte, str) and texte.strip().startswith("/"):
                return None
            with _LOCK:
                st = _STATE.get(sid or "-") or {}
                avis = st.get("avis") or ""
                if avis:
                    st["avis"] = ""
            if not avis:
                return None
            return {"context": avis}
        except Exception as exc:  # noqa: BLE001
            logger.debug("auto-context-reset: pre_llm_call: %s", exc)
            return None

    return on_post_auxiliary_call, on_api_request_error, on_pre_llm_call


# --------------------------------------------------------------------- CLI

def setup_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="auto_reset_action")
    subs.add_parser("on", help="Activer la surveillance (defaut)")
    subs.add_parser("off", help="Desactiver (plugin inerte)")
    subs.add_parser("status", help="Reglages, journal, dossier de handoff, etat par session")
    subs.add_parser("check", help="Verifier ecriture journal/handoff, lecture state.db, hooks")
    p = subs.add_parser("simuler", help="Fabriquer N incidents et ecrire un vrai handoff (test)")
    p.add_argument("--session", default="", help="session_id a utiliser (defaut : simulation-<ts>)")
    p.add_argument("--n", type=int, default=2, help="nombre d'incidents a fabriquer")
    p.add_argument("--genre", default="etouffement", help="genre du dernier incident")
    p.add_argument("--detail", default="simulation : compression sans progres (300 s, 0 texte rendu)",
                   help="detail du dernier incident")


def _cmd_status(ctx, settings: dict) -> int:
    print("mode            : %s" % settings["mode"])
    print("seuil_echecs    : %s   duree_suspecte_s : %ss" % (settings["seuil_echecs"],
                                                             settings["duree_suspecte_s"]))
    print("notify_every_s  : %ss" % settings["notify_every_s"])
    print("handoff         : %s (%s)" % (handoff_dir(settings),
                                         "ecriture active" if settings["ecrire_handoff"] else "desactivee"))
    print("journal         : %s" % log_file(settings))
    with _LOCK:
        etats = {k: dict(v) for k, v in _STATE.items()}
    if etats:
        print("sessions suivies :")
        for sid, st in etats.items():
            print("  %-28s incidents=%d genres=%s handoff=%s"
                  % (sid, st["n"], ",".join(st["genres"][-4:]), st["handoff"] or "-"))
    else:
        print("sessions suivies : aucune (aucun incident depuis le chargement)")
    return 0


def _cmd_check(ctx, settings: dict) -> int:
    ok = True
    try:
        p = log_file(settings)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write("")
        print("journal   : OK (%s)" % p)
    except Exception as exc:  # noqa: BLE001
        print("journal   : ECHEC (%s)" % exc); ok = False
    try:
        d = handoff_dir(settings)
        d.mkdir(parents=True, exist_ok=True)
        t = d / ".ecriture-test"
        t.write_text("x", encoding="utf-8")
        t.unlink()
        print("handoff   : OK (%s)" % d)
    except Exception as exc:  # noqa: BLE001
        print("handoff   : ECHEC (%s)" % exc); ok = False
    try:
        db = _hermes_home() / "state.db"
        if not db.exists():
            print("state.db  : ABSENT (%s) — handoff sans metadonnees" % db)
        else:
            con = sqlite3.connect("file:%s?mode=ro" % str(db).replace("\\", "/"), uri=True, timeout=4)
            n = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            m = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            con.close()
            print("state.db  : OK (%d sessions, %d messages)" % (n, m))
    except Exception as exc:  # noqa: BLE001
        print("state.db  : ECHEC (%s)" % exc); ok = False
    print("hooks     : %s" % ", ".join(HOOKS))
    return 0 if ok else 1


def _cmd_simuler(ctx, settings: dict, args) -> int:
    sid = args.session or ("simulation-%d" % int(time.time()))
    n = max(1, int(args.n))
    for i in range(n):
        genre = args.genre if i == n - 1 else "erreur"
        detail = args.detail if i == n - 1 else "simulation : erreur provider (HTTP 503)"
        _incident(ctx, settings, sid, genre, detail)
    with _LOCK:
        st = dict(_STATE.get(sid) or {})
    print("session simulee : %s" % sid)
    print("incidents       : %d" % st.get("n", 0))
    print("handoff         : %s" % (st.get("handoff") or "(non ecrit)"))
    print("journal         : %s" % log_file(settings))
    print()
    print("--- avis qui sera injecte au prochain tour (pre_llm_call) ---")
    print(st.get("avis") or "(aucun : deja consomme ou mode off)")
    return 0


def run_cli(ctx, args: argparse.Namespace) -> int:
    action = getattr(args, "auto_reset_action", None)
    if action in ("on", "off"):
        try:
            # bool : YAML 1.1 lit `on`/`off` comme des booleens, et le schema declare `mode: bool`
            ctx.set_config("mode", action == "on")
        except Exception as exc:  # noqa: BLE001
            print("impossible d'ecrire mode: %s" % exc)
            return 1
        print("auto-context-reset : mode -> %s" % action)
        return 0
    settings = _settings(ctx)
    if action == "status":
        return _cmd_status(ctx, settings)
    if action == "check":
        return _cmd_check(ctx, settings)
    if action == "simuler":
        return _cmd_simuler(ctx, settings, args)
    print("Usage: hermes auto-context-reset {on|off|status|check|simuler}")
    return 2


def _cli_command(args: argparse.Namespace) -> int:
    return run_cli(_CTX, args)


def register(ctx) -> None:
    """Cable les hooks et la commande CLI (appele une fois par le loader)."""
    global _CTX
    _CTX = ctx
    a, b, c = make_hooks(ctx)
    ctx.register_hook("post_auxiliary_call", a)
    ctx.register_hook("api_request_error", b)
    ctx.register_hook("pre_llm_call", c)
    ctx.register_cli_command(COMMAND,
                             "Saturation de contexte : detection, handoff, avis (on|off|status|check|simuler)",
                             setup_cli, _cli_command,
                             description="Detecte les echecs de compression, ecrit un handoff, injecte un avis.")
