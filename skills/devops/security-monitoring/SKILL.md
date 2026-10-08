---
name: security-monitoring
description: "Use when a monitor spams or misses alerts."
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

## When to Use

- Un flux d'alertes Telegram a faire taire (faux positifs recurrents d'un moniteur).
- Un moniteur qui n'alerte pas, ou pas quand il devrait : etat d'alerte, anti-spam, trace.
- Tester ou modifier un moniteur a etat sans envoyer d'alerte reelle.
- Verifier qu'un run planifie a bien tourne (tache Windows + journal applicatif).

Fichiers clés :
- `~/AppData/Local/hermes/data/security-monitoring/monitors/log_monitor.py` — lit les logs (Hermes/Ollama/VibeVoice), détecte, alerte Telegram
- `~/AppData/Local/hermes/data/security-monitoring/monitors/port_monitor.py` — ports
- `~/AppData/Local/hermes/data/security-monitoring/telegram/alert_bridge.py` — envoi Telegram
- `~/AppData/Local/hermes/scripts/hidden_SecurityMonitoring-*.vbs` — wrappers VBS (lancent Python masqué via `Python310/python.exe`)
- `~/AppData/Local/hermes/data/route_ia_fix/health_architecture.py` — heartbeat d'architecture (ports, tâches planifiées, fraîcheur d'index, verrous, orphelins), tâche « Hermes - Health Architecture » toutes les 15 min, état `health_state.json` + rapport `health.json`. Règles d'état des alertes et harnais de test : `references/etat-alertes-moniteur.md`. Les sections à états normalisés (`services`, `routing`, `models`, `knowledge`, `decision`, `jobs`, `cost`, `fallback`, `alerts`, `overall_state`) sont produites par `data/route_ia_fix/health_anima.py`, appelé par ce heartbeat juste avant l'écriture ; série d'échecs dans `health_anima_state.json`, schéma documenté dans `health_anima_schema.md`

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
rafraîchissement OAuth d'un serveur MCP déclenche la règle auth — faux positif),
`calling get_updates` (erreur transitoire du polling Telegram `get_updates one more time`),
`Another gateway instance` (double-lancement transitoire du gateway — le garde
single-instance a fonctionné, la 2e instance sort toute seule),
`OAuth flow error` (échec du refresh OAuth d'un serveur MCP, bénin),
`Clean EOF, no finish_reason` (le serveur LLM coupe le stream proprement sans
finish_reason ; le mot « exception » de « no transport exception » matchait la
règle `Exception` — faux positif bénin, déjà exclu).

## Spam d'alertes « 🔴 Ports en écoute » (port_monitor.py)

`port_monitor.py` compare les ports LISTENING (`netstat -ano`) à la liste blanche
de `config.json` : un port est anormal s'il n'est ni dans `ports.allowlist`, ni dans
la plage éphémère, ni tenu par un process de `ports.process_allowlist`.

Faire taire un port légitime (faux positif) = ajouter le **nom du process** à
`ports.process_allowlist` (convention existante : « Adobe Desktop Service.exe », « AdobeCollabSync.exe »
(Acrobat collab sync, port 19292), « steam.exe », « Cyberpunk2077.exe »). Ajouter le **numéro de port** à
`ports.allowlist` seulement pour un service connu (API locale, proxy).

Piège : une app de bureau qui écoute sur un port non standard (ex. Adobe Premiere
Pro sur 3111) est un faux positif, pas un backdoor. **Identifier le process AVANT
de whitelister** : `netstat -ano | grep ":PORT"` → PID →
`powershell Get-CimInstance Win32_Process -Filter "ProcessId=PID"` → lire
`CommandLine`. Un `python.exe` en `127.0.0.1` (localhost uniquement) est un service
local légitime, pas un backdoor : whitelister le **numéro de port** (jamais
« python.exe » seul, trop générique). Services locaux connus de cette machine :
8188 ComfyUI, 6806 SiYuan, 9119 `hermes_cli.main serve`, 8200 RAG
(`serveur_rag.py`), 8787 Laya TTS (`server.py --onnx-dir data/laya-onnx/english`, localhost). Vérifier avec `python port_monitor.py` (attendu :
« Aucun port anormal persistant »).

**Correction « intelligente » (transitoire vs persistant) :** le moniteur mémorise
les ports dans `port_state.json`. Un port anormal NOUVEAU (1re apparition) est
signalé en 🟠 « transitoire » (installateur/updater, PAS d'alerte Telegram). Seul
un port PERSISTANT (encore ouvert au run suivant) déclenche l'alerte 🔴 backdoor.
Un process éphémère (ex. « AI.exe » disparu, port 25001 fermé) ne doit donc
jamais être whitelisté à l'aveugle : laisser le mécanisme de persistance trancher.

## Vérifier AVANT d'éditer, puis après chaque ajout

**Prouver d'abord que la ligne n'est pas DEJA filtrée.** Une même ligne qui revient nuit après nuit
dans `errors.log` n'est pas une preuve d'alerte : le journal garde la ligne brute, le filtre agit à la
**classification**. Compter les occurrences par horodatage sur la fenêtre réelle
(`grep -h '<motif>' logs/errors.log logs/agent.log.1 logs/agent.log.2 | awk '{print substr($0,1,23)}' | sort`,
puis dater le fichier avec `head -1` / `tail -1` — `errors.log` couvre quelques jours, pas 24 h) : deux
lignes à la **même seconde** sont UN incident (l'adaptateur puis `gateway.run`), pas deux, et un pic à
la même minute chaque nuit désigne un redémarrage planifié, pas une panne. Rejouer ensuite les lignes
RÉELLES trouvées sur l'`EXCLUDE` **en cours** : quand les deux rendent `None`, le filtre est déjà en
place — ne rien éditer, et le rapporter comme « N occurrences brutes dans le journal, 0 alerte
émise ». Un filtre posé lors d'une session précédente se retrouve ainsi sans retaper de motif ; le
harnais rejouable est `scripts/verify_exclude.py`.

`classify()` est autonome : la ligne exclue doit donner `None`, les vraies
erreurs doivent encore déclencher :

```python
classify("... ERROR ...: Streaming failed before delivery: 503") is None      # True
classify("... ERROR ...: 401 unauthorized") is not None                       # True (auth)
classify("... CRITICAL ...: out of memory") is not None                       # True (crash)
classify("... union select * from users") is not None                         # True (attaque)
```

## Moniteur à état : ne jamais effacer la trace d'une alerte

Un moniteur maison garde son anti-spam dans un JSON d'état (un `statut` + un `last_alert` par
composant). Quatre règles, chacune née d'un faux diagnostic :

- **Ne jamais remettre `last_alert` à 0 sur un retour à la normale.** Conserver la valeur et ajouter
  `dernier_retour_ts`. Un `0` écrit au retour au vert fait dire « le moniteur n'a pas alerté » alors
  que l'alerte est partie — on cherche ensuite un bug inexistant.
- **Mémoriser le franchissement d'un seuil**, pas seulement l'état courant
  (`<metrique>_depassement : {actif, detecte_ts, age_s, clos_ts, clos_par}`). Sinon, un run planifié
  manqué suivi d'une réparation manuelle devient invisible : l'état repasse au vert et plus rien ne
  dit que la fenêtre a été franchie.
- **Purger les entrées des composants qu'on ne surveille plus.** Un verrou supprimé ou un orphelin
  réglé laisse sinon une entrée `anomalie` à vie (l'état garde plus d'entrées que de composants
  réellement observés) : un lecteur croit la panne encore active.
- **La fraîcheur n'est pas la réussite.** Une sonde qui teste l'âge du dernier artefact voit le
  rafraîchissement manuel et repasse au vert ; elle ne dit donc rien du run planifié. Comparer en
  plus `LastRunTime`/`LastTaskResult` de la tâche au créneau attendu.

Répondre à « le moniteur a-t-il alerté ? » se fait sur `last_alert`, qui n'est écrit **que si
l'envoi a réussi**, et sur les horodatages voisins (`date -d @<epoch>`) : un composant alerté dans le
même run porte le même horodatage et prouve que le transport fonctionnait à cet instant. Ne jamais
conclure « pas d'alerte » depuis un `last_alert` à 0.

## Tester un moniteur à état sans envoyer d'alerte réelle

1. Copier le script dans le scratch et **réécrire sa constante de chemin de base** vers un dossier de
   test (l'original de production n'est jamais lancé en mode test).
2. **Neutraliser l'envoi** : remplacer le corps de la fonction d'alerte par une écriture dans
   `alertes_test.txt`. Un moniteur de test ne doit JAMAIS toucher Telegram — l'alerte part sur le
   téléphone de l'utilisateur.
3. Fabriquer un arbre synthétique (artefact daté par `os.utime`, verrou factice, état pré-rempli) et
   scénariser : seuil franchi → alerte + trace ; réparation → retour au vert avec trace conservée ;
   entrée fantôme → purgée ; anti-spam → 2e run muet.
4. **Anti-spam : compter les occurrences, pas la présence.** Le journal d'alertes est en append, donc
   `motif in fichier` reste vrai après un 2e run bloqué → test faussement en échec. Utiliser
   `fichier.count(motif)` avant/après chaque run.
5. **Relever le SHA256 des fichiers de production avant et après la campagne** et exiger l'identique :
   c'est la preuve qu'aucun test n'a écrit dans le réel.

Squelette du harnais, tableau des scénarios, commandes de vérification d'un run planifié et lecture
d'un verrou résiduel : `references/etat-alertes-moniteur.md`.

## Périmètre et qualité des sondes (hériter d'un moniteur existant)

- **Le périmètre d'une surveillance, c'est sa LISTE de sondes.** Un service qui n'apparaît dans aucune
  sonde n'est jamais signalé : la liste des composants surveillés EST le périmètre réel, et tout
  service hors liste se rapporte INCONNU — jamais « sain parce que rien ne l'a signalé ». Mesure : un
  service annoncé dans la doc d'architecture (un backend sur `9119`) était mort depuis deux jours
  (aucune écoute, dernière exécution 48 h plus tôt) pendant que tous les composants surveillés
  étaient verts. Avant d'écrire « tout est sain », citer les composants de la liste et leur verdict.
- **`200` n'est pas le seul code sain.** Plusieurs sondes locales répondent VOLONTAIREMENT en `401`
  (auth requise) ou `404` (route inconnue) quand le service va bien — c'est le cas d'OmniRoute
  (`GET /api/combos` -> 401, `GET /` -> 307) et du proxy NIM (`GET /` -> 404). Une sonde écrite « tout
  ce qui n'est pas 200 = panne » alerte en boucle sur des services sains, ou pire fait retirer la
  sonde : fixer PAR SERVICE le code (ou l'ensemble de codes) ATTENDU, et l'écrire à côté de la sonde.
- **Une sonde de disponibilité ne dit rien de la qualité.** Un `GET /sante` de moteur de recherche
  répond `200` avec le nombre de fragments et le modèle d'embedding même quand le classement s'est
  dégradé. La sonde utile est la requête fonctionnelle (une question dont la réponse est connue) et le
  verdict porte sur la POSITION du document attendu : rapporter « cohérence partielle » quand le bon
  document sort en 2e/3e au lieu de convertir un `200` en « service OK ».
- **Un service sans sonde se marque INCONNU, jamais READY par defaut** — sinon un tableau de bord
  vert certifie un perimetre qu'il ne couvre pas.
- **Un composant qui reste DEGRADED (ou READY) en continu est un faux positif STRUCTUREL, pas une
  panne.** Verifier que chaque condition de la sonde lit une cle que son PARSEUR remplit reellement :
  rejouer le parseur seul, imprimer le dict obtenu et comparer aux cles lues par la sonde — une cle
  absente rend `None`, la comparaison est toujours fausse et l'etat ne bougera plus jamais (mesure :
  une sonde comparait `primaire["model"]` quand le parseur remplissait la cle `default`). Meme piege
  pour un critere vrai PAR CONSTRUCTION : « dernier etage de la chaine atteint » est forcement vrai
  quand le dernier etage EST le modele primaire, donc il n'informe sur rien. Apres correction, prouver
  les DEUX sens : le cas reel sort de l'alerte, ET un contre-cas (un repli reel, distinct, effectivement
  utilise) doit encore alerter — sinon on a eteint un signal au lieu de corriger un faux positif.

## Etendre un heartbeat existant : etats normalises et rapport additif

- **Un seul ecrivain par fichier d'etat.** Le rapport de sante a deja un producteur (la tache du
  heartbeat) : un second script qui reecrit le meme fichier efface a chaque tick les cles de l'autre.
  Faire produire les nouvelles sections par un MODULE appele depuis l'ENTREE existante
  (`rapport.update(module.superviser(legacy=rapport))` juste avant l'ecriture) et laisser la tache
  planifiee inchangee : aucune nouvelle tache, aucun second planificateur.
- **Le rapport s'etend en AJOUT SEUL.** Les cles historiques gardent leur nom et leur forme, car
  d'autres lecteurs en dependent (anti-spam d'alertes, harnais de test, documentation). Prouver
  l'ajout en listant les cles presentes avant/apres, et rapporter un heartbeat qui tourne toujours
  en un temps normal.
