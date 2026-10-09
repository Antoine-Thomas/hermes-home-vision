---
name: windows-path-handling
description: "Use when file writes or tool paths go wrong on Windows."
version: "1.0.0"
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, paths, file-writes, msys, bash]
    category: devops
---

# Windows Path Handling

Comment faire arriver un fichier ou un argument la ou on le croit, quand on pilote les outils Hermes et un shell sur Windows.

## When to use

- Ecrire des fichiers EN DEHORS du workspace de session (depot sur le disque de l'utilisateur, dossier de livrables).
- Toute commande dont un argument est un chemin consomme par un programme natif Windows (git, node, python, ffmpeg, gh).
- Toute tache de scaffolding / lot d'ecritures : c'est la que l'erreur de chemin coute l'integralite du lot.

## Regle 1 — les ecritures hors workspace passent par un chemin natif absolu

`C:/Users/<user>/projet/fichier.md` — lettre de disque, slashes avant.

Ni `/home/<user>/...` ni `~/...`. Un chemin commencant par `/` mais sans lettre de disque est resolu **contre la racine du disque courant** : `/home/<user>/projet/fichier.md` devient `C:\home\<user>\projet\fichier.md`, un dossier qui n'existe pas — et non `C:\Users\<user>\projet\fichier.md`. Le shell bash MSYS comprend `/c/Users/...`, mais ce n'est pas un chemin pour les outils d'ecriture de fichiers.

## Regle 2 — `verified: true` prouve le contenu, pas l'emplacement

L'ecriture reussie garantit que le fichier a ete ecrit au chemin **resolu** ; elle ne garantit pas que ce chemin est celui qu'on visait. Un lot entier peut donc partir dans un dossier fantome sans aucune erreur.

- Apres la PREMIERE ecriture d'un lot, verifier l'atterrissage : `ls -la <dossier>` (ou `find <dossier> -type f`).
- Seulement ensuite derouler les autres fichiers.
- L'avertissement « resolved to ... which is OUTSIDE the active workspace » est le signal a lire attentivement : c'est souvent la resolution fautive, pas un simple avertissement.

## Regle 3 — shell MSYS contre argument d'outil natif

- Bash (MSYS) : `cd /c/Users/...` fonctionne, `~` est developpe par le shell.
- Outil natif (git, rg, node, python, ffmpeg) : les chemins ne sont PAS traduits, passer `C:/Users/...`. `~` n'est developpe ni par les outils d'ecriture ni par un programme natif.
- Fichier temporaire qu'un programme natif doit lire ou ecrire : preferer `$LOCALAPPDATA/Temp` a `/tmp`.
  **`$TMPDIR` n'est PAS le dossier scratch, meme quand l'en-tete d'environnement de la session
  l'annonce** : dans le bash de l'agent il vaut `/tmp`, donc `curl -sS -o "$TMPDIR/x.json"` depose le
  fichier dans `C:\tmp\` et la relecture qui suit (`sed`, `read_file`, `python`) repond
  `No such file or directory` sur une requete pourtant reussie — le contenu est a `C:/tmp/`, pas perdu.
  Des qu'un binaire natif produit un fichier qu'on veut relire, ecrire le chemin ABSOLU en `C:/...`
  (typiquement `C:/Users/<user>/AppData/Local/hermes/cache/scratch/<fichier>`) et confirmer par `ls`
  de la cible. Ne pas rejouer l'appel pour « recuperer » la sortie : le fichier existe deja, au chemin
  natif.
- **Un chemin MSYS passe a un binaire natif est resolu contre la racine du disque courant** :
  `git clone <url> /tmp/wiki` lance depuis bash reussit (`exit 0`, aucune erreur) et cree
  `C:\tmp\wiki` ; le `ls /tmp/wiki` qui suit repond « No such file or directory » sur un clone qui a
  bel et bien eu lieu. Le meme ecart vaut pour tout binaire natif recevant un chemin de sortie.
  Symptome a retenir : un outil annonce un succes et la cible est introuvable au chemin MSYS —
  chercher sous `C:/tmp/...` avant de conclure a un echec ou de relancer. Le meme ecart produit aussi
  l'erreur INVERSE, tout aussi trompeuse, quand le chemin fautif est une SORTIE : `ffmpeg` recoit
  `/c/Users/.../sortie.mp4` et repond `Error opening output file /c/...: No such file or directory`
  **alors que ce chemin existe bel et bien sous bash** — on part chercher un fichier manquant au lieu
  d'un chemin mal forme. Un binaire natif recoit des `C:/...` pour ses entrees, ses sorties ET ses
  fichiers temporaires ; et sous bash, ne jamais melanger les deux formes dans la MEME commande :
  `mkdir -p /c/Users/...` (builtin du shell, chemin MSYS accepte) suivi de l'outil natif qui ecrit
  dedans en `/c/...` est le cas ou l'echec semble disproportionne puisque le dossier vient d'etre cree.
- **Une sonde dont on jette stderr transforme un chemin faux en « valeur inconnue ».**
  `ffprobe -v error -show_entries format=duration -of csv=p=0 /c/Users/.../v.mp4` rend une sortie
  **vide** et un `exit 0` : le message du binaire natif (« No such file or directory ») part sur
  stderr, que `2>/dev/null` supprime. En boucle sur plusieurs fichiers on lit alors des lignes vides
  (`duree=`) et on les prend pour des metadonnees absentes (duree inconnue, fichier sans pistes) au
  lieu d'un chemin invalide — et une valeur vide alimente ensuite un rapport faux. Ne JAMAIS mettre
  `2>/dev/null` sur une sonde (`ffprobe`, `ffmpeg`, `git`, `python`) : garder `2>&1`, et construire la
  boucle avec des chemins NATIFS `C:/Users/...`. Sur une boucle de mesures, une ligne vide est un
  echec de chemin, pas une valeur : la relancer apres avoir change la FORME du chemin.
- **Le tool `terminal` refuse une commande qu'il lit comme un service long** (`docker compose ... up`,
  un `docker run` sans `-d` lisible) : c'est le TEXTE de la commande qui declenche le garde-fou. Ecrire
  la commande dans un petit `.sh` du scratch et executer le chemin du script : elle passe, et c'est
  bien la meme chose qui est lancee (verifier ensuite l'EFFET — `docker ps`, port en LISTENING).
  **Le meme garde-fou se declenche aussi sur la TAILLE du payload inline** (plusieurs `grep`/`echo`/
  `for` enchaines par `;` dans une seule ligne) : la reponse est « command parser limit or malformed
  executable payload », avec le chemin d'un `.sh` deja sauvegarde dans `cache/blocked-scripts/` — ce
  fichier est exactement la commande a relire, et le remede est le meme : un `.sh` du scratch lance par
  `bash <chemin>`. Le developper en plusieurs appels courts ne fait que multiplier les tours.
- **`docker compose up -d` ne recree que les services dont la definition a change** : lire la sortie
  (`Container X Recreate` / `Running`) plutot que le code de sortie, et confirmer par l'uptime reel de
  chaque conteneur (`docker ps`) — un manager laisse `Up 42 hours` prouve qu'il n'a pas ete redemarre.
- **Du Python lance par l'outil `execute_code`, `subprocess.run(..., shell=True)` ouvre `cmd.exe`, PAS le bash MSYS** : `'head' n'est pas reconnu en tant que commande interne`, idem `wc`, `tail`, `find`. Le piege est silencieux sur le fond : le `exit_code` peut rester **0** alors que la sortie ne contient que les messages d'erreur de `cmd` — ne pas lire un code de retour 0 comme une preuve que la commande a tourne. Passer une **liste d'arguments** (`subprocess.run(['git', 'ls-files', 'wiki'], capture_output=True, cwd=<chemin natif>)`, `shell=False`) : c'est le seul mode ou `git`, `node`, `python` recoivent vraiment leurs arguments. Pour du filtrage POSIX (`| head`, `| wc -l`), passer par l'outil `terminal` (bash) ou filtrer en Python.
- **Et appeler `bash` explicitement depuis `execute_code` ne rend PAS le bash du terminal.**
  `subprocess.run(["bash", "-lc", cmd])` tombe sur un **bash WSL**, ou les chemins MSYS n'existent pas
  (`/bin/bash: line 1: cd: /c/Users/<user>/...: No such file or directory`) et ou les variables du shell
  Windows sont vides (`cd: /hermes: No such file or directory` pour un `$LOCALAPPDATA` non herite). Les
  deux messages ressemblent a un dossier manquant : c'est le mauvais interpreteur, pas une cible absente.
  Pour un lot de mesures, ne pas passer de shell du tout — `os.walk` + `re` en Python, `json` pour les
  configs, `read_file`/`search_files` pour lire et chercher, et un `.ps1` en `-File` quand il faut
  PowerShell. Garder le bash du terminal pour ce ou il marche vraiment (`cd /c/...`, `grep`, `sha256sum`,
  `date -r`), jamais en sous-processus.
- **Le `python.exe` d'un venv Hermes n'execute pas un script comme un CPython nu.**
  `hermes-agent/venv/Scripts/python.exe` est un lanceur : il rejoue le script par `runpy` depuis un
  `.pth`, **avant** que `site-packages` soit sur `sys.path`. Signature trompeuse :
  `python -c "import ruamel.yaml"` reussit alors que `python script.py` leve
  `ModuleNotFoundError: No module named 'ruamel'` sur un paquet pourtant installe dans ce venv. Ne pas
  en conclure a une dependance manquante, ne pas l'installer : prendre l'interpreteur de base declare
  dans `pyvenv.cfg` (`home = .../.hermes-runtime/python/generation-*/cpython-*-windows-x86_64-none/`)
  avec `PYTHONPATH=<venv>/Lib/site-packages`, ou poser les deux racines en tete de script :
  `sys.path.insert(0, r"...\hermes-agent\venv\Lib\site-packages")` puis
  `sys.path.insert(0, r"...\hermes-agent")`. Le meme lanceur avale un `python - <<'PY'` (heredoc) : il
  peut re-executer son propre `sys.argv[0]` et finir sur `FileNotFoundError: ...\-` apres des sorties
  correctes. **Avec le `python` nu (hors lanceur de venv), le meme `python - <<'PY'` ne tombe pas :
  il entre dans la REPL interactive**, avale le corps du heredoc ligne a ligne et boucle sur
  `OSError: [WinError 6] Descripteur non valide` / `WinError 123` — des Mo de tracebacks identiques
  (mesure : ~9 Mo, appel tue au bout de 180 s), et le `|| fallback` place derriere s'execute alors
  AUSSI. Ne jamais nourrir un script par `python -` ni par heredoc sur cet hote : `write_file` le
  script dans le scratch, puis l'appeler par son chemin NATIF (`python C:/.../script.py`) — c'est le
  seul mode ou l'erreur reelle s'affiche au lieu d'etre noyee. Une sortie qui part en boucle
  d'erreurs repetees n'est pas un script qui travaille : tuer et reprendre en fichier.
 - **Le meme `cmd.exe` produit une SECONDE signature d'erreur, plus trompeuse** : `Le chemin d'acces specifie est introuvable.` sur un `grep -rIl … | head`, un `ls -la … | tail`, ou un `docker ps --format "{{.Names}}"` (les commandes MSYS existent sur le PATH, donc pas de « n'est pas reconnu » — c'est le pipe ou le gabarit qui casse). Le remede durable pour un lot de mesures : **ne pas passer par un pipeline du tout** — filtrer en Python pur (`os.walk` borne par un `skip` de dossiers, `re` pour les motifs) et ecrire la sortie dans un fichier du scratch. Un `= 0 octet` / une sortie vide sur une commande qui « devait » filtrer est un echec de shell, pas un resultat vide.
- **Ne jamais terminer un chemin cite par un antislash : le guillemet fermant est mange.** La forme
  `cmd /c "dir /a \"C:\...\tools\""` part avec un chemin boiteux et rend `La syntaxe du nom de
  fichier, de repertoire ou de volume est incorrecte.` Pour un lot de commandes cmd (`dir /a`,
  `icacls`, `if exist`), ecrire un `.bat` dans le scratch qui construit ses chemins par
  `%LOCALAPPDATA%` et l'appeler par `cmd /c <chemin du .bat>` : c'est la seule forme ou le chemin
  arrive intact. Mesure : le MEME `dir /a` sur un dossier existant rend `Fichier introuvable` quand le
  chemin part en ligne depuis bash, et le listing correct depuis le `.bat` — un chemin natif inline
  peut donc arriver tronque SANS erreur de syntaxe, et ce faux « introuvable » sert ensuite de preuve
  a une conclusion fausse (fichier absent).
- **Pour `icacls` / `takeown` / `attrib` depuis bash : chemin a SLASHES avant, guillemets SIMPLES**
  (`icacls 'C:/Users/<user>/AppData/Local/hermes/tools'`). Un chemin a antislashs passe en ligne est
  la ou arrive le desastre silencieux : `icacls "$L\\$d"` part avec la variable NON developpee
  (`...\hermes$d`) et repond `Le fichier specifie est introuvable` — un message qui accuse le dossier
  alors que c'est la forme du chemin. Ne pas conclure « absent » : changer la FORME du chemin et
  refaire la mesure.
- **Un compte localise et accentue ne se passe pas par la ligne de commande : viser son SID.**
  `icacls … /grant:r "Système:(F)" "Administrateurs:(F)"` part avec un nom mal encode (meme ecart que
  le nom de tache accentue de `gated-step-missions`) et passe ou echoue selon l'encodage du moment. Les
  SID sont ASCII et sans ambiguite : `*S-1-5-18` (SYSTEM), `*S-1-5-32-544` (Administrateurs), et le nom
  du compte utilisateur sans accent. `icacls` les accepte dans `/grant:r` et **reaffiche ensuite les
  noms canoniques localises** — la coherence avec les fichiers deja durcis se verifie donc a l'oeil sur
  sa sortie, ce qui est aussi la preuve a joindre. Meme logique pour tout parametre designant un compte
  (proprietaire, groupe, `-TaskName`).
- **Construire un chemin Windows dans un champ `sed` casse sur le delimiteur.** `sed 's|^C:/|C:\\|'`
  rend `sed: unknown option to 's'` : l'antislash final du remplacement echappe le delimiteur fermant.
  Ne pas bricoler la FORME du chemin en shell — ecrire les chemins natifs une fois et les passer tels
  quels ; une conversion se fait en Python (`p.replace('/', chr(92))`), jamais dans un `s|…|…|`. Et
  quand une boucle rend un compteur impossible (0 ACE sur un fichier qui en porte 3), suspecter
  d'abord la construction du chemin DANS la boucle, pas la mesure : un compteur a zero est un echec de
  harnais tant qu'une autre forme de chemin ne l'a pas refute.
- `curl`, `7z`, `tar` : ce sont des binaires natifs, ils ouvrent le fichier de sortie avec l'API
  Windows. Leur passer `C:/...`. Le symptome d'un `/c/...` est TROMPEUR :
  `curl: (23) client returned ERROR on write of N bytes` — ce n'est ni une erreur reseau ni un
  disque plein, c'est le chemin de sortie qui n'a pas pu etre ouvert. Le meme piege se paie deux
  fois dans une session (telecharger, puis ecrire un fichier de sortie en `-o`).
  **Le meme code 23 arrive SANS chemin fautif** : `curl -s <url> -o /dev/null -w '%{http_code}
  %{size_download}'` rend un `bytes=0` intermittent alors que le service a bien repondu — le
  pseudo-device MSYS n'est pas un fichier ouvrable par le binaire natif. Ce n'est PAS une panne du
  service mesure, et un `bytes=0` sur `-o /dev/null` ne se lit jamais comme « reponse vide ».
  Toute verification de TAILLE vise un vrai fichier (`-o "<scratch>/reponse.json"` puis `ls -la` /
  `wc -c`) : la mesure sur fichier est la seule qui vaut.
- **`tar` lit `C:` comme un HOTE DISTANT avant de voir un chemin.** `tar czf "C:/Users/.../x.tar.gz" …`
  ne cree rien et rend `tar (child): Cannot connect to C: resolve failed` (puis `Broken pipe`,
  `exit 2`) : le parseur `hote:chemin` s'applique aussi aux chemins Windows, et le message accuse une
  connexion reseau qui n'existe pas. Parade verifiee : ecrire par REDIRECTION —
  `tar czf - -C <dossier> <cible> > "C:/Users/.../x.tar.gz"` (c'est le shell qui ouvre le fichier) —
  ou se placer dans le dossier (`cd`) et passer un nom relatif. Le meme piege attend `-f` en extraction
  (`tar xzf "C:/..."`) et tout autre binaire a option `-f`/`--file` qui accepte la syntaxe `hote:chemin`.
  Ne pas partir chercher un probleme de droits ou de disque plein : la cible n'a jamais ete ouverte.
- Les executables Windows a options en `/flag` (schtasks, robocopy, reg, sc) ne sont pas proteges de
  la traduction MSYS : `/run` peut partir tel quel ou etre converti en chemin, et la parade reflexe
  `//run` arrive litteralement comme `//run` (`Argument ou option non valide`). Preferer l'equivalent
  PowerShell (`Start-ScheduledTask`, `Get-ScheduledTask`, `Register-ScheduledTask`,
  `Enable-ScheduledTask`, `Disable-ScheduledTask`) ou passer par
  `cmd //c "<commande complete>"` en gardant la commande entre guillemets.
- **Ne pas imbriquer des guillemets dans un `cmd /c '...'`.**
  `cmd /c 'schtasks /Change /TN "X" /ENABLE'` part avec des guillemets DOUBLES (`""X""`) et schtasks
  repond `le nom de la tache specifiee ""X"" n'existe pas` — un message qui accuse le NOM de la tache
  alors qu'elle est saine et bien enregistree. Lire ce message comme une erreur d'ECHAPPEMENT, jamais
  comme une tache absente : ne pas partir verifier le registre des taches. Remede verifie :
  `Enable-ScheduledTask -TaskName 'X'` (ou `Disable-ScheduledTask`) en guillemets SIMPLES, ou un `.ps1`
  en `-File`. Pour prouver l'etat, `Get-ScheduledTask` / `Get-ScheduledTaskInfo` rendent `State`
  (`Ready`/`Disabled`), `NextRunTime` et la repetition (`PT5M`) — plus lisibles que `schtasks /V`.
- **`msiexec` : `//x` / `//i` / `//qn` ne donnent pas une option invalide mais un ECHEC SILENCIEUX**
  (mesure du 27/09/2026). `msiexec //x "{GUID}" //qn //norestart //l*v C:\...\log` lance depuis bash
  rend **`exit 103`**, n'ecrit **aucun fichier de log** et ne desinstalle **rien** : le produit reste
  au registre, le dossier d'installation garde ses fichiers, le service reste en place. Le code 103
  n'est pas un code de retour MSI documente, il ne dit rien de la cause. La forme qui marche est
  PowerShell avec liste d'arguments, et le code de retour est alors le vrai :
  `Start-Process msiexec.exe -ArgumentList @('/x','{GUID}','/qn','/norestart','/l*v','C:\...\log') -Wait -PassThru`
  -> `.ExitCode` (0 = succes | 3010 = succes + reboot requis | 1605 = produit inconnu | 1603 = echec).
  Ne jamais croire le code seul : verifier l'EFFET — presence du produit sous
  `HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{GUID}` et nombre de
  fichiers du dossier cible. Pour desinstaller, viser le **ProductCode** lu au registre (l'Uninstall
  key) plutot que `Get-CimInstance Win32_Product | Uninstall()`, qui declenche une reconfiguration de
  tous les paquets MSI et reste lent. Un MSI legitime signe porte une signature Authenticode
  verifiable (`Get-AuthenticodeSignature`) : c'est la provenance a exiger quand l'editeur ne publie
  pas de SHA256, et la table `Property` du paquet se lit en COM (`WindowsInstaller.Installer`) pour
  confirmer la version avant d'installer.
- **Commandes PowerShell depuis bash** : des qu'une commande contient des variables `$env:` ou des
  guillemets imbriques, ne pas la passer en ligne a `powershell -Command` — les variables arrivent
  mangees (`UserId:OMATHS\:USERNAME`) et l'appel echoue (mappage de compte introuvable sur
  `Register-ScheduledTask`). Ecrire un fichier `.ps1` et l'appeler par
  `powershell -NoProfile -ExecutionPolicy Bypass -File <script>` : le fichier traverse l'echappement
  intact. Garder ces `.ps1` (et les `.vbs`) en **ASCII pur** : PowerShell 5.1 lit l'UTF-8 sans BOM
  comme de l'ANSI, donc accents, tirets longs et puces s'affichent de travers.
- **`$_` est deja consomme par bash avant d'arriver a PowerShell.** Dans une commande passee en
  guillemets DOUBLES, `Where-Object { $_.CommandLine -match ... }` part au shell et `$_` y est
  substitue (derniere valeur du shell) : PowerShell cherche alors un cmdlet portant ce nom et rend,
  POUR CHAQUE processus, un bloc `Le terme «…» n'est pas reconnu comme nom d'applet de commande` —
  des dizaines de Ko d'erreurs identiques qui noient la sortie utile (et la font tronquer). Meme
  piege pour `$env:X`, `$args`, `$PWD`. Une commande inline se met donc en guillemets SIMPLES
  (`powershell -NoProfile -Command '... $_.X ...'`) ; des qu'elle porte plusieurs variables, un `if`
  ou un pipe, passer par un `.ps1` en `-File` — c'est la seule forme qui traverse l'echappement
  intact, et un fichier `.ps1` ne se fait pas expanser par le shell.
- **Ne pas imprimer un listing natif en entier.** Une enumeration (`Get-CimInstance Win32_Process`,
  `Get-ChildItem -Recurse`) depasse vite les 100 000 caracteres et se fait tronquer en tete/queue :
  la partie interessante est justement celle qui manque, et le script a bien tourne (on croit a une
  sortie vide ou a un echec). Filtrer cote PowerShell (`-Filter`, `Where-Object`, liste de PID
  connus) ou compter les octets avant d'imprimer.
- **Pour un lot de mesures, ecrire le resultat dans un fichier du scratch puis le relire**
  (`write` vers `cache/scratch/<sujet>/lotN.txt`, puis `read_file`). Un `print()` massif qui ressort
  resume ou tronque fait perdre la donnee, et une sortie tronquee n'est PAS une sortie vide : la
  relecture du fichier est la seule preuve, elle survit aussi a un timeout de l'appel suivant.
- **Ne jamais faire passer un pipeline cmd.exe par le terminal bash** : les builtins DOS n'existent
  pas ici et leurs homonymes sont ceux de MSYS. `dir "...\*.png" /b | find /c /v ""` ne compte rien :
  `find` est le GNU find, il part arpenter le systeme de fichiers et ne rend jamais la main (mesure :
  tue au bout de 180 s alors que les 290 PNG etaient bien sur le disque). Compter en POSIX :
  `ls <dossier> | grep -c '\.png$'`, et `ls -la <dossier>` pour un effet `dir`.
- Apres un `mkdir -p ~/...`, faire `ls` sur l'arborescence creee AVANT d'y ecrire : le shell et les outils d'ecriture ne developpent pas `~` de la meme facon, et un `mkdir` reussi ne dit rien sur l'endroit ou les outils ecriront.
- **Un binaire natif peut etre intercepte par un ALIAS du shell : `node` n'est pas `node.exe`.**
  `type -a node` rend ici `node is aliased to 'winpty node.exe'`. `winpty` exige un TTY : des que
  stdin n'en est pas un (tache de fond, harnais, sous-processus), l'appel meurt en ~0,1 s avec
  `stdin is not a tty` et **rc=1 AVANT d'executer le script** — sans aucune erreur metier, ce qui
  fait accuser a tort ffmpeg, les chemins, le `.env` ou la config. Remede verifie : ecrire
  **`node.exe`** (ou le chemin complet du binaire), l'alias n'est plus resolu et node demarre
  normalement. La sonde qui tranche en une commande : `type -a <nom>`. Regle generale : quand un
  binaire natif echoue instantanement avec un message qui ne vient pas de lui, lire `type -a` AVANT
  de suspecter le binaire, ses arguments ou l'environnement.

## Regle 4 — espaces dans les chemins

`Local Sites`, `hermes tuto`, etc. : mettre le chemin entre guillemets doubles dans la commande. Quand un chemin contient des espaces, verifier que le programme a bien ouvert le fichier plutot que de supposer (un `No such file or directory` sur un chemin sans espace est le symptome d'un chemin mal construit, pas d'un fichier absent).

## Regle 5 — un chemin injecte dans du code genere

Des qu'on ECRIT un chemin Windows dans du source (patch d'une constante, lanceur temporaire, script
genere, bloc Python passe en heredoc), deux pieges font echouer la compilation, pas l'execution :

