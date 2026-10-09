# Extraction des Shorts 9:16 — commandes et exécution

## 1. Vérifier la source

```
ffprobe -v error -show_entries stream=width,height,codec_name,bit_rate,codec_type \
  -of default=noprint_wrappers=1 "<source.mp4>"
```

Attendu pour une source 4K : 3840x2160. Si la source est plus petite, NE PAS upscaler : signaler
et demander confirmation avant de lancer.

## 2. Extraire les pistes

Audio (copie, pas de réencodage) :
```
ffmpeg -y -ss <start> -i <speech.wav> -t <dur> -c copy short_XX_audio.wav
```
Avatar (copie, préserve l'alpha ProRes) :
```
ffmpeg -y -ss <start> -i <avatar_alpha.mov> -t <dur> -c copy short_XX_avatar.mov
```

## 3. Recadrer en 9:16 vertical 4K

```
ffmpeg -y -ss <start> -i "<source.mp4>" -t <dur> \
  -vf "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=2160:3840:flags=lanczos" \
  -c:v libx264 -preset slow -crf 16 -profile:v high -pix_fmt yuv420p \
  -c:a aac -b:a 320k -ar 48000 -ac 2 short_XX_vertical_4k.mp4
```

Math à connaître : sur une source 3840x2160, `crop=ih*9/16:ih` donne 1215x2160 (largeur = 2160 *
9/16), puis `scale=2160:3840` est un upscale ×1,78, pas un crop 4K natif. Le dire dans le rapport
si l'utilisateur attend du « natif ». Mettre `-ss` avant `-i` (input seeking) : le décodage démarre
à l'offset même sur un fichier de plusieurs Go.

## 4. Exécution longue — background obligatoire

Un Short de 45 s en `-preset slow -crf 16` demande ~8 min. `execute_code` a un timeout court
(~5 min) : lancer l'encodage via `terminal(background=true, notify=true)` et suivre avec
`process_manage(action='poll'|'wait')`. UN SEUL encodage à la fois : en parallèle le débit
s'effondre (~0,07x contre ~0,17x) et rien ne finit plus vite. Les copie-only (audio, avatar) sont
instantanées et peuvent tourner ensemble.

## 5. Vérifier la sortie

```
ffprobe -v error -show_entries stream=width,height,codec_name,pix_fmt,bit_rate \
  -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 short_XX_vertical_4k.mp4
```

Cibles : 2160x3840, h264, yuv420p, débit ~50-80 Mbps, durée ≈ demandée.

## 6. Packaging (par Short)

`metadata.json` :

```
{
  "short_id": "short_01",
  "start_time": "03:09", "end_time": "03:54",
  "duree_s": 45.47, "resolution": "2160x3840", "codec": "h264",
  "bitrate_mbps": 59.27, "fichier_mo": 322.0,
  "critere": "punchline_avis_tranche",
  "titre": "...", "description": "...",
  "hashtags": ["#TheWitcher3", "..."], "tags": ["...", "...", "..."],
  "hook_phrase": "...", "transcription": "..."
}
```

CSV récapitulatif : `short_id, start_time, end_time, duree_s, resolution, bitrate_mbps, titre,
description, hashtags, tags, hook_phrase, chemin_video_4k, chemin_srt`.
Limites : titre ≤ 60 caractères, description ≤ 200 caractères avec 3-5 hashtags, 3 tags.
