# Bugs du pipeline talking head (volet 6) — symptome / cause / correction

Pipeline : `C:\Users\searc\AppData\Local\hermes\data\video_youtube\pipeline_talkinghead.py`
Assemblage : `C:\Users\searc\AppData\Local\hermes\data\video_youtube\assemble_v6.py`
(wrapper de l'etape g : `LatentSync\tests\post_hf_transfer.py`)

Ces bugs ont coute 4 interventions manuelles pendant le volet 6 (22-23/09/2026).
Aucun n'etait visible avant le run : les deux premiers ne se declenchent qu'a des branches
precises (`--segmenter auto`, JSON de mesures present), le troisieme seulement si la variable
contient les crochets, et le quatrieme (graphe ffmpeg non borne) se manifeste en heures d'encodage
perdues plutot qu'en erreur.

## 1. `_taille_segment` n'existe pas (`--segmenter auto`)

- **Symptome** (run du 22/09 23:36, branche `--segmenter auto` uniquement) :

```
File "...\pipeline_talkinghead.py", line 1030, in main
    etapes["boucle"] = etape_boucle(a, source_stab, a.audio)
File "...\pipeline_talkinghead.py", line 730, in etape_boucle
    seg_frames = _taille_segment(a, cycle_r, w_loop, h_loop, libre_ram)
NameError: name '_taille_segment' is not defined
```

- **Cause** : appel d'une fonction inexistante ; la fonction reelle s'appelle `taille_tranche`
  (definie ligne 189). Nom different, jamais execute avant ce run.
- **Correction** : ligne 730 -> `seg_frames = taille_tranche(a, cycle_r, w_loop, h_loop, libre_ram)`.
  Verifier apres coup avec `grep -rn "_taille_segment" pipeline_talkinghead.py` (doit etre vide).
- **Regle** : un nom de fonction faux ne se voit qu'a l'execution — un `python -c "import ast; ..."`
  ou un simple `python -m py_compile` ne le detecte pas. Lancer le pipeline sur un volet court
  avant le run de production.

## 2. `AttributeError: 'list' object has no attribute 'items'` a l'etape i

- **Symptome** (fin de run, apres les heures de calcul) :

```
  File "...\pipeline_talkinghead.py", line 907, in etape_rapport
    for cle, val in m.items():
AttributeError: 'list' object has no attribute 'items'
```

- **Cause** : `mesures_hf.json` n'est PAS un dict. `hf_rapport.py` construit une **liste** d'un dict
  par instant mesure (`mesures = []` ligne 127, `mesures.append(entree)` ligne 170,
  `json.dump(mesures, ...)` ligne 187). Preuve sur le fichier reel :
  `json.load(...)` -> `list` de 3 elements, chacun avec `t`, `box`, `colonnes`.
- **Correction** : fonction `blocs_mesures(m)` qui accepte **les deux** formes (dict et liste),
  utilisee par `etape_rapport` ; le rapport affiche `### t=1.0`, `### t=2.0`, ... pour une liste.
  Verifie sur le fichier reel du volet 6 : 3 blocs produits, 1 bloc sur un dict, `[]` sur `None`.
- **Regle** : avant d'ecrire `for k, v in x.items()` sur du JSON produit par un autre outil,
  mesurer la forme racine (`print(type(d).__name__, len(d))`) sur un fichier reel — c'est 5 secondes
  contre la perte du rapport en fin de run. Un rapport qui ne se genere plus ne fait pas echouer
  le run : il passe inapercu.

## 3. Assemblage final : double crochet ffmpeg (`[[0:v]][1:v]overlay=`)

- **Symptome** (reproduit le 23/09 sur cette machine, ffmpeg de `C:\ProgramData\chocolatey\bin`) :

```
[AVFilterGraph] Trailing garbage after a filter: overlay=0:0[v]
[AVFilterGraph] Error parsing filterchain '[[0:v]][1:v]overlay=0:0[v]' around: overlay=0:0[v]
Error : Invalid argument
```

- **Cause** : la variable de chainage contient **les crochets** : `cour = "[0:v]"` puis le f-string
  ajoute les siens (`f"[{cour}][{idx}:v]overlay=..."`) -> `[[0:v]][1:v]`. ffmpeg ne connait que
  l'etiquette `[x]` ; les crochets font partie de la **syntaxe**, pas du nom du flux.
- **Correction** : `cour = "0:v"` (sans crochets), les crochets restant uniquement dans le f-string :

```python
cour = "0:v"                 # jamais "[0:v]"
filtres.append(f"[{cour}][{idx}:v]overlay=0:0:enable='between(t,{l['start']},{l['end']})'[v{idx}]")
cour = f"v{idx}"             # idem : sans crochets
```

- **Verification A/B (a refaire en 5 s si un graphe ffmpeg est en doute)** :

```bash
ffmpeg -v error -f lavfi -i color=c=red:s=64x64:d=1 -f lavfi -i color=c=blue:s=64x64:d=1 \
  -filter_complex "[[0:v]][1:v]overlay=0:0[v]" -map "[v]" -f null -     # -> Error parsing filterchain
ffmpeg -v error -f lavfi -i color=c=red:s=64x64:d=1 -f lavfi -i color=c=blue:s=64x64:d=1 \
  -filter_complex "[0:v][1:v]overlay=0:0[v]" -map "[v]" -f null -       # -> silence = OK
```

  `-f null -` valide un graphe sans ecrire de fichier : le test ne touche aucune video produite.
- **Regle generale** : chainer des labels en Python = la variable porte le **nom** (`v1`), le
  f-string porte la **syntaxe** (`[v1]`). Mettre les deux dans la variable donne des doubles crochets.

## 4. Assemblage final : un graphe non borne (`moov` absent, « encodage interminable »)

**Symptome** : l'encodage final 1080p tourne des heures, le fichier grossit sans fin, et une fois
arrete `ffprobe` repond :

```
[mov,mp4,m4a,3gp,3g2,mj2] moov atom not found
...: Invalid data found when processing input
```

**Cause racine** : les incrustations sont des images ajoutees en `-loop 1` (entrees **infinies**) et
la commande ffmpeg d'`assemble_v6.py` ne portait ni `-shortest` ni `-t`. Sans borne, ffmpeg encode
jusqu'a l'arret force : l'index `moov` n'est ecrit qu'a la toute fin, donc **le fichier livre ne
pouvait jamais etre lisible**. Mesure : le meme rendu de 336 s termine en **~6 min** avec
`-shortest`, contre **2 h 31** sans (4 h 48 de video generee, `speed=1.91x`). C'est la cause reelle
du « assemblage beaucoup trop lent », pas l'encodeur.

**Correction** (dans `assemble_v6.py`, commande finale) :

```python
"-pix_fmt", "yuv420p", "-r", "25", "-shortest", "-c:a", "aac", ...
```

**Regles :**

- **Tout graphe ffmpeg dont une entree est une image en `-loop 1` doit porter `-shortest` (ou
  `-t <duree>`).** Sans borne, le graphe n'a pas de fin — le symptome n'est pas une erreur mais un
  fichier qui grossit et un process qui ne rend jamais la main.
- **Controle AVANT de lancer** : lire la ligne de progression ffmpeg (`frame=... time=... speed=...`).
  Si `time=` depasse la duree de l'audio source, le graphe est non borne : couper et corriger.
- **Ne pas deduire la taille attendue d'un run precedent non borne.** Ici 441 Mo puis 707 Mo venaient
  d'encodages infinis ; le fichier juste fait 218 Mo pour 336 s. Une bande de taille heritee d'un run
  casse fait conclure a tort a un resultat invalide.
- **Fin d'encodage = deux conditions** : plus aucun process `ffmpeg` **et** taille stable pendant
  60 s. La seule stabilite ou la seule taille ne suffisent pas.
- **Validation de livraison (`ffprobe` sur le fichier final)** : `duration` = duree de l'audio,
  `nb_frames` = `duration x fps` (8410 = 336,4 x 25), codec `h264`, 1920x1080, audio `aac`. Un
  `duration` coherent avec `nb_frames` prouve que le fichier est complet (pas seulement present).
- Lancer l'encodage final en `terminal(background=true, notify_on_complete=true)` pour qu'une fin de
  session ne le tue pas au milieu, puis verifier par sondage (`stat` de taille + `tasklist`), jamais
  en bloquant le shell.

## 5. PNG d'incrustation decodes a 25 im/s

- **Cause** : `["-loop", "1", "-i", png]` sans `-framerate` : une image **statique** est relue au
  rythme de sortie (25 im/s). Avec 5 PNG = 125 decodages/s pour rien, en plus du decodage video.
- **Correction** : `["-loop", "1", "-framerate", "1", "-i", png]` pour **chaque** PNG
  (incrustations et filigrane). Le framerate de sortie reste impose par `-r 25` ; l'overlay repete
  la derniere image, le rendu est identique.
- **Verification** : `grep -n 'framerate' assemble_v6.py` -> une occurrence par entree PNG.

## 6. ffmpeg orphelin apres l'echec du script

- **Symptome** : un `assemble_v6.py` qui echoue laisse son `ffmpeg` vivant (subprocess non tue) ; il
  consomme un coeur pendant des heures et peut tourner **en parallele** du suivant. Volet 6 : deux
  ffmpeg infinis en simultane, 2 h 30 d'assemblage au lieu de ~15 min.
- **Correction** : envelopper l'appel ffmpeg et tuer l'orphelin.

```python
try:
    r = subprocess.run(cmd, capture_output=True, text=True)
except Exception:
    subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True)
    raise
if r.returncode != 0:
    subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True)
    sys.exit(1)
```

- **Verification** : `grep -n taskkill assemble_v6.py` (2 occurrences) ; `tasklist | grep -i ffmpeg`
  doit etre vide apres un echec.
- **Regle** : un encodage n'est pas termine parce que le script a rendu la main — verifier qu'aucun
  `ffmpeg.exe` ne tourne.

## 7. Reference de 19 s et duree cible d'un volet (correctifs 9 et 10)

- **Symptome** : toutes les estimations du volet 6 etaient faussees. Mesure du 23/09 sur les deux
  fichiers du Bureau : `tutotete19.mp4` dure **19,12 s** (extrait) et `tutotete20_jev_llmwiki.mp4`
  (= volet 6 publie) dure **336,40 s**. La « reference 336 s » annoncee pointait donc sur un clip
  de 19 s.
- **Regle** : la reference de format et de duree d'un volet est **le volet precedent publie**,
  verifiee par `ffprobe` au demarrage ; **si elle dure moins de 60 s, arreter et demander la bonne
  reference** (garde-fou `verifier_reference()` dans `assemble_v6.py`).
- **Duree cible** : jamais une valeur ronde — c'est la duree **reelle** du dernier
  `sortie_latentsync_<volet>*.mp4` (greffe `_hf` prioritaire), passee a l'assemblage en `-t` en plus
  de `-shortest` (`dernier_latentsync()` + `duree_ffprobe()`). Volet 6 : 336,44 s.
- **Verification (sans encoder)** : `VIDEO_REFERENCE="<clip de 19 s>" python assemble_v6.py` doit
  s'arreter sur « reference suspecte » **avant** tout appel ffmpeg.

## 8. Scripts du pipeline non versionnes

`data\video_youtube\` est gitignore : un correctif applique seulement la-bas disparait a la
reinstallation. Le gabarit vit dans `%LOCALAPPDATA%\hermes\scripts\video\` (copie, jamais de
placement) : `pipeline_talkinghead.py`, `assemble_v6.py` (futur `assemble_template.py`),
`faire_overlays_v6.py`, `surveiller_v6.py`, `PIPELINE_TALKINGHEAD_README.md`.
