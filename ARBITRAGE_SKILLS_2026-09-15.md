# Arbitrages — skills : références mortes et doublon photo/record (15/09/2026)

Rapport demandé après la première révision des skills. **Aucun skill n'a été touché** : liste,
analyse, propositions. Décision à l'utilisateur.

## 1. Les 10 skills signalés « références mortes »

Le détecteur cherche les chemins Windows et les commandes cités dans chaque `SKILL.md` et vérifie
leur existence. Bilan après vérification manuelle : **8 faux positifs** (gabarits et troncatures) et
**1 vrai cas** touchant 2 skills.

| # | Skill | Référence signalée | Contexte | Verdict / suggestion |
|---|---|---|---|---|
| 1 | `local-flywheel-setup` | `C:\Users\<user>\Local` | gabarit `C:\Users\<user>` dans une explication d'installation | **Faux positif** — rien à faire |
| 2 | `premiere-montage-comparatif` | `C:\Program` | troncature du détecteur sur l'espace de `C:\Program Files\Adobe\...` | **Faux positif** — rien à faire |
| 3 | `siyuan-second-brain` | `C:\...\demarrer_siyuan.cmd` (et `C:\Users\<user>\SiYuan\<workspace>`) | exemple PowerShell de création de tâche planifiée, écrit avec des points de suspension | **Faux positif**, mais améliorable : le vrai chemin existe (`C:\Users\searc\SiYuan\demarrer_siyuan.cmd`). Suggestion : **mise à jour** du chemin réel dans l'exemple. À toi de dire |
| 4 | `smll-talk-podcast` | `C:\Users\searc\Desktop\the cypher\clone\mavoix1-6.wav` | dossier des six prises de voix servant à cloner la voix des épisodes | **Vrai cas** : ce dossier **n'existe plus** sur le Bureau. Suggestion : **mise à jour** vers le nouvel emplacement si tu l'as déplacé, sinon **archivage** du skill (il décrit un flux sans matière première) |
| 5 | `vibevoice-tts` | `C:\Users\searc\Desktop\the cypher\clone\` | mêmes six fichiers, avec la mise en garde « PAS `...\smll talk\clone\` » | **Vrai cas**, identique au 4 : le piège documenté (ne pas confondre deux chemins) perd son sens si les deux ont disparu. Suggestion : **mise à jour** ou **archivage** |
| 6 | `video-editing-automation` | `C:\path\to\folder` | gabarit d'exemple | **Faux positif** — rien à faire |
| 7 | `windows-path-handling` | `C:\Users\<user>\projet\fichier.md`, `C:\home\<user>\projet\fichier.md` | les deux formes de chemins en exemple | **Faux positif** — rien à faire |
| 8 | `windows-system-backup` | `D:\WindowsImageBackup\<computername>\Backup` | arborescence type produite par `wbadmin` | **Faux positif** — c'est le format d'un lecteur externe, pas un chemin local |
| 9 | `wordpress-backup-restore` | `C:\backups`, `C:\chemin\skills\...` | dossier de sortie en exemple et gabarit | **Faux positif** — les vrais scripts existent (`backup_site.py`, `restore_site.py`, `list_backups.py` sont bien dans `scripts/`) |
| 10 | `wordpress-local-flywheel-publishing` | `validate_skills.py`, `validate_structure.py` | arborescence **type** d'un skill documentée dans le corps | **Faux positif** — ce sont des exemples de structure, pas des fichiers de ce skill |

**Ce qu'il faut retenir** : un seul dossier a réellement disparu — `Desktop\the cypher` (voix du
podcast / vibevoice). Il est cité par `smll-talk-podcast` et `vibevoice-tts`, qui sont donc tous les
deux inutilisables en l'état. Les huit autres signalements sont des gabarits (`<user>`,
`C:\path\to\...`, `C:\chemin\...`) ou des troncatures de mon détecteur sur les espaces : je corrige
le détecteur pour ne plus les remonter, ce qui rendra la prochaine révision exploitable.

## 2. Le doublon `photo` / `record` (0,36 de recouvrement)

**Faux positif. Sujet clos.** Les deux skills se ressemblent par le vocabulaire, pas par le rôle :

| | `photo` | `record` |
|---|---|---|
| Objet | **une image fixe** | **une séquence vidéo+audio**, 5 à 60 s |
| Déclencheur | `/photo`, capture | `/record`, `/record 30`, `/record 60` |
| Voyant | fenêtre rouge fixe, 1,5 s | fenêtre rouge **clignotante** pendant toute la durée |
| Capture | OpenCV `VideoCapture(0)`, repli `PIL.ImageGrab` (écran) | ffmpeg dshow (vidéo+audio réels), replis OpenCV puis rafale PIL → GIF |
| Sortie | `.jpg` dans `captures/` | `.mp4` dans `captures/` |

Ce qui les unit — respect d'ESTOP, voyant visible, envoi par Telegram, refus du flux infini — est une
**règle commune**, pas une fonction commune. Fusionner reviendrait à faire un skill qui doit dire
« si l'utilisateur veut une image, faire ceci ; si c'est une vidéo, faire cela » : deux branches sans
rapport dans un même fichier, pour un gain nul. À conserver séparés.

*Note pour la prochaine révision* : le seuil de similarité (0,34) est trop bas sur des descriptions
courtes — un partage de vocabulaire métier suffit à le franchir. Le porter à 0,45 ferait tomber ce
faux positif sans rater les vrais doublons de rôle.

## 3. Les 74 scripts sans skill

Écarté à ta demande : c'est normal, tous les scripts ne méritent pas un skill. La liste reste dans le
rapport de révision comme filet de sécurité, à lire seulement si une tâche se répète à la main.

## Suite

Rien n'a été modifié. Trois décisions t'attendent : les deux skills du dossier `the cypher`
(mise à jour ou archivage), et l'éventuelle mise à jour du chemin réel dans `siyuan-second-brain`.
