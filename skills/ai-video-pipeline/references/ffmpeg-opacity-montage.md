# FFmpeg Opacity Montage 1s/1s — Alternance par transparence

Alternance mécanique sans écran noir : V1 au-dessus, V2 en dessous, on module l'alpha de V1 chaque seconde.

## Quand utiliser

- Pattern 1s V1 / 1s V2 sur toute la durée (ex: 2753s) sans transition xfade — flash cut par opacité.
- Deux sources même durée/résolution/fps qui avancent en parallèle (même timecode).
- Grading global voulu après overlay (pas par segment).

## Vérifications préalables

- `ls -lh "$OUT" 2>&1` — si existe, STOP + confirmation, jamais écraser.
- `ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate` sur V1 et V2 — confirmer 1920x1080 60fps et durée identique.
- Pas de MCP Premiere pour ce type — tout FFmpeg single-pass.

## Filter (validé FFmpeg 8.1, libavfilter 11.14)

```
[1:v]setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease:eval=frame,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=60[base];
[0:v]setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease:eval=frame,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=60,format=yuva420p,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(eq(mod(floor(T),2),0),alpha(X,Y),0)'[fg];
[base][fg]overlay=0:0:format=auto,eq=contrast=1.05:saturation=1.12:brightness=0.005,curves=all='0/0 0.25/0.22 0.75/0.78 1/1'[out]
```

- `T` majuscule dans `geq` (temps en secondes), `t` minuscule ne marche pas dans ce filtre.
- `format=yuva420p` obligatoire avant `geq` pour que `alpha(X,Y)` existe.
- `colorchannelmixer=aa='if(eq(mod(floor(t),2),0),1,0)'` ÉCHOUE sur cette build : `Undefined constant or missing '(' in 't),2),0),1,0)'` — utiliser `geq` ci-dessus.
- Grading (`eq` + `curves`) APRÈS `overlay`, pas par segment.

## Test 10s avant encodage complet

```bash
ffmpeg -y -t 10 -i "V1.mp4" -t 10 -i "V2.mp4" -filter_complex "[1:v]setpts=PTS-STARTPTS[base];[0:v]setpts=PTS-STARTPTS,format=yuva420p,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(eq(mod(floor(T),2),0),alpha(X,Y),0)'[fg];[base][fg]overlay=0:0:format=auto,format=yuv420p[out]" -map "[out]" -c:v libx264 -preset veryfast -crf 20 -r 60 -pix_fmt yuv420p -an "/tmp/test_opacity_10s.mp4"
for ts in 0.5 1.5 2.5 3.5; do ffmpeg -y -ss $ts -i /tmp/test_opacity_10s.mp4 -vframes 1 /tmp/frame_test_${ts}.jpg; done
```

Comparer visuellement ou par distance pixel : 0.5s doit matcher V1, 1.5s V2, 2.5s V1, 3.5s V2. Si inversé, changer `eq(...,0)` en `eq(...,1)`.

## Encodage complet

```bash
ffmpeg -y -i "V1" -i "V2" -filter_complex "...voir ci-dessus..." -map "[out]" -c:v libx264 -preset veryfast -crf 20 -r 60 -pix_fmt yuv420p -an -movflags +faststart "$OUT"
```

- Lancer en background (`terminal background=true notify=true`) — durée 1h30-2h30 pour 45min de source.
- Si >3h sur `veryfast`, basculer sur `ultrafast`.
- Log : `C:/Users/searc/AppData/Local/Temp/ffmpeg_opacity_full.log`.

## Vérification finale

- `ffprobe -v error -show_entries format=duration,size,bit_rate:stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 "$OUT"` — attendre durée ~2753.95s, 1920x1080 60fps yuv420p 0 audio.
- Frames : extraire à 0.5 / 1.5 / 2.5 / 3.5 / 2700s, vérifier alternance V1/V2/V1/V2.
- `ffprobe` est natif Windows : chemin `C:/Users/...` natif, pas `/c/Users/...` MSYS, sinon `No such file`.
