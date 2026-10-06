# Commandes de recuperation d'un projet perdu

Verifiees, a adapter. Ordre d'usage 1 -> 5. Aucune n'ecrit dans le projet.

## 1. Retrouver le brief dans l'historique

    session_search(query="<vocabulaire utilisateur>", detail="adaptive", limit=8)

- Plusieurs requetes COURTES, en francais ET en anglais, plutot qu'une longue.
- Bonnes cles : nom du fichier de SORTIE attendu, nom du script de fabrication, un timecode
  (« 101,65-158,69 »), un titre YouTube, un mot du brief (« overlay », « schema », « panneau »).
- Un ancien message UTILISATEUR est souvent le brief lui-meme : le citer verbatim avec son lien
  `@session:default/<id>` (il se rend cliquable), plutot que de le resumer.
- Pour elargir autour d'un resultat compact :
  `session_search(session_id=<id>, around_message_id=<match_message_id>)`.
- Chercher ensuite les messages de CORRECTION posterieurs au brief : ils portent les bornes
  finales (decalages de timecodes, duree a conserver).

## 2. Fouille disque

Gros fichiers, tries par date :

    find "<dossier>" -type f -iname "*.mp4" -size +100M \
      -printf "%10s %TY-%Tm-%Td_%TH:%TM %p\n" | sort -k2

Briefs colles (fichiers texte volumineux) :

    find "<dossier_pastes>" -type f \( -iname "*.txt" -o -iname "*.md" \) | while read f; do
      n=$(wc -l < "$f"); [ "$n" -ge 200 ] && echo "$n lignes  $f"; done | sort -rn

Identification du brief en une passe :

    grep -ril -E "overlay|schema|timecode|youtube|panneau" "<dossier_pastes>"

Base de connaissances (SiYuan 3.8.x, port 6806 ; jeton dans `$HERMES_HOME/.env`, ne jamais
l'afficher) :

    T=$(grep -m1 '^SIYUAN_TOKEN=' "$HERMES_HOME/.env" | cut -d= -f2-)
    curl -s -X POST http://127.0.0.1:6806/api/query/sql \
      -H "Authorization: Token $T" -H "Content-Type: application/json" \
      -d '{"stmt":"SELECT id, type, substr(content,1,140) AS extrait, hpath FROM blocks WHERE content LIKE '\''%<mot>%'\'' LIMIT 8"}'

Un `data` vide est un resultat : rapporter « rien dans la base », pas un echec.

## 3. Le script definit le livrable

    grep -rn -E "^(OUT|HEAD|AUDIO|PAN|CARD|DUR|PANELS)" <script de fabrication>
    for f in <chaque chemin nomme>; do [ -e "$f" ] && echo "EXISTE $f" || echo "ABSENT $f"; done

- Un `OUT = .../X_final.mp4` ABSENT = livrable jamais rendu, quel que soit ce qui existe a cote.
- Une entree ABSENTE (tete, audio master) explique pourquoi le script ne peut pas re-tourner en
  l'etat : le dire, ne pas le corriger d'office.
- Le nom de la sortie porte souvent la nuance qui compte (`..._sans_carte`, `..._v6`) : le lire
  comme l'enonce d'un etat, et chercher le fichier jumeau manquant.
- Un mode « test » deja execute (extrait court present sur le disque) prouve que le graphe tourne :
  la suite est une question de rendu, pas de mise au point.

## 4. Verifier un overlay par mesure (aucun GPU)

    ffmpeg -hide_banner -v info -ss <T> -i <video> -frames:v 1 \
      -vf "crop=<W>:<H>:<X>:<Y>,signalstats,metadata=print:file=-" -f null - 2>/dev/null \
      | grep -E "lavfi.signalstats.(YMIN|YMAX|YAVG)="

Lecture :

- `YMIN=YMAX=YAVG` -> zone UNIFORME (le fond) : rien d'incruste a cet instant.
- `YMIN < YMAX` -> il y a du contenu dans la zone.
- Mesurer au moins un instant DANS le creneau attendu, un instant HORS creneau (temoin), et la
  zone voisine (video de fond) : le contraste entre les trois est la preuve, pas le chiffre seul.
- Le chemin passe a `ffmpeg` doit etre NATIF (`C:/Users/...`) : un chemin MSYS rend une sortie
  vide avec `exit 0` (voir `windows-path-handling`, Regle 3).

## 5. Rapport de candidats (puis STOP)

Table : nom | chemin | duree MESUREE | taille | frames | version du brief associee.

- Distinguer explicitement le livrable du BRIEF, la piece INTERMEDIAIRE deja conforme, et le
  hors-sujet — le rendre visible fait accepter le tri.
- Donner les ecarts « mesure contre formulation utilisateur » avec les deux chiffres.
- Terminer par des questions numerotees qui tranchent entre les versions concurrentes du brief.
- Ne rien creer ni modifier avant la reponse.

## 6. Apres un arret sale (crash / redemarrage force) — A FAIRE EN PREMIER dans ce cas

Etablir l'etat AVANT de chercher le brief : quelle session est morte, qu'est-ce qui tournait, quel
travail a ete interrompu. Aucun GPU, aucune ecriture.

a) **La session morte se reconnait a `ended_at` NULL.** Lecture seule :

    python -c "
    import sqlite3
    con = sqlite3.connect('file:<HERMES_HOME>/state.db?mode=ro', uri=True)
    for r in con.execute('SELECT id,started_at,ended_at,model,message_count,title FROM sessions ORDER BY rowid DESC LIMIT 5'):
        print(r)"

   Une session encore « active » a `ended_at` NULL ET un `last_activity_description` non nul ; c'est
   la derniere avant l'arret. `message_count` et `tool_call_count` eleves = beaucoup de travail en jeu.

