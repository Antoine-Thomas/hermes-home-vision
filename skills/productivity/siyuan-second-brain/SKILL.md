---
name: siyuan-second-brain
description: "Use when installing or wiring SiYuan for Hermes."
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - siyuan
  - knowledge-base
  - second-brain
  - pkm
  - windows-install
---

# SiYuan — second cerveau de Hermes

## Quand utiliser ce skill

- Installer, mettre a jour ou demarrer SiYuan, ou rebrancher Hermes dessus.
- Quand l'utilisateur parle de « second cerveau », de base de connaissances externe, de sortir du
  contexte ou de la memoire un savoir durable.
- L'USAGE de l'API (endpoints, SQL, creation de documents, blocs) est couvert par le skill installe
  `productivity/siyuan` — ce skill-ci couvre l'installation, l'exploitation et le cablage. Ne pas
  dupliquer la liste d'endpoints ici.

## Installer

```bash
winget show --id B3log.SiYuan --exact --versions          # versions reellement disponibles
winget install --id=B3log.SiYuan --exact --version <v> --accept-package-agreements --accept-source-agreements --disable-interactivity
```

Verifier que le port 6806 est libre AVANT (`netstat -ano | grep ":6806"`). Installation par
utilisateur (aucun UAC, ~750 Mo), binaire dans `%LOCALAPPDATA%\Programs\SiYuan\`, noyau dans
`resources\kernel\SiYuan-Kernel.exe`.

Choisir la version : verifier les notes de la derniere version du depot
(`api.github.com/repos/siyuan-note/siyuan/releases/tags/v<v>`) — une version plus recente n'est pas
forcement un correctif de securite, et l'utilisateur peut avoir epingle une version pour une raison
precise. Rester sur la version demandee quand elle est disponible, et signaler l'existence d'une
plus recente.

## Piege 0 — une barre oblique dans un titre cree une HIERARCHIE de documents

`createDocWithMd` traite le `path` comme un chemin : un titre contenant `/` devient une
arborescence. Constate le 15/09 : « Audit voix - corpus du 15/09/2026 » a cree **trois** documents
(« Audit voix - corpus du 15 » > « 09 » > « 2026 »), le contenu allant dans la feuille.

**Regle : refuser tout titre contenant une barre oblique.** Utiliser un tiret — « 15-09-2026 », pas
« 15/09/2026 ». `C:\Users\searc\SiYuan\publier.py` refuse desormais ces titres explicitement
(garde-fou ajoute le 15/09/2026) ; tout appel direct a l'API doit faire pareil.

**Second piege, dans la foulee :** supprimer le document **parent** d'une telle hierarchie supprime
ses enfants par cascade. C'est ainsi qu'un document de contenu a ete perdu en croyant supprimer une
enveloppe vide — il a fallu le republier depuis sa source.


## Bug connu — PANIC sur suppression de document imbrique (SiYuan 3.8.2)

**Symptome** : dans le journal du noyau,

```
removed children dir [...]
PANIC RECOVERED: interface conversion: interface {} is nil, not string
  siyuan/kernel/api/filetree.go:758
