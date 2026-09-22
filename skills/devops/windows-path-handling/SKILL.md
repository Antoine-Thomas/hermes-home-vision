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
- Fichier temporaire qu'un programme natif doit lire : preferer `$LOCALAPPDATA/Temp` a `/tmp`.
- `curl`, `7z`, `tar` : ce sont des binaires natifs, ils ouvrent le fichier de sortie avec l'API
  Windows. Leur passer `C:/...`. Le symptome d'un `/c/...` est TROMPEUR :
  `curl: (23) client returned ERROR on write of N bytes` — ce n'est ni une erreur reseau ni un
  disque plein, c'est le chemin de sortie qui n'a pas pu etre ouvert. Le meme piege se paie deux
  fois dans une session (telecharger, puis ecrire un fichier de sortie en `-o`).
- Les executables Windows a options en `/flag` (schtasks, robocopy, reg, sc) ne sont pas proteges de
  la traduction MSYS : `/run` peut partir tel quel ou etre converti en chemin, et la parade reflexe
  `//run` arrive litteralement comme `//run` (`Argument ou option non valide`). Preferer l'equivalent
  PowerShell (`Start-ScheduledTask`, `Get-ScheduledTask`, `Register-ScheduledTask`) ou passer par
  `cmd //c "<commande complete>"` en gardant la commande entre guillemets.
- **Commandes PowerShell depuis bash** : des qu'une commande contient des variables `$env:` ou des
  guillemets imbriques, ne pas la passer en ligne a `powershell -Command` — les variables arrivent
  mangees (`UserId:OMATHS\:USERNAME`) et l'appel echoue (mappage de compte introuvable sur
  `Register-ScheduledTask`). Ecrire un fichier `.ps1` et l'appeler par
  `powershell -NoProfile -ExecutionPolicy Bypass -File <script>` : le fichier traverse l'echappement
  intact. Garder ces `.ps1` (et les `.vbs`) en **ASCII pur** : PowerShell 5.1 lit l'UTF-8 sans BOM
  comme de l'ANSI, donc accents, tirets longs et puces s'affichent de travers.
- **Ne jamais faire passer un pipeline cmd.exe par le terminal bash** : les builtins DOS n'existent
  pas ici et leurs homonymes sont ceux de MSYS. `dir "...\*.png" /b | find /c /v ""` ne compte rien :
  `find` est le GNU find, il part arpenter le systeme de fichiers et ne rend jamais la main (mesure :
  tue au bout de 180 s alors que les 290 PNG etaient bien sur le disque). Compter en POSIX :
  `ls <dossier> | grep -c '\.png$'`, et `ls -la <dossier>` pour un effet `dir`.
- Apres un `mkdir -p ~/...`, faire `ls` sur l'arborescence creee AVANT d'y ecrire : le shell et les outils d'ecriture ne developpent pas `~` de la meme facon, et un `mkdir` reussi ne dit rien sur l'endroit ou les outils ecriront.

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

Parades, dans l'ordre :
- `schtasks ... 2>&1 | tr -d '\0' | grep -i <motif>` — retirer les octets nuls suffit a rendre le flux lisible ;
- lire en Python avec le bon codec :
  `subprocess.run([...], capture_output=True, text=True, encoding="utf-16", errors="replace")` ;
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

- `Get-CimInstance Win32_Process -Filter "ProcessId = N" | Select-Object ...` -> `tasklist /FI "PID eq N"`
  (sortie lisible ; ajouter `2>&1 | tr -d '\0'` si elle ressort en UTF-16, cf. Regle 6).
  `wmic process where processid=N get name,commandline` quand il faut la ligne de commande.
- `ps -p N -o pid,cmd` et `/proc/N/cmdline` -> ne voient PAS les processus Windows natifs
  (`ps: unknown option -- o`, `/proc/N/cmdline` vide). Tout ce qui est `.exe` natif (python.exe,
  hermes.exe) passe par `tasklist` ; ne pas en conclure que le processus n'existe pas.
- `Start-Process -FilePath x -ArgumentList y -NoNewWindow` -> `(x y >"$LOCALAPPDATA/hermes/y.log" 2>&1 &)`
  dans un appel `terminal` a part : enchainer `(cmd &) echo ...` derriere un `&&` est une erreur de
  syntaxe bash, et le log reste vide sans aucun message.
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

## Pitfalls

- **Le lot perdu sans erreur** : ecrire dix fichiers avec `/home/<user>/...` dans un dossier cree par `mkdir -p ~/...` produit deux arborescences distinctes, dont une inexistante. Symptome : `find` ne trouve aucun des fichiers alors que chaque ecriture avait ete annoncee reussie. Reprendre le lot avec des chemins `C:/Users/...`.
- **Ne pas en conclure qu'un outil ne marche pas** : l'ecriture a fonctionne, c'est le chemin qui etait faux. Ne pas inscrire « les ecritures de fichiers echouent sur cet hote » comme une regle.
- **Verifier avant de continuer, pas a la fin** : sur un scaffolding de plusieurs dizaines de fichiers, le controle apres le premier fichier coute une commande ; la reprise d'un lot entier coute tout le lot.

## Voir aussi

- L'umbrella `windows-ops` (operations Windows : GPU Docker/WSL2, tuning).