- **Quatre etats normalises** `READY / DEGRADED / FAILED / BLOCKED`, avec la regle d'agregation
  ecrite dans le rapport : un composant critique `FAILED` -> global `FAILED` ; sinon un composant
  `DEGRADED`/`BLOCKED` -> `DEGRADED` ; sinon `READY`. `BLOCKED` = « non evaluable » (role non
  demontre, run en cours) : il n'invente ni panne ni reussite.
- **Chaque composant porte** `state`, `last_check`, `latency_ms`, `error`, `last_success`,
  `failure_streak` ; la serie d'echecs vit dans un fichier d'etat SEPARE de l'anti-spam d'alertes
  (deux roles, deux fichiers).
- **Seuils exposes dans le rapport, pas enterres dans le code** (`seuils` + un drapeau
  `provisoire`) : l'utilisateur doit pouvoir discuter un seuil sans lire la source.
- **Une sonde profonde ne coute rien au tick.** Un test fonctionnel qui charge un modele en VRAM
  (plusieurs Go) ne se declenche que si le modele est DEJA resident ; sinon la supervision force un
  chargement toutes les 15 min sur un GPU deja occupe.
- **Ne pas ajouter de dependance a l'interpreteur de la tache.** L'interpreteur d'une tache
  planifiee n'a pas forcement la bibliotheque de parsing (pas de PyYAML) : lire les quelques cles
  utiles avec un parseur cible, pas en installant un paquet dans l'environnement de production.

