# Windows : sonder sans lancer, et cadrer les scans

Deux problemes reviennent sur tout audit disque Windows : prouver a qui appartient un gros fichier sans
demarrer le service qui le porte, et mesurer un volume de plusieurs To sans qu'une commande depasse son
timeout et perde tout son travail.

## Cartographier un VHDX jusqu'a son proprietaire

Ne jamais juger un `.vhdx` sur son nom de dossier. Trois sondes, toutes passives :

```bash
# 1. proprietaire (distro WSL) + chemin de base, sans lancer WSL
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss" /s | grep -i -E "BasePath|DistributionName"

# 2. etat des distros
wsl.exe --list -v        # NAME | STATE (Running/Stopped) | VERSION

# 3. activite Docker
docker info --format '{{.ServerVersion}}|{{.Driver}}|{{.DockerRootDir}}|{{.ContainersRunning}}'
docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}'
docker system df
```

- Les vhdx Docker et WSL ne partagent pas de dossier : `%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`
  (stockage des conteneurs), `%LOCALAPPDATA%\Docker\wsl\main\ext4.vhdx` (distro `docker-desktop`),
  `%LOCALAPPDATA%\wsl\<distro>\ext4.vhdx` et `%LOCALAPPDATA%\WSL\<distro>\ext4.vhdx` (distros utilisateur),
  plus un TEMPLATE non monte dans `C:\Program Files\Docker\Docker\resources\wsl\ext4.vhdx` (~0,1 Go, a garder).
  Le registre Lxss est insensible a la casse, le chemin sur disque non.
- Un vhdx dont le `LastWriteTime` avance PENDANT l'audit est en cours d'ecriture : `docker ps -a` doit
  montrer des conteneurs `Up`. Un SIEM, une base ou un service dans ce vhdx rend la cible intouchable,
  quelle que soit sa taille.
- `docker system df` chiffre ce qui est recuperable A L'INTERIEUR du vhdx (images d'un conteneur sorti,
  conteneurs arretes). Ces Go ne reviennent PAS au volume hote tant que le vhdx n'est pas compacte :
  les presenter comme un lot separe (purge puis compactage), jamais additionnes au gain annonce.
- Deplacer une distro dormante se fait par `wsl --export` / `wsl --import` vers un second volume : elle est
  conservee et le volume systeme est libere. A proposer AVANT toute suppression de vhdx.

## Modeles installes d'Ollama sans demarrer le serveur

`ollama list` demarre un serveur arrete et peut declencher une auto-mise a jour (cf. SKILL.md). Lire les
manifests sur disque :

```bash
find ~/.ollama/models/manifests -type f
grep -o '"model":"[^"]*"\|"size":[0-9]*\|"mediaType":"[^"]*"' <manifest>
```

Chaque manifeste nomme son modele (chemin `library/<modele>/<tag>`) et donne la taille de chaque couche ;
les blobs correspondants vivent dans `~/.ollama/models/blobs/sha256-*` (fichiers SANS extension). Un blob
reference par un manifeste n'est PAS un orphelin : c'est une dependance de l'application.

## Fichiers systeme de la racine d'un volume

```powershell
Get-ChildItem -LiteralPath 'C:\' -File -Force | Where-Object { $_.Length -gt 100MB } |
  ForEach-Object { '{0}|{1}|{2}' -f $_.Length, $_.LastWriteTime, $_.FullName }
powercfg /a
Get-CimInstance Win32_ComputerSystem | ForEach-Object { $_.TotalPhysicalMemory/1GB }
```

`pagefile.sys` et `hiberfil.sys` n'ont pas d'extension et pesent souvent la moitie d'une categorie
« fichiers sans extension >100 Mo » : c'est attendu, pas une anomalie. Un `hiberfil.sys` a ~40-43 % de la
RAM est la taille par defaut. `pagefile.sys` se garde : un redimensionnement est une decision mesuree,
pas un gain gratuit.

### Decider pour l'hibernation : 3 sondes, puis 2 options

