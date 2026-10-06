# Grille de verdict par categorie de cible

Un nom de dossier ne prouve rien. Pour chaque categorie : le controle a faire, et le verdict par defaut
quand le controle ne tranche pas.

Verdicts : SUR (supprimable) / A VERIFIER (a valider en phase B) / A GARDER.

---

## Cache d'un gestionnaire de paquets (uv, pip, npm, pnpm, cargo)

- Controle : identifier la commande de regeneration (`uv cache clean <famille>`, `npm cache clean --force`)
  et la presence du gestionnaire.
- Verdict par defaut : **SUR**.
- Piege : ne supprimer qu'une FAMILLE de cache, pas le dossier parent. Le layout uv separe
  `archive-v0` (roues depaquete, le gros du poids), `sdists-*`, `simple-*`, `wheels-*`, `git-v0`. Mesure :
  `archive-v0` = 16,7 Go sur 17,1 Go du parent ; supprimer le parent emporte les cinq familles.
- Emplacement typique : `%LOCALAPPDATA%\uv\cache`, `~/.cache/pip`, `~/.npm/_cacache`.

## Cache de modeles (HuggingFace hub, torch/hub, whisper, ollama)

- Controle : `grep -rn -i -E "<nom-modele>|SentenceTransformer|HF_HOME|<chemin-du-cache>" <scripts actifs>`
  puis lire le manifeste du service (modele + nombre de fragments indexes).
- Verdict par defaut : **A VERIFIER**. Le cache HF contient les poids que les scripts locaux chargent par
  nom de depot (embeddings de RAG, CLIP d'un pipeline diffusion, whisper d'un transcripteur) : le
  supprimer casse un service en marche et impose un re-telechargement.
- **Suppression partielle possible** : tout sauf le(s) depot(s) references. Chiffrer l'option separement
  (total cache moins le poids du modele utilise) et la proposer comme decision utilisateur, pas l'appliquer.
- Contrainte de l'utilisateur a respecter au mot : "jamais de telechargement sans validation". Un cache
  re-telechargeable n'est donc pas gratuit — dire ce qui devra etre re-telecharge, et combien.

## node_modules

- Controle : mesurer le `node_modules` RACINE **et** ceux des workspaces (`apps/*/node_modules`,
  `web/`, `ui-tui/`) separement — le premier ne contient pas les seconds. Chercher les binaires de
  runtime dedans (`electron`, `node-pty`) et l'existence d'un build (`apps/desktop/dist`).
- Verdict par defaut : **A VERIFIER**.
- Regenerable par `npm ci` / `npm install`, mais coute reseau + build : ce n'est pas un residu. Si un
  runtime y est present (Electron ~335 Mo) et qu'une app construite a ete rebuild recemment, c'est une
  installation en service.

## Archive d'installation telechargee (.7z / .zip d'une distribution)

- Controle : verifier que la copie EXTRAITE existe et fonctionne (binaire d'entree present, dossier de
  donnees garni) et que l'archive est bien la meme distribution.
- Verdict par defaut : **SUR** si l'installation extraite est en service.
- Piege de chemin : l'archive git dans le dossier des sources ou au-dessus, pas dedans ; verifier
  l'existence reelle avant de mesurer, un libelle d'audit peut pointer un sous-dossier qui ne la contient
  pas.