Modele d'etat, sondes par type de composant, gestion des identifiants de sonde et harnais de test
des 4 etats : `references/supervision-etats-normalises.md`.

## Commande « Manage » (bilan quotidien)

Quand l'utilisateur répond « Manage » au bilan quotidien (`update_checker.py`,
« 🔧 Bilan sécurité & mises à jour »), l'action attendue = appliquer les mises à
jour + remettre en route les services arrêtés :

1. `winget upgrade --all --silent --accept-package-agreements --accept-source-agreements --disable-interactivity` — via un `.ps1` ASCII pur lancé par `powershell -NoProfile -File` (sous git-bash, winget échoue avec « stdin is not a tty » ; et un `.ps1` avec accents sans BOM casse le parseur PowerShell 5.1 — ParserError).
2. Démarrer Ollama (`ollama serve`) et Docker Desktop (le manager Wazuh vit en conteneur : si Docker est arrêté, le check Wazuh renvoie « ? »). La pile Wazuh (`~/wazuh-docker/single-node`, projet `single-node-wazuh`) est en `restart: always` : elle remonte SEULE dès que le démon Docker est prêt (~10 s), donc `docker compose up -d` est inutile — un rapport qui attribue le retour à cette commande est faux. Trois conteneurs : `indexer` (9200), `dashboard` (8443), `manager` (55085 → 55000 dans le conteneur). Le compose porte DEUX couples d'identifiants, et les confondre fabrique une fausse panne : `INDEXER_*` sert l'indexer, `API_*` sert le manager — `POST /security/user/authenticate` sur 55085 rend `401` avec les identifiants indexer et `200` + JWT avec `API_*`. Une API qui répond `401` prouve que le service est DEBOUT. La section Wazuh d'ANIMA ne sonde que l'indexer (`https://127.0.0.1:9200/_cluster/health`, attendu `200`, `status: green`) : c'est cette route qu'il faut valider, puis relancer la sonde (`health_anima.py --resume`).
3. Relister `winget upgrade` (lecture seule) pour séparer les réussites des échecs (« fichiers utilisés » = app ouverte ; « élévation » = admin à l'écran).

Cas « fichiers utilisés » qui résiste à la fermeture de l'app (vu sur OBS) — escalade :

1. Énumérer les modules chargés depuis le répertoire cible : `Get-Process | ForEach-Object { $_.Modules } | Where-Object FileName -like '<dir>*'`. Un autre process peut charger une DLL de l'app — Chrome charge `obs-virtualcam-module64.dll` quand un onglet utilise la cam virtuelle OBS comme source caméra. Tuer ce process, puis `regsvr32 /u /s` sur les DLL virtualcam 32+64 (session élevée).
2. Confirmer qu'aucun verrou ne reste : `handle64.exe -accepteula -nobanner '<chemin>'` (SysInternals — `curl -sL https://download.sysinternals.com/files/Handle.zip` + unzip ; en session élevée il voit aussi les handles système). « No matching handles found » = aucun handle fichier, même au niveau système. Recouper par un test d'ouverture exclusive : `[System.IO.File]::Open($f, 'ReadWrite', 'None')` sur chaque fichier du dossier — s'ils ouvrent tous, rien n'est verrouillé (ce test est plus strict que l'installateur).
3. Si l'installateur échoue ENCORE sur un état totalement propre (dossier supprimé, registre nettoyé, aucun device/driver/CLSID résiduel), le verrou est au niveau session/noyau → **reboot**. Ne PAS désinstaller l'app pour « contourner » : une réinstall fraîche échoue à l'identique (code de sortie 6), et l'app est perdue en plus.

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
9. **`agent.conversation_loop: Context length exceeded` + `agent resource teardown exceeded 10.0s`
   sur un job cron = le job tourne en mode agent alors que son script fait déjà tout.** Le prompt de
   l'agent lui ordonne de ré-exécuter le script déjà lancé en pre-run : contexte agent gonflé jusqu'au
   plafond (128K pour `eco`) + double sonde (quota gratuit gaspillé). Corriger à la racine par
   `hermes cron edit <id> --no-agent` (le script EST le job, stdout livré direct), pas en filtrant la ligne
   — un job script-only ne lève jamais `conversation_loop`.
10. **`Fatal whatsapp adapter error (whatsapp_bridge_exited)` = le bridge Node
   (Baileys) crash en boucle.** Si l'utilisateur n'utilise pas WhatsApp,
   `WHATSAPP_ENABLED=false` dans le `.env` ne suffit pas toujours : le désactiver
   définitif est `hermes config set platforms.whatsapp.enabled false` (ce YAML est
   traité comme prioritaire — « it never beats an explicit YAML disable »), puis
   `hermes gateway restart`. Vérifier que le log ne re-tente plus
   `Reconnecting whatsapp`.

11. **« gateway TOUJOURS MORT » après relevage alors que le gateway tourne = le détecteur cherche un motif qui n'existe plus.** `check_gateways.ps1` décidait « vivant » sur `CommandLine -match 'gateway run'`, avec un repli cherchant le même motif. Depuis Hermes v0.21.5+ le gateway tourne sous `hermes.exe` (bundle PyInstaller, ou le wrapper du venv qui spawn un `python.exe` enfant) : **aucun** process ne porte plus `gateway run` dans sa ligne de commande, donc la détection rend « mort » à chaque tick et le repli échoue pour la même raison. Vérifier le process réel avec `tasklist.exe | findstr hermes.exe` (le `ps` de MSYS ne voit pas les process Windows natifs — un `ps aux | grep gateway` vide ne prouve rien). Corriger le DÉTECTEUR, jamais whitelister le pid : lire `pid` **et** `gateway_state` depuis `gateway_state.json`, déclarer vivant si le process de ce pid existe (`Get-Process -Id <pid>`) **et** que son nom est l'un de `hermes.exe`/`python.exe`/`pythonw.exe` **et** que `gateway_state -eq 'running'`. Corriger le `pid` du state ne suffit pas quand le test lui-même est faux — l'alerte revient au tick suivant. Confirmer par `check_gateways.ps1 -DryRun` → « OK pid=... vivant » + « aucune transition d'etat, pas d'alerte ». Un port en LISTENING n'est pas une preuve de santé du gateway (`netstat -ano | findstr :20128` appartient à OmniRoute).
