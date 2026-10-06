# Recettes de preuve (verifiees sur cet hote)

Commandes reellement utilisees pour instruire un incident fichier. Aucune n'ecrit sur le disque.

## Journal USN (NTFS) — la seule trace retroactive des deplacements et suppressions

```
fsutil usn readjournal C: csv 2>/dev/null | grep -a -i "<motif>"
fsutil usn queryjournal C:                       # bornes de la fenetre (Premier USN, USN suivant, taille max)
fsutil file queryfileid "C:/chemin/du/dossier"    # FRN d'un chemin -> 0x0000000000000000001a000000253bb6
```

- Le CSV porte : nom, raison (hex), raison (texte), horodatage, drapeaux, FRN, FRN parent. Extraire
  malgre les virgules internes : couper par guillemets (`cut -d'"' -f2,4,8`) ou parser en Python.
- **Codes de raison a connaitre** : `0x00000100` creation · `0x00000102` extension + creation ·
  `0x00001000` renommage (ancien nom) · `0x00002000` renommage (nouveau nom) · `0x80000100` creation +
  fermeture · `0x80000200` suppression + fermeture.
- **Signature d'un deplacement** : une paire ancien/nouveau nom portant le MEME nom avec un parent
  (FRN parent) different. Un renommage en place garderait le meme parent. Aucun enregistrement
  `Suppression` n'accompagne un deplacement : c'est la preuve que rien n'a ete detruit.
- **Le journal ne contient ni chemin ni PID** : identifier un dossier par `queryfileid` sur le chemin
  courant, puis verifier que le FRN obtenu est bien celui des enregistrements.
- Lire tout le journal est long : borner par `grep -a '<date heure>'` sur la fenetre, ou filtrer par
  FRN. Un motif trop large ressort des milliers de lignes.
- Prouver une ABSENCE : « aucune suppression (ni au premier niveau du dossier X) sur la periode » est un
  resultat en soi, qui ecarte l'hypothese de l'elagueur ou d'un `rm`.

## Heures : CreationTime, LastWriteTime, mtime des parents

```
stat -c "%W %w %n" <chemin>                 # %W = CreationTime epoch, %w = CreationTime lisible (MSYS)
powershell -NoProfile -Command "Get-Item '<chemin>' | Format-Table FullName,CreationTime,LastWriteTime,Attributes -AutoSize"
```

- Un dossier dont le CreationTime colle a l'evenement peut etre : neuf (delete + mkdir) ou point
  d'atterrissage d'un deplacement. **Le discriminant est chez les enfants** : s'ils gardent leur
  CreationTime ancienne, il n'y a pas eu suppression recursive.
- Un renommage deplace la CreationTime AVEC l'objet : un arbre deplace deux fois garde sa date
  d'origine, dans un parent neuf.
- Destination d'un deplacement, sans chercher au hasard :

```
find /c/Users/<user> -maxdepth 7 -type d \( -newermt "<t-1s>" ! -newermt "<t+3s>" \) -printf "%T+ %p\n"
find /c/Users/<user> -maxdepth 7 -type d -iname "*<motif>*" -printf "%T+ %p\n"
```

  Le dossier qui recoit (ou perd) un enfant voit son mtime bouger a cet instant : c'est le candidat a
  inspecter en premier. Le `find` ne donne pas la CreationTime : la demander a l'API Windows
  (`Get-Item ... | Format-Table`) sur le candidat trouve.

## Attribution d'un processus : ce qui est prouvable, ce qui ne l'est pas

```
powershell -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; StartTime=$s; EndTime=$e} | Select-Object TimeCreated,Id"
```

- Ids **40961** (« console en cours de demarrage ») / **40962** (« prete ») / **53504** : l'instant de
  lancement d'un `powershell.exe`. Faisceau, pas identite.
- **Etablir la cadence de reference avant** : lister toutes les ouvertures de console du jour
  (`Id=40961`, depuis 00:00) et reperer la periodicite. Une tache planifiee en `PT5M` produit un
  lancement a chaque `:x0`/`:x5` ; un lancement hors cadence, a la seconde precedant l'evenement FS,
  est le seul signal utile.
- Journaux d'attribution a tester AVANT de promettre un nom : **4104** (bloc de script — donne le
  texte), **4688** (creation de processus, log `Security` — donne la ligne de commande), **4663**
  (acces objet — donne acces et suppressions). Sur un poste par defaut ces trois sont desactives :
  l'attribution s'arrete alors a « type de processus + heure ».
- Un compte nul de 4663/4688 ne prouve pas l'absence d'action, seulement l'absence de journalisation.
- Lire les artefacts systeme du meme instant pour ecarter le bruit :
  `Microsoft-Windows-TaskScheduler/Operational` (ids 100/102/129/200/201/322) montre quelles taches
  ont tourne ; `140 Task registration updated` accompagne une (re)inscription, pas une execution.
- **Ne pas ecrire de backtick PowerShell** (`-split "`n"`) dans une commande passee depuis bash : bash
  ouvre un quoting et la reponse est `unexpected EOF while looking for matching`. Utiliser un motif
  regex (`-split '\s+'`) ou un `.ps1` en `-File`.

## Relecture de `state.db` (ce qu'une session precedente a reellement vu)

```python
import sqlite3, os
con = sqlite3.connect('file:' + os.path.abspath('state.db').replace(os.sep, '/') + '?mode=ro', uri=True)
cur = con.cursor()
cur.execute("select id, session_id, role, tool_name, timestamp, content, tool_calls from messages")
```

- Tables : `sessions` (id, source, title, started_at, message_count) et `messages` (id, session_id,
  role, tool_name, content, tool_calls, timestamp — epoch secondes).
- Les `tool_calls` portent la commande EXACTE envoyee, souvent tronquee a l'affichage : les extraire
  (`json.loads`) et les imprimer en entier — c'est ce qui permet de rejouer un tour precis.
- Cibler une fenetre de temps : `where session_id=? and timestamp between ? and ?` (bornes lues dans
  les tours voisins).
- Base d'un autre profil : `profiles/<profil>/state.db`. Toujours `mode=ro` (le runtime tient la base).
- **Piege** : l'outil de recherche de sessions classe et borne, et peut rendre « 0 session » la ou une
  requete `LIKE` sur `messages` (en incluant `tool_calls`) trouve la ligne. Pour une question
  exhaustive, interroger la base directement — ne jamais conclure « absent de toutes les sessions »
  depuis le seul outil.

## Verifier un arbre avant de conclure

- Compter a la nouvelle place : `find <nouveau> -type f | wc -l`, `ls -A <nouveau> | wc -l` (entrees de
  premier niveau), et rapprocher du listing d'origine lu dans la session.
- Statut git de l'arbre concerne : `git check-ignore -v <chemin>` et `git ls-files <chemin> | wc -l`
  (0 = non versionne : aucune restauration par git, mais aucune perte de contenu versionne non plus).
- Les fichiers ecrits par un outil qui fait `write temp + rename` apparaissent comme deux
  enregistrements (`renommage ancien nom` sur `.hermes-tmp.*` puis `renommage nouveau nom`) : c'est le
  mode d'ecriture normal de l'agent, pas un evenement suspect.