```

**Declencheur** : `removeDocByID` sur un document **parent**. L'API repond une erreur 500, mais
les fichiers sont **reellement supprimes**, enfants compris. Deux consequences : on croit avoir
supprime une enveloppe vide et on perd le contenu de l'enfant ; et l'erreur 500 fait croire a un
echec alors que l'operation a eu lieu.

**Contournement** (obligatoire) : **ne jamais** appeler `removeDocByID` sur un parent qui a des
enfants. Supprimer les enfants un par un, du plus profond au plus proche, puis le parent.
Le script `C:\Users\searc\SiYuan\supprimer_document_siyuan.py` applique cette regle
(`--simuler` pour voir le plan sans rien supprimer).

**Verifier apres coup** : l'erreur 500 ne dit pas si la suppression a eu lieu — requeter
`SELECT id FROM blocks WHERE hpath LIKE '<hpath>/%'` pour le savoir.

**Piege lie, sur le lancement** : le noyau ecrit `kernel.log` dans son **dossier de travail**.
Lance par le `.vbs` silencieux sans `shell.CurrentDirectory`, le journal partait ailleurs et
semblait ne plus etre ecrit (constate le 16/09).


## Piege 1 — dossier de config ABSENT : fenetre blanche, aucun noyau

```bash
mkdir -p "$USERPROFILE/.config/siyuan"      # AVANT le premier lancement
```

L'application Electron ecrit son journal dans `%USERPROFILE%\.config\siyuan\`. Sur une installation
neuve ce dossier n'existe pas : elle meurt en `ENOENT` sur `app.log`, n'affiche qu'une fenetre
blanche et ne demarre jamais son noyau (port 6806 ferme, workspace vide). Aucun message n'est visible
pour l'utilisateur : le diagnostic se fait en tuant le processus et en lisant sa sortie.

## Lancer le noyau

```bash
"<install>\resources\kernel\SiYuan-Kernel.exe" serve --workspace="C:\Users\<user>\SiYuan\<workspace>" --port=6806 --lang=fr_FR
```

- Le noyau initialise le workspace au premier demarrage (`conf/`, `data/`, bases) et sert AUSSI
  l'interface web sur le meme port — inutile de dependre de l'application graphique.
- Il n'ecoute que sur `127.0.0.1` (jamais `0.0.0.0`) : c'est deja l'etat sur.
- CLI complete disponible en secours de l'API : `notebook`, `document`, `search`, `sql`, `serve`,
  `workspace`, `export`, `repo` (voir `--help`). Pratique pour agir sans jq ni curl.
- Ne PAS passer le secret en ligne de commande : une fois le workspace initialise, le noyau relit
  `accessAuthCode` et `api.token` dans `conf.json`. Le redemarrage sans secret est aussi la
  VERIFICATION que la configuration est durable — la faire systematiquement.
- Pour un demarrage durable : un lanceur **`.vbs`** en mode cache, arme par une tache planifiee a
  l'ouverture de session. Un `.cmd` seul ne suffit pas a cacher la console : `start /min` minimise
  mais laisse la fenetre visible, et un `.vbs` qui se contente d'appeler ce `.cmd` ne cache que la
  console DU `.cmd` — celui-ci en cree une seconde pour le noyau. Mesure :
  `ConsoleWindowClass visible=True` dans les deux cas. Solution : lancer le noyau **directement**
  depuis le `.vbs` avec `sh.Run """<noyau>"" serve --workspace=... --port=6806", 0, False`
  (mode 0 = cache), et non `start /min`. Verifier par enumeration des fenetres du processus
  (`IsWindowVisible`), pas a l'oeil : `MainWindowHandle` non nul ne prouve pas la visibilite.
- **Fixer `sh.CurrentDirectory`** dans ce `.vbs` : le noyau ecrit `kernel.log` dans son dossier de
  travail. Sans cette ligne, le journal part ailleurs et semble ne plus etre ecrit du tout — on
  cherche alors une panne qui n'existe pas.
- Reprendre la forme de lancement deja utilisee par les autres services Hermes sur la machine
  (`%LOCALAPPDATA%\hermes\gateway-service\*.vbs` : `HERMES_HOME`, `VIRTUAL_ENV`, `PYTHONPATH`,
  `python.exe -m ...`) plutot que d'inventer un chemin de lanceur — `hermes.cmd` peut ne pas exister.
- Un enfant lance par une commande au premier plan est emporte quand l'appel se termine : le 
  verifier par `netstat` avant de croire que le service tourne.

## Piege 2 — DEUX secrets distincts, celui qui coute une heure

`conf.json` (dans le workspace) contient deux champs qui n'ont rien a voir :

| Champ | Role |
|---|---|
| `accessAuthCode` | ouvre l'INTERFACE web (le navigateur le demande) |
| `api.token` (section `api`) | authentifie les API — c'est LUI qui va dans `SIYUAN_TOKEN` |

Mettre l'`accessAuthCode` dans `SIYUAN_TOKEN` donne `Auth failed [header: Authorization]`, ce qui
ressemble a une autorisation mal activee alors que le code est simplement le mauvais. Ne pas
afficher ces valeurs : elles vivent dans le fichier, l'utilisateur peut choisir son code d'acces.

## Cabler Hermes

`.env` de Hermes — sur Windows `%LOCALAPPDATA%\hermes\.env`, PAS `~/.hermes` :

```
SIYUAN_TOKEN=<api.token de conf.json>
SIYUAN_URL=http://127.0.0.1:6806
```

- Sauvegarder le `.env` avant de le modifier, et verifier qu'aucune ligne `SIYUAN_` n'existe deja.
- Les variables ne sont chargees qu'au DEMARRAGE d'une session Hermes : dans la session courante,
  les exporter a la main pour tester (`export SIYUAN_TOKEN=$(grep '^SIYUAN_TOKEN=' ... | cut -d= -f2-)`).
- Prerequis du skill d'API : `jq` (`winget install --id=jqlang.jq --exact`). Sans lui, toutes les
  commandes du skill tournent mais ne rendent rien d'exploitable — et l'echec est silencieux.

## Installer le skill d'API

```bash
hermes skills install official/productivity/siyuan --yes
```

Sans `--yes`, la confirmation interactive annule l'installation (« Installation cancelled ») quand
la commande est lancee depuis un outil non interactif.

## Verifier — jamais supposer

```bash
netstat -ano | grep ":6806.*LISTENING"                       # le noyau ecoute
curl -s -X POST "$SIYUAN_URL/api/notebook/lsNotebooks" -H "Authorization: Token $SIYUAN_TOKEN" \
     -H "Content-Type: application/json" -d '{}'             # attendu : {"code":0,...}
curl -s -X POST "$SIYUAN_URL/api/query/sql" -H "Authorization: Token $SIYUAN_TOKEN" \
     -H "Content-Type: application/json" -d '{"stmt":"SELECT COUNT(*) AS n FROM blocks"}'
curl -s -o /dev/null -w "%{http_code}\n" "$SIYUAN_URL/"     # 401 = protection de l'interface active
```

Prouver l'authentification DANS LES DEUX SENS : mauvais jeton et absence de jeton doivent repondre
`Auth failed`. Un `code: 0` obtenu avec une protection inactive n'est pas une preuve de cablage.

- **L'index est ASYNCHRONE** : un document cree ou supprime n'apparait pas tout de suite dans
  `/api/query/sql`. Compter juste apres une ecriture rend un chiffre faux, et un re-import peut
  croire un document « deja present » alors qu'il vient d'etre supprime (il sera alors silencieusement
  saute). Attendre que l'index se rattrape avant de conclure, puis recompter.
- Ne pas trier par `created` pour distinguer deux documents crees dans la meme seconde : l'ordre est
  indetermine et renvoie deux fois le meme document. Relire par identifiant explicite.
- Un document se verifie par sa RELECTURE (`/api/block/getBlockKramdown`), pas par le `code: 0` de sa
  creation : controler l'en-tete et la presence des sections attendues.

### Il n'existe PAS de table `notebooks` (ni `boxes`) en SQL

Une requete du type `WHERE box=(SELECT id FROM notebooks WHERE name='<notebook>')` echoue avec
`no such table: notebooks` dans le journal du noyau, et son remplacement suppose
`SELECT id, name FROM boxes` echoue tout autant (`no such table: boxes`). SiYuan n'expose aucune
table de notebooks.

- Les documents sont des lignes de `blocks` avec `type='d'` ; la colonne `box` n'est qu'un
  identifiant de notebook, sans nom.
- Les NOMS viennent de l'API : `/api/notebook/lsNotebooks` rend `id` + `name`. Construire la table de
  correspondance cote script, puis grouper par `box`.
- Requete qui marche pour inventorier : `SELECT box, content FROM blocks WHERE type='d' ORDER BY hpath`
  puis mapper `box` -> nom. Compter par notebook et comparer au nombre attendu : c'est le controle
  qui detecte une creation parasite (hierarchie accidentelle, doublon).
- Une erreur SQL doit AFFICHER le message du noyau : un script qui n'imprime que le code de retour
  laisse passer ces echecs sans rien dire, et on construit ensuite sur du faux.

## A quoi ca sert : memoire d'Hermes vs SiYuan

La memoire permanente est relue a CHAQUE session : n'y garder que des faits courts et transverses.
SiYuan porte le detail long (inventaire de sites, pieges par skill, parametres de pipeline mesures)
qu'Hermes va chercher a la demande par SQL ou recherche plein texte. Regle de partage : si
l'information n'est utile qu'a un projet, elle va dans SiYuan, pas dans la memoire.

Convention de documents qui reste exploitable : un notebook par domaine, un document par sujet, en
tete une ligne *statut* et une ligne *derniere mise a jour*, puis Fait / Reste a faire / Pieges /
Commandes. Les attributs personnalises (`custom-statut`, `custom-projet`) permettent de filtrer en
SQL au lieu de tout relire — ce qui est precisement ce qui economise les tokens.

## Modifier conf.json — arreter le noyau D'ABORD

```bash
# 1) sauvegarder le fichier, 2) editer, 3) redemarrer le noyau
cp conf.json conf.json.bak.$(date +%Y%m%d_%H%M%S)
python - <<'EOF'
import io, re
p = r"...\hermes-projects\conf\conf.json"
t = io.open(p, encoding="utf-8").read()
io.open(p, "w", encoding="utf-8", newline="").write(
    re.sub(r'("accessAuthCode"\s*:\s*")[^"]*(")', r'\1<nouveau>\2', t))
EOF
```

Le noyau reecrit `conf.json` en s'arretant : editer le fichier pendant qu'il tourne fait perdre la
modification. Substituer le SEUL champ vise au lieu de re-serialiser le JSON, puis verifier que
l'autre secret (`api.token`) est intact.

Preuve d'un changement de code d'acces, dans les deux sens : `/api/system/loginAuth` avec
`{"authCode":"<nouveau>"}` doit rendre `code 0`, un ancien code doit etre refuse avec un message
explicite, et `GET /` doit repondre 401 sans session.

## Demarrage automatique a l'ouverture de session

Tache planifiee UTILISATEUR (pas systeme, aucun privilege eleve) :

```powershell
$action   = New-ScheduledTaskAction -Execute "C:\...\demarrer_siyuan.cmd"
$trigger  = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
              -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "SiYuan - noyau second cerveau" -Action $action `
              -Trigger $trigger -Settings $settings -Force
```

- Sans `-ExecutionTimeLimit ([TimeSpan]::Zero)`, le planificateur arrete le noyau au bout de
  quelques jours — panne silencieuse et difficile a relier a la tache.
- `MultipleInstances IgnoreNew` double la protection du script, qui sort deja si le port est pris.
- VERIFIER en declenchant pour de vrai (`Start-ScheduledTask -TaskName ...`) puis `netstat` : une
  tache a l'etat « Ready » n'est pas une tache qui fonctionne.

## Remplir la base sans polluer

- Tout document qui decrit l'existant (sites, versions, mesures) se remplit avec des donnees LUES :
  fichiers de configuration, fichiers d'extension, dumps. Jamais de valeur supposee — et signaler la
  provenance quand elle est indirecte (« etat deduit du dump, pas d'une instance en cours »).
- Un document par skill = extrait VERBATIM de son `SKILL.md` (role, version, pieges, commandes) ; le
  fichier du skill reste la reference, le document n'est qu'une entree consultable.
- Ne pas dupliquer ce qui existe deja : quand une note couvre deja un sujet, le nouveau document ne
  garde que le COMPLEMENT et renvoie a la note d'origine.
- Un notebook vide ne se cree pas tout seul : le creer explicitement, sinon il manque a l'appel.
- Scripts d'import a rejouer : lire le jeton dans le `.env`, ignorer ce qui existe deja (aucun
  doublon), et offrir une option de remplacement explicite.
- Quand la ressource decrite DISPARAIT (site supprime, service retire, dossier efface), les fiches
  deviennent fausses et coutent plus qu'elles ne rapportent : les consolider en UN document
  d'historique qui garde ce qui servira a recreer (versions, listes, chemins), puis supprimer les
  fiches individuelles. Verifier l'etat reel avant d'agir (fichier de configuration vide, dossier
  absent), et prevenir l'utilisateur de ce qui a ete remplace.
- Un livrable se publie a DEUX endroits, pas a l'un ou l'autre : le fichier dans le depot de
  l'utilisateur (source, versionnee, commitee) et un document SiYuan qui porte l'en-tete de
  convention, une synthese Fait / Reste a faire / Pieges / Commandes, puis le corps complet du
  rapport. La synthese sert au quotidien, le corps evite d'avoir a ouvrir le fichier.
- **Ecrire la conclusion dans les mots de la question.** Un document qui decrit un sujet sans jamais
  enoncer le verdict (« la cause est X, le correctif est Y ») ne sera pas retrouve par une question
  explicative, meme bien posee : la recherche remonte ce qui PARLE du sujet avant ce qui le tranche.
  Une ligne de conclusion explicite vaut mieux qu'un long paragraphe de contexte.
- **Ne jamais laisser une question en clair dans un document indexe** (compte rendu de test, journal) :
  elle contient litteralement les mots de la requete et passe devant le document qui repond.

## Inserer dans une SECTION existante — le piege de l'ordre des blocs

Ajouter une puce « en fin de section Pieges » ne se fait pas avec un tri SQL.

- `SELECT id, type, content FROM blocks WHERE root_id='...' ORDER BY sort` **ne rend PAS l'ordre du
  document** : `sort` est relatif au parent. La puce part alors dans une autre section (ici sous
  « Reste a faire ») et le document perd son sens, meme si l'API repond `code: 0`.
- Source de verite de l'ordre : **`/api/block/getChildBlocks`** (enfants ordonnes). Parcourir les
  enfants du document, reperer le titre vise, avancer jusqu'au titre suivant, prendre le DERNIER
  element de la section, puis `insertBlock` avec `previousID` = ce bloc.
- Pour deplacer un bloc mal place : `deleteBlock` puis reinserer au bon ancrage — ne pas empiler un
  second bloc « correctif ».
- **Verifier par relecture du kramdown** (`getBlockKramdown`) : la puce doit apparaitre dans la
  section visee ET a la bonne position. `code: 0` ne prouve rien sur le placement.
- **Toute modification d'un document se suit d'une reconstruction de l'index RAG** (skill
  `rag-second-cerveau`) : sinon la recherche continue de servir l'ancienne version. Cette
  reconstruction est COMPLETE (quelques minutes), pas incrementale.

## Ne rien faire sans accord explicite

- **Un accord donne dans la conversation ne suffit pas a l'outil.** Le garde-fou peut refuser une
  suppression (fichiers, documents) meme autorisee par l'utilisateur : dans ce cas, le dire, laisser
  l'action en attente et continuer sur le reste du travail — **jamais** la reprendre, la reformuler
  ou l'obtenir par un autre chemin (`--force`, un script equivalent, un appel direct a l'API).
  « Silence n'est pas consentement » vaut aussi pour la suite : ne pas reboucler sur l'action.
- Creer des notebooks : proposer une structure, la faire valider d'abord.
- Synchronisation S3/WebDAV ou cloud : attendre une demande.
- `config.yaml` de Hermes : le serveur MCP optionnel que mentionne le skill d'API exige de le
  modifier, donc le faire valider avant.