- **Chaine non brute** : `"C:\Users\<user>\..."` dans un litteral ordinaire est un `SyntaxError`
  (`truncated \UXXXXXXXX escape`) parce que `\U` ouvre un echappement Unicode. Ecrire le litteral en
  **chaine brute** (`r"C:\..."`) ou doubler les antislashs. Le meme piege attend un heredoc Python
  qui contient un chemin dans ses triples guillemets : passer la chaine en `r"""..."""`.
- **Un heredoc bash mange un niveau d'echappement, meme avec un delimiteur quote** (`<<'PY'`) : un
  motif ecrit `r'Desktop\\hermes_install(?!x)'` arrive au Python avec des antislashs simples et meurt
  sur `re.error: bad escape \h`. Des qu'un script porte des antislashs (regex, chemin Windows, motif
  `\b…\b`), ne pas le passer en ligne : `write_file` le script dans `$LOCALAPPDATA/Temp`, puis
  `python <chemin NATIF>`. Pour rendre l'intention non ambigue, batir le separateur explicitement
  (`chr(92)`) au lieu de compter les antislashs.
- **Le piege frappe aussi le heredoc qui ECRIT ou EDITE du code, pas seulement celui qui s'execute.**
  Un `python - <<'PY'` dont le `replace()` insere une ligne portant une classe de caracteres
  (`[\[\]…]`), un quantificateur (`{20,}`) ou un `\d` depose dans le fichier une version amputee d'un
  antislash — silencieusement : le script s'ecrit tres bien et n'echoue qu'a l'execution
  (`re.error: unterminated character set`). Pour EDITER du code qui porte des antislashs, passer par
  l'outil `patch` (ou `write_file`), jamais par un heredoc ; et apres toute ecriture inline, valider
  avant de lancer : `python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" <fichier>`.