```powershell
Get-CimInstance Win32_Battery                    # vide = poste fixe
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" /v HiberbootEnabled  # 0x1 = demarrage rapide
Get-WinEvent -FilterHashtable @{LogName="System"; Id=42,107,506,507} -MaxEvents 40              # 30 j
```

- **42/107 = veille S3, 506/507 = hibernation.** Des evenements 42/107 sans AUCUN 506/507 signifient que le
  fichier ne sert qu'au demarrage rapide : c'est le cas courant sur un fixe, et c'est ce qui rend la cible
  sure. Un poste sans batterie n'a aucune raison d'hiberner.
- Option A `powercfg /h /type reduced` : garde le demarrage rapide, retire l'hibernation, fait passer le
  fichier de ~40 % a ~20 % de la RAM. Mesure : 27,46 -> 13,73 Go sur 64 Go de RAM, soit 13,73 Go rendus —
  pas les 14,7 Go qu'une estimation « moitie du fichier » laisse croire. Reversible par `/type full`.
- Option B `powercfg /h off` : rend la totalite du fichier mais supprime AUSSI le demarrage rapide.
- Precautions : `powercfg` exige une session elevee (verifier `IsInRole(Administrator)`, sinon l'appel
  echoue sans bruit) ; `Get-Item C:\hiberfil.sys` peut rendre `0` ou rien sur le fichier en cours
  d'utilisation — mesurer par enumeration `Get-ChildItem -LiteralPath 'C:\' -Force -File` ; apres l'appel,
  recontrôler les DEUX cotes (nouvelle taille du fichier ET `powercfg /a` qui doit toujours lister
  « Demarrage rapide ») plus l'espace libre en octets.

### WATCHDOG : le gros dump est a la RACINE, pas dans le sous-dossier

