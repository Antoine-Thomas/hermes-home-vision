# -*- coding: utf-8 -*-
"""Supervision ANIMA 0.2 — états normalisés READY / DEGRADED / FAILED / BLOCKED.

Ce module NE REMPLACE PAS ``health_architecture.py`` : il est appelé par lui
(``superviser()``) et ses sections sont fusionnées dans ``health.json`` en plus des
clés historiques (timestamp, ports, taches, fraicheur, verrous,
orphelins_sans_ecrivain, anomalies), qui restent inchangées pour ne casser aucun
consommateur.

Objectif : que la supervision représente réellement l'état opérationnel d'ANIMA
(Hermes + services connectés + fallback). Un service qui répond mais dont le test
FONCTIONNEL échoue n'est PAS READY.

Règles :
  - aucune valeur de ``.env`` n'est écrite dans un rapport (seuls des NOMS de variables
    sont cités) ; les rares valeurs lues (mot de passe Wazuh, clé OpenRouter) restent
    en mémoire et sont masquées ;
  - jamais HTTP 200 = READY quand un test fonctionnel est possible ;
  - 127.0.0.1 par défaut ; aucun appel payant n'est déclenché par la supervision ;
  - la clé OpenRouter est lue en MÉMOIRE pour la SEULE mesure de quota gratuit
    (``GET /api/v1/auth/key`` : lecture, aucune inférence, aucun coût) ; sa valeur
    n'est jamais écrite (masquage ``_SECRETS``) et seuls des NOMS de variables sont
    cités ;
  - le backend 9119 est retiré de l'architecture : il n'existe AUCUNE sonde 9119 ici ;
  - états BLOCKED : composant non évaluable (rôle non démontré, run en cours).
  - sortie : sections renvoyées à l'appelant ; état persistant dans
    ``health_anima_state.json`` (last_success / failure_streak).

Usage direct (diagnostic, écrit health_anima.json à côté) ::

    python health_anima.py            # sonde tout, imprime le JSON
    python health_anima.py --resume   # résumé texte d'une ligne par composant
"""
import ctypes
import datetime
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERMES = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
ROUTE = os.path.join(HERMES, "data", "route_ia_fix")
CONFIG_YAML = os.path.join(HERMES, "config.yaml")
ENV_DEFAULT = os.path.join(HERMES, ".env")
ETAT_JSON = os.path.join(ROUTE, "health_anima_state.json")
REF_JSON = os.path.join(ROUTE, "health_anima.json")
STATE_LEGACY = os.path.join(ROUTE, "health_state.json")
HEALTH_JSON = os.path.join(ROUTE, "health.json")
OMNI_DB = os.path.join(os.path.expanduser("~"), ".omniroute", "storage.sqlite")
STATE_DB = os.path.join(HERMES, "state.db")
COUT_JSON = os.path.join(ROUTE, "surveillance_cout.json")
JEV_JSONL = os.path.join(ROUTE, "jev_routing.jsonl")
LOGS = os.path.join(HERMES, "logs")
STATE_DIR = os.path.join(HERMES, "state")

#: Endpoints sondés. Regroupés ici pour être remplaçables par un test (aucune sonde
#: n'écrit en dur un autre hôte que 127.0.0.1).
ENDPOINTS = {
    "omniroute": "http://127.0.0.1:20128",
    "nim_proxy": "http://127.0.0.1:20200",
    "ollama": "http://127.0.0.1:11434",
    "rag": "http://127.0.0.1:8200",
    "siyuan": "http://127.0.0.1:6806",
    "laya": "http://127.0.0.1:8787",
    "wazuh_indexer": "https://127.0.0.1:9200",
    "wazuh_dashboard": "https://127.0.0.1:8443",
}

SYSTEM_NAME = "ANIMA"
SYSTEM_VERSION = "0.2"

READY, DEGRADED, FAILED, BLOCKED = "READY", "DEGRADED", "FAILED", "BLOCKED"
ETATS = (READY, DEGRADED, FAILED, BLOCKED)

#: Composants dont une panne dégrade l'état global d'ANIMA.
CRITIQUES = ("gateway", "profils", "omniroute", "ollama", "rag", "siyuan",
             "wazuh", "fallback", "reindex", "memoire")
SECONDAIRES = ("nim_proxy", "laya", "jev", "cron", "couts")

#: Seuils (provisoires, documentés ici — un seuil choisi par le propriétaire les remplacera).
SEUILS = {
    "gateway_heartbeat_s": 120,      # battement du gateway plus vieux = anormal (tick ~30 s)
    "cron_ticker_s": 300,            # battement du planificateur cron
    "omniroute_appels": 200,         # fenêtre d'appels pour le taux de succès
    "omniroute_succes_pct": 80,      # en dessous : OmniRoute DEGRADED (upstreams instables)
    "reindex_age_s": 26 * 3600,      # fraîcheur de l'index RAG (reindex quotidien 03:00)
    "memoire_pct_alerte": 90,        # occupation d'un budget mémoire (USER.md / MEMORY.md)
    "cout_24h_usd": 5.0,             # budget 24 h provisoire (ANIMA 0.2) — abaissé (L3a)
    "repli_payant_24h_usd": 0.50,    # alerte si le repli payant (bascule vers deepseek-flash) dépasse 0,50 $/24 h
    "rag_top": 3,                    # critère : document attendu dans le top 3
    "jev_appel_recent_j": 7,         # âge max du dernier appel JEV jugé « fonctionnel »
    "jev_quota_gratuit_min": 1,      # free_model_daily_requests.remaining < ce seuil = quota épuisé
}
#: Requête de contrôle RAG + document attendu (critère top3, RRF non modifié).
RAG_CONTROLE = {"question": "Quel modele d'embedding utilise le RAG local ?", "k": 3}
RAG_DOC_ATTENDU = "RAG local - resultat Phase 1"
#: Composants sortis de l'architecture (aucune sonde, aucune obligation).
COMPOSANTS_RETIRES = [
    {"composant": "backend 9119", "statut": "OUT_OF_SCOPE / OBSOLETE",
     "retire_le": "2026-09-29 15:25",
     "preuve": "data/route_ia_fix/backend_9119_retirement_plan.md §6"},
]


# --------------------------------------------------------------------------- #
# utilitaires
# --------------------------------------------------------------------------- #
def _iso(ts=None):
    return datetime.datetime.fromtimestamp(ts or time.time()).isoformat(timespec="seconds")


def _resume(txt, n=300):
    """Tronque et neutralise un message d'erreur (jamais de secret affiché).

    Toute valeur de secret lue en mémoire (identifiants Wazuh du compose) est masquée
    avant d'être journalisée dans health.json.
    """
    t = re.sub(r"\s+", " ", str(txt or "")).strip()
    for s in _SECRETS:
        if s:
            t = t.replace(s, "***")
    return t[:n]


#: Valeurs de secrets lues en MÉMOIRE uniquement (jamais écrites dans un rapport ni un log).
_SECRETS = []


def _compose_wazuh():
    """Identifiants de l'indexer Wazuh, lus dans le compose, gardés en mémoire.

    Retourne (utilisateur, mot_de_passe) ou (None, None). Aucune valeur n'est imprimée :
    elle n'est utilisée que pour l'en-tête Authorization des sondes HTTPS locales, et
    masquée par ``_resume()`` si elle apparaissait dans un message.
    """
    chemin = os.path.join(os.path.expanduser("~"), "wazuh-docker", "single-node", "docker-compose.yml")
    txt = lire_texte(chemin, 200000) or ""
    u = re.search(r"INDEXER_USERNAME\s*[:=]\s*['\"]?([^'\"\s,}]+)", txt)
    p = re.search(r"INDEXER_PASSWORD\s*[:=]\s*['\"]?([^'\"\s,}]+)", txt)
    usr = u.group(1) if u else None
    pwd = p.group(1) if p else None
    if pwd:
        _SECRETS.append(pwd)
    return usr, pwd


def _entete_basic(usr, pwd):
    import base64
    return {"Authorization": "Basic " + base64.b64encode(("%s:%s" % (usr, pwd)).encode()).decode(),
            "User-Agent": "ANIMA-health/0.1"}


def _noms_env(chemin):
    """NOMS des variables d'un .env (jamais les valeurs)."""
    noms = set()
    try:
        for ligne in open(chemin, encoding="utf-8", errors="replace"):
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ligne)
            if m:
                noms.add(m.group(1))
    except OSError:
        pass
    return noms


