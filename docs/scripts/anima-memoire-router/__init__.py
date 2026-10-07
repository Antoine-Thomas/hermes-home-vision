"""anima-memoire-router — route la question vers la mémoire (JEV → RAG) avant l'appel LLM.

Hook ``pre_llm_call`` : JEV (repli regex) choisit la couche mémoire ; si le niveau 3
(RAG) est requis, le hook interroge le RAG local (127.0.0.1:8200) et injecte les
extraits dans le contexte de l'utilisateur sous ``<rag_context>``. Fail-open sur
chaque chemin d'erreur : un routeur cassé ne casse jamais un tour. Mode ``off`` par
défaut (opt-in). Stdlib uniquement. Une ligne JSON par décision.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

COMMAND = "anima-memoire-router"
HOOK = "pre_llm_call"

_CTX = None


def _hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def _settings(ctx) -> dict:
    """Lit les réglages du plugin. Ne lève jamais."""

    def num(key, default, cast):
        try:
            return cast(ctx.get_config(key, default))
        except (TypeError, ValueError):
            return default

    return {
        "mode": str(ctx.get_config("mode", "off") or "off").strip().lower(),
        "rag_url": str(ctx.get_config("rag_url", "http://127.0.0.1:8200")
                       or "http://127.0.0.1:8200"),
        "rag_k": num("rag_k", 5, int),
        "rag_k_complexe": num("rag_k_complexe", 20, int),
        "routeur": str(ctx.get_config("routeur", "on") or "on").strip().lower(),
        "timeout_s": num("timeout_s", 4.0, float),
        "max_chars": num("max_chars", 4000, int),
        "log_path": str(ctx.get_config("log_path", "") or ""),
    }


def log_file(settings: dict) -> Path:
    if settings["log_path"]:
        return Path(settings["log_path"]).expanduser()
    return _hermes_home() / "logs" / "anima-memoire-router.log"


def log(settings: dict, entry: dict) -> None:
    """Ajoute une ligne JSON. Ne lève jamais (le log ne doit jamais casser un tour)."""
    try:
        path = log_file(settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:  # pragma: no cover
        logger.debug("anima-memoire-router: log write failed: %s", exc)


def _route(question: str):
    """Importe router_memoire (data/rag) et route la question. Ne lève jamais.

    router_memoire.router() appelle JEV (repli regex intégré) et journalise
    déjà sa décision dans jev_routing.jsonl.
    """
    try:
        rag_dir = _hermes_home() / "data" / "rag"
        if str(rag_dir) not in sys.path:
            sys.path.insert(0, str(rag_dir))
        import router_memoire as rm  # noqa: E402
        return rm.router(question)
    except Exception as exc:
        logger.debug("anima-memoire-router: route failed: %s", exc)
        return None


def _rag_search(settings: dict, question: str, k: int) -> dict:
    url = settings["rag_url"].rstrip("/") + "/search"
    body = json.dumps({"question": question, "k": int(k)}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=settings["timeout_s"]) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _decider_complexite(question: str):
    """Classe la question (simple / moderee / complexe) via data/rag/routeur_complexite.py.

    Ne leve jamais : sans le module, on retourne None et le hook retombe sur
    l'ancien comportement (RAG top-k systematique).
    """
    try:
        rag_dir = _hermes_home() / "data" / "rag"
        if str(rag_dir) not in sys.path:
            sys.path.insert(0, str(rag_dir))
        import routeur_complexite as rc  # noqa: E402
        return rc.decider(question)
    except Exception as exc:
        logger.debug("anima-memoire-router: routeur complexite indisponible: %s", exc)
        return None


def _selectionner(question: str, candidats: list, k: int) -> list:
    """Selection locale des k fragments d'un chemin « complexe » (aucun reranker externe)."""
    try:
        rag_dir = _hermes_home() / "data" / "rag"
        if str(rag_dir) not in sys.path:
            sys.path.insert(0, str(rag_dir))
        import routeur_complexite as rc  # noqa: E402
        return rc.selectionner(list(candidats), question, k=k)
    except Exception as exc:
        logger.debug("anima-memoire-router: selection locale indisponible: %s", exc)
        return list(candidats)[:k]


def _block(results: list, max_chars: int) -> str:
    """Le bloc injecté : extraits RAG, borné à max_chars."""
    lines = []
    total = 0
    for r in results:
        titre = str(r.get("titre") or "").strip()
        extrait = str(r.get("extrait") or "").strip()
        source = str(r.get("source") or "").strip()
        chunk = "- [%s] %s\n  %s" % (source, titre, extrait)
        if total + len(chunk) > int(max_chars):
            break
        lines.append(chunk)
        total += len(chunk)
    head = ("<rag_context>\n"
            "Extraits de la mémoire locale (RAG) pertinents pour la question. "
            "Cite le document si pertinent ; ignore ce qui ne correspond pas.\n")
    return head + "\n".join(lines) + "\n</rag_context>"


