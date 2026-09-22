---
name: security-monitoring
description: "Use when silencing 'Erreur API' Telegram alert spam."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [securite, monitoring, telegram, logs, alertes, schtasks]
    related_skills: [security-audit]
---

# Surveillance continue (SecurityMonitoring)

Système distinct du scanner d'audit (`security-audit`) : il surveille en continu
logs et ports, et relaie les alertes sur Telegram via des tâches planifiées
Windows (schtasks `SecurityMonitoring-*`).

Fichiers clés :
- `~/AppData/Local/hermes/data/security-monitoring/monitors/log_monitor.py` — lit les logs (Hermes/Ollama/VibeVoice), détecte, alerte Telegram
- `~/AppData/Local/hermes/data/security-monitoring/monitors/port_monitor.py` — ports
- `~/AppData/Local/hermes/data/security-monitoring/telegram/alert_bridge.py` — envoi Telegram
- `~/AppData/Local/hermes/scripts/hidden_SecurityMonitoring-*.vbs` — wrappers VBS (lancent Python masqué via `Python310/python.exe`)

## Spam d'alertes « 🚨 Erreur API »

**Les alertes viennent de `log_monitor.py`, PAS du gateway Hermes.** Chercher
« Erreur API » dans le cœur Hermes ne trouve rien : la chaîne est construite dans
le moniteur (règle `api_error`, niveau 8), qui relaie chaque ligne `ERROR` et
chaque `Traceback (most recent call last)` du journal.

Faire taire un spam récurrent = étendre la regex `EXCLUDE` de `log_monitor.py`
avec le motif spécifique. Ne jamais modifier le cœur Hermes.

