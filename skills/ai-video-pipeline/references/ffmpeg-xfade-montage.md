# FFmpeg xfade Montage — Référence détaillée

Couvre l'alternance mécanique A/B en une passe (5508 segments 1s, ~47 min de sortie après recouvrement xfade).

## 1. Vérifications préalables (ne jamais écraser)
- `ls -lh "$OUT" 2>&1` — si existe, stop + demander confirmation, jamais `-y` implicite.
- `ls -lh montage_alternance_5s.mp4` — confirmer intact après encodage.
- `ffprobe -v error -show_entries format=duration -of csv=p=0` sur A/B ; `nb = 2*ceil(max(dur)/1)`.

## 2. Analyse virages (optionnelle, 900s max)
- OpenCV `calcOpticalFlowFarneback` sur frames 320x180, échantillon toutes les 2s (~1377/vidéo).
- Seuils : `|mean_flow_x| > 2.0` => gauche (`<0`) / droit (`>0`), `1.0-2.0` => incertain, sinon rien.
- Sortie `%TEMP%/virages.json` `{videoA:[{time,type,confiance}],videoB:[...]}`.
- Si timeout/erreur : abandonner, xfade `fade:0.3` partout.

## 3. Mapping jonctions
- Pour chaque jonction `t_n`, chercher virage dans `[t_n-1, t_n+1]`.
- incertain : alterner `wipeleft`/`wiperight` sur occurrences consécutives (compteur).
- Compter par type pour rapport (ex: wipeleft 2587, wiperight 2449, fade 471).

## 4. Construction filter_complex (fichier)
- Par segment `i` : `[0:v]trim=start=S:end=E,setpts=PTS-STARTPTS,eq=...,scale=...,pad=...,setsar=1,fps=60[sI]`
- Chaîne xfade séquentielle : `[s0][s1]xfade=transition=wipeleft:duration=0.5:offset=O0[xf0]; [xf0][s2]xfade=...:offset=O1[xf1] ...`
- Offsets : `O0 = durée(s0) - dur_transition_0`, `Ok = Ok-1 + durée(s{k+1}) - dur_transition_k` (somme segments moins somme transitions déjà appliquées).
- Grading final sur dernier `[xflast]` : `curves=all='0/0 0.25/0.23 0.75/0.78 1/1',vignette=angle=PI/5:mode=forward[xflast_g]`
- Fichier ~11k lignes / 1.7 Mo — passer via `-filter_complex_script C:/.../filter_1s.txt` (pas `-filter_complex "$(cat ...)"` qui explose la ligne de commande).
- Test parse : `ffmpeg -i A -i B -filter_complex_script filter.txt -map "[xflast_g]" -f null - -t 2` => EXIT 0.

## 5. Encodage
```
ffmpeg -i A -i B -filter_complex_script filter.txt -map "[xflast_g]" \
  -c:v libx264 -preset medium -crf 20 -r 60 -pix_fmt yuv420p -an -movflags +faststart "$OUT"
```
- Lancer en background, log `%TEMP%/ffmpeg_1s.log`, poll régulier. 1-3h attendu.
- Sans `-y` pour ne pas écraser.

## 6. Vérification
- `ffprobe` : 1920x1080, 60fps, `codec_name=h264`, pas de piste audio, `duration >= max(durA,durB)` (tolérance 1s), taille >0.
- `ffmpeg -ss 60 -i "$OUT" -frames:v 1 test.jpg` => 0.
- Nettoyer : `filter_*.txt`, `virages.json`, `test.jpg` listés dans rapport ; garder log.

## Pitfalls spécifiques
- `vignette=angle=PI/5:mode=forward` — `vignette=PI/5` seul est syntaxe invalide.
- Chaîne 5507 xfade parse OK sur ffmpeg 7.x — ne basculer vers fallback `concat` + `fade=t=in/out` ou `1 xfade /10` que si parse échoue.
- `curves` avec `'` dans shell : échapper correctement dans fichier (pas d'expansion).