b) **La cause se lit dans `logs/errors.log`.** L'ultime entree de la session est typiquement un
   `{"output": "", "exit_code": <n>}` : `1073807364` = `0x40010004` = DBG_TERMINATE_PROCESS
   (processus tue par l'arret machine). Confirmer par
   `powershell -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"` :
   un boot posterieur de quelques dizaines de secondes, c'est un redemarrage, pas un plantage de l'appli.

c) **Processus restants.** `tasklist | grep -aiE "python|ffmpeg"` — le `-a` est OBLIGATOIRE, sinon
   grep traite la sortie comme binaire et ne rend que « Binary file (standard input) matches ».
   Puis lire la ligne de commande
   (`Get-CimInstance Win32_Process -Filter "name='python.exe'" | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CreationDate.ToString('MM-dd HH:mm') + ' | ' + $_.CommandLine }`)
   : les services Hermes se relancent au boot et portent une heure de demarrage POSTERIEURE au boot —
   un `python.exe` dont la ligne de commande cite le venv du chantier et qui a demarre AVANT le boot
   est un zombie.

d) **Travail interrompu.** Les fichiers du chantier plus recents que le dernier livrable valide, et
   les temporaires :

    find <dossier_chantier> -newer <dernier_livrable_valide> -type f | head -50
    find <dossier_chantier> \( -name "*.part" -o -name "*.tmp" -o -name "*.incomplete" \)

   Un dossier de sortie incomplet (comparer le nombre de fichiers au plan du script) est la signature
   exacte de la coupure : il dit OU le travail s'est arrete.

e) **Integrite avant de rassurer.** `PRAGMA quick_check` (et `integrity_check`) sur la base en
   `mode=ro` ; un `ffprobe` des livrables (duree, frames). Une base SQLite en WAL se recupere seule
   au prochain open ; un mp4 tronque ne se repare pas. Nommer explicitement ce qui est verifie.

f) **Signaler, ne pas reparer.** Ne rien relancer, ne rien supprimer, ne rien « nettoyer » : rendre
   l'etat des lieux, lister les 3 prochaines actions, puis attendre le GO.
