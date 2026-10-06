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

Sous git-bash, un script PowerShell multi-ligne se passe par STDIN avec un heredoc quote, ce qui evite
l'enfer des guillemets imbriques (`'yyyy-MM-dd'`, `'C:'`, `@{LogName="System"}`) :

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command - <<'PSEOF'
$t = Get-ChildItem -LiteralPath "C:\Windows\LiveKernelReports" -Filter *.dmp -Recurse -File
$t | Select-Object FullName, Length | Export-Csv -LiteralPath $m -NoTypeInformation
PSEOF
```

Le corps n'est pas interprete par bash : les `$` et les guillemets simples arrivent intacts a PowerShell.
Ne pas mettre d'esperluette (`&`, operateur d'appel) ni de `2>&1` dans ces commandes : l'outil terminal
les lit comme une mise en arriere-plan et refuse l'appel entier. Appeler l'executable directement
(`powercfg.exe /h /type reduced`) et lire `$LASTEXITCODE` au lieu de rediriger la sortie.
Ecrire le `.ps1` avec l'outil d'ecriture puis le lancer en `-File` reste la variante sure si le script doit
etre relance ou relu.

Le script rend un TSV `kind | bytes | mtime | path` trie par taille decroissante (kind = FILE | DIR |
MISSING), ce qui donne directement le tableau du rapport. Garder `du -sh` pour un petit dossier et
`df -h` pour l'espace libre : eux restent rapides.

- **Mtime d'un dossier** = derniere modification de son repertoire (ajout/retrait d'entree), pas le max
des enfants. C'est un signal d'ACTIVITE, a confirmer en regardant le mtime des sous-dossiers avant d'en
conclure qu'une cible est morte.
- **Toujours sortir une ligne MISSING / retypee** pour une cible introuvable ou d'une autre nature, au
lieu de sauter la ligne : une cible absente du rapport passe pour inexistante.
- Ne pas lancer une lecture de contenu sur un fichier de nature inconnue : `read_file` sur un `.exe`
deverse des pages d'octets illisibles et pollue la session. Etablir d'abord le type (extension, `file`,
`stat -c %s`) et ne garder `read_file` que pour un fichier texte.
- "Les 5 premieres lignes" ne s'appliquent qu'a un fichier TEXTE. Quand aucune cible n'est un fichier
texte (archives ZIP/7z, dossiers), le dire explicitement plutot que d'omettre la demande.

## Perimetre d'inventaire : ce qu'une liste de modeles rate systematiquement

Une liste de fichiers de modele >N Mo construite par balayage de dossiers connus rate les caches dont
les fichiers n'ont PAS d'extension : ils echappent au filtre `\.(safetensors|pt|bin|gguf)$`. Sur une meme
session, la liste de 228,49 Go manquait trois gisements : `\.cache\huggingface\hub\**\blobs\<sha256>`
(5,86 Go), `\.ollama\models\blobs\*` (6,70 Go, cibles `sha256-*` sans extension) et le cache HF propre
d'un pipeline (`data\<pipeline>\hf_cache\...\blobs\`, 9,32 Go). Total corrige : 249,81 Go, soit +21 Go
(+9 %) invisibles. Toujours enumerer en plus : `blobs/`, `.ollama\models`, les `hf_cache` internes aux
pipelines, et compter separement "poids de modele" et "arborescence totale du pack" (venvs, repos, sorties).

Un sous-dossier de cache PEUT etre une coquille vide trompeuse : 10 entrees `models--*` du hub HF ne
contenaient qu'un fichier de 40 octets (`refs/main`) — telechargements jamais materialises. Une entree de
cache n'est pas une preuve de presence : mesurer la taille avant de conclure.

## Windows : dumps, hibernation, VHDX — les chemins reels

- **WATCHDOG dumps.** Le gros fichier est a la RACINE de `C:\Windows\LiveKernelReports\`
  (`WATCHDOG-<date>.dmp`, 5,2 Go mesure), les petits sont dans le sous-dossier `WATCHDOG\`. Chercher
  seulement dans le sous-dossier rate le seul fichier qui compte. Le reste : `AppData\Roaming\<app>\Crashpad\reports\`
  (VS Code, Antigravity), generalement 30-40 Mo chacun. `C:\Windows\Minidump`, WER et `Local\CrashDumps`
  peuvent etre vides — le dire ligne par ligne plutot que d'omettre.
- **Mapping VHDX -> distro SANS lancer WSL** : `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss" /s`
  donne `DistributionName` + `BasePath` par GUID. `wsl --list -v` ne donne que l'etat (Running/Stopped) :
  les deux ensemble distinguent un VHDX actif d'un VHDX dormant sans demarrer de service.