def _cle_openrouter():
    """Clé OpenRouter lue en MÉMOIRE (jamais affichée) pour la seule mesure de quota.

    Aucune valeur n'est écrite : la clé est ajoutée à ``_SECRETS`` pour être masquée
    par ``_resume()`` si elle apparaissait dans un message d'erreur.
    """
    v = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not v:
        txt = lire_texte(ENV_DEFAULT, 200000) or ""
        m = re.search(r'^\s*OPENROUTER_API_KEY\s*=\s*["\']?([^"\'\s]+)', txt, re.MULTILINE)
        v = (m.group(1).strip() if m else "")
    if v and v not in _SECRETS:
        _SECRETS.append(v)
    return v


def _quota_openrouter(timeout=8):
    """Quota gratuit OpenRouter : ``GET /api/v1/auth/key`` + ``/api/v1/credits``.

    Lecture seule, aucune inférence, aucun coût, aucun quota consommé. Sert à ce que
    « quota épuisé » ne ressemble plus à « panne » : la mesure est journalisée BRUTE
    (remaining, used, limit) à côté de l'état du composant. Ne lève jamais.
    """
    det = {"mesure": False, "epuise": False, "code": None}
    cle = _cle_openrouter()
    if not cle:
        det["erreur"] = "OPENROUTER_API_KEY absente (nom seul vérifié, valeur non lue)"
        return det
    entetes = {"Authorization": "Bearer " + cle, "User-Agent": "ANIMA-health/0.1"}
    ok, code, lat, txt, err = http("https://openrouter.ai/api/v1/auth/key",
                                   entetes=entetes, timeout=timeout)
    det["code"] = code
    det["latence_ms"] = lat
    try:
        d = (json.loads(txt) or {}).get("data") or {}
    except Exception:
        d = {}
    if not ok or not d:
        det["erreur"] = _resume(err or ("réponse illisible (HTTP %s)" % code), 160)
        return det
    fmdr = d.get("free_model_daily_requests") or {}
    reste = fmdr.get("remaining")
    det["mesure"] = True
    det["is_free_tier"] = d.get("is_free_tier")
    det["usage_daily_usd"] = d.get("usage_daily")
    det["usage_weekly_usd"] = d.get("usage_weekly")
    det["free_model_daily_requests"] = {"used": fmdr.get("used"), "limit": fmdr.get("limit"),
                                       "remaining": reste}
    det["epuise"] = bool(reste is not None and reste < SEUILS["jev_quota_gratuit_min"])
    okc, codec, latc, txtc, errc = http("https://openrouter.ai/api/v1/credits",
                                        entetes=entetes, timeout=timeout)
    if okc:
        try:
            det["total_credits"] = ((json.loads(txtc) or {}).get("data") or {}).get("total_credits")
        except Exception:
            pass
    det["credits_code"] = codec
    return det


_SSL_CTX = ssl.create_default_context()
_SSL_NOCHECK = ssl._create_unverified_context()


def http(url, methode="GET", corps=None, timeout=8, entetes=None, ctx=None, brut=False):
    """Appel HTTP. Ne lève pas : retourne (ok, code, latence_ms, texte, erreur)."""
    t0 = time.time()
    data = None
    h = dict(entetes or {})
    if corps is not None:
        data = json.dumps(corps, ensure_ascii=False).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=methode, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            corps_txt = r.read(400000).decode("utf-8", "replace")
            return True, r.status, int((time.time() - t0) * 1000), corps_txt, None
    except urllib.error.HTTPError as e:
        # 401/403/404/422 = le service RÉPOND : ce n'est pas une panne de transport.
        try:
            corps_txt = e.read(400000).decode("utf-8", "replace")
        except Exception:
            corps_txt = ""
        return (200 <= e.code < 400), e.code, int((time.time() - t0) * 1000), corps_txt, None
    except Exception as e:
        return False, None, int((time.time() - t0) * 1000), "", "%s: %s" % (type(e).__name__, e)


def port_ouvert(port, hote="127.0.0.1", timeout=3):
    """Test TCP brut (aucune donnée envoyée)."""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((hote, port))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def tls_joignable(hote, port=443, timeout=6):
    """Test TLS sortant (JEV) : handshake sans requête applicative, sans coût."""
    try:
        s = socket.create_connection((hote, port), timeout=timeout)
        try:
            _SSL_CTX.wrap_socket(s, server_hostname=hote).close()
        finally:
            try:
                s.close()
            except Exception:
                pass
        return True, None
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)


def pid_vivant(pid):
    """Vérifie qu'un PID existe — OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION), aucun effet de bord."""
    try:
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    except Exception:
        return False


def lire_json(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return defaut


def lire_texte(chemin, limite=400000):
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return f.read(limite)
    except Exception:
        return None


def age_s(chemin):
    try:
        return round(time.time() - os.path.getmtime(chemin))
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# config.yaml : chaîne de repli + limites mémoire (parseur ciblé, sans PyYAML)
# --------------------------------------------------------------------------- #
def _bloc_yaml(lignes, cle, indent=0):
    """Retourne les lignes du bloc ``cle:`` à l'indentation donnée (jusqu'au déindentage)."""
    pref = " " * indent
    out, dedans = [], False
    for l in lignes:
        if not dedans:
            if re.match(r"^%s%s\s*:" % (pref, re.escape(cle)), l):
                dedans = True
                reste = l.split(":", 1)[1].strip()
                if reste:
                    out.append(reste)
            continue
        if l.strip() and not l.startswith(pref + " "):
            break
        out.append(l)
    return out


def lire_config_anima(chemin=None):
    """Extrait ce que la supervision doit connaître de config.yaml.

    Retour : {"primaire": {...}, "repli": [{provider, model}], "modeles_locaux": {...},
              "limites_memoire": {...}, "sha256": ...}
    Aucune valeur de secret n'est lue (les clés ``key_env`` ne sont que des NOMS).
    """
    chemin = chemin or CONFIG_YAML
    txt = lire_texte(chemin) or ""
    lignes = txt.splitlines()
    res = {"chemin": chemin, "primaire": {}, "repli": [], "modeles_locaux": {},
           "limites_memoire": {}, "sha256": None}
    import hashlib
    res["sha256"] = hashlib.sha256(txt.encode("utf-8")).hexdigest() if txt else None

    for l in _bloc_yaml(lignes, "model"):
        m = re.match(r"^\s*(default|provider)\s*:\s*(.+)$", l)
        if m:
            res["primaire"][m.group(1)] = m.group(2).strip().strip("'\"")

    # fallback_providers : liste de mappings « - provider: X » / « model: Y »
    bloc = _bloc_yaml(lignes, "fallback_providers")
    courant = {}
    for l in bloc:
        mp = re.match(r"^\s*-\s*provider\s*:\s*(.+)$", l)
        mm = re.match(r"^\s*-\s*model\s*:\s*(.+)$", l)
        cp = re.match(r"^\s*provider\s*:\s*(.+)$", l) if l.startswith("    ") else None
        cm = re.match(r"^\s*model\s*:\s*(.+)$", l) if l.startswith("    ") else None
        if mp or mm:
            if courant:
                res["repli"].append(courant)
            courant = {"provider": None, "model": None}
            if mp:
                courant["provider"] = mp.group(1).strip().strip("'\"")
            if mm:
                courant["model"] = mm.group(1).strip().strip("'\"")
        elif cp:
            courant["provider"] = cp.group(1).strip().strip("'\"")
        elif cm:
            courant["model"] = cm.group(1).strip().strip("'\"")
    if courant and (courant.get("provider") or courant.get("model")):
        res["repli"].append(courant)

    # providers.<nom>.default_model / api  (seuls ollama-local et omniroute nous intéressent)
    prov = _bloc_yaml(lignes, "providers")
    nom, sous = None, {}
    for l in prov:
        m = re.match(r"^  ([A-Za-z0-9_.\-]+)\s*:\s*$", l)
        if m:
            if nom:
                res["modeles_locaux"][nom] = sous
            nom, sous = m.group(1), {}
            continue
        m = re.match(r"^    (api|base_url|default_model|name)\s*:\s*(.+)$", l)
        if m and nom:
            sous[m.group(1)] = m.group(2).strip().strip("'\"")
    if nom:
        res["modeles_locaux"][nom] = sous

    for l in _bloc_yaml(lignes, "memory"):
        m = re.match(r"^\s*(memory_char_limit|user_char_limit)\s*:\s*(\d+)", l)
        if m:
            res["limites_memoire"][m.group(1)] = int(m.group(2))
    return res


# --------------------------------------------------------------------------- #
# état persistant (last_check / last_success / failure_streak)
# --------------------------------------------------------------------------- #
def _etat_charge():
    return lire_json(ETAT_JSON, {}) or {}


def _etat_sauve(d):
    try:
        tmp = ETAT_JSON + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, ETAT_JSON)
    except Exception:
        pass