def make_hook_handler(ctx):
    """Construit le handler pre_llm_call. Lit user_message, ne lève jamais."""

    def on_pre_llm_call(**kwargs):
        try:
            settings = _settings(ctx)
            if settings["mode"] != "on":
                return None
            text = kwargs.get("user_message")
            if not isinstance(text, str) or not text.strip():
                return None
            if text.strip().startswith("/"):
                return None
            if len(text) > int(settings["max_chars"]):
                return None
            if "<rag_context>" in text:
                return None
            result = _route(text)
            if not result:
                log(settings, {"outcome": "no_route"})
                return None
            niveaux = list(result.get("niveaux_a_consulter") or [])
            source = result.get("source_decision")
            if 3 not in niveaux:
                log(settings, {"outcome": "no_rag", "niveaux": niveaux, "source": source})
                return None
            # Phase B : le routeur de complexite decide AVANT le POST /search.
            # simple -> aucune recherche ; moderee -> top-k ; complexe -> top-N puis selection locale.
            decision = _decider_complexite(text) if settings["routeur"] == "on" else None
            classe = (decision or {}).get("classe")
            if classe == "simple":
                log(settings, {"outcome": "no_rag_simple", "classe": classe,
                               "raisons": (decision or {}).get("raisons"),
                               "niveaux": niveaux, "source": source})
                return None
            k_recherche = int((decision or {}).get("k_recherche") or settings["rag_k"])
            k_injecte = int((decision or {}).get("k_injecte") or k_recherche)
            try:
                data = _rag_search(settings, text, k_recherche)
            except urllib.error.URLError as exc:
                log(settings, {"outcome": "rag_error", "classe": classe,
                               "k_recherche": k_recherche, "error": str(exc)[:120]})
                return None
            results = list(data.get("resultats") or [])
            if not results:
                log(settings, {"outcome": "rag_empty", "source": source, "classe": classe})
                return None
            if classe == "complexe":
                results = _selectionner(text, results, k_injecte)
            block = _block(results, settings["max_chars"])
            log(settings, {"outcome": "injected", "classe": classe, "k_recherche": k_recherche,
                           "k_injecte": len(results), "source": source, "niveaux": niveaux,
                           "chars": len(block), "raisons": (decision or {}).get("raisons")})
            return {"context": block}
        except Exception as exc:  # un routeur cassé ne casse jamais un tour
            logger.debug("anima-memoire-router: hook error (fail-open): %s", exc)
            return None

    return on_pre_llm_call


def setup_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="anima_memoire_action")
    subs.add_parser("on", help="Activer le routage mémoire (chaque tour éligible)")
    subs.add_parser("off", help="Désactiver (défaut ; rien ne sort de la machine)")
    subs.add_parser("status", help="Montrer mode, endpoints, log")
    subs.add_parser("check", help="Vérifier import router_memoire, RAG et log (sans inférence)")


def _cmd_status(ctx, settings: dict) -> int:
    print("mode:     %s" % settings["mode"])
    print("rag_url:  %s" % settings["rag_url"])
    print("rag_k:    %s (moderee)   rag_k_complexe: %s   routeur: %s" % (
        settings["rag_k"], settings["rag_k_complexe"], settings["routeur"]))
    print("timeout:  %ss   max_chars: %s" % (settings["timeout_s"], settings["max_chars"]))
    print("log:      %s" % log_file(settings))
    return 0


def _cmd_check(ctx, settings: dict) -> int:
    ok = True
    r = _route("Quel modèle d'embedding utilise mon RAG local ?")
    print("router_memoire: %s" % ("OK (source=%s, niveaux=%s)" % (
        r.get("source_decision"), r.get("niveaux_a_consulter")) if r else "FAIL (import/route)"))
    ok = ok and bool(r)
    dec = _decider_complexite("Compare le port du RAG et celui de ComfyUI : lequel est apparu en premier ?")
    print("routeur:       %s" % ("OK (classe=%s, k=%s)" % (dec.get("classe"), dec.get("k_recherche"))
                                 if dec else "FAIL (import routeur_complexite)"))
    ok = ok and bool(dec)
    dec_simple = _decider_complexite("Bonjour")
    print("routeur simple: %s" % ("OK (classe=%s -> aucune recherche)" % dec_simple.get("classe")
                                   if dec_simple else "FAIL"))
    ok = ok and bool(dec_simple) and dec_simple.get("classe") == "simple"
    try:
        d = _rag_search(settings, "Quel modèle d'embedding utilise mon RAG local ?", 1)
        n = len(d.get("resultats") or [])
        print("RAG /search:    OK (%d résultat(s))" % n)
        ok = ok and n > 0
    except Exception as exc:
        print("RAG /search:    FAIL (%s)" % str(exc)[:80])
        ok = False
    try:
        p = log_file(settings)
        p.parent.mkdir(parents=True, exist_ok=True)
        print("log:           %s" % ("OK (writable %s)" % p if os.access(p.parent, os.W_OK)
                                     else "FAIL (%s)" % p))
        ok = ok and os.access(p.parent, os.W_OK)
    except Exception as exc:
        print("log:           FAIL (%s)" % exc)
        ok = False
    return 0 if ok else 1


def run_cli(ctx, args: argparse.Namespace) -> int:
    action = getattr(args, "anima_memoire_action", None)
    if action in ("on", "off"):
        try:
            ctx.set_config("mode", action)
        except Exception as exc:
            print("could not set mode: %s" % exc)
            return 1
        print("anima-memoire-router: mode -> %s" % action)
        return 0
    settings = _settings(ctx)
    if action == "status":
        return _cmd_status(ctx, settings)
    if action == "check":
        return _cmd_check(ctx, settings)
    print("Usage: hermes anima-memoire-router {on|off|status|check}")
    return 2


def _cli_command(args: argparse.Namespace) -> int:
    return run_cli(_CTX, args)


def register(ctx) -> None:
    """Câble le hook et la commande CLI (appelé une fois par le loader)."""
    global _CTX
    _CTX = ctx
    ctx.register_hook(HOOK, make_hook_handler(ctx))
    ctx.register_cli_command(COMMAND, "Routage mémoire JEV→RAG (on|off|status|check)",
                             setup_cli, _cli_command,
                             description="Route la question vers la mémoire et injecte le RAG au LLM.")