- **hiberfil.sys : fixe ou portable, et qui l'utilise reellement.** Trois sondes avant de proposer
  `powercfg /h off` : `Get-CimInstance Win32_Battery` (vide = fixe), `HiberbootEnabled` dans
  `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power` (0x1 = demarrage rapide actif), et
  `Get-WinEvent -FilterHashtable @{LogName="System";Id=42,107,506,507}` sur 30 j — **42/107 = veille S3,
  506/507 = hibernation** : des evenements 42/107 sans 506/507 signifient que le fichier ne sert QU'au
  demarrage rapide. Dans ce cas proposer `powercfg /h /type reduced` (garde le demarrage rapide, reduit le
  fichier, ~20 % de la RAM au lieu de 40 %) avant le `powercfg /h off` total, qui lui supprime aussi le
  demarrage rapide. La taille de hiberfil vaut ~40 % de la RAM : la comparer a `TotalPhysicalMemory` comme
  controle de coherence. Deux precautions de mesure et le chiffre exact du gain :
  `references/windows-probes-and-scoping.md`.

## Inventaire : faux negatifs et faux comptages

Une mesure fausse a l'inventaire produit une liste de suppression fausse. Cinq pieges :

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
- **Le perimetre d'un inventaire anterieur se revalide, pas sa liste.** Un inventaire deja fait (« deja
  228 Go identifies ») se remesure par DOSSIER : son total peut etre exact et son perimetre faux. Mesure :
  une liste de modeles filtres a >100 Mo rate tout gisement dont les fichiers n'ont pas d'extension
  (blobs de cache HF/Ollama, `hf_cache` d'un pipeline) — la mesure par dossier a ajoute ~21 Go que la
  liste ignorait. Ne jamais reprendre un total anterieur sans remesurer un dossier par famille de cible.
- **Un agregat par extension n'est pas un inventaire.** Un CSV d'outil graphique (WizTree) agrege par
  extension ne porte AUCUN chemin : il sert a confronter les totaux (`26 .dmp / 5,51 Go` annonces vs 18
  mesures) et a cadrer ce qui manque, jamais a localiser un fichier. Un ecart se nomme avec le perimetre
  non scanne (`D:\` interrompu par timeout, `Packages` non parcouru), jamais en silence.

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
- **Contenu d'un disque virtuel (VHDX).** Les images et conteneurs Docker, et le systeme de fichiers d'une
  distro WSL, vivent DANS un `.vhdx` a extension dynamique : les supprimer libere de l'espace *interieur*,
  et **C: ne le recupere pas** tant que le disque virtuel n'est pas compacte. Mesure de l'ordre de grandeur :
  conteneurs arretes + images sans conteneur + deux grosses images = ~35 Go annonces, dont **0 Go rendu a
  l'hote** sans `fstrim` puis compactage (Docker Desktop arrete, ou `Optimize-VHD` / `diskpart compact vdisk`).
  Un palier « Docker » se chiffre donc en deux colonnes : gain interieur (immediat, invisible pour C:) et
  gain hote (apres compactage, a valider separement). Sans cette distinction, le rapport promet des Go qui
  n'arriveront jamais.

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
- **Cartographier un service depuis ses fichiers, pas depuis sa CLI.** Les modeles installes d'Ollama se
  lisent dans `~/.ollama/models/manifests/**` (JSON avec `"size"` par couche), l'activite de Docker dans
  `docker info` + `docker ps -a` (conteneurs `Up`) + `docker system df`, la propriete d'un VHDX dans le
  registre `HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss` (`DistributionName` + `BasePath`) : aucun
  de ces trois ne demarre un service arrete. Commandes et seuils :
  `references/windows-probes-and-scoping.md`.
- **Demarrer une distro WSL pour l'inspecter detruit la preuve de son inactivite.** `wsl -d <distro> -- <commande>`
  demarre la distro meme pour un `ls` : mesure, chaque VHDX a grossi de ~33,5 Mo et son mtime est passe de
  la date d'activite reelle (20/09) a l'instant de la sonde (29/09 02:25). L'indicateur « dormant depuis X »
  qu'on s'apprete a rapporter est donc pollue par sa propre mesure — le dire explicitement dans le rapport
  (date d'activite humaine : dernier fichier ecrit, `bash_history`, log de bench) au lieu de citer un mtime
  qu'on vient de reecrire. La cartographie passive (registre Lxss + `wsl --list -v`) ne coute rien et ne
  fausse rien : n'utiliser `wsl -d` que si la demande porte sur le CONTENU de la distro.
- Si une CLI doit etre invoquee et qu'elle modifie l'etat (demarrage de service, telechargement, mise a
  jour), l'ecrire dans les anomalies ET proposer de le defaire — ne pas le defaire en silence : le mandat
  "lecture seule" interdit l'initiative, pas le signalement.

## Suppression (phase B)

### Un `Remove-Item -Recurse -Force` peut rendre la main en laissant du residu — toujours verifier

Sur un arbre de 887 695 fichiers / 231,78 Go, `Remove-Item -LiteralPath "C:\c" -Recurse -Force` a
libere 233,01 Go **et** s'est arrete en erreur sur un seul fichier, laissant en place ce fichier et les
5 dossiers parents vides. Un script qui n'enchaine pas sur un controle d'absence annonce « supprime » a
tort.

- **Fichier nomme `nul` (ou `con`, `aux`, `prn`, `com1`...)** : nom reserve du noyau, cree par un
  `> nul` execute dans le mauvais dossier. Il apparait dans l'enumeration avec sa vraie taille (178 o mesure)
  mais toute operation par chemin normal echoue (« Fonction incorrecte »). Le prefixe `\\?\` **n'est pas
  gere par le provider PowerShell** (`Get-Item -LiteralPath '\\?\C:\...' ` rend
  « Il n'existe aucun lecteur nomme \\?\C ») et `[System.IO.File]::Delete` le refuse aussi. Les deux
  voies qui marchent : `cmd /c del /f /q "\\?\<chemin>\nul"` ou, en repli,
  `cmd /c ren "\\?\<chemin>\nul" <nom_normal>` puis suppression du fichier renomme. Depuis git-bash,
  appeler `cmd //c '...'` en guillemets simples (pas de `Start-Process` avec deux redirections vers le
  meme fichier : PowerShell refuse). Verifier l'absence en **enumerant le dossier**
  (`Get-ChildItem -Force | Where Name -eq 'nul'`) : `Test-Path` sur un nom de peripherique repond n'importe
  quoi.
- **Un fichier reserve se replique** : robocopy l'a copie tel quel, la copie de sauvegarde contient donc le
  meme `nul` (confirme dans les listes de verification des deux cotes). Le signaler : le meme blocage
  attend la deuxieme copie.

**Correction mesuree — la piste `cmd` ci-dessus ne marche PAS sur ce cas.** L'appel `cmd` avec le prefixe
longueur-etendue a ete rejete (« Nom de repertoire non valide », rc=11) pour la suppression comme pour le
renommage, et l'appel `cmd` en double-slash depuis git-bash ne fait rien du tout : la conversion de chemin
MSYS est desactivee, donc `cmd //c` arrive tel quel, cmd demarre en interactif et rend **rc=0 — un faux
succes**. La voie qui a fonctionne : compiler a la volee un appel a l'API noyau `DeleteFileW`
(`Add-Type` + `DllImport` sur kernel32, `CharSet=CharSet.Unicode`) et l'appeler avec le chemin prefixe
longueur-etendue -> retour `True`, fichier supprime, dossier parent ensuite purgé sans erreur. C'est la
validation du runtime .NET sur les noms reserves, pas l'API noyau, qui bloque. Repli sans suppression
immediate : `MoveFileExW(chemin, $null, 4)` = suppression differee au prochain redemarrage. Taille du
fichier lisible par `dir /a` (178 o mesure) alors que `FileInfo.Length` la rend vide.

**Un script PowerShell alimente par STDIN (`powershell -Command -`) peut rendre une sortie VIDE avec
code 0** des qu'il rencontre une erreur terminante : stderr n'est pas capture et le diagnostic disparait.
Meme piege possible sur un heredoc tronque. Ne pas en conclure « rien ne s'est passe » ni « tout va bien » :
ecrire le `.ps1`, le lancer en `-File`, et faire ecrire les resultats dans un fichier texte relu ensuite.

### Le gain reel peut DEPASSER la somme logique

Meme arbre : 231 781 377 402 octets logiques annonces, **233 014 161 408 octets reellement rendus**
(+1,23 Go, +0,53 %), alors que des ecritures concurrentes (Docker) rognaient le gain dans le meme temps :
l'overhead d'allocation est donc d'au moins 1,23 Go. Cause : la taille logique ignore l'arrondi aux
clusters (4 ko) et les metadonnees NTFS (MFT, entrees de repertoire) des 887 695 fichiers. L'ecart va dans
les deux sens — un arbre contenant des fichiers sparse ou compresses (`.gguf` mesure : 43,4 Go logiques pour
21,7 Go alloues) rendra beaucoup MOINS que sa somme logique. Dans les deux cas : mesurer `FreeSpace` avant/
apres en octets, jamais annoncer la somme logique comme un gain.

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

## Deplacer hors du volume (phase B, variante non destructive)

Quand le verdict est « deplacer vers <volume> » et non « supprimer », le risque change de nature : la
copie est longue, traverse deux supports, et peut echouer a mi-chemin.

- **Mesurer la cible EXACTE de l'action, pas un sous-dossier de celle-ci.** Un audit peut n'avoir mesure
  que le dossier interne (ex. `<racine>\hermes_backup_<date>`) alors que l'action porte sur le parent :
  le parent contenait 187 fichiers et 11 Mo de plus (deux charges voisines non inventoriees). Remesurer la
  cible telle qu'elle sera deplacee, et remesurer le perimetre reel de l'action avant d'annoncer un total.
- **Ne pas utiliser `/MOVE` vers un support amovible ou USB.** Robocopy supprime chaque source au fur et
  a mesure : une deconnexion USB en cours de route detruit la source ET laisse une copie partielle. Faire
  la copie (`/E`, sans `/MOVE`), VERIFIER, puis supprimer la source — meme duree totale, deux risques
  separes, deux validations separees.
- **Le resume robocopy est en GiB** (suffixe `g`) : `215.863 g` = 215,863 GiB = 231,78 Go (10^9). Le
  comparer a une mesure en 10^9 sans convertir fait croire a un manque de 16 Go. RC 0-7 = succes
  (1 = fichiers copies), 8+ = echec ; la source de verite reste le log (`/LOG:`), a fouiller pour
  `ERREUR|ERROR|ECHEC` et pour les colonnes Ignore / Extras.
- **Verifier par ENSEMBLE de fichiers, pas par comptage.** Comparer les deux arbres sur la cle
  `chemin relatif + taille` (deux listes ecrites par la MEME enumeration .NET, puis `Compare-Object`) :
  attendre 0 et 0. Un comptage egal ne prouve rien (deux erreurs symetriques s'annulent) et un comptage
  different ne prouve pas une perte (perimetres differents). Script pret a l'emploi :
  `scripts/verify-copy-tree.ps1` ; recette detaillee : `references/volume-move-verification.md`.
- **Borner le hachage.** Le SHA256 complet de fichiers de plusieurs Go lus depuis un disque externe lent
  depasse le mur d'appel de l'outil (~420 s constate) : SHA256 complet sur des fichiers <=100 Mo pris un
  par sous-arbre, et pour les plus gros un controle PARTIEL (debut + fin 32 Mo par `Seek`), annonce comme
  partiel — jamais presente comme un SHA256. Grouper les sous-arbres APRES avoir retire le prefixe commun
  de la cible deplacee, sinon tout retombe dans un seul groupe.
- **Chiffrer la duree avec une sonde, pas au feeling.** Copier un sous-arbre representatif vers un dossier
  temporaire du volume cible, chronometrer, en deduire deux bornes (Mo/s et fichiers/s) et retenir la plus
  grande, puis supprimer la sonde. Mesure : 23 Mo/s et 458 fichiers/s sur un HDD USB, soit 168 min par le
  debit contre 32 min par le nombre de fichiers — et 62 min reellement obtenus.
- **Lancer en arriere-plan des que la copie depasse ~10 min**, et verifier qu'elle PROGRESSE (taille de la
  destination + queue du log) avant de rendre la main. Si un appel en avant-plan expire, le processus
  enfant peut survivre et continuer a saturer le disque : le retrouver
  (`Get-CimInstance Win32_Process -Filter "Name='powershell.exe'"`, CreationDate + CPU) et le tuer par
  `Stop-Process -Id <pid> -Force` — sous git-bash, `taskkill //PID` est mangue par MSYS et refuse.

## Rapport — pieges

- Ecrire la taille MESUREE, pas la taille annoncee : sur une meme session les chiffres d'audit differaient
des mesures d'un facteur 2,5 a 6. Un tableau qui recopie l'inventaire d'origine propage l'erreur.
- **Chiffrer le but reel du nettoyage, pas seulement les cibles.** Quand l'utilisateur nettoie « pour
reduire la taille d'un backup », comparer le total des cibles a l'espace libre ET au poids de l'image, et
l'ecrire : un plafond negligeable (12 cibles = 1,13 Go contre 1,26 To libres) signifie que le poids de
l'image vient d'ailleurs (users, ProgramData, vhdx WSL, pagefile, autres volumes). Un nettoyage qui ne
sert pas le but annonce se dit dans le rapport ; il ne s'execute pas en silence pour rassurer.
- Une cible vide (0 Mo) et une sauvegarde partielle sont deux ANOMALIES a signaler, pas a taire.
- Un artefact durable range dans un dossier temporaire elague automatiquement (cache/scratch) est un
risque de perte silencieuse, pas un fichier a supprimer : le dire et proposer l'emplacement durable.
- Ne pas conclure "redundant" depuis un nom de dossier horodate : le dossier le plus recent peut etre le
plus vide.

## Forme du rapport attendue

Un audit demande en plusieurs volets (A/B/C/D) se rend en UN SEUL rapport final, pas un message par
volet. Structure attendue :

1. **Methode et perimetre** : ce qui a ete scanne, ce qui ne l'a PAS ete et pourquoi, la convention de
   taille, l'espace libre par volume, et la mention explicite que rien n'a ete supprime / deplace / renomme.
2. **Une section par volet** (A, B, C, D) avec le tableau demande : `nom | chemin racine | taille |
   nb fichiers | mtime max`. Etiqueter la nature du mtime : « arborescence » (a-t-elle servi ?) et
   « poids » (date du fichier) sont deux informations differentes et ne se melangent pas sans le dire.
3. **Tableau recapitulatif** `Categorie | Taille totale mesuree | Gain estime`.
4. **Classement en 3 colonnes par categorie** : SUPPRIMABLE SANS RISQUE / DEPLAÇABLE VERS <volume> /
   A CONSERVER. Aucune cible dans deux colonnes ; une cible mixte se SCINDE (poids identiques ailleurs =
   supprimable, fichiers absents du live = deplacer ou garder) au lieu d'etre tranchee en bloc.
5. **Gain par paliers, jamais un chiffre unique** : palier 1 sans risque (fichiers seuls), palier 2
   deplacement (risque nul si le volume cible a la place), palier 3 decisions apres verification. Donner
   le plafond theorique du gisement ET ce qui ne rendra rien (blocs partages).
6. **Anomalies numerotees** en section separee (cf. Procedure §5).

Protocole de contraintes quand l'utilisateur l'impose : timeout EXPLICITE sur chaque commande, annonce
AVANT toute commande >60 s, un seul root par appel pour les gros arbres, impression incrementale pour
qu'un timeout conserve les lignes deja produites. Ce protocole fait partie du livrable : le rapport dit
quelles commandes ont ete tuees et quelles zones sont restees non scannees.

## Fichiers

- `scripts/measure-targets.ps1` — mesure taille + mtime d'une liste de cibles (enumeration .NET, TSV trie).
- `scripts/inventory-windows-host.ps1` — inventaire lecture seule d'un hote Windows avant nettoyage :
  volumes en octets exacts, tailles des cibles, top processus (WS + memoire privee), cumul par famille,
  RAM/CIM (standby inclus), VRAM `nvidia-smi`. Ecrit un TSV par lot, ne supprime rien.
- `scripts/verify-copy-tree.ps1` — verifie une copie inter-volumes : listes `chemin relatif + taille` des
  deux arbres, diff d'ensembles (attendu 0 et 0), SHA256 echantillonnes un par sous-arbre, controle
  partiel des plus gros fichiers. Exit 0 = identique, 3 = ecart.
- `references/volume-move-verification.md` — deplacement de volume de bout en bout : sonde de debit,
  copie sans `/MOVE` en arriere-plan, verification par ensemble, hachage borne, processus orphelins.
- `references/target-verdicts.md` — grille par categorie (cache d'outillage, cache de modeles,
  node_modules, archive d'installation, sauvegarde, snapshot d'etat, venv retire, runtime navigateur,
  dossier de travail de skill) : quoi verifier, verdict par defaut.
- `references/windows-probes-and-scoping.md` — Windows : cartographier un VHDX jusqu'a son service
  (registre Lxss, Docker, distro WSL) sans lancer de service, modeles Ollama depuis les manifests,
  fichiers systeme de la racine (pagefile/hiberfil), cadrage des scans root par root avec timeout
  explicite, et ou vivent les gros fichiers par defaut.
- `references/space-accounting.md` — mesurer le gain d'espace REEL : espace libre en octets exacts,
  reconciliation logique/reel, sonde `fsutil hardlink list`, lecture de la corbeille (`$I*`), et les
  consommateurs concurrents a ecarter avant d'attribuer un ecart aux hardlinks. Prouver un doublon
  (md5 complet + `fsutil hardlink list` + inodes) avant d'annoncer un gain.