Déjà exclus (bénins) : timeout `updater.stop()`, `Fatal telegram adapter error`,
`Streaming failed before delivery` (503 fournisseur), `Traceback (most recent
call last)`, `getaddrinfo`, `IMAP (fetch error|connection failed)`,
`Fatal email adapter error`, `Network Retry Loop`, `map_(httpcore_)?exceptions`,
`above exception was the direct cause`, `self.gen.throw`, `openai.APIError`,
`not available in the active live catalog`, `rate limit`, `authentication
expired`, `API call failed`, `media file not found`, `Error analyzing image` / `Error analyzing video` (vision),
`Analyzing image` (chemin vision), `conversation turn`, `inbound message` (échos
du message utilisateur), `NotADirectoryError` (write_file transitoire),
`Non-retryable client error` (stall fournisseur), `Unrepairable tool_call`,
`Retrying API call` (diagnostic OmniRoute), `httpx2: HTTP Request` (le client HTTP
journalise chaque requête/réponse, donc un `401 Unauthorized` pendant le
rafraîchissement OAuth d'un serveur MCP déclenche la règle auth — faux positif).

## Spam d'alertes « 🔴 Ports en écoute » (port_monitor.py)

`port_monitor.py` compare les ports LISTENING (`netstat -ano`) à la liste blanche
de `config.json` : un port est anormal s'il n'est ni dans `ports.allowlist`, ni dans
la plage éphémère, ni tenu par un process de `ports.process_allowlist`.

Faire taire un port légitime (faux positif) = ajouter le **nom du process** à
`ports.process_allowlist` (convention existante : « Adobe Desktop Service.exe »,
« steam.exe », « Cyberpunk2077.exe »). Ajouter le **numéro de port** à
`ports.allowlist` seulement pour un service connu (API locale, proxy).

Piège : une app de bureau qui écoute sur un port non standard (ex. Adobe Premiere
Pro sur 3111) est un faux positif, pas un backdoor. **Identifier le process AVANT
de whitelister** : `netstat -ano | grep ":PORT"` → PID →
`powershell Get-CimInstance Win32_Process -Filter "ProcessId=PID"` → lire
`CommandLine`. Un `python.exe` en `127.0.0.1` (localhost uniquement) est un service
local légitime, pas un backdoor : whitelister le **numéro de port** (jamais
« python.exe » seul, trop générique). Services locaux connus de cette machine :
8188 ComfyUI, 6806 SiYuan, 9119 `hermes_cli.main serve`, 8200 RAG
(`serveur_rag.py`). Vérifier avec `python port_monitor.py` (attendu :
« Aucun port anormal persistant »).

**Correction « intelligente » (transitoire vs persistant) :** le moniteur mémorise
les ports dans `port_state.json`. Un port anormal NOUVEAU (1re apparition) est
signalé en 🟠 « transitoire » (installateur/updater, PAS d'alerte Telegram). Seul
un port PERSISTANT (encore ouvert au run suivant) déclenche l'alerte 🔴 backdoor.
Un process éphémère (ex. « AI.exe » disparu, port 25001 fermé) ne doit donc
jamais être whitelisté à l'aveugle : laisser le mécanisme de persistance trancher.

## Vérifier après chaque ajout

`classify()` est autonome : la ligne exclue doit donner `None`, les vraies
erreurs doivent encore déclencher :

```python
classify("... ERROR ...: Streaming failed before delivery: 503") is None      # True
classify("... ERROR ...: 401 unauthorized") is not None                       # True (auth)
classify("... CRITICAL ...: out of memory") is not None                       # True (crash)
classify("... union select * from users") is not None                         # True (attaque)
```

## Pièges

1. **`Traceback (most recent call last)` duplique la ligne `ERROR` qui le précède**
   (écrit par `logger.exception`). L'exclure déduplique : les vrais crashs restent
   couverts par `FATAL/crash/OOM` (niv. 10) et `Unhandled` (niv. 8). Ne pas exclure
   le seul mot `Traceback` : une ligne « Traceback: real crash » doit encore remonter.
2. **Ne pas calmer le spam en descendant le niveau de log dans le cœur**
   (`adapter.py`, `chat_completion_helpers.py`). La notification passe par le
   moniteur, pas par le log level du gateway : corriger `EXCLUDE`, pas le cœur.
3. **Les règles sont insensibles à la casse (`(?i)`)** : `Traceback` matche aussi
   « traceback » en minuscule (ex. `self.gen.throw(typ, value, traceback)`) et
   `Exception` matche « exceptions » dans un nom de fonction (`map_exceptions`,
   `map_httpcore_exceptions`). Un traceback d'exception attrapée déclenche donc
   UNE alerte par ligne de corps : exclure toute la signature du traceback
   (en-tête + corps), pas seulement l'en-tête.
4. **Les erreurs DNS/réseau transitoires sont des faux positifs, pas des bugs.**
   `getaddrinfo` (Errno 11001), `IMAP fetch/connection failed`,
   `Fatal email adapter error`, `Network Retry Loop` apparaissent quand la machine
   est brièvement hors ligne. Les whitelister ; ne pas « corriger » l'adaptateur.
5. **Les erreurs de modèle OmniRoute/LLM sont des faux positifs, pas des échecs
d'auth.** `openai.APIError` (modèle mort `not available in the active live
catalog`, `rate limit` 429, `authentication expired`) et `API call failed
(attempt N/3)` matchent la règle auth (niv. 9) via un « auth »/« 401 »/« 403 »
dans le message d'erreur. Les whitelister ; corriger plutôt le combo qui
référence les modèles morts (skill `omniroute-gateway`).
6. **`kanban dispatcher: tick failed` (PermissionError: delegate_task child
contexts cannot mutate Kanban tasks or boards) = le gateway a hérité du marqueur
d'environnement `HERMES_DELEGATED_CHILD_CONTEXT=1` (un sous-agent delegate_task a
redémarré le gateway avec son env). Ce n'est PAS un spam à whitelister : corriger
la cause par `hermes gateway restart` (redémarrage propre sans le marqueur), puis
vérifier `env | grep HERMES_DELEGATED` (doit être vide) et que le tick kanban
suivant ne remonte plus d'erreur.
7. **Les lignes qui RECOPIENT le message de l'utilisateur sont des faux positifs.**
   `conversation turn` (agent.turn_context) et `inbound message` (gateway.run) sont
   des lignes INFO qui contiennent le texte intégral du message entrant. Quand
   l'utilisateur colle le texte d'une alerte (« Erreur critique / crash », un
   traceback…), ces lignes matchent les regex crash/error et relancent l'alerte
   qu'il vient de signaler. Exclure `conversation\s+turn|inbound\s+message` —
   ce sont des échos, pas des erreurs réelles.
8. **Les règles matchent le CONTENU de la ligne, pas son niveau de log.** Une ligne
   INFO/WARNING déclenche une alerte si son CONTENU contient un mot déclencheur,
   même sans erreur réelle : « crash » dans la doc d'un skill dumpé dans un log
   `Unrepairable tool_call`, un « 401 » dans le diagnostic d'un `Retrying API
   call`, un `../` dans le chemin d'un `Analyzing image`. Corriger en excluant le
   motif de la LIGNE (`Unrepairable\s+tool_call`, `Retrying\s+API\s+call`,
   `Analyzing\s+image`, `Error\s+analyzing\s+video`, `Non-retryable\s+client\s+error`),
   jamais en descendant le niveau de log du cœur.
9. **`Fatal whatsapp adapter error (whatsapp_bridge_exited)` = le bridge Node
   (Baileys) crash en boucle.** Si l'utilisateur n'utilise pas WhatsApp,
   `WHATSAPP_ENABLED=false` dans le `.env` ne suffit pas toujours : le désactiver
   définitif est `hermes config set platforms.whatsapp.enabled false` (ce YAML est
   traité comme prioritaire — « it never beats an explicit YAML disable »), puis
   `hermes gateway restart`. Vérifier que le log ne re-tente plus
   `Reconnecting whatsapp`.
