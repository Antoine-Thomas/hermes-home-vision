# Bugs du pipeline talking head (volet 6) — symptome / cause / correction

Pipeline : `C:\Users\searc\AppData\Local\hermes\data\video_youtube\pipeline_talkinghead.py`
Assemblage : `C:\Users\searc\AppData\Local\hermes\data\video_youtube\assemble_v6.py`
(wrapper de l'etape g : `LatentSync\tests\post_hf_transfer.py`)

Ces trois bugs ont coute 4 interventions manuelles pendant le volet 6 (22-23/09/2026).
Aucun n'etait visible avant le run : les deux premiers ne se declenchent qu'a des branches
precises (`--segmenter auto`, JSON de mesures present) et le troisieme seulement si la variable
contient les crochets.

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

## 4. Un assemblage interrompu laisse un MP4 inutilisable (moov absent)

Constate le 23/09 : l'encodage final 1080p a ete tue volontairement a 17:27 (banc d'essai),
le fichier livre restait a 441,8 Mo / 463 470 640 octets, et `ffprobe` repond :

```
[mov,mp4,m4a,3gp,3g2,mj2] moov atom not found
...: Invalid data found when processing input
```

Le fichier grossit pendant tout l'encodage et **n'esquisse la mouvbox qu'a la fin** : une taille
qui augmente ne prouve pas un fichier valide. Consequences pratiques :

- ne jamais livrer/annoncer un MP4 sans `ffprobe` sur le fichier **final** (pas sur l'entree) ;
- un `taskkill /F` sur ffmpeg, une coupure de session ou un retry du watchdog laissent ce cadavre
  au chemin de livraison — le supprimer ou relancer l'encodage avant de conclure quoi que ce soit ;
- lancer toujours l'encodage final en `terminal(background=true, notify_on_complete=true)` pour
  qu'une fin de session ne le tue pas au milieu.