def marquer(etat_global, nom, etat, erreur=None, latence=None, detail=None):
    """Enregistre un composant : fusionne son état, met à jour la série d'échecs."""
    st = _etat_charge()
    cur = dict(st.get(nom) or {})
    maintenant = _iso()
    if etat == READY:
        cur["last_success"] = maintenant
        cur["failure_streak"] = 0
    elif etat in (DEGRADED, FAILED):
        cur["failure_streak"] = int(cur.get("failure_streak") or 0) + 1
    # BLOCKED : le composant n'est pas évaluable -> la série n'avance ni ne se remet à zéro.
    cur["last_state"] = etat
    cur["last_check"] = maintenant
    st[nom] = cur
    st["_maj"] = maintenant
    _etat_sauve(st)
    rec = {"state": etat, "last_check": maintenant,
           "last_success": cur.get("last_success"),
           "failure_streak": int(cur.get("failure_streak") or 0)}
    if latence is not None:
        rec["latency_ms"] = int(latence)
    if erreur:
        rec["error"] = _resume(erreur)
    if detail:
        rec.update(detail)
    etat_global[nom] = rec
    return rec


# --------------------------------------------------------------------------- #
# sondes
# --------------------------------------------------------------------------- #
def sonde_gateway(etat_global, cfg):
    """GATEWAY HERMES : battement, PID, profils multiplexés, planificateur cron."""
    t0 = time.time()
    latence = None
    det = {}
    erreurs = []
    hb = os.path.join(STATE_DIR, "gateway.heartbeat")
    d = lire_json(hb, {}) or {}
    age = age_s(hb)
    det["heartbeat_age_s"] = age
    det["pid"] = d.get("pid")
    det["pid_vivant"] = pid_vivant(d.get("pid")) if d.get("pid") else False
    det["start_time"] = d.get("start_time")
    if age is None:
        erreurs.append("battement absent")
    elif age > SEUILS["gateway_heartbeat_s"]:
        erreurs.append("battement vieux de %s s" % age)

    lc = lire_json(os.path.join(STATE_DIR, "gateway.lifecycle.json"), {}) or {}
    det["phase"] = lc.get("phase")
    det["prior_unclean_exit"] = lc.get("prior_unclean_exit")

    gs = lire_json(os.path.join(HERMES, "gateway_state.json"), {}) or {}
    det["gateway_state"] = gs.get("gateway_state")
    det["active_agents"] = gs.get("active_agents")

    profs = lire_json(os.path.join(LOGS, "gateway-health.state.json"), {}) or {}
    profils = {k: v for k, v in profs.items() if not k.startswith("_")}
    det["profils"] = profils
    det["battement_profils"] = profs.get("_battement_le")
    down = [k for k, v in profils.items() if str(v).lower() not in ("up", "ok", "ready")]
    if down:
        erreurs.append("profils %s" % ",".join(down))

    tick = os.path.join(HERMES, "cron", "ticker_heartbeat")
    age_tick = age_s(tick)
    det["planificateur_age_s"] = age_tick
    if age_tick is None or age_tick > SEUILS["cron_ticker_s"]:
        erreurs.append("planificateur cron inactif (%s s)" % age_tick)

    if not det["pid_vivant"] or (age is not None and age > SEUILS["gateway_heartbeat_s"]):
        etat = FAILED
    elif erreurs:
        etat = DEGRADED
    else:
        etat = READY
    return marquer(etat_global, "gateway", etat, " ; ".join(erreurs) or None,
                   int((time.time() - t0) * 1000) if latence is None else latence, det)


def sonde_profils(etat_global, cfg):
    """PROFILS : config.yaml lisible + .env présent, pour chacun des profils déployés."""
    t0 = time.time()
    profils = {"default": HERMES, "veille": os.path.join(HERMES, "profiles", "veille"),
               "watch": os.path.join(HERMES, "profiles", "watch"),
               "docs-writer": os.path.join(HERMES, "profiles", "docs-writer")}
    det, erreurs, manquants = {}, [], []
    for nom, base in profils.items():
        cy = os.path.join(base, "config.yaml")
        env = os.path.join(base, ".env")
        item = {"config_yaml": os.path.exists(cy), "env": os.path.exists(env),
                "nb_vars_env": len(_noms_env(env)) if os.path.exists(env) else 0}
        if not item["config_yaml"]:
            manquants.append(nom)
        elif not item["env"]:
            erreurs.append("%s : .env absent" % nom)
        det[nom] = item
    det["nb_profils"] = len(profils)
    if manquants:
        etat = FAILED
        erreurs.append("config.yaml manquant : %s" % ",".join(manquants))
    elif erreurs:
        etat = DEGRADED
    else:
        etat = READY
    return marquer(etat_global, "profils", etat, " ; ".join(erreurs) or None,
                   int((time.time() - t0) * 1000), det)


def _omniroute_sql(requete, args=()):
    import sqlite3
    con = sqlite3.connect("file:%s?mode=ro" % OMNI_DB.replace("\\", "/"), uri=True, timeout=10)
    try:
        return list(con.execute(requete, args))
    finally:
        con.close()


def sonde_omniroute(etat_global, cfg):
    """OMNIROUTE : vivant ? + test FONCTIONNEL (taux de succès des appels récents).

    HTTP 200/401 seul ne suffit pas : c'est le taux d'échec réel des appels qui
    distingue READY de DEGRADED (les upstreams gratuits renvoient 429/503/504).
    Retourne aussi la section « routing ».
    """
    t0 = time.time()
    det, erreurs = {}, []
    ok, code, lat, _txt, err = http(ENDPOINTS["omniroute"] + "/api/combos", timeout=8)
    det["http_code"] = code
    if not ok and code is None:
        etat = FAILED
        det["taux_succes_pct"] = None
        routing = {"state": FAILED, "error": "OmniRoute ne répond pas", "latency_ms": lat}
        marquer(etat_global, "omniroute", FAILED, err or "pas de réponse", lat, det)
        return routing
    n = SEUILS["omniroute_appels"]
    try:
        appels = _omniroute_sql(
            "SELECT status, COUNT(*) FROM (SELECT status FROM call_logs ORDER BY rowid DESC LIMIT ?) GROUP BY status", (n,))
        total = sum(c for _s, c in appels)
        rep = {str(s): c for s, c in appels}
        ok200 = rep.get("200", 0)
        taux = round(100.0 * ok200 / total, 1) if total else None
        det["appels_analyses"] = total
        det["repartition"] = dict(sorted(rep.items(), key=lambda kv: -kv[1])[:8])
        det["taux_succes_pct"] = taux
        det["dernier_appel"] = (_omniroute_sql("SELECT timestamp, requested_model, status FROM call_logs ORDER BY rowid DESC LIMIT 1") or [[None]])[0]
        det["connexions_actives"] = (_omniroute_sql("SELECT COUNT(*) FROM provider_connections WHERE is_active=1") or [[0]])[0][0]
        det["connexions"] = [{"provider": p, "nom": nm, "actif": bool(a), "test_status": ts,
                              "error_code": ec, "backoff": bo}
                             for p, nm, a, ts, ec, bo in _omniroute_sql(
                                 "SELECT provider, name, is_active, test_status, error_code, backoff_level "
                                 "FROM provider_connections ORDER BY provider")]
        det["combos"] = [r[0] for r in _omniroute_sql("SELECT name FROM combos ORDER BY name")]
        det["cibles_locales"] = [p for (p,) in _omniroute_sql(
            "SELECT DISTINCT provider FROM provider_connections WHERE lower(provider) LIKE '%ollama%' OR lower(name) LIKE '%ollama%'")]
        if taux is None:
            erreurs.append("aucun appel journalisé")
        elif taux < SEUILS["omniroute_succes_pct"]:
            erreurs.append("taux de succès %s %% sur %d appels (seuil %d %%)"
                           % (taux, total, SEUILS["omniroute_succes_pct"]))
        etat = DEGRADED if erreurs else READY
    except Exception as e:
        det["erreur_sqlite"] = _resume(e)
        erreurs.append("lecture call_logs impossible")
        etat = DEGRADED
    marquer(etat_global, "omniroute", etat, " ; ".join(erreurs) or None,
            int((time.time() - t0) * 1000), det)
    routing = {"state": etat, "taux_succes_pct": det.get("taux_succes_pct"),
               "appels_analyses": det.get("appels_analyses"), "repartition": det.get("repartition"),
               "connexions_actives": det.get("connexions_actives"), "combos": det.get("combos"),
               "cibles_locales_dans_omniroute": det.get("cibles_locales"),
               "dernier_appel": det.get("dernier_appel")}
    return routing


