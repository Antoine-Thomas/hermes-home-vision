# Triage « encore utile ou vestige » — service local (proxy, sidecar, port dédié)

## Quand appliquer

Un port local dédié n'écoute plus alors qu'un launcher et une tâche planifiée existent encore.
Trois issues possibles : **relancer et durcir**, **retirer proprement des deux côtés**, ou
**statu quo documenté**. La question à trancher n'est pas « le process tourne-t-il ? » mais
« un consommateur actif en dépend-il encore ? ».

**Ne jamais conclure « vestige » depuis un grep de config.** Un proxy local n'est pas déclaré dans
`config.yaml` : c'est le routeur en aval qui détient son URL. Une absence dans `config.yaml`, `.env`
et `scripts/` ne prouve rien — elle prouve seulement qu'on a cherché au mauvais endroit.

## Procédure

1. **Écoute réelle** : `netstat -ano | grep -a ':<port>'`. Vide = le service est mort. Un
   `curl` de contrôle (`/health`) confirme.
2. **Identifier le consommateur, pas le producteur.** Pour un port local du parc, le consommateur
   est le routeur LLM (OmniRoute), pas Hermes.
3. **Interroger la base du consommateur** : `~/.omniroute/storage.sqlite` — attention, **le dossier
   de données OmniRoute est `~/.omniroute`, pas sous `AppData`**. Passe rapide par recherche
   d'octets, qui donne l'emplacement avant toute requête :
   ```bash
   grep -a -o -b '.\{0,80\}<port>.\{0,80\}' ~/.omniroute/storage.sqlite | head
   ```
   Puis lecture SQLite propre, toujours **en lecture seule** :
   ```python
   sqlite3.connect('file:C:/Users/<user>/.omniroute/storage.sqlite?mode=ro', uri=True)
   ```
   Tables utiles : `provider_connections` (colonne `provider_specific_data` → `baseUrl`, plus
   `is_active`, `test_status`, `last_tested`) ; `combos` (colonne `data` = JSON avec
   `models[].providerId`) ; `call_logs` et `proxy_logs` (`timestamp` + texte d'erreur).
4. **Dater la panne par les échecs du consommateur** : chercher les lignes contenant
   `ECONNREFUSED <host>:<port>` dans `call_logs` / `proxy_logs` et compter par jour
   (`substr(CAST(timestamp AS TEXT),1,10)`). Un échec daté d'après le dernier redémarrage du
   routeur prouve que le consommateur sollicite **encore** le service mort.
5. **Verdict** : connexion provider `is_active=1` dont un combo référence les modèles ⇒ **encore
   utile** (mais vérifier si le modèle par défaut passe par ce combo : un proxy peut être actif et
   hors du chemin par défaut). Aucun consommateur identifié ⇒ vestige.
6. **Traçabilité de la décision** : ne rien modifier dans une passe de diagnostic. Livrer des
   options numérotées (relancer et durcir / retirer proprement / statu quo) avec une recommandation
   et attendre la décision opérateur.

## Après relance : prouver la chaîne, pas le maillon

- **`LISTENING` ne veut pas dire « qui répond ».** Deux pannes distinctes à ne pas confondre :
  - *mort* — aucun listener, `ECONNREFUSED` côté consommateur ;
  - *bloqué* — process vivant, port `LISTENING`, plus aucune réponse. Signes : `curl -sv` affiche
    `Established connection` puis `0 bytes received` ; la connexion traîne en `CLOSING` ; le CPU du
    process ne bouge plus. Cause typique : un **serveur mono-thread** (`http.server.HTTPServer`)
    immobilisé sur un appel amont dont le client s'est déjà déconnecté (deadline locale du routeur).
    Il se débloque seul à la fin de l'appel amont : un `/health` muet qui répond 30 s plus tard n'est
    donc pas une intermittence.
  - Conséquence directe : **un launcher idempotent (« si le port écoute, sortir ») ne répare que le
    mort, jamais le bloqué.** Constater `LISTENING` après relance ne prouve pas la remise en service.
- **Vérifier la chaîne complète, jamais le maillon qu'on vient de relancer.** Un `200` en direct sur
  le service ne prouve pas que le consommateur sait l'utiliser : c'est l'appel *à travers le routeur*
  qui tranche.
- **Le routeur résout le provider par le PRÉFIXE DU NOM DE MODÈLE, pas par le `providerId` du combo.**
  Un combo qui déclare `"nvidia/<modele>"` avec `providerId: "openai"` part vers un provider `nvidia`
  sans credentials (`401 No active credentials for provider: nvidia`), alors que le même modèle appelé
  `openai/nvidia/<modele>` répond `200`. Correctif = préfixer les entrées du combo dans la forme que le
  proxy documente dans son en-tête ; ne pas toucher au proxy.
- **Faire chauffer avant d'accuser.** Les modèles « reasoning » répondent en 9-12 s au premier appel et
  en moins de 2 s ensuite ; une deadline locale du routeur plus courte
  (`resilienceSettings.requestQueue.maxWaitMs`) fabrique des `504` qui ressemblent à une panne du
  service. Rejouer l'appel avant de conclure.
- **Clore la vérification par le compteur d'échecs** : rejouer la requête SQL sur la fenêtre
  *postérieure* à l'heure de relance (`… AND timestamp > '<ISO de relance>'`). Le seul verdict
  acceptable est **0 nouvelle occurrence**.

## Durcir le launcher (option « relancer et durcir »)

- **Le test d'idempotence doit porter sur `LISTENING`, jamais sur la simple présence du port.**
  `netstat -an | findstr ":<port> "` matche aussi les sockets clientes restées en `TIME_WAIT` après
  l'arrêt du service : le launcher conclut « déjà lancé » et sort en **no-op alors que rien n'écoute**.
  Symptôme trompeur : une relance qui ne relance rien, sans le moindre message, et un code retour `0`.
  Ajouter un second filtre (`... | findstr "LISTENING"`) — le no-op doit signifier « un service
  écoute », pas « une connexion a existé ».
- **Relancer par la tâche planifiée, pas depuis le shell de l'agent.** `Start-ScheduledTask` /
  `schtasks /Run` démarre hors du Job Object du shell. Un lanceur (VBS, `wscript`) invoqué depuis une
  session d'agent voit son processus tué à la fin de l'appel : le service démarre puis disparaît, ce
  qui se lit à tort comme « le lanceur est cassé ». Faire passer la relance par la tâche est à la fois
  la preuve de la chaîne complète (tâche → launcher → service) et la seule façon que le service
  survive à l'appel.
- **Rediriger la sortie d'un sidecar change son ENCODAGE, pas seulement sa destination.** Un `stdout`
  qui n'est plus une console fait tomber Python sur l'encodage de la locale (cp1252 sous Windows) au
  lieu de l'UTF-8 console : toute ligne de log contenant un caractère non-ASCII lève
  `UnicodeEncodeError` **dans le gestionnaire de requête**, donc l'appel meurt — le service est vivant
  mais ne sert plus rien. Poser `PYTHONIOENCODING=utf-8` dans l'environnement de l'enfant (le motif
  déjà utilisé par les VBS du parc) **avant** de brancher la redirection. Ajouter `python -u` : sans
  non-bufferisé, les lignes de démarrage restent dans le tampon et un log vide se lit à tort comme un
  process muet.
- **Prouver la ligne de log, pas le fichier.** Après branchement, envoyer une requête et vérifier que
  sa ligne de trace apparaît (ex. `[PROXY] <modele> → <modele>`, la flèche U+2192 étant précisément le
  caractère qui casse en cp1252). Fichier créé mais vide ⇒ buffering ; ligne absente et requête
  perdue ⇒ encodage.

## Règles et pièges

- **Retrait des deux côtés ou pas du tout** : désactiver le launcher sans désactiver la connexion
  provider (et son combo) laisse une connexion « active » condamnée qui échoue en silence ;
  l'inverse laisse un port ouvert sans usage. Toute action de retrait touche le routeur **et** la
  machine.
- **Désactivation explicite, jamais de suppression silencieuse** : tâche planifiée → `Disable-`
  (état traçable), pas `Unregister-`.
- **Un combo HS est invisible depuis Hermes** : l'échec est consommé par le routeur, aucune erreur
  ne remonte dans la session. Ne pas conclure « ce modèle marche » parce qu'il apparaît dans le
  catalogue du routeur.
- **L'API HTTP d'OmniRoute exige une authentification** (`AUTH_001` / `invalid_api_key` sur
  `/v1/models`, `/api/providers`, `/api/status`). La clé est `OMNIROUTE_API_KEY` dans le `.env`
  Hermes : l'extraire dans une variable shell et ne jamais l'afficher.
- Le routeur tourne sous node (`.../npm/node_modules/omniroute/dist/server-ws.mjs`) et est relancé
  par sa propre tâche : son `CreationDate` est le repère pour savoir si un échec est antérieur ou
  postérieur à un redémarrage.
