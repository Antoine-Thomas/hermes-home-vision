---
name: disk-space-reclamation
description: "Use when auditing disk space or reclaiming GB."
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [disk, cleanup, audit, deletion, storage, cache, windows]
    category: devops
---

# Disk Space Reclamation

## When to use

- L'utilisateur demande un audit disque, une liste de cibles "supprimables", ou la recuperation de N Go.
- Toute tache ou l'on propose de SUPPRIMER des donnees sur le disque de l'utilisateur : caches, sauvegardes,
snapshots, venvs retires, archives d'installation.

## Regle 0 — deux phases, jamais une seule

Phase A = lecture seule : mesures + verdict + rapport. Phase B = suppression, seulement apres validation
EXPLICITE de l'utilisateur, dans l'ordre de risque.

- Ne jamais supprimer dans la meme reponse que la mesure. Un audit qui se termine sans validation se
termine par "aucune suppression effectuee" — et c'est un resultat valide.
- Respecter les zones exclues nommees par l'utilisateur (pending/, memories/, une quarantaine deja
comptee ailleurs) et le redire dans le rapport, sinon l'utilisateur ne peut pas savoir si l'exclusion a
ete honoree.
- Ne jamais supprimer un artefact de rollback (sauvegarde de profil, snapshot pre-update, venv retire)
dans la meme phase que des caches : ce sont deux risques differents, ils se valident separement.
- Decouper par NIVEAU DE RISQUE, pas par taille : une phase "cibles sures" et une phase "cibles qui
touchent un service actif" (SIEM, RAG, moteur d'inference, base de donnees) ne se valident pas ensemble.
Chaque phase s'ouvre par sa propre passe lecture seule — pour les cibles sensibles, cette passe sert a
IDENTIFIER la dependance avant de decider quoi que ce soit.

## Procedure

1. **Inventaire lecture seule.** Mesurer chaque cible : taille exacte, mtime, nature reelle (fichier /
dossier). Verifier l'existence AVANT de mesurer : un chemin d'audit peut ne pas exister, ou designer
autre chose que ce que son libelle annonce.
2. **Statuer par categorie, pas par nom de dossier.** Un dossier nomme `cache`, `backup` ou `tmp` n'est
ni jetable ni regenerable du seul fait de son nom. Grille de decision :
`references/target-verdicts.md`.
3. **Tableau de verdicts**, une ligne par cible : `chemin | taille mesuree | mtime | verdict`.
Verdicts : SUR / A VERIFIER / A GARDER. Annoncer la convention de taille utilisee
(taille logique = somme des octets des fichiers, 1 Go = 10^9).
4. **Liste "a supprimer" triee par taille decroissante**, puis total recuperable. Donner aussi le total
laisse en "a verifier" : c'est ce qui cadre la phase B.
5. **Signaler les ecarts.** Toute difference entre les chiffres/chemins annonces par l'audit d'origine et
la mesure est ecrite dans le rapport, jamais corrigee en silence : taille qui double, chemin qui n'est pas
le bon, "fichier" qui est un dossier, nom reel different. Mettre ces ecarts dans une section "anomalies"
separee, numerotee.
6. **Attendre la validation**, puis supprimer dans l'ordre decroissant de taille et remesurer l'espace
libre **en octets** (pas `df -h`, qui arrondit au GiB) pour rendre l'ecart entre annonce et gain reel —
cf. « Mesurer le gain REEL » : une somme de tailles logiques n'est pas un gain d'espace.

## Mesurer une arborescence volumineuse

