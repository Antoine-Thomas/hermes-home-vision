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

## Pitfalls

- **Le lot perdu sans erreur** : ecrire dix fichiers avec `/home/<user>/...` dans un dossier cree par `mkdir -p ~/...` produit deux arborescences distinctes, dont une inexistante. Symptome : `find` ne trouve aucun des fichiers alors que chaque ecriture avait ete annoncee reussie. Reprendre le lot avec des chemins `C:/Users/...`.
- **Ne pas en conclure qu'un outil ne marche pas** : l'ecriture a fonctionne, c'est le chemin qui etait faux. Ne pas inscrire « les ecritures de fichiers echouent sur cet hote » comme une regle.
- **Verifier avant de continuer, pas a la fin** : sur un scaffolding de plusieurs dizaines de fichiers, le controle apres le premier fichier coute une commande ; la reprise d'un lot entier coute tout le lot.

## Voir aussi

- L'umbrella `windows-ops` (operations Windows : GPU Docker/WSL2, tuning).