def sonde_nim(etat_global, cfg):
    """NIM PROXY (20200) : /health + brique de configuration (nom de variable seulement)."""
    t0 = time.time()
    det, erreurs = {}, []
    ok, code, lat, txt, err = http(ENDPOINTS["nim_proxy"] + "/health", timeout=8)
    det["http_code"] = code
    det["reponse"] = _resume(txt, 120)
    if not ok and code is None:
        marquer(etat_global, "nim_proxy", FAILED, err or "pas de réponse", lat, det)
        return etat_global["nim_proxy"]
    noms = _noms_env(os.path.join(HERMES, ".env"))
    det["cle_configuree"] = any(n for n in noms if n.upper().startswith("NVIDIA"))
    if not det["cle_configuree"]:
        erreurs.append("aucune variable NVIDIA_* dans .env")
    etat = DEGRADED if erreurs else READY
    return marquer(etat_global, "nim_proxy", etat, " ; ".join(erreurs) or None, lat, det)


def sonde_ollama(etat_global, cfg):
    """OLLAMA : modèle configuré présent + test FONCTIONNEL chaud s'il est en VRAM."""
    t0 = time.time()
    det, erreurs = {}, []
    modele = ((cfg.get("modeles_locaux") or {}).get("ollama-local") or {}).get("default_model")
    det["modele_attendu"] = modele
    ok, code, lat, txt, err = http(ENDPOINTS["ollama"] + "/api/tags", timeout=8)
    det["http_code"] = code
    if not ok and code is None:
        marquer(etat_global, "ollama", FAILED, err or "pas de réponse", lat, det)
        return etat_global["ollama"], {"state": FAILED, "locaux": []}
    try:
        dispo = [m.get("name") for m in (json.loads(txt) or {}).get("models", [])]
    except Exception:
        dispo = []
    det["modeles_disponibles"] = dispo
    if modele and modele not in dispo:
        erreurs.append("modèle configuré %s absent (/api/tags)" % modele)
    charge, vram = None, None
    try:
        ok2, _c2, _l2, t2, _e2 = http(ENDPOINTS["ollama"] + "/api/ps", timeout=8)
        en_cours = (json.loads(t2) or {}).get("models", []) if ok2 else []
        for m in en_cours:
            if m.get("name") == modele:
                charge = True
                vram = m.get("size_vram")
        det["charge_en_vram"] = bool(charge)
        det["vram_octets"] = vram
    except Exception:
        det["charge_en_vram"] = None

    # Test fonctionnel : uniquement si le modèle est déjà en VRAM (aucun chargement forcé,
    # aucune amplification d'usage GPU depuis la supervision).
    det["test_fonctionnel"] = "non effectue (modele non charge en VRAM)"
    if charge:
        ok3, code3, lat3, t3, e3 = http(ENDPOINTS["ollama"] + "/api/generate", "POST",
                                        {"model": modele, "prompt": "ping", "stream": False,
                                         "options": {"num_predict": 1}}, timeout=120)
        det["test_fonctionnel_ms"] = lat3
        try:
            rep = json.loads(t3) or {}
        except Exception:
            rep = {}
        if ok3 and (rep.get("response") is not None or rep.get("done")):
            det["test_fonctionnel"] = "generation reelle OK"
        else:
            det["test_fonctionnel"] = "generation reelle ECHEC"
            erreurs.append("test fonctionnel (generation) en echec")
    etat = READY if not erreurs else DEGRADED
    marquer(etat_global, "ollama", etat, " ; ".join(erreurs) or None,
            int((time.time() - t0) * 1000), det)
    locaux = [{"provider": "ollama-local", "model": modele, "disponible": (modele in dispo),
               "charge_vram": bool(charge), "fallback": "dernier etage"}]
    return etat_global["ollama"], {"state": etat, "locaux": locaux,
                                   "test_fonctionnel": det["test_fonctionnel"]}


def sonde_rag(etat_global, cfg):
    """RAG : /sante + test FONCTIONNEL /search -> document attendu dans le top 3."""
    t0 = time.time()
    det, erreurs = {}, []
    ok, code, lat, txt, err = http(ENDPOINTS["rag"] + "/sante", timeout=10)
    det["http_code"] = code
    if not ok and code is None:
        marquer(etat_global, "rag", FAILED, err or "pas de réponse", lat, det)
        return etat_global["rag"], {"state": FAILED, "top3": []}
    try:
        sante = json.loads(txt) or {}
        det["fragments"] = sante.get("fragments")
        det["modele_embedding"] = sante.get("modele")
        det["index_mo"] = sante.get("index_mo")
        det["mis_a_jour"] = sante.get("mis_a_jour")
    except Exception:
        erreurs.append("/sante illisible")
        sante = {}
    top, rang = [], None
    # NB : la requête n'envoie PAS "source": null (l'API RAG renvoie 422 sur un null explicite).
    ok2, code2, lat2, t2, e2 = http(ENDPOINTS["rag"] + "/search", "POST", RAG_CONTROLE, timeout=60)
    det["search_code"] = code2
    det["search_ms"] = lat2
    if ok2:
        try:
            res = json.loads(t2) or {}
            for i, r in enumerate(res.get("resultats") or [], 1):
                top.append({"rang": i, "score": r.get("score"), "cos": r.get("cos"),
                            "source": r.get("source"), "titre": r.get("titre")})
                if r.get("titre") == RAG_DOC_ATTENDU and rang is None:
                    rang = i
        except Exception:
            erreurs.append("/search illisible")
    else:
        erreurs.append("test fonctionnel /search en echec (%s)" % code2)
    det["requete_controle"] = RAG_CONTROLE["question"]
    det["document_attendu"] = RAG_DOC_ATTENDU
    det["rang_document_attendu"] = rang
    det["top3"] = top
    if rang is None:
        erreurs.append("document attendu ABSENT du top %d" % SEUILS["rag_top"])
    elif rang > SEUILS["rag_top"]:
        erreurs.append("document attendu hors top %d (rang %d)" % (SEUILS["rag_top"], rang))
    etat = READY if not erreurs else DEGRADED
    marquer(etat_global, "rag", etat, " ; ".join(erreurs) or None,
            int((time.time() - t0) * 1000), det)
    return etat_global["rag"], {"state": etat, "document_attendu": RAG_DOC_ATTENDU,
                                "rang": rang, "top3": top, "fragments": det.get("fragments")}


def sonde_siyuan(etat_global, cfg):
    """SIYUAN : version + requête SQL réelle (dernière écriture, nombre de carnets)."""
    t0 = time.time()
    det, erreurs = {}, []
    ok, code, lat, txt, err = http(ENDPOINTS["siyuan"] + "/api/system/version", timeout=10)
    det["http_code"] = code
    if not ok and code is None:
        marquer(etat_global, "siyuan", FAILED, err or "pas de réponse", lat, det)
        return etat_global["siyuan"]
    try:
        det["version"] = (json.loads(txt) or {}).get("data")
    except Exception:
        erreurs.append("/api/system/version illisible")
    det["derniere_ecriture_blocks"] = _siyuan_sql_local("SELECT updated FROM blocks WHERE type='d' ORDER BY updated DESC LIMIT 1")
    det["nb_carnets"] = _siyuan_sql_local("SELECT COUNT(*) FROM boxes")
    det["nb_docs"] = _siyuan_sql_local("SELECT COUNT(*) FROM blocks WHERE type='d'")
    if det["derniere_ecriture_blocks"] is None:
        erreurs.append("requête SQL sans résultat (API/jeton indisponible)")
    etat = READY if not erreurs else DEGRADED
    return marquer(etat_global, "siyuan", etat, " ; ".join(erreurs) or None,
                   int((time.time() - t0) * 1000), det)


def _siyuan_sql_local(stmt):
    import sqlite3
    try:
        import urllib.request as ur
        jeton = None
        for ligne in open(ENV_DEFAULT, encoding="utf-8", errors="replace"):
            if ligne.startswith("SIYUAN_TOKEN="):
                jeton = ligne.split("=", 1)[1].strip()
                break
        if not jeton:
            return None
        req = ur.Request(ENDPOINTS["siyuan"] + "/api/query/sql",
                         data=json.dumps({"stmt": stmt}, ensure_ascii=False).encode("utf-8"),
                         headers={"Authorization": "Token " + jeton, "Content-Type": "application/json"})
        with ur.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
        rows = d.get("data") or []
        if not rows:
            return 0 if stmt.lower().startswith("select count") else None
        v = rows[0]
        return list(v.values())[0] if isinstance(v, dict) else v
    except Exception:
        return None