`du -sb` / `du -sm` (busybox/MSYS) est trop lent des que les cibles se comptent en Go : une passe sur 18
cibles (dont une de 17,6 Go et une de 68 Go) n'a pas rendu la main en 420 s. Ne pas relancer avec un
timeout plus grand — changer de methode : une enumeration .NET boucle sur les fichiers au lieu de
parcourir les inodes cote shell, et rend la meme mesure en minutes.

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/<user>/.../scripts/measure-targets.ps1 -List C:/chemin/cibles.txt
```

Le script rend un TSV `kind | bytes | mtime | path` trie par taille decroissante (kind = FILE | DIR |
MISSING), ce qui donne directement le tableau du rapport. Garder `du -sh` pour un petit dossier et
`df -h` pour l'espace libre : eux restent rapides.

- **Mtime d'un dossier** = derniere modification de son repertoire (ajout/retrait d'entree), pas le max
des enfants. C'est un signal d'ACTIVITE, a confirmer en regardant le mtime des sous-dossiers avant d'en
conclure qu'une cible est morte.
- **Toujours sortir une ligne MISSING / retypee** pour une cible introuvable ou d'une autre nature, au
lieu de sauter la ligne : une cible absente du rapport passe pour inexistante. **Piege : c'est le
constructeur de liste qui tue la ligne MISSING.** La boucle canonique
`for d in <base>/* ; do [ -e "$d" ] && echo "$d" >> "$L" ; done` ecarte les chemins absents AVANT que
le script ne les voie : le garde `[ -e ]` rend la ligne MISSING **structurellement impossible**, et une
cible disparue n'apparait nulle part — ni mesuree, ni manquante. Ne pas mettre le filtre d'existence
dans le constructeur : ecrire tous les chemins sans condition (le script les marque MISSING), ou
verifier l'existence dans une passe separee et lister explicitement les absents dans le rapport.
  Corollaire : les fichiers de travail de l'audit lui-meme (TSV, CSV, listes de cibles) vivent dans
  `cache/scratch` et **comptent dans la cible mesuree** — un dossier de cache parait gros parce qu'il
  contient le travail d'audit, pas parce qu'il est plein. Le dire plutot que de le proposer a la
  suppression.
- Ne pas lancer une lecture de contenu sur un fichier de nature inconnue : `read_file` sur un `.exe`
deverse des pages d'octets illisibles et pollue la session. Etablir d'abord le type (extension, `file`,
`stat -c %s`) et ne garder `read_file` que pour un fichier texte.
- "Les 5 premieres lignes" ne s'appliquent qu'a un fichier TEXTE. Quand aucune cible n'est un fichier
texte (archives ZIP/7z, dossiers), le dire explicitement plutot que d'omettre la demande.

## Inventaire : faux negatifs et faux comptages

Une mesure fausse a l'inventaire produit une liste de suppression fausse. Trois pieges :

- **Deux racines imbriquees comptent double.** `%LOCALAPPDATA%` est DANS `%USERPROFILE%`
  (`C:\Users\<user>\AppData\Local`) : `find "$LOCALAPPDATA" "$HOME" -name <fichier>` rend chaque fichier
  deux fois. Mesure : « 5 copies » annoncees, 3 reelles. Passer UNE racine, ou dedupliquer les racines
  avant d'enumerer.
- **Une variable peut etre vide d'une commande a l'autre.** `grep -rli <motif> "$LA/..."` avec `$LA` non
  defini cherche dans `/...` et rend ZERO resultat — ce qui se lit comme « aucun consommateur », donc comme
  un feu vert a la suppression. Utiliser `$LOCALAPPDATA` / `$HOME` inline, ou re-affecter la variable dans
  la MEME commande, et traiter tout resultat vide sur un chemin construit comme suspect : relancer.
- **Un timeout n'est pas une absence.** Un `grep -r` sur un arbre enorme (packs venv / site-packages,
  130 Go) n'aboutit pas. Borner au sous-arbre utile (skill, scripts, config) et ecrire dans le rapport que
  la recherche est INCOMPLETE, au lieu de conclure « rien ne le consomme ».

## Ce qui rend une cible NON sure

Ces six controles, passes sur chaque cible "regenerable", ont chacun retourne une cible en "a verifier"
sur une meme session :

1. **Elle est encore ecrite.** Un mtime du jour sur le dossier ou sur un sous-dossier = magasin ACTIF,
pas un residu (un magasin de blobs de sauvegarde du curateur, 1556 fichiers, ecrit le jour meme).
Chercher la date avant de declarer "ancien".
2. **Un composant vivant la lit.** Chercher le nom du modele / le chemin du cache dans les scripts
actifs avant de conclure "regenerable" :
`grep -rn -i -E "<nom-modele>|SentenceTransformer|<chemin-cache>" --include='*.py' --include='*.json'
<nom-de-dossier>/` — **jamais un `grep -r` lance depuis la racine du profil** : il avale
`skills/.hub/index-cache/hermes-index.json` (~29 Mo, une seule commande a rendu 29 M de caracteres puis
expire) et les arbres `*venv*`/`site-packages`/`node_modules` ; preferer `search_files` avec `file_glob`,
qui reste borne — et lire le manifeste d'index. Un cache qui contient un modele charge par un service en marche n'est pas un cache,
c'est une DEPENDANCE (le cache de modeles portait le modele d'embedding du RAG local, sans lequel
l'index ne se recharge pas). Le consommateur peut etre HORS du depot du service : pour un service branche
sur une stack voisine (une IA, un moteur d'inference), la reponse est dans le config de la STACK — un
`config.json` portant un bloc `ollama` avec `api_url` / `model` / `model_deep` — pas dans le depot du
service lui-meme. Un `grep -i` sur le depot du SIEM ne trouve rien et fait conclure a tort "aucune IA
connectee" : nommer le modele exact ET le protocole (API native `/api/generate` sur 11434, pas
`/v1/chat`), et citer le fichier qui l'atteste.
3. **Une doctrine de retention la protege.** Lire les docs du profil avant de toucher un artefact de
rollback : un venv retire peut avoir une date de suppression prevue (`grep -n -i -E "retention|retired"
docs/*.md`). Supprimer avant la date contredit une decision documentee.
4. **Son contenu n'est pas versionne.** `git check-ignore -v <cible>` puis `git ls-files <cible> | wc -l`.
Un dossier ignore ET non suivi (donnees metier, `.env`) rend une sauvegarde "redundante" la SEULE copie
existante hors du profil.
5. **Une sauvegarde n'est "remplacee" que si la plus recente est complete.** Verifier la presence des
sous-arbres attendus (memories/, skills/, data/, state.db) : une sauvegarde voisine plus recente peut
etre VIDE (0 Mo) — un echec de sauvegarde, pas un remplacement. Un dossier partiel contient une copie de
donnees gitignores : ce n'est pas un doublon.
6. **Le cout de regeneration n'est pas le prix du telechargement.** Un artefact produit par un run long
non reproductible en une commande (export/conversion de poids, index) se garde meme s'il est
techniquement regenerable.

7. **Un remplacement annonce n'est pas un remplacement verifie — et une migration d'API n'est pas un
changement de configuration.** Un consommateur ecrit contre l'API NATIVE de son runtime (corps `prompt`,
endpoint `/api/generate`, reponse lue dans `response`) ne se repointe PAS vers un routeur compatible OpenAI
avec une URL et un nom de modele : c'est une reecriture du code d'appel du service. Quand une suppression de
modeles locaux est justifiee par « on bascule sur autre chose », exiger que la bascule soit d'abord validee
par des appels reels et garder les modeles locaux comme repli : sinon on supprime le seul chemin qui
fonctionne, sur la foi d'un plan qui ne peut pas marcher tel quel. Corollaire de mesure : l'absence de trace
d'usage n'est pas une preuve de non-usage — pour un runtime de modeles local, le mtime d'un poids est sa date
de telechargement et le log du serveur tourne. Le dire comme une LIMITE de la mesure et decider avec
l'utilisateur, jamais conclure « jamais appele » depuis un log vide.

Et un controle de propriete : avant de proposer la suppression du dossier de travail d'un skill, verifier
si ce skill est actif dans `config.yaml` (liste `skills.disabled`) — s'il est actif, la cible n'est pas
sure, quelle que soit sa taille.

## Mesurer le gain REEL, pas la taille logique

Une somme de tailles de fichiers n'est PAS un gain d'espace. Deux mecanismes font que des octets
"supprimes" ne reviennent jamais au volume :

- **Hardlinks / reflinks.** Une entree de cache partagee avec les environnements qui l'ont consommee
n'occupe le disque qu'une fois : supprimer le cache retire UN lien, pas les blocs, tant qu'un autre lien
vit. Mesure : `uv cache clean` a supprime 16,75 GiB logiques et rendu **~6,5 GiB** ; preuve du partage
par `fsutil hardlink list <fichier>` — le meme `torch_cuda.dll` de 1 176 Mo portait **trois** liens
vivants (`hermes-agent/venv`, `liveportrait/venv`, `wav2lip/venv`).
- **Doublon apparent.** Avant d'annoncer « N Go recuperables » sur une cible presente en plusieurs
copies, prouver que ce sont des allocations distinctes : `fsutil hardlink list <fichier>` ne doit rendre
QUE le fichier lui-meme, et `stat -c '%i %h'` doit donner des inodes differents avec un link count de 1.
Deux chemins au contenu identique (md5 egal) peuvent partager les blocs : la suppression ne rend alors RIEN.
- **Corbeille.** Un fichier "supprime" par l'Explorateur occupe encore sa taille (cf. plus bas).

Donc, pour chaque lot : lire l'espace libre **en octets exacts** avant/apres
(`Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"` -> `FreeSpace` ; `df -h` arrondit au GiB et
peut ne pas bouger pour 1 Go rendu), puis **reconcilier** :
`somme des cibles autonomes + part reellement liberee des caches partages - octets partis en corbeille`.
Un ecart qui ne se referme pas se nomme dans les anomalies — il ne s'arrondit pas.

A prevoir des l'audit : un profil dont la taille logique depasse nettement l'occupation reelle ne rendra
jamais ce delta. Sondes de reconciliation (hardlinks, corbeille, espace libre exact, consommateurs
concurrents a ecarter) : `references/space-accounting.md`.

## Une sonde n'est pas neutre

Un audit lecture seule change quand meme l'etat du systeme. Lancer la CLI d'un service pour l'inventorier
n'est pas une lecture : `ollama list` a demarre un serveur volontairement arrete ET declenche son
auto-mise a jour (0.34.1 -> 0.34.4, ~280 Mo consommes, port 11434 en LISTENING ensuite).

- Preferer les sources PASSIVES : fichier de config, logs, `netstat -ano | grep <port>`, `Get-Service`,
  tailles de dossiers, `fsutil hardlink list`.
- Si une CLI doit etre invoquee et qu'elle modifie l'etat (demarrage de service, telechargement, mise a
  jour), l'ecrire dans les anomalies ET proposer de le defaire — ne pas le defaire en silence : le mandat
  "lecture seule" interdit l'initiative, pas le signalement.

## Suppression (phase B)

- Ordre : plus grosse cible d'abord. Le gain se mesure tot et une erreur coute moins cher sur un cache que
sur une sauvegarde.
- **Un cache outillage n'a pas toujours de selecteur de sous-famille.** `uv cache clean` prend des noms
de PAQUETS, pas des sous-dossiers de cache (`uv cache clean --help` : `[PACKAGE]...`) : `uv cache clean
archive-v0` ne cible rien. Sans argument il vide **tout** le cache d'un coup — mesure : 219 201 fichiers
et 16,8 GiB logiques toutes familles confondues (`archive-v0` 16,7 + `sdists-*`/`simple-*`/`git-v0`).
Pour se limiter a une sous-famille, supprimer le dossier. Preferer l'outil officiel quand l'utilisateur
le demande, mais **nommer l'ecart de perimetre** dans le rapport (+0,4 Go au-dela de la cible ici).
- Apres chaque lot : lire l'espace libre **en octets** (`FreeSpace` du volume, cf. « Mesurer le gain
REEL ») et comparer au total annonce. Un gain different de la somme mesuree est un ecart a expliquer,
pas a arrondir.
- **Un fichier disparu n'est pas un fichier supprime : verifier la corbeille.** L'Explorateur deplace et
renomme (`$R<code>.<ext>`, metadonnees `$I*`) avant de le ranger dans `C:\$Recycle.Bin\<SID>\` : une
recherche par le nom d'origine ne trouve RIEN et fait conclure a tort « deja supprime » alors que les
octets sont toujours occupes. Proposer de vider la corbeille — c'est une action de l'utilisateur, pas
une initiative d'agent.
- **Re-mesurer le chemin EXACT qui va etre supprime, pas le sous-chemin chiffre a l'audit.** Un audit qui
a mesure `X/models` suivi d'une phase B qui supprime `X` rend plus que l'annonce, et l'ecart n'est plus
explicable une fois les octets partis : mesure `X/localai/models` 19,02 Go contre `X/localai` 20,99 Go
supprime = 1,97 Go sans explication. Chiffrer la cible telle qu'elle sera supprimee, et si un ecart
apparait quand meme, enumerer les enfants du dossier AVANT de le supprimer pour pouvoir nommer les
octets en trop.
- **Ordonner les retraits AVANT l'arret du service quand les deux figurent dans le meme lot.** `ollama rm`
exige le serveur vivant, et le CLI `ollama` RELANCE le serveur — et son auto-update — s'il est arrete :
executer une consigne « arreter le service, puis retirer les modeles » annule l'arret. Faire les retraits
d'abord, l'arret en dernier, et signaler la permutation dans le rapport quand la consigne donnait
l'ordre inverse.

## Rapport — pieges

- Ecrire la taille MESUREE, pas la taille annoncee : sur une meme session les chiffres d'audit differaient
des mesures d'un facteur 2,5 a 6. Un tableau qui recopie l'inventaire d'origine propage l'erreur.
- **La premisse de l'utilisateur se mesure comme le reste.** Quand un cadrage designe un responsable
  (« ~200 Go occupes par tel outil »), mesurer son ou ses dossiers reels AVANT de batir le rapport
dessus : un outil peut n'etre qu'un **squelette** (un depot de modele jamais telecharge pese quelques
dizaines d'octets, un paquet pip vit hors de l'interpreteur de la session). Annoncer le chiffre mesure
et rediriger vers ce qui occupe reellement le disque : citer « X Go » sur la foi d'un nom, c'est
inventer un chiffre — et l'ecart peut se compter en ordres de grandeur, pas en pourcentage.
- **Un affichage tronque n'est pas une mesure.** `ls -la <dossier> | head -4` coupe le listing apres
  `.gitignore` : un dossier de 866 Mo se lit alors comme vide. Quand une observation contredit une
  mesure deja faite, suspecter l'OBSERVATION (troncature, `head`, glob sans `-a`) avant de corriger le
  chiffre — et recontroler par le compteur d'octets, jamais par une ligne de listing. Le dire si
  l'ecart a ete vu par l'utilisateur : c'est le rapport qui a semble faux, pas la mesure.
- Une cible vide (0 Mo) et une sauvegarde partielle sont deux ANOMALIES a signaler, pas a taire.
- Un artefact durable range dans un dossier temporaire elague automatiquement (cache/scratch) est un
risque de perte silencieuse, pas un fichier a supprimer : le dire et proposer l'emplacement durable.
- Ne pas conclure "redundant" depuis un nom de dossier horodate : le dossier le plus recent peut etre le
plus vide.

## Fichiers

- `scripts/measure-targets.ps1` — mesure taille + mtime d'une liste de cibles (enumeration .NET, TSV trie).
- `scripts/delete-targets.py` — phase B : pour chaque cible, mesure -> suppression (retire l'attribut
  lecture seule) -> verification d'absence -> cumul, plus `--dry-run` et refus des chemins racine. C'est le
  pendant executable de `measure-targets.ps1` ; une cible encore presente est signalee RESTE et n'entre
  pas dans le cumul.
- `references/target-verdicts.md` — grille par categorie (cache d'outillage, cache de modeles,
  node_modules, archive d'installation, sauvegarde, snapshot d'etat, venv retire, runtime navigateur,
  dossier de travail de skill) : quoi verifier, verdict par defaut.
- `references/space-accounting.md` — mesurer le gain d'espace REEL : espace libre en octets exacts,
  reconciliation logique/reel, sonde `fsutil hardlink list`, lecture de la corbeille (`$I*`), et les
  consommateurs concurrents a ecarter avant d'attribuer un ecart aux hardlinks. Prouver un doublon
  (md5 complet + `fsutil hardlink list` + inodes) avant d'annoncer un gain.