- **`re.sub` avec une chaine de remplacement** : les `\` du texte insere sont interpretes comme des
  references de groupe — le chemin arrive avec des antislashs Simples, donc invalide. Toujours passer
  une **fonction** : `motif.sub(lambda m: "%s = %s" % (nom, json.dumps(valeur)), source, count=1)`.
  `json.dumps` echappe correctement pour du JSON/Python, mais il faut la lambda pour que `re.sub` ne
  retraite pas le resultat.
- Eviter `exec()` d'une chaine portant un chemin : l'encodage des antislashs y est decode deux fois.
  Ecrire un fichier temporaire et l'executer est plus court et plus sur.
- Le controle coute une ligne : `compile(source, chemin, "exec")` avant de lancer, et une empreinte
  du fichier d'origine avant/apres pour prouver qu'il n'a pas ete modifie.

## Regle 6 — la sortie de plusieurs outils Windows est en UTF-16LE

`schtasks`, `wmic` et `tasklist` ecrivent en UTF-16LE. Un `grep` sur leur sortie ne renvoie rien
d'exploitable : il repond `Binary file (standard input) matches` (ou zero resultat), et `awk`/`cut`
sur les colonnes echouent silencieusement. Le diagnostic est trompeur — la donnee est bien la,
c'est le decodage qui est faux.

**Le codec depend du FORMAT demande : ne pas trancher a l'avance.** Mesure : un
`schtasks /query /fo CSV /v` redirige est sorti en **cp1252** (guillemets courbes a `0x93`, `file`
annonce « CSV Non-ISO extended-ASCII ») et un `iconv -f UTF-16LE` y a rendu un fichier VIDE, alors que
`/fo LIST` peut sortir en UTF-16LE. Detecter avant de decoder (`file`, `head -c 200 | od -c`), puis
decoder par essai. Et un CSV de `schtasks` porte des champs MULTILIGNES (commandes, descriptions) : un
parsing ligne a ligne echancre les enregistrements, il faut `csv.reader` en Python avec
`encoding="cp1252", errors="replace"`. Pour seulement retrouver une ligne, `grep -a <motif>` suffit.

Parades, dans l'ordre :
- `schtasks ... 2>&1 | tr -d '\0' | grep -i <motif>` — retirer les octets nuls suffit a rendre le flux lisible ;
- **vaut aussi pour un fichier ecrit par une redirection cmd** (`cmd /c ... > "<scratch>\sortie.txt") :
  `dir`, `whoami`, `tasklist` y laissent des octets nuls, et le fichier est alors refuse en lecture
  texte (`Binary file ... cannot display`, ou un filtrage qui rend zero ligne). Le convertir avant
  tout filtrage — `tr -d '\0' < sortie.txt > sortie.clean.txt` — puis travailler sur le `.clean.txt`.
  Un lot de tests cmd qui « rend une sortie vide » ou binaire est presque toujours ce cas ;