def sonde_laya(etat_global, cfg):
    """LAYA : /health + test FONCTIONNEL /v1/choice (décision réelle attendue)."""
    t0 = time.time()
    det, erreurs = {}, []
    ok, code, lat, txt, err = http(ENDPOINTS["laya"] + "/health", timeout=10)
    det["http_code"] = code
    if not ok and code is None:
        marquer(etat_global, "laya", FAILED, err or "pas de réponse", lat, det)
        return etat_global["laya"]
    try:
        h = json.loads(txt) or {}
        det["model_loaded"] = h.get("model_loaded") or h.get("model_loaded_ms")
        det["detail_health"] = {k: v for k, v in list(h.items())[:8] if k != "model"}
    except Exception:
        pass
    corps = {"state": {"contexte": "ANIMA 0.2 — supervision"},
             "instructions": "Quelle couche doit repondre a une question sur un document deja indexe ?",
             "options": ["wiki_L1", "memoire_native", "rag_L2"]}
    ok2, code2, lat2, t2, e2 = http(ENDPOINTS["laya"] + "/v1/choice", "POST", corps, timeout=90)
    det["decision_code"] = code2
    det["decision_ms"] = lat2
    decision = None
    if ok2:
        try:
            d = (json.loads(t2) or {}).get("answers", {}).get("choice", {})
            decision = d.get("choice") or d.get("answer")
            det["decision"] = decision
            det["probabilite"] = d.get("probability")
            det["confiance"] = d.get("confidence")
        except Exception:
            erreurs.append("réponse /v1/choice illisible")
    else:
        erreurs.append("test fonctionnel /v1/choice en echec (%s)" % code2)
    if not decision and not erreurs:
        erreurs.append("aucune décision retournée")
    etat = READY if not erreurs else DEGRADED
    rec = marquer(etat_global, "laya", etat, " ; ".join(erreurs) or None,
                  int((time.time() - t0) * 1000), det)
    return rec


def _raison_technique(ligne):
    """Le repli regex de cette ligne est-il une PANNE (et non une abstention) ?

    Motifs techniques écrits par ``router_memoire._log_jev`` : ``jev_down`` (réponse
    None : timeout, 429, breaker) et ``erreur`` (exception). Tout autre motif explicite
    (``sous_seuil``, ``choix_hors_mapping``, ``confiance_illisible``) est une ABSTENTION :
    JEV a répondu, le seuil local a écarté sa décision. Lignes historiques sans
    ``raison`` : on considère que JEV a répondu dès qu'une confiance ou des probabilités
    sont présentes (seules les branches d'échec n'en écrivent pas).
    """
    r = str(ligne.get("raison") or "").strip().lower()
    if r in ("jev_down", "erreur"):
        return True
    if r:
        return False
    return not (ligne.get("probabilities") is not None or ligne.get("confidence") is not None)


def sonde_jev(etat_global, cfg):
    """JEV : abstention (seuil) et panne (technique) sont DISTINGUÉES (ANIMA 0.2 E4/A1).

    Le health check expose cinq niveaux de preuve — service accessible / modèle
    accessible / appel fonctionnel / décision valide / repli regex — et deux d'entre eux
    ne se lisent plus sur la SEULE dernière ligne :

      - ``decision_valide`` : au moins une décision ``source=jev`` dans la fenêtre de
        ``SEUILS["jev_appel_recent_j"]`` jours (au lieu de la seule dernière ligne) ;
      - ``fallback_regex``  : dernier appel en repli pour un motif TECHNIQUE
        (``jev_down`` / ``erreur``) seulement ; un ``raison="sous_seuil"`` est une
        abstention, pas une panne.

    ``role_decideur_demontre`` (critère 3.4) devient la CONCLUSION de ces mesures au lieu
    d'être codé en dur : READY quand le rôle est démontré et qu'aucun repli technique n'est
    en cours, BLOCKED sinon (non évaluable). Le quota gratuit est mesuré en LECTURE
    (``_quota_openrouter``) : quota épuisé = DEGRADED documenté, pas une panne. Aucun appel
    d'inférence n'est déclenché ici.
    """
    t0 = time.time()
    det, erreurs = {}, []
    joignable, err = tls_joignable("openrouter.ai", 443)
    det["service_accessible"] = bool(joignable)
    if not joignable:
        det["service_error"] = _resume(err, 120)
    lignes = []
    try:
        with open(JEV_JSONL, encoding="utf-8", errors="replace") as f:
            lignes = [json.loads(l) for l in f.read().splitlines() if l.strip()]
    except Exception:
        pass
    det["appels_journalises"] = len(lignes)
    dernier = lignes[-1] if lignes else {}
    det["dernier_appel"] = {k: dernier.get(k) for k in ("ts", "source", "decision", "confidence", "latence_ms")}
    fenetre_s = SEUILS["jev_appel_recent_j"] * 86400
    maintenant = datetime.datetime.now()

    def _age(l):
        try:
            return (maintenant - datetime.datetime.fromisoformat(str(l.get("ts")))).total_seconds()
        except Exception:
            return None

    decisions = [l for l in lignes if l.get("source") == "jev" and l.get("decision")]
    dans_fenetre = [l for l in decisions if (_age(l) is None or _age(l) <= fenetre_s)]
    det["decisions_jev_fenetre_7j"] = len(dans_fenetre)
    det["dernier_appel_decision_valide"] = None
    for l in reversed(decisions):
        det["dernier_appel_decision_valide"] = {k: l.get(k) for k in ("ts", "decision", "confidence")}
        break
    det["modele_accessible"] = bool(det["dernier_appel_decision_valide"])
    age_dernier = _age(dernier) if dernier else None
    det["dernier_appel_age_s"] = round(age_dernier) if age_dernier is not None else None
    det["appel_fonctionnel"] = bool(age_dernier is not None and age_dernier <= fenetre_s)
    # A1 : la décision valide se lit sur la FENÊTRE, plus sur la seule dernière ligne.
    det["decision_valide"] = bool(dans_fenetre)
    det["raison_dernier_appel"] = dernier.get("raison")
    # A1 : le repli regex ne compte comme repli que pour un motif TECHNIQUE.
    det["fallback_regex"] = bool(dernier.get("source") == "regex" and _raison_technique(dernier))
    det["abstention_dernier_appel"] = bool(dernier) and not det["fallback_regex"] \
        and not (dernier.get("source") == "jev" and dernier.get("decision"))
    plugins = [p for p in os.listdir(os.path.join(HERMES, "hermes-agent", "plugin-catalog"))
               if "jev" in p.lower()] if os.path.isdir(os.path.join(HERMES, "hermes-agent", "plugin-catalog")) else []
    det["plugins_jev_disponibles"] = len(plugins)
    # Mesure du quota gratuit : « quota épuisé » ne doit plus ressembler à « panne ».
    det["quota_gratuit"] = _quota_openrouter()
    # Conclusion du critère 3.4 (au lieu d'un False codé en dur).
    det["role_decideur_demontre"] = bool(det["decision_valide"] and not det["fallback_regex"])
    if not det["decision_valide"]:
        motif = ("aucune décision JEV valide dans les %d j (rôle décideur non démontré, "
                 "critère ANIMA 3.4)" % SEUILS["jev_appel_recent_j"])
        etat = BLOCKED
    elif det["fallback_regex"]:
        motif = ("dernier appel en repli pour un motif technique (%s)"
                 % (det["raison_dernier_appel"] or "raison inconnue"))
        etat = BLOCKED
    elif det["quota_gratuit"].get("epuise"):
        motif = ("quota gratuit OpenRouter épuisé (remaining %s) : décision impossible, "
                 "ce n'est pas une panne de service"
                 % (det["quota_gratuit"].get("free_model_daily_requests") or {}).get("remaining"))
        etat = DEGRADED
    else:
        motif = ("rôle décideur démontré (%d décision(s) source=jev dans les %d j%s)"
                 % (len(dans_fenetre), SEUILS["jev_appel_recent_j"],
                    " ; dernier appel en abstention de seuil (raison=%s)"
                    % det["raison_dernier_appel"] if det["abstention_dernier_appel"] else ""))
        etat = READY
    det["motif"] = motif
    rec = marquer(etat_global, "jev", etat, None if etat == READY else motif,
                  int((time.time() - t0) * 1000), det)
    return rec