`C:\Windows\LiveKernelReports\WATCHDOG-<date>.dmp` (plusieurs Go) est au PREMIER niveau, les petits
(1-3 Mo) sont dans `...\LiveKernelReports\WATCHDOG\`. Chercher uniquement dans le sous-dossier rate le seul
fichier qui compte.

## Cadrer les scans

- **Un root par appel.** Une enumeration `-Recurse -Filter '*.vhdx'` lancee sur `AppData\Local\Packages`
  ET `D:\` (plusieurs To) ne rend pas la main en 90-120 s. Decouper : un appel par root, et `-Depth N`
  pour les volumes de plusieurs To — trouver un fichier a 3 niveaux de la racine coute des secondes,
  parcourir l'arbre entier coute des minutes.
- **Imprimer racine par racine.** Une boucle qui ecrit chaque resultat des qu'elle l'obtient survit au
  timeout : une commande tuee rend quand meme 4 VHDX sur 5. Un tri ou une agregation globale en fin de
  commande perd tout.
- **Partir d'une liste d'emplacements connus** (tableau ci-dessous) et verifier l'existence, plutot qu'un
  parcours de masse. Sortir un `ABSENT`/`MISSING` par racine visitee : c'est la preuve que la zone a ete
  regardee, et l'absence d'un resultat ne se lit plus comme une absence de recherche.
- **`-File -Force` obligatoire** sur la racine d'un volume : sans `-Force`, les fichiers systeme caches
  (pagefile, hiberfil) n'apparaissent pas et l'audit rate les plus gros postes.
- **Un timeout n'est pas une absence** : la zone non scannee est ecrite comme telle dans les anomalies.

## Ou vivent les gros fichiers, par defaut

- vhdx Docker : `%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`, `...\wsl\main\ext4.vhdx`,
  template `C:\Program Files\Docker\Docker\resources\wsl\ext4.vhdx`
- vhdx WSL : `%LOCALAPPDATA%\wsl\<distro>\ext4.vhdx`, `%LOCALAPPDATA%\WSL\<distro>\ext4.vhdx`
- blobs Ollama : `~/.ollama/models/blobs/sha256-*` (+ `manifests/`)
- blobs HuggingFace : `~/.cache/huggingface/hub/models--<repo>/blobs/<sha>` (+ `snapshots/`)
- dumps noyau : `C:\Windows\LiveKernelReports\` et son sous-dossier `WATCHDOG\`
- dumps applicatifs : `%LOCALAPPDATA%\CrashDumps`, `%APPDATA%\<App>\Crashpad\reports\`
- cache de poids d'un pipeline : `<projet>/hf_cache/hub/models--<repo>/blobs/<sha>`

Un `hf_cache` DANS un projet est un second cache de modeles, symetrique de celui du profil : le compter a
part, et comparer les tailles des blobs des deux cotes avant d'annoncer un doublon — une distribution qui
materialise `snapshots/` en fichiers reels pese le double d'une qui les laisse en liens.

## Inventaire RAM / processus / VRAM (avant nettoyage ou backup)

Toutes ces sondes sont passives et sans elevation obligatoire (sauf cibles systeme). Script pret a
l'emploi : `scripts/inventory-windows-host.ps1`.

- **Lire la memoire par les proprietes CIM, pas par `Get-Counter`.** Les noms de compteurs sont LOCALISES :
  sur une machine FR, `'\Memory\Standby Cache Normal Priority Bytes'` ne se resout pas et la sonde rend 0 ou
  une erreur — ce qui se lit « pas de standby ». `Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory`
  expose les memes valeurs sous des noms stables et non traduits : AvailableBytes, CommittedBytes,
  CommitLimit, ModifiedPageListBytes, FreeAndZeroPageListBytes, StandbyCacheCoreBytes /
  StandbyCacheNormalPriorityBytes / StandbyCacheReserveBytes, PoolNonpagedBytes, PoolPagedBytes.
- **Le standby n'est pas de la RAM perdue.** Il est compte DANS `AvailableBytes` : le vider ne libere ni RAM
  utilisable ni un octet de disque, ne reduit aucun backup, et n'interesse qu'un benchmark qui exige des
  pages libres. Le dire au lieu de l'executer ; RAMMap / EmptyStandbyList sont des outils tiers a ne pas
  installer sans GO.
- **Classer par working set ET par memoire privee.** Un service qui mappe plusieurs Go hors du working set
  sort a ~66 Mo de WS pour ~4 Go de prive : un classement par WS seul rate le plus gros consommateur et fait
  conclure a une machine tranquille. Rapporter les deux colonnes.
- **Le cumul par famille est le chiffre decisionnaire, pas le top 10.** Grouper par `ExecutablePath` ou par
  nom : 161 processus `chrome.exe` = 12,4 Go, dont 142 processus d'un navigateur d'outillage a 8,3 Go qu'il
  faut distinguer des 19 processus du navigateur utilisateur. Un pool appartenant a l'outillage en cours
  d'execution n'est pas un candidat a la fermeture — le nommer comme tel.
- **Ne jamais filtrer les processus par mot-cle sur `CommandLine`, et ne jamais imprimer cette ligne.**
  Elle porte des secrets (jetons en argument) et le filtrage par sous-chaine fabrique des faux positifs
  (« rag » matche `storage` / `fragment` : 150 lignes parasites pour 12 utiles). Filtrer sur `ExecutablePath`
  ou par motif ancre (`\b`), et n'imprimer que nom + PID + memoire + mot-cle matche.
- **VRAM : seul le total est fiable.** `nvidia-smi --query-gpu=memory.total,memory.used,memory.free` donne
  le chiffre a rapporter ; la memoire par processus sort en `[N/A]` sur les pilotes grand public en WDDM et
  l'option `--query-accounting-apps` n'existe pas (seulement `--query-compute-apps`). A 0 % d'utilisation,
  il n'y a rien a liberer : l'ecrire, ne pas promettre un gain.
- **Compter les fichiers RECENTS des cibles Temp.** Une cible dont le mtime du jour est actif donne surtout
  des echecs de verrou : mesurer la part > 7 j et > 30 j (fichiers + octets) pour chiffrer ce qui est
  reellement supprimable, et annoncer la taille mesuree comme un PLAFOND, pas comme un gain.