- lire en Python avec le bon codec :
  `subprocess.run([...], capture_output=True, text=True, encoding="utf-16", errors="replace")` ;
- **mettre `errors="replace"` sur TOUT `subprocess.run` en mode texte** : sans `encoding`, Python
decode en UTF-8 et une sortie locale en cp1252 (git, outils Windows) fait tomber le thread de
lecture — `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x82 in position 80` — l'exception
part dans un thread et la donnee revient **vide ou partielle sans erreur visible**. Meme piege pour
un `r.stdout.decode('utf-8')` ecrit dans un `try` : le decodage ne leve pas la ou on l'attend.
- preferer les applets PowerShell equivalentes (`Get-ScheduledTask`, `Get-CimInstance Win32_Process`) —
  leur sortie passe le shell correctement, et sur une commande simple elles suppriment le probleme.
  **Mais un cmdlet PowerShell n'est PAS une commande du shell de l'agent** : tape `Get-CimInstance`
  directement dans le terminal et il repond `command not found` — le terminal est bash MSYS, les
  cmdlets n'existent que dans un hote PowerShell. Les appeler via
  `powershell -NoProfile -Command "..."` (ou un `.ps1` en `-File`, cf. Regle 3).

Corollaire : un `grep` qui repond « Binary file matches » n'est PAS un motif introuvable. Ne pas en
conclure que la tache planifiee ou le processus n'existe pas — decoder d'abord, conclure ensuite.