def sonde_wazuh(etat_global, cfg):
    """WAZUH : indexer 9200 (HTTPS + auth), dashboard 8443, manager (conteneur + ports).

    Constat de mesure : le port 9200 est en **TLS** (le plugin de sécurité OpenSearch
    rejette tout HTTP en clair : NotSslRecordException) et exige une authentification.
    La sonde utilise donc https avec les identifiants lus dans le compose, GARDÉS EN
    MÉMOIRE et jamais écrits dans health.json (masquage systématique). Wazuh n'est pas
    modifié (consigne 3.6).
    """
    t0 = time.time()
    det, erreurs = {}, []
    usr, pwd = _compose_wazuh()
    entetes = _entete_basic(usr, pwd) if (usr and pwd) else {"User-Agent": "ANIMA-health/0.1"}
    det["indexer_transport"] = "https (TLS requis par le plugin de securite)"
    det["indexer_identifiants_compose"] = bool(usr and pwd)

    ok, code, lat, txt, err = http(ENDPOINTS["wazuh_indexer"] + "/_cluster/health", timeout=15,
                                   entetes=entetes, ctx=_SSL_NOCHECK)
    det["indexer_code"] = code
    if not ok and code is None:
        marquer(etat_global, "wazuh", FAILED, "indexer injoignable: %s" % _resume(err), lat,
                dict(det, conteneurs=_wazuh_conteneurs()))
        return etat_global["wazuh"]
    if code == 401:
        erreurs.append("indexer : 401 (identifiants du compose absents ou refuses)")
    else:
        try:
            cs = json.loads(txt) or {}
            det["cluster_status"] = cs.get("status")
            det["noeuds"] = cs.get("number_of_nodes")
            det["shards"] = cs.get("active_shards")
            if cs.get("status"):
                det["cluster_sante"] = "vert" if cs["status"] == "green" else cs["status"]
        except Exception:
            erreurs.append("cluster health illisible")
    ok2, code2, _l, _t, _e = http(ENDPOINTS["wazuh_dashboard"] + "/app/login", timeout=15,
                                  ctx=_SSL_NOCHECK, entetes={"User-Agent": "ANIMA-health/0.1"})
    det["dashboard_code"] = code2
    if code2 != 200:
        erreurs.append("dashboard HTTP %s" % code2)
    if code != 401:
        ok3, code3, _l3, t3, _e3 = http(ENDPOINTS["wazuh_indexer"] + "/wazuh-alerts-*/_count", timeout=15,
                                        entetes=entetes, ctx=_SSL_NOCHECK)
        det["alertes_code"] = code3
        try:
            det["alertes_indexees"] = (json.loads(t3) or {}).get("count")
        except Exception:
            pass
    det["ports_manager"] = {str(p): port_ouvert(p) for p in (1514, 1515, 55085)}
    det["conteneurs"] = _wazuh_conteneurs()
    if not any("manager" in k for k in det["conteneurs"]):
        erreurs.append("conteneur manager arrêté")
    if "cluster_status" in det and str(det["cluster_status"]).lower() not in ("green", "yellow"):
        erreurs.append("cluster %s" % det.get("cluster_status"))
    etat = READY if not erreurs else DEGRADED
    return marquer(etat_global, "wazuh", etat, " ; ".join(erreurs) or None,
                   int((time.time() - t0) * 1000), det)