- Sinon (rien d'extrait) : l'archive est la seule copie locale — la garder ou signaler le re-telechargement.

## Sauvegarde (Desktop/hermes_backup_*, skills_backup_*, *.bak.*)

- Controle : (1) completude — presence de `memories/`, `skills/`, `data/`, `state.db`, `.env` ; (2) est-elle
  la plus recente ; (3) son contenu est-il versionne ailleurs (`git check-ignore -v <cible>` +
  `git ls-files <cible> | wc -l`).
- Verdict par defaut : **A VERIFIER**.
- Un `data/` et un `.env` ignores par git font de la sauvegarde la SEULE copie hors profil : la declarer
  redundante parce que le depot git est propre est faux.
- Un dossier de sauvegarde voisin plus recent mais vide (0 Mo) est un ECHEC de sauvegarde : le signaler
  comme anomalie. Il ne remplace rien.
- **Une sauvegarde se DEPLACE avant de se supprimer.** Quand le rapport doit classer en SUPPRIMABLE /
  DEPLAÇABLE / A CONSERVER, une sauvegarde entiere va en DEPLAÇABLE vers un volume secondaire : risque
  nul, archive intacte, volume systeme libere. Seul son payload strictement identique au live (meme chemin
  relatif ET meme taille, puis `fsutil hardlink list` a 1 seul lien) est SUPPRIMABLE.
- **Comparer les SOUS-ARBRES, pas le total.** Une sauvegarde peut etre plus GROSSE que le live (mesure :
  `data/` 213 Go en sauvegarde vs 156 Go en production) : ses sous-arbres en surnombre contiennent alors
  des fichiers qui n'existent nulle part ailleurs (variantes de poids, sorties anciennes). Les lister
  fichier par fichier (chemin relatif + taille) avant de proposer quoi que ce soit, et les garder.

## Snapshot d'etat (<horodatage>-pre-update)

- Controle : comparer avec l'etat courant (`state.db` courant vs celui du snapshot, version installee).
- Verdict par defaut : **A VERIFIER** — c'est le chemin de rollback de la derniere mise a jour. Garder tant
  que la version en place n'a pas passe son rodage.

## Venv / environnement Python retire (.venv.retired-*)

- Controle : lire la doctrine du profil (`grep -n -i -E "retention|retired" docs/*.md`) — une date de
  suppression prevue y est souvent ecrite.
- Verdict par defaut : **A GARDER** jusqu'a la date documentee.
- La taille annoncee est souvent fausse (mesure : 1,10 Go vs 177 Mo annonces) : remesurer.

## Runtime de navigateur (ms-playwright, .cache/puppeteer)

- Controle : identifier le moteur REELLEMENT configure (`browser.engine` dans config.yaml), chercher le
  second cache, verifier les processus en cours et les serveurs MCP qui l'utilisent.
- Verdict : **SUR** pour celui qui n'est PAS le moteur en service ; **A GARDER** pour l'autre.
- Ne pas supprimer les deux "parce qu'ils font doublon".

## Dossier de travail d'un skill (sous cache/scratch, ou un dossier de skill)

- Controle : le skill est-il actif ? `config.yaml` -> `skills.disabled` (une liste YAML, pas un flag par
  skill). Verifier aussi le mtime : ecrit le jour meme = travail en cours.
- Verdict : **A GARDER** si le skill est actif.
- Signaler separement le risque de conception : `cache/scratch` est elague automatiquement apres 24 h
  d'inactivite, donc un artefact durable (poids convertis, export) qui y vit peut disparaitre tout seul.
  Proposer un emplacement durable plutot que de le supprimer.

## Magasin interne d'un service (backups/ du profil, .curator_backups, quarantaine)

- Controle : mtime des SOUS-dossiers (un magasin de blobs ecrit le jour meme est actif).
- Verdict par defaut : **A GARDER** / ne pas toucher sans demande explicite.
- Une quarantaine "deja comptee ailleurs" dans l'inventaire ne se supprime pas deux fois : la compter une
  seule fois et le dire.

## Poids d'un modele en plusieurs formats (dossier diffusers : unet/, text_encoder/)

- Controle : ouvrir le SCRIPT de run vivant et lire la paire `--pretrained_model_name_or_path=<dossier>` +
  `--variant=<v>`. C'est elle qui designe le fichier charge : `--variant=fp16` fait lire
  `diffusion_pytorch_model.fp16.safetensors`, pas `diffusion_pytorch_model.safetensors`.
- Verdict par defaut : **SUR** pour les variantes non chargees et citees par aucun script —
  `*.bin` (ancien format PyTorch, lu seulement si le `.safetensors` manque), `*.fp16.bin`,
  `*.non_ema.bin|safetensors` (poids non-EMA, jamais lus par un entrainement standard).
- Garder 2 poids + `config.json` : la variante reellement chargee et le `.safetensors` fp32 de repli
  (defaut de diffusers quand `--variant` est omis).
- Ne pas conclure depuis la liste des fichiers du dossier : ils servent a l'ENTRAINEMENT (diffusers),
  tandis qu'une UI d'inference (ComfyUI, A1111) charge ses propres checkpoints mono-fichier ailleurs —
  elle n'en "protege" aucun.

## Store d'une application desinstallee ou renommee (.bak, store orphelin)

- Controle : trois sondes avant de declarer le store orphelin — (1) le binaire existe-t-il encore
  (`find <dir-de-l-app> -maxdepth 2 -iname "*.exe"`) ; (2) un pointeur de HOME vise-t-il ce store
  (un `.<app>-home-pointer` pointant vers un dossier ABSENT = pointeur mort) ; (3) la config utilisateur
  subsiste-t-elle ailleurs (`AppData/Roaming/<App>`) ?
- Verdict par defaut : **A VERIFIER** — un dossier de programme qui ne contient plus que 2 DLL + le store
  de modeles signifie application desinstallee, mais le store peut etre la seule copie locale de gros poids
  a re-telecharger (chiffrer le re-telechargement avant de proposer).
- Lire les MANIFESTES du store (JSON de type ollama/localai) avant de traiter un blob comme orphelin :
  un blob reference par un manifeste est une dependance de l'app, pas un residu.

## VHDX d'une machine virtuelle (WSL, Docker Desktop)

- Controle : mapper chaque fichier a son proprietaire AVANT tout verdict — registre Lxss
  (`DistributionName` + `BasePath`) pour WSL, `wsl --list -v` pour l'etat, `docker ps -a` + `docker info`
  pour Docker. Un vhdx dont le mtime avance pendant l'audit est en cours d'ecriture.
- Verdict : **A GARDER** si la distro ou les conteneurs sont `Running` (mesure : 47,4 Go de
  `docker_data.vhdx` portant un SIEM actif) ; **A VERIFIER** si la distro est `Stopped` depuis des
  semaines — verifier son contenu avant de la declarer morte ; **A GARDER** pour le template non monte de
  `C:\Program Files\Docker\Docker\resources\wsl\ext4.vhdx` (~0,1 Go).
- Un vhdx ne se reduit pas tout seul : `docker system df` peut annoncer des Go recuperables a l'interieur
  du fichier sans que le vhdx hote diminue (purge + compactage). Ne pas compter ces Go dans le gain.
- Alternative au demantelement : `wsl --export` / `wsl --import` vers un second volume — conserver la
  distro et liberer le volume systeme. A proposer avant toute suppression.

## Fichiers systeme de la racine d'un volume (pagefile.sys, hiberfil.sys, swapfile.sys)

- Controle : `Get-ChildItem -LiteralPath C:\ -File -Force | Where Length -gt 100MB`, `powercfg /a`
  (hibernation / demarrage rapide actifs ?), RAM totale (`Win32_ComputerSystem.TotalPhysicalMemory`).
- Verdict : **SUR** pour `hiberfil.sys` — mais jamais par effacement : `powercfg /h off` desactive
  hibernation ET demarrage rapide (decision utilisateur, gain ~40-43 % de la RAM). **A GARDER** pour
  `pagefile.sys` : un redimensionnement est une decision mesuree, pas un gain gratuit. `swapfile.sys` suit
  le pagefile.
- Sans extension, ces fichiers arrivent en tete de toute categorie « fichiers sans extension >100 Mo » et
  faussent la lecture si on y cherche des artefacts applicatifs.

## Dumps de crash (.dmp)

- Emplacements a sonder : `C:\Windows\LiveKernelReports\` ET son sous-dossier `WATCHDOG\`,
  `C:\Windows\MEMORY.DMP`, `C:\Windows\Minidump`, `%LOCALAPPDATA%\CrashDumps`,
  `C:\ProgramData\Microsoft\Windows\WER`, et les `Crashpad\reports\` des applications Electron
  (VS Code, IDE tiers).
- Verdict : **SUR** — un dump est un artefact de diagnostic, pas une donnee. Exception : conserver (ou
  deplacer) le dump d'un incident RECURRENT non instruit (plusieurs dumps de la meme source etalees sur des
  semaines = incident a instruire, le dire dans le rapport).
- Le poids se concentre dans UN fichier noye parmi des petits : un `LiveKernelReports\WATCHDOG-<date>.dmp`
  peut peser plusieurs Go quand ses jumeaux du sous-dossier pesent 2 Mo. Trier par taille, pas par dossier.