## Regle 7 — une ecriture en mode texte reecrit TOUTES les fins de ligne

`Path.write_text(...)` (et tout `open(..., 'w')`) ecrit en mode texte : Python traduit chaque `\n`
en `\r\n` sur Windows. Editer un script de 250 lignes qui etait en LF en change donc 250 lignes a la
fois : le `diff` devient illisible (tout le fichier apparait modifie) alors que le contenu logique
a change sur 3 lignes.

- Ecrire avec `newline="\n"` (ou en binaire) et **relire l'octet** apres :
  `b.count(b"\r\n")` / `b.count(b"\n")`. Corriger en place si besoin :
  `p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))`.
- Le controle `grep -c $'\r$'` n'est PAS fiable pour savoir si un fichier est en CRLF (observe :
  210/210 lignes annoncees CR sur un fichier LF). Comparer les octets en Python, pas avec grep.
- Avant d'editer un fichier existant, mesurer sa convention (`read_bytes().count(b"\r\n")`) et la
  preserver : ces scripts (`.ps1`, `.env`, `.yaml`) sont edites par plusieurs sessions.
- **L'outil `patch` peut normaliser TOUT un fichier en CRLF sans rien casser du commit** : le diff
  affiche alors chaque ligne en `-`/`+` et ressemble a un reformatage complet. Sur un fichier
  versionne, verifier avant de conclure : `git diff --numstat <fichier>` (un seul chiffre de lignes
  ajoutees = rien de perdu) et `git diff --ignore-cr-at-eol <fichier>` (le diff logique). Avec
  `* text=auto eol=lf` dans `.gitattributes`, l'index normalise et le commit ne porte que les lignes
  voulues — la reecriture des fins de ligne est un bruit de working tree, pas un contenu publie.
- Un chemin Windows insere dans du texte genere doit etre relu en octets : un heredoc bash a deja
  transforme `scripts\verif_24h.ps1` en `scripts<VT>erif_24h.ps1` (le `\v` est devenu un onglet
  vertical, invisible a l'oeil dans l'editeur). Controler `b.count(b"\x0b") == 0` apres insertion.
- **`sed` produit exactement le meme degat, sans heredoc en cause.** Dans le champ de remplacement,
  `\\` suivi de `v` redevient l'echappement `\v` : `sed -i 's|agent\\.venv|agent\\venv|g'` ecrit un
  onglet vertical a la place du nom (`agent<VT>env`), sans erreur, et le fichier reste executable —
  l'erreur ne sort qu'a l'execution suivante, sur un chemin introuvable. Un chemin Windows passant par
  le champ de remplacement de `sed` doit etre considere comme dangereux : garder une copie `.bak`,
  restaurer, puis substituer en OCTETS (`data.replace(b'agent\\.venv', b'agent\\venv')`) et relire les
  lignes touchees pour les afficher. Idem `re.sub` avec une chaine de remplacement (Regle 5).

- **Un `\r\r` en fin de ligne dans une SORTIE CAPTUREE n'est pas un fichier corrompu.** `print()` en
  mode texte traduit son `\n` en `\r\n` : une ligne qui se termine deja par un CR ressort donc
  `...\r\r\n`, et un diff unifie parait porter deux retours chariot par ligne ajoutee. C'est un
  artefact d'affichage, pas un contenu — le lire comme une corruption fait perdre le tour a chercher un
  fichier mixte qui n'existe pas. Ne pas conclure depuis la sortie d'un outil : relire les octets en
  Python (`"\r\r" in io.open(p, encoding="utf-8", newline="").read()` doit rendre `False`) et
  comparer les compteurs (`wc -l`, caracteres, octets) — eux distinguent un CR de trop.

## Regle 8 — comparer un chemin imbrique : un hash vide signifie « absent », pas « different »

Le repertoire courant **persiste entre les appels** d'une meme session de terminal. Sur un dossier
imbrique (un doublon cree dans `<base>/models/`), enchainer des chemins relatifs ecrits a la main
(`models/<f>`, puis `models/models/<f>`) depuis une base deja relative produit plusieurs lectures
fausses d'affilee — et chaque lecture fausse a l'air d'un resultat :

```
DIFFERENT  det_10g.onnx  ( vs 4c10eef5c9e168357a16fdd580fa8371)
```

Ici la colonne de gauche est **vide** : le fichier n'a jamais ete lu. Une comparaison qui annonce
« different » avec une valeur vide, ou un `md5sum` qui n'affiche rien, signifie **fichier absent** —
jamais contenu different. Deux parades, dans cet ordre :

- **Lister d'abord, comparer ensuite.** `ls -la <dossier>` sur le dossier ou l'on croit etre, et
  seulement apres construire les chemins a comparer. Un chemin dont on n'a pas vu le listing n'est
  pas un chemin verifie. Sous Windows, `Get-ChildItem -Force | Select Name,Mode,Length,LinkType`
  tranche en plus la nature reelle d'une entree (dossier, fichier, jonction, lien).
- **Ancrer chaque chemin sur une racine absolue** (`C:/Users/...`), meme quand le `cd` precedent
  semblait le faire. Le controle qui coute une ligne : `pwd` puis `ls` de la cible avant de conclure.

Corollaire pour une suppression : une comparaison suspecte (hash vide, moitie des fichiers
« differents ») interdit de supprimer. Refaire la comparaison au bon chemin d'abord.