def _wazuh_conteneurs():
    try:
        p = subprocess.run(["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
                           capture_output=True, timeout=40)
        out = p.stdout.decode("utf-8", "replace")
        return {n: s for n, s in (l.split("|", 1) for l in out.splitlines() if "|" in l and "wazuh" in l.lower())}
    except Exception:
        return {}


def sonde_cron(etat_global, cfg):
    """CRON : par job — id, nom, activé, dernier run, dernier résultat, série d'échecs, prochain run.

    Aucun job n'est réparé (consigne 3.7).
    """
    t0 = time.time()
    det, jobsen, erreurs = {}, [], []
    for chemin in (os.path.join(HERMES, "cron", "jobs.json"),
                   os.path.join(HERMES, "profiles", "veille", "cron", "jobs.json")):
        d = lire_json(chemin, {})
        for j in (d.get("jobs") or []):
            item = {"id": j.get("id"), "nom": j.get("name"), "profil": j.get("profile") or
                    ("veille" if "veille" in chemin else "default"),
                    "enabled": bool(j.get("enabled")), "dernier_run": j.get("last_run_at"),
                    "dernier_resultat": j.get("last_status"), "dernier_erreur": _resume(j.get("last_error"), 160),
                    "failure_streak": j.get("failure_streak", 0), "prochain_run": j.get("next_run_at"),
                    "planification": j.get("schedule_display") or j.get("schedule")}
            jobsen.append(item)
    det["jobs"] = jobsen
    det["nb_jobs"] = len(jobsen)
    det["nb_actifs"] = sum(1 for j in jobsen if j["enabled"])
    det["en_erreur"] = [{"id": j["id"], "nom": j["nom"], "failure_streak": j["failure_streak"],
                         "dernier_resultat": j["dernier_resultat"]}
                        for j in jobsen if j["enabled"] and j["dernier_resultat"] == "error"]
    tick = age_s(os.path.join(HERMES, "cron", "ticker_heartbeat"))
    det["planificateur_age_s"] = tick
    if tick is None or tick > SEUILS["cron_ticker_s"]:
        etat = FAILED
        erreurs.append("planificateur cron inactif")
    elif det["en_erreur"]:
        etat = DEGRADED
        erreurs.append("%d job(s) actif(s) en erreur" % len(det["en_erreur"]))
    else:
        etat = READY
    marquer(etat_global, "cron", etat, " ; ".join(erreurs) or None,
            int((time.time() - t0) * 1000), det)
    return etat_global["cron"]


def sonde_reindex(etat_global, cfg, legacy=None):
    """REINDEX : fraîcheur de l'index + identité du dernier run (données du heartbeat historique)."""
    t0 = time.time()
    det, erreurs = {}, []
    legacy = legacy or {}
    frais = legacy.get("fraicheur") or {}
    age = frais.get("reindex_age_s")
    ok_frais = frais.get("reindex_ok")
    if age is None:
        # Mode autonome (sans le heartbeat historique) : mesure directe de l'index.
        idx = os.path.join(HERMES, "data", "rag", "index.faiss")
        age = age_s(idx)
        ok_frais = (age is not None and age <= SEUILS["reindex_age_s"])
        det["source_fraicheur"] = "mesure directe (index.faiss)"
    else:
        det["source_fraicheur"] = "heartbeat historique"
    st = lire_json(STATE_LEGACY, {}) or {}
    run = st.get("reindex_run_etat") or {}
    dep = st.get("reindex_depassement") or {}
    det["age_index_s"] = age
    det["age_index_h"] = round(age / 3600.0, 1) if age is not None else None
    det["index_frais"] = ok_frais
    det["run_actif"] = bool(run.get("actif"))
    det["run_motifs"] = run.get("motifs")
    det["dernier_run_tache"] = (run.get("trace") or {}).get("dernier_run_tache")
    det["dernier_resultat"] = (run.get("trace") or {}).get("dernier_resultat")
    det["journal_dernier_debut"] = (run.get("trace") or {}).get("journal_dernier_debut")
    det["journal_dernier_terme"] = (run.get("trace") or {}).get("journal_dernier_terme")
    det["runs_morts_recents"] = (run.get("trace") or {}).get("runs_morts_recents")
    det["depassement_actif"] = bool(dep.get("actif"))
    task = legacy.get("taches") or {}
    det["tache_etat"] = task.get("Hermes - Reindex RAG")
    if det["tache_etat"] in ("desactivee", "absente"):
        erreurs.append("tâche %s" % det["tache_etat"])
    if run.get("actif"):
        etat = BLOCKED
        erreurs.append("run en cours — aucune conclusion sur ce composant")
    elif det["tache_etat"] in ("desactivee", "absente") or (age is not None and not ok_frais and det["depassement_actif"]):
        etat = FAILED
        if age is not None and not ok_frais:
            erreurs.append("index vieux de %.1f h" % (age / 3600.0))
    elif (age is not None and not ok_frais) or dep.get("actif") or run.get("motifs"):
        etat = DEGRADED
        if run.get("motifs"):
            erreurs.append("run : %s" % " ; ".join(run["motifs"]))
    else:
        etat = READY
    marquer(etat_global, "reindex", etat, " ; ".join(erreurs) or None,
            int((time.time() - t0) * 1000), det)
    return etat_global["reindex"]


def sonde_memoire(etat_global, cfg):
    """MÉMOIRE : occupation des budgets (USER.md / MEMORY.md) — lecture seule (3.8)."""
    t0 = time.time()
    det, erreurs = {}, []
    lim = cfg.get("limites_memoire") or {}
    lim_user = lim.get("user_char_limit") or 1375
    lim_mem = lim.get("memory_char_limit") or 2200
    for nom, chemin, seuil in (("USER.md", os.path.join(HERMES, "memories", "USER.md"), lim_user),
                               ("MEMORY.md", os.path.join(HERMES, "memories", "MEMORY.md"), lim_mem)):
        txt = lire_texte(chemin) or ""
        pct = round(100.0 * len(txt) / seuil, 1) if seuil else None
        det[nom] = {"chars": len(txt), "limite": seuil, "pct": pct}
        if pct is not None and pct >= 100:
            erreurs.append("%s plein (%s %%)" % (nom, pct))
        elif pct is not None and pct >= SEUILS["memoire_pct_alerte"]:
            erreurs.append("%s à %s %% (seuil %s %%)" % (nom, pct, SEUILS["memoire_pct_alerte"]))
    det["seuil_pct"] = SEUILS["memoire_pct_alerte"]
    det["lecture_seule"] = True
    etat = READY if not erreurs else DEGRADED
    return marquer(etat_global, "memoire", etat, " ; ".join(erreurs) or None,
                   int((time.time() - t0) * 1000), det)


def sonde_couts(etat_global, cfg):
    """COÛTS : cumul payant + coût des dernières 24 h (lecture seule)."""
    t0 = time.time()
    det, erreurs = {}, []
    etat_fichier = lire_json(COUT_JSON, {}) or {}
    det["cumul_par_profil_usd"] = etat_fichier.get("couts")
    det["dernier_scan_ts"] = _iso(etat_fichier.get("last_scan_ts")) if etat_fichier.get("last_scan_ts") else None
    det["alerte_active"] = etat_fichier.get("alerting")
    import sqlite3
    try:
        con = sqlite3.connect("file:%s?mode=ro" % STATE_DB.replace("\\", "/"), uri=True, timeout=10)
        lim = time.time() - 24 * 3600
        det["cout_24h_usd"] = round((con.execute(
            "SELECT COALESCE(SUM(COALESCE(estimated_cost_usd,0)),0) FROM sessions WHERE started_at >= ?",
            (lim,)).fetchone() or [0])[0], 4)
        det["cout_24h_par_modele"] = [{"modele": m, "sessions": n, "usd": round(c or 0, 4)}
                                      for m, n, c in con.execute(
            "WITH u AS (SELECT session_id, model, "
            "ROW_NUMBER() OVER (PARTITION BY session_id "
            "ORDER BY COALESCE(estimated_cost_usd,0) DESC, last_seen DESC) rn "
            "FROM session_model_usage) "
            "SELECT u.model, COUNT(*), SUM(COALESCE(s.estimated_cost_usd,0)) "
            "FROM sessions s JOIN u ON u.session_id = s.id AND u.rn = 1 "
            "WHERE s.started_at >= ? AND COALESCE(s.estimated_cost_usd,0) > 0 "
            "GROUP BY u.model ORDER BY 3 DESC LIMIT 8",
            (lim,))]
        det["cumul_total_usd"] = round((con.execute(
            "SELECT COALESCE(SUM(COALESCE(estimated_cost_usd,0)),0) FROM sessions").fetchone() or [0])[0], 4)
        det["repli_payant_24h_usd"] = round((con.execute(
            "SELECT COALESCE(SUM(COALESCE(estimated_cost_usd,0)),0) FROM sessions "
            "WHERE started_at >= ? AND COALESCE(estimated_cost_usd,0) > 0 "
            "AND COALESCE(billing_provider,'') IN ('omniroute','custom','ollama-local','')",
            (lim,)).fetchone() or [0])[0], 4)
        con.close()
    except Exception as e:
        erreurs.append("lecture state.db impossible: %s" % _resume(e, 120))
    det["seuil_24h_usd"] = SEUILS["cout_24h_usd"]
    det["seuil_provisoire"] = True
    if det.get("cout_24h_usd") is not None and det["cout_24h_usd"] > SEUILS["cout_24h_usd"]:
        erreurs.append("coût 24 h %.2f $ > seuil %.2f $" % (det["cout_24h_usd"], SEUILS["cout_24h_usd"]))
    det["seuil_repli_payant_24h_usd"] = SEUILS["repli_payant_24h_usd"]
    if det.get("repli_payant_24h_usd") is not None and det["repli_payant_24h_usd"] > SEUILS["repli_payant_24h_usd"]:
        erreurs.append("repli payant 24 h %.2f $ > seuil %.2f $"
                       % (det["repli_payant_24h_usd"], SEUILS["repli_payant_24h_usd"]))
    etat = READY if not erreurs else DEGRADED
    return marquer(etat_global, "couts", etat, " ; ".join(erreurs) or None,
                   int((time.time() - t0) * 1000), det)


def _dispo_etage(etage, etats):
    """Un étage de repli est-il disponible ? (sondes déjà réalisées, aucun appel LLM)."""
    prov = (etage.get("provider") or "").lower()
    mod = etage.get("model") or ""
    if prov == "omniroute":
        sr = etats.get("omniroute") or {}
        dispo = sr.get("state") in (READY, DEGRADED)
        detail = "OmniRoute %s" % sr.get("state")
        if dispo:
            try:
                con = _omniroute_sql("SELECT COUNT(*) FROM provider_connections WHERE is_active=1")
                detail += " (%s connexion(s) active(s))" % con[0][0]
            except Exception:
                pass
        return dispo, detail
    if prov == "ollama-local":
        sr = etats.get("ollama") or {}
        detail = "Ollama %s" % sr.get("state")
        if sr.get("state") == DEGRADED:
            detail += " (%s)" % (sr.get("error") or "")
        return sr.get("state") in (READY, DEGRADED), detail
    if prov == "deepseek":
        noms = _noms_env(ENV_DEFAULT)
        cle = any(n.upper().startswith("DEEPSEEK") for n in noms)
        return cle, "clé absente du .env" if not cle else "clé présente (nom seulement)"
    return None, "provider non sondé"


def sonde_fallback(etat_global, cfg, etats):
    """FALLBACK : chaîne complète ? étage indisponible ? repli activé ? dernier étage atteint ?

    Ne MODIFIE pas la chaîne (consigne 3.5) : lecture de config.yaml et des sessions.
    """
    t0 = time.time()
    det, erreurs = {}, []
    chaine = cfg.get("repli") or []
    primaire = cfg.get("primaire") or {}
    det["primaire"] = primaire
    det["chaine"] = chaine
    det["chaine_complete"] = bool(chaine) and all(e.get("provider") and e.get("model") for e in chaine)
    det["nb_etages"] = len(chaine)
    etages = []
    for i, e in enumerate(chaine, 1):
        dispo, motif = _dispo_etage(e, etats)
        etages.append({"rang": i, "provider": e.get("provider"), "model": e.get("model"),
                       "disponible": dispo, "motif": motif})
    det["etages"] = etages
    ind = [e for e in etages if e["disponible"] is False]
    det["etages_indisponibles"] = [{"rang": e["rang"], "provider": e["provider"], "model": e["model"],
                                    "motif": e["motif"]} for e in ind]
    if not det["chaine_complete"]:
        erreurs.append("chaîne de repli incomplète ou illisible dans config.yaml")
    if ind:
        erreurs.append("%d étage(s) indisponible(s) : %s" % (len(ind), ", ".join(
            "%s/%s" % (e["provider"], e["model"]) for e in ind)))
    # Repli réellement activé ? (dernières sessions : provider/modèle utilisés)
    import sqlite3
    det["repli_active"] = None
    det["dernier_etage_atteint"] = None
    det["utilisation_recente"] = []
    try:
        con = sqlite3.connect("file:%s?mode=ro" % STATE_DB.replace("\\", "/"), uri=True, timeout=10)
        rows = list(con.execute(
            "SELECT session_id, model, billing_provider, api_call_count, last_seen FROM session_model_usage "
            "ORDER BY last_seen DESC LIMIT 25"))
        con.close()
        det["utilisation_recente"] = [{"session": r[0], "model": r[1], "provider": r[2],
                                       "appels": r[3], "vu": _iso(r[4]) if r[4] else None} for r in rows]
        modeles_chaine = [(e.get("provider") or "").lower() + "/" + (e.get("model") or "") for e in chaine]
        utilises = {((r[2] or "").lower() + "/" + (r[1] or "")) for r in rows if r[1]}
        det["etages_utilises_recemment"] = sorted(
            {m for m in utilises if m in modeles_chaine or m.split("/")[0] == "ollama-local"})
        prim = (primaire.get("provider") or "").lower() + "/" + (primaire.get("default") or primaire.get("model") or "")
        det["primaire"] = dict(primaire, cle_courante=prim)
        det["repli_active"] = bool(rows) and not any(
            (r[1] or "") == (primaire.get("default") or primaire.get("model") or "") and (r[2] or "").lower() == (primaire.get("provider") or "").lower()
            for r in rows)
        if chaine:
            dernier = (chaine[-1].get("provider") or "").lower() + "/" + (chaine[-1].get("model") or "")
            # Le dernier etage peut etre identique au modele primaire (cas de cette config :
            # fallback_providers se termine sur deepseek/deepseek-flash, deja primaire). Ce n'est
            # alors pas un etage de REPLI : il est utilise normalement, et « dernier etage
            # atteint » serait vrai par construction — ce n'est pas un signal. On ne le compte
            # que s'il est distinct du primaire.
            dernier_est_primaire = (
                (chaine[-1].get("provider") or "").lower() == (primaire.get("provider") or "").lower()
                and (chaine[-1].get("model") or "") == (primaire.get("default") or primaire.get("model") or ""))
            det["dernier_etage_est_primaire"] = dernier_est_primaire
            det["dernier_etage_atteint"] = bool(dernier in utilises and not dernier_est_primaire)
        if det["repli_active"]:
            erreurs.append("repli activé récemment (dernier modèle utilisé : %s/%s)"
                           % (rows[0][2], rows[0][1])) if rows else None
        if det["dernier_etage_atteint"]:
            erreurs.append("dernier étage de la chaîne atteint (%s)" % dernier)
    except Exception as e:
        erreurs.append("lecture des sessions impossible: %s" % _resume(e, 120))
    if not det["chaine_complete"] or (not ind and det.get("chaine") and all(e["disponible"] is False for e in etages)):
        etat = FAILED
    elif erreurs:
        etat = DEGRADED
    else:
        etat = READY
    return marquer(etat_global, "fallback", etat, " ; ".join(erreurs) or None,
                   int((time.time() - t0) * 1000), det)


# --------------------------------------------------------------------------- #
# agrégation
# --------------------------------------------------------------------------- #
def _etat_global(etats):
    """Règle documentée : FAILED critique > DEGRADED > BLOCKED ignoré pour l'état global."""
    critiques = {k: (etats.get(k) or {}).get("state") for k in CRITIQUES}
    secondaires = {k: (etats.get(k) or {}).get("state") for k in SECONDAIRES}
    if any(v == FAILED for v in critiques.values()):
        return FAILED, "au moins un composant critique FAILED"
    if any(v == DEGRADED for v in critiques.values()):
        return DEGRADED, "au moins un composant critique DEGRADED"
    if any(v == FAILED for v in secondaires.values()):
        return DEGRADED, "composant secondaire FAILED"
    if all(v == BLOCKED for v in liste_etats(etats)):
        return BLOCKED, "aucune sonde n'a pu conclure"
    if (any(v == DEGRADED for v in secondaires.values())
            or any(v == BLOCKED for v in secondaires.values())):
        return DEGRADED, "composant secondaire DEGRADED/BLOCKED (rôle non démontré)"
    return READY, "toutes les sondes critiques READY"


def liste_etats(etats):
    return [v.get("state") for k, v in etats.items() if k not in ("_maj",)]


def superviser(legacy=None, cfg=None):
    """Exécute toutes les sondes et retourne les sections ANIMA à fusionner dans health.json."""
    legacy = legacy or {}
    cfg = cfg or lire_config_anima()
    etats = {}
    sections = {}
    services = etats  # même dictionnaire : chaque composant y est marqué une seule fois

    sonde_gateway(etats, cfg)
    sonde_profils(etats, cfg)
    sections["routing"] = sonde_omniroute(etats, cfg)
    sonde_nim(etats, cfg)
    modele_section, models = sonde_ollama(etats, cfg)
    sections["knowledge"] = {"state": None}
    rag_rec, knowledge_rag = sonde_rag(etats, cfg)
    siyuan_rec = sonde_siyuan(etats, cfg)
    laya_rec = sonde_laya(etats, cfg)
    sections["decision"] = {"jev": sonde_jev(etats, cfg), "laya": laya_rec,
                            "state": None}
    sonde_wazuh(etats, cfg)
    sections["jobs"] = {"cron": sonde_cron(etats, cfg), "reindex": sonde_reindex(etats, cfg, legacy),
                        "state": None}
    sonde_memoire(etats, cfg)
    sections["cost"] = sonde_couts(etats, cfg)
    sections["fallback"] = sonde_fallback(etats, cfg, etats)
    sections["models"] = models
    sections["knowledge"] = {"rag": knowledge_rag, "siyuan": siyuan_rec,
                             "state": _pire([knowledge_rag.get("state"), siyuan_rec.get("state")])}

    # anomalies historiques (verrous, orphelins) : elles comptent dans l'état global
    anomalies_legacy = [a for a in (legacy.get("anomalies") or [])]
    if anomalies_legacy:
        etats["anomalies_historiques"] = {
            "state": DEGRADED, "last_check": _iso(), "last_success": None,
            "failure_streak": 0, "nb": len(anomalies_legacy),
            "error": " ; ".join("%s: %s" % (a.get("composant"), a.get("detail")) for a in anomalies_legacy[:4]),
        }
    else:
        etats["anomalies_historiques"] = {"state": READY, "last_check": _iso(),
                                          "last_success": _iso(), "failure_streak": 0, "nb": 0}

    gj, motif = _etat_global(etats)
    if anomalies_legacy and gj == READY:
        gj, motif = DEGRADED, "anomalies du heartbeat historique (verrous/orphelins)"
    sections["services"] = services
    sections["system_name"] = SYSTEM_NAME
    sections["system_version"] = SYSTEM_VERSION
    sections["overall_state"] = gj
    sections["overall_motif"] = motif
    sections["critical_state"] = _pire([(etats.get(k) or {}).get("state") for k in CRITIQUES])
    sections["states_vus"] = sorted({v.get("state") for k, v in etats.items() if k != "_maj" and v.get("state")})
    sections["composants_retires"] = COMPOSANTS_RETIRES
    sections["seuils"] = SEUILS
    sections["alerts"] = _alertes()
    sections["supervision_version"] = "anima-health/0.1"
    sections["regle_overall"] = ("FAILED critique -> FAILED ; DEGRADED critique ou "
                                 "FAILED/DEGRADED/BLOCKED secondaire -> DEGRADED ; sinon READY")
    return sections


def _pire(liste):
    for e in (FAILED, DEGRADED, BLOCKED):
        if e in liste:
            return e
    return READY


def _alertes():
    """Dernières alertes/retours à la normale connus (état anti-spam du heartbeat historique)."""
    st = lire_json(STATE_LEGACY, {}) or {}
    out = []
    for comp, v in st.items():
        if not isinstance(v, dict) or "statut" not in v:
            continue
        out.append({"composant": comp, "statut": v.get("statut"),
                    "derniere_alerte": _iso(v["last_alert"]) if v.get("last_alert") else None,
                    "dernier_retour": _iso(v["dernier_retour_ts"]) if v.get("dernier_retour_ts") else None})
    out.sort(key=lambda x: (x["statut"] != "anomalie", x["composant"]))
    return out


# --------------------------------------------------------------------------- #
# CLI de diagnostic (indépendant : n'écrit PAS health.json)
# --------------------------------------------------------------------------- #
def main(argv):
    sections = superviser()
    try:
        with open(REF_JSON, "w", encoding="utf-8") as f:
            json.dump(sections, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    if "--resume" in argv:
        for nom, rec in sorted(sections["services"].items()):
            if not isinstance(rec, dict) or "state" not in rec:
                continue
            print("%-22s %-9s %6s ms  %s" % (nom, rec["state"], rec.get("latency_ms", "-"),
                                             (rec.get("error") or "")[:90]))
        print("%-22s %-9s %s" % ("OVERALL", sections["overall_state"], sections["overall_motif"]))
        return 0
    print(json.dumps(sections, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