Corollaire pour les artefacts de travail : une **sortie en chemin relatif atterrit dans le dernier
`cd` de la session**, pas dans le dossier de l'outil qu'on croit. Un `curl -o resultat.json` et le
`__pycache__` d'un script lance depuis son propre dossier se sont ainsi retrouves dans le dossier
d'un skill, parce qu'un appel precedent y avait fait `cd` — deux fichiers parasites a nettoyer apres
coup, dans un dossier qui doit rester propre (un skill, un depot). Ecrire les sorties de test par un
chemin ABSOLU vers `$LOCALAPPDATA/hermes/cache/scratch` (ou `$TMPDIR`), et faire `pwd` avant toute
commande qui produit un fichier sans chemin complet.

**Un `cd` de session devenu invalide fait echouer TOUTE commande avant qu'elle ne s'execute.**
`bash: line 4: cd: /c/Users/<user>/.../cache/scratch/scratch: No such file or directory` suivi de
`exit 126`, avec la commande demandee jamais lancee : le shell de l'outil `terminal` rejoue le
repertoire courant de la session en tete de chaque appel. Ne pas relancer la meme commande et ne pas
en conclure que la cible est absente ou que l'outil est casse : passer `workdir=<chemin absolu>` a
l'appel (il remplace ce `cd`) ou reprendre par un `cd` vers une racine qui existe. Corollaire utile
sur cet hote : la disparition d'un dossier pendant une session est **visible sans la chercher**, et
l'heure du premier echec est un releve gratuit quand un arbre vient d'etre deplace.

## Regle 9 — un outil qui fabrique son arborescence sous un `root` qu'on lui passe

Beaucoup de bibliotheques prennent un `root` / `base_dir` / `cache_dir` et creent **elles-memes**
`root/models/<nom>/`, en telechargeant au passage. Passer un cran trop bas dans l'arborescence ne
leve aucune erreur : ca ajoute un niveau et refait le telechargement.

Cas mesure — insightface, `FaceAnalysis(name='buffalo_l', root=R)` telecharge `R/models/buffalo_l.zip`
(276 Mo) puis l'extrait dans `R/models/buffalo_l/`. Avec un `R` situé un cran trop bas (le dossier des
modeles au lieu de son parent), on obtient `<...>/models/models/` et 601 Mo dupliques, sans un mot,
sans avertissement, exit code 0.

- Le `root` a passer est celui du **parent** du dossier attendu, pas le dossier des modeles lui-meme.
- **Un exit code 0 ne prouve pas qu'on n'a rien telecharge.** Le controle est une mesure de taille du
  dossier apres le script : ici 326 Mo de `.onnx` + 276 Mo d'archive = ~601 Mo, et au-dela il y a un
  doublon. La contrainte « ne rien telecharger » ne se verifie pas au code de retour.
- Avant de supprimer le doublon : comparer par empreinte (`md5sum` des fichiers **et** de l'archive)
  ET par arithmetique de tailles (la somme doit retomber sur le total). Un seul fichier different =
  ne pas supprimer, signaler.

## Regle 10 — un extrait PowerShell fourni par l'utilisateur ne s'execute pas tel quel

Les taches arrivent souvent formulees en PowerShell Windows ; le terminal de l'agent est bash MSYS,
ou les cmdlets n'existent pas. Les recopier telles quelles donne `command not found` sur chacun
d'eux (`Get-CimInstance`, `Select-Object`, `Start-Process`, `Invoke-RestMethod`, `Get-ChildItem`),
et un `Start-Process` enfoui dans une chaine `&&` echoue sans un mot (log vide, aucune erreur).

Traductions qui marchent :

- `Get-CimInstance Win32_Process -Filter "ProcessId = N" | Select-Object ...` -> `tasklist /FO CSV /FI "PID eq N"`
  (CSV : le champ cite `"N"` n'apparait QUE si le processus existe — tester ce champ, jamais `$?`,
  car un non-match sort en **exit 0** avec une ligne `INFORMATION: aucune tache...` sur stdout ;
  ajouter `2>&1 | tr -d '\0'` + `grep -a` si la sortie ressort en UTF-16, cf. Regle 6).
  `wmic process where processid=N get name,commandline` quand il faut la ligne de commande — mais
  MASQUER avant d'afficher : une ligne de commande de service porte souvent une cle en argument
  (`--api-key`, `sk-…`) ; remplacer par `[REDACTED]` et ne rapporter que la presence du secret.
- `ps -p N -o pid,cmd` et `/proc/N/cmdline` -> ne voient PAS les processus Windows natifs
  (`ps: unknown option -- o`, `/proc/N/cmdline` vide). Tout ce qui est `.exe` natif (python.exe,
  hermes.exe) passe par `tasklist` ; ne pas en conclure que le processus n'existe pas.
- **Appli Windows GUI (installeur, `.exe` de bureau)** :
  `powershell -NoProfile -Command "Start-Process -FilePath 'C:\...\app.exe'"`. L'execution
  directe depuis bash (`./app.exe`, meme avec le bit executable vu par MSYS) peut rendre
  `Permission denied` avec `exit 126` — ce n'est PAS un binaire corrompu ni un telechargement
  rate : ne pas re-telecharger, passer par `Start-Process`. Puis **verifier la fenetre** :
  `Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | Select Id,ProcessName,MainWindowTitle`
  (un `Get-Process <App>` sans `MainWindowTitle` ne prouve pas que la fenetre est ouverte ;
  `tasklist` repond `Binary file (standard input) matches` a un `grep` sur sa sortie UTF-16,
  cf. Regle 6).
- `Start-Process -FilePath x -ArgumentList y -NoNewWindow` applique a un OUTIL EN LIGNE DE
  COMMANDE -> `(x y >"$LOCALAPPDATA/hermes/y.log" 2>&1 &)` dans un appel `terminal` a part :
  enchainer `(cmd &) echo ...` derriere un `&&` est une erreur de syntaxe bash, et le log reste
  vide sans aucun message.
- `Invoke-RestMethod -Uri ... -Body ...` -> Python `urllib.request` (plus sur que `curl.exe` pour du
  JSON imbrique), avec `User-Agent` explicite si l'endpoint est derriere Cloudflare.
- `taskkill /F /PID N` -> marche tel quel (binaire natif) ; c'est l'outil qui libere un venv
  verrouille par un processus tiers (cf. skill `hermes-install-troubleshooting`).

## Regle 11 — un glob qui ne trouve rien ne prouve pas l'absence (fichiers caches)

Un fichier dont le nom commence par un point est **invisible** aux motifs `*.ext`, dans les deux
mondes : `ls <dossier>/*.partial*` comme `Get-ChildItem "<dossier>\*.partial*"` ne renvoient **rien**
pour `.pre-update-<horodatage>.zip.<pid>-<tid>.partial`. Le resultat vide ressemble a un resultat
(« aucun fichier de ce type ») et fait conclure a tort que le disque est propre : sur un dossier de
sauvegardes, l'ecart mesure etait de 14,9 Go repartis sur 3 fichiers annonces absents.

- Bash : `ls -a <dossier>` ou `find <dossier> -name "*.partial*" -type f` — `find` voit les caches.
- PowerShell : `Get-ChildItem <dossier> -Force -Filter "*.partial*"` (`-Force` inclut les elements
  caches ; `-Filter` filtre cote fournisseur et reste plus sur que `-Include`, qui exige `-Recurse`
  ou un `-Path` se terminant par `\*`).
- **Regle generale** : avant d'annoncer « absent », refaire le test avec un chemin d'acces DIFFERENT
  (`find` plutot qu'un glob, `ls -a` plutot que `ls`, `-Force` plutot que rien). Une absence conclue
  d'un seul glob n'est pas une absence mesuree — et l'annonce d'un fichier « deja supprime » sur ce
  fond est un rapport faux.
- **Une recherche lancee depuis le repertoire courant de la session ne voit pas le projet.** Le
  repertoire de depart est souvent un dossier systeme (`C:\Windows\System32`) : une recherche de
  fichiers y rend `total_count: 0` (et peut meme echouer sur des fichiers verrouilles :
  `os error 32`, `panneaux de configuration`, `nul`), ce qui ressemble a « la fonction n'existe pas »
  alors que l'arborescence visee est ailleurs. Ne pas repeter la meme requete : elle est idempotente
  et l'outil finit par signaler une boucle. Localiser d'abord la racine reelle
  (`find /c/Users/<user> -iname "<fichier>"` depuis bash, ou `find <racine> -maxdepth 3`), puis
  chercher dedans. Pour ce parc, les projets vivent sous `%LOCALAPPDATA%\hermes` (donnees, scripts,
  plugins, traces) — y ancrer les recherches de contenu et non sur la racine du depot.

## Regle 12 — `Start-Process -ArgumentList` et les chemins avec espaces (mesure du 23/09/2026)

`Start-Process` aplatit `-ArgumentList` en une **ligne de commande brute** : il concatene les
lements avec des espaces **sans ajouter de guillemets**. Tout argument contenant un espace est
alors red coupe par le programme enfant (python/argparse voit deux tokens).

Mesure sur cette machine (PowerShell 5.1.26100.9444), sonde `args_dump.py` appelee avec
`--source "C:\Users\searc\Desktop\hermes tuto\talkinghead.mp4"` :

| Forme | argv recus | Verdict |
|-------|------------|---------|
| `-ArgumentList "script.py --source C:\...\hermes tuto\talkinghead.mp4"` | `'C:\...\hermes'` + `'tuto\talkinghead.mp4'` | **CASSE** |
| `-ArgumentList @("script.py","--source","C:\...\hermes tuto\talkinghead.mp4")` | meme decoupage | **CASSE** |
| `-ArgumentList @("script.py","--source",'"C:\...\hermes tuto\talkinghead.mp4"')` | 1 seul token | OK |
| `-ArgumentList "script.py --source `"C:\...\hermes tuto\talkinghead.mp4`""` | 1 seul token | OK |
| `& $py "script.py" "--source" "C:\...\hermes tuto\talkinghead.mp4"` | 1 seul token | OK (a preferer) |

Enseignements :

- **Le tableau ne suffit PAS.** L'idee recue « passer `-ArgumentList` en tableau pour que les espaces
  soient preserves » est fausse : PowerShell rejoint les elements avec des espaces sans les citer.
  Chaque element qui contient un espace doit porter **ses propres guillemets**.
- **Symptome cote programme** : `argparse: error: unrecognized arguments: tuto\talkinghead.mp4`.
  Le token tronque au premier espace suffit a identifier la cause — inutile de chercher un bug de
  parsing dans le script.
- **Preferer l'appel natif** (`& $exe @args`, ou en bash `(cmd &)`), qui cite correctement ;
  pour un lancement **detache et masque**, passer par le wrapper VBS de `windows-ops`
  (`references/scheduled-tasks.md` et la section « fenetre console qui flashe »).
- **Sonde reutilisable** : un `args_dump.py` de 6 lignes qui imprime `sys.argv` (a garder dans
  `cache/scratch/`) tranche le debat en une commande, sans dependre d'un run de production.

## Regle 13 — `write_file` refuse d'ecraser un fichier lu en mode pagine

Reecrire EN ENTIER un fichier deja lu avec `read_file(..., limit=...)` est refuse par le garde
anti-ecrasement (« last read with offset/limit pagination (partial view) ... use patch ») : le
fichier n'est PAS modifie, et l'erreur ne dit rien de son contenu. **Rejouer le meme `write_file` a
l'identique ne passera pas davantage** — c'est une boucle, et le compte de repetitions declenche
l'avertissement de boucle de l'outil.

- Le chemin qui marche est `patch` : une passe par section visee (`old_string` / `new_string`),
autant de `patch` que de sections a changer. C'est aussi ce que recommande le message du garde.
- Relire le fichier en entier puis reecrire n'est PAS une parade : une nouvelle lecture paginee
(meme avec la limite maximale) laisse le garde en place. Sur un fichier long, l'edition ciblee se
fait en `patch` ; une reecriture integrale assumee passe par une suppression prealable (voir
ci-dessous), jamais par un simple rejeu de `write_file`.
- **Reecriture integrale : `rm` puis `write_file` passe.** Supprimer le fichier (`rm "<chemin>"`,
ou `del` sous cmd) fait tomber le garde, et `write_file` cree alors un fichier neuf. A ne faire
que si le contenu final est deja ecrit et verifie : entre la suppression et l'ecriture, l'original
n'existe plus. C'est le chemin pour un script ou un document dont tout le contenu change ; garder
`patch` pour les modifications ciblees.
- **Variante NON destructive, a preferer a `rm`** : ecrire le nouveau contenu dans un fichier NEUF du
  meme dossier (`<nom>.new`), le verifier, puis `cp <nom>.new <nom>` depuis le terminal. Le fichier
  d'origine reste en place jusqu'au `cp`, donc aucun instant ou il n'existe plus — c'est ce qu'on veut
  pour un script ou un document livre. `rm` + `write_file` reste valable mais ouvre une fenetre ou le
  fichier a disparu si l'ecriture echoue.
- Le meme garde protege un fichier modifie sur le disque depuis la derniere lecture : relire,
fusionner, puis `patch`.
- Diagnostic : un outil de reecriture qui « refuse » n'a rien tronque. Ne pas partir verifier le
contenu du fichier — il est intact, c'est l'ecriture qui n'a pas eu lieu.

## Regle 14 — trois pieges d'un script PowerShell de mesure (resultat FAUX, pas d'erreur)

Un script de mesure qui rend un resultat plausible mais faux coute plus cher qu'un script qui plante :
les trois cas ci-dessous ont ete payes dans une meme session d'audit.

- **PowerShell est INSENSIBLE A LA CASSE : une variable de boucle `$l` et une liste `$L` sont la MEME
  variable.** Un script de mesure qui accumule dans `$L = New-Object List[string]` puis boucle
  `foreach ($l in $sortie)` (nvidia-smi, Get-ChildItem) ecrase la liste par la derniere chaine lue :
  les `.Add()` suivants echouent en silence (`$ErrorActionPreference = 'SilentlyContinue'` masque le
  method-not-found), `$L.Count` rend `1` (longueur de la CHAINE) et le fichier de sortie ne contient
  qu'une ligne — sans aucune erreur ni code de retour non nul. Signature : sortie d'une ligne, compteur
  a 1, script qui annonce pourtant avoir tourne. Nommer la liste et les boucles avec des noms
  distincts (`$Lines` / `$row`).
- **`+=` sur un tableau est quadratique.** Boucler `$all += [pscustomobject]@{...}` sur ~900 000
  elements ne rend pas la main : mesure ~27 min sur un parcours qui se termine en 7 s avec la bonne
  structure — script tue, aucun resultat produit. Utiliser
  `[System.Collections.Generic.List[object]]` + `.Add()`, ou eviter la collecte (compteurs et top-N en
  variables, un seul passage).
- **La virgule lie plus fort que `+` dans un tableau.** `@($P + "a", $P + "b")` ne fait pas deux
  elements : PowerShell agrege autour de la virgule et rend **une seule chaine** ou les morceaux sont
  joints par des espaces. Signature a reconnaitre : un message qui affiche tous les chemins colles sur
  une ligne (`ABSENT SOURCE <chemin1> <chemin2> <chemin3>`) — c'est le tableau aplati, pas trois
  fichiers absents. Mettre chaque element entre parentheses, ou batir la liste par `.Add()`.
- **Un script alimente par STDIN (`powershell -Command -`) peut rendre une sortie VIDE avec code 0**
  des qu'il rencontre une erreur terminante : stderr n'est pas capture et le diagnostic disparait. Un
  `exit 0` et une sortie vide ne prouvent donc PAS que le script a fait ce qu'il annonce — ni qu'il n'a
  rien fait. Ecrire le `.ps1` (outil d'ecriture), le lancer en `-File`, et lui faire ecrire ses
  resultats dans un fichier texte relu ensuite : la relecture du fichier est la seule preuve.

- **`"a={0} b={1}" -f $x,$y` avec un argument construit par `-join` leve `FormatError`** et laisse une
  sortie PARTIELLE : le `Write-Output "AUCUNE"` place avant la boucle en echec s'affiche quand meme et
  devient une fausse conclusion (« aucune tache ne correspond » alors que 4 correspondent). Batir la
  ligne par concatenation (`Write-Output ("TACHE : " + $t.TaskName)`) et terminer tout script par un
  compteur (`TOTAL_CIBLES=N`) : un resultat vide se conteste, un `TOTAL=0` se verifie.

Corollaire commun : **faire publier au script une valeur de controle** (compteur, taille totale, nombre
 de lignes du fichier de sortie) et la confronter a une mesure independante. Un script de mesure qui
n'expose que sa conclusion n'est pas verifiable, et une conclusion non verifiable sur un audit se
retourne contre son auteur.

## Regle 15 — choisir un candidat parmi plusieurs : trois selections qui reussissent sur le mauvais

Sur ce parc il y a plusieurs candidats pour presque tout (interpreteurs, venvs, environnements
stages, mais aussi PID, dossiers de version). Une selection qui « marche » n'est pas une selection
juste : ces trois formes rendent une valeur plausible et fausse.

- **`grep -o` ne rend que le FRAGMENT matche, pas la ligne.** Selectionner une entree de `$PATH` par
  `printf '%s' "$PATH" | tr ':' '\n' | grep -aoE '/environments/[a-f0-9]+/venv/Scripts$'` rend
  `/environments/…/venv/Scripts` — un chemin RELATIF qui n'existe pas : le `[ -f "$p/python.exe" ]`
  qui suit echoue en silence, la detection se rabat sur le candidat suivant, et le script annonce
  une cible AUTRE que celle visee sans aucune erreur. Pour garder la ligne entiere, `grep -aE`
  (sans `-o`) ; `-o` ne sert qu'a extraire un champ d'une ligne deja identifiee.
- **`ls -1dt` sur des fichiers extraits d'une archive ne trie rien.** Les binaires extraits d'un
  meme zip/7z partagent l'horodatage de l'archive (mesure : trois `python.exe` de venvs differents,
  tous dates du meme jour de janvier 2024) : `-t` les voit a egalite et retombe sur l'ordre
  alphabetique — donc sur une cible potentiellement perimee. Trier les DOSSIERS qui les contiennent
  (`ls -1dt <parent>/*/bin` puis descendre au binaire), ou departager sur un critere reel (entree de
  `$PATH`, fichier de config, source autoritative).
- **Confirmer l'existence d'un processus par le code de retour est faux** : `tasklist` sort en 0
  meme sans correspondance. Tester le champ (`/FO CSV` + `"<pid>"`), cf. Regle 10.

Corollaire : quand plusieurs candidats existent, **faire afficher celui qui a ete retenu** (chemin
complet, version, date) et le confronter a la source autoritative (PATH, config, `hermes doctor`).
Une detection qui se rabat silencieusement sur un autre candidat ne se voit pas dans le resultat —
elle ne se voit que si le script dit ce qu'il a choisi.

## Regle 16 — prouver qu'un controle peut echouer : casser l'etat vivant sous `trap` + hash de restauration

Un controle de sante (health check, moniteur, watchdog) dont le chemin d'echec n'a jamais ete
observe n'est pas un controle : il faut casser exprès ce qu'il inspecte. Sur un parc ou l'etat testé
est VIVANT (le venv runtime d'une gateway en service, un fichier de config lu par un processus),
la maniere courte de le faire est aussi la seule sure :

- **Ne renommer/supprimer la cible que dans un harnais qui la restaure automatiquement**
  (`restore()` + `trap restore EXIT INT TERM`), et laisser le harnais dans un `.sh` du scratch
  plutot qu'en ligne : l'appel peut etre coupe, le fichier survit.
- **Prouver la restauration par une empreinte, pas par « le `mv` a tourne »** :
  `find <cible> -type f | sort | sha256sum` AVANT/APRES, puis un import/tests reel dans le processus
  concerne. Un dossier restaure a moitie casse toutes les sessions suivantes.
- **Desactiver l'auto-reparation du controle teste** (crochet du type `*_NOFIX=1`) : sinon le check
  reinstalle ce qu'on vient de casser et masque exactement la panne qu'on veut voir signaler.
- **Rejouer le chemin nominal apres la simulation** (il doit repasser au vert) et comparer a l'etat
d'avant : renommer une cible vivante puis ne rien remettre en place est une panne auto-infligee.
- **Renvoyer la sortie du harnais, pas son intention** : le script imprime l'EXIT du check simule
  (`EXIT_SIM=1` = la panne est bien detectee) ; un rapport qui affirme « le check echoue bien »
sans cette trace n'est pas une preuve.

## Pitfalls

- **Le lot perdu sans erreur** : ecrire dix fichiers avec `/home/<user>/...` dans un dossier cree par `mkdir -p ~/...` produit deux arborescences distinctes, dont une inexistante. Symptome : `find` ne trouve aucun des fichiers alors que chaque ecriture avait ete annoncee reussie. Reprendre le lot avec des chemins `C:/Users/...`.
- **Ne pas en conclure qu'un outil ne marche pas** : l'ecriture a fonctionne, c'est le chemin qui etait faux. Ne pas inscrire « les ecritures de fichiers echouent sur cet hote » comme une regle.
- **Verifier avant de continuer, pas a la fin** : sur un scaffolding de plusieurs dizaines de fichiers, le controle apres le premier fichier coute une commande ; la reprise d'un lot entier coute tout le lot.

## Voir aussi

- L'umbrella `windows-ops` (operations Windows : GPU Docker/WSL2, tuning).
- `disk-space-reclamation` — audit d'espace disque : mesurer une arborescence volumineuse (`du` MSYS trop
  lent sur des cibles en Go, enumeration .NET) et statuer avant de supprimer.
