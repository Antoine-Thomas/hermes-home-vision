# Graphe ffmpeg exact — ANIMA v7 (panneaux 1600x900, 12 s + 18 s de respiration)

Généré par `_work_2c\build_v7_final.py` (fonction `graph()`), écrit dans
`_work_2c\v7f_filter_full.txt` au moment du rendu du livrable
`ANIMA_v7_final_v7.mp4` (sha256 `4930be99ed3c508316b66deaccb8271feb289a0714297da4d3368557f1e8723c`).

## Correspondance entrées -> panneaux

```
entrée 0 : ANIMA_tete_finale.mp4                (vidéo + audio)
entrée 1 : calques_v7\ov_01_f%02d.png  (13 img)  entrée 2 : ov_02_f%02d.png (13)
entrée 3 : calques_v7\ov_03.png        (statique) entrée 4 : ov_04_f%02d.png (13)
entrée 5 : calques_v7\ov_05_f%02d.png  (13 img)  entrée 6 : ov_06_f%02d.png (13)
entrée 7 : calques_v7\ov_07.png        (statique) entrée 8 : ov_08_f%02d.png (26)
entrée 9 : calques_v7\ov_card.png      (statique, plein écran)
```

## filter_complex intégral (tel quel)

```
[0:v]setpts=PTS-STARTPTS[v0];
[1:v]format=rgba,setpts=PTS+30.000/TB,tpad=stop_mode=clone:stop_duration=13.000,fade=t=in:st=30.000:d=0.500:alpha=1,fade=t=out:st=41.500:d=0.500:alpha=1[o1];
[v0][o1]overlay=0:0:enable='between(t,30.000,42.000)'[v1];
[2:v]format=rgba,setpts=PTS+60.000/TB,tpad=stop_mode=clone:stop_duration=13.000,fade=t=in:st=60.000:d=0.500:alpha=1,fade=t=out:st=71.500:d=0.500:alpha=1[o2];
[v1][o2]overlay=0:0:enable='between(t,60.000,72.000)'[v2];
[3:v]format=rgba,fade=t=in:st=90.000:d=0.500:alpha=1,fade=t=out:st=101.500:d=0.500:alpha=1[o3];
[v2][o3]overlay=0:0:enable='between(t,90.000,102.000)'[v3];
[4:v]format=rgba,setpts=PTS+120.000/TB,tpad=stop_mode=clone:stop_duration=13.000,fade=t=in:st=120.000:d=0.500:alpha=1,fade=t=out:st=131.500:d=0.500:alpha=1[o4];
[v3][o4]overlay=0:0:enable='between(t,120.000,132.000)'[v4];
[5:v]format=rgba,setpts=PTS+150.000/TB,tpad=stop_mode=clone:stop_duration=13.000,fade=t=in:st=150.000:d=0.500:alpha=1,fade=t=out:st=161.500:d=0.500:alpha=1[o5];
[v4][o5]overlay=0:0:enable='between(t,150.000,162.000)'[v5];
[6:v]format=rgba,setpts=PTS+180.000/TB,tpad=stop_mode=clone:stop_duration=13.000,fade=t=in:st=180.000:d=0.500:alpha=1,fade=t=out:st=191.500:d=0.500:alpha=1[o6];
[v5][o6]overlay=0:0:enable='between(t,180.000,192.000)'[v6];
[7:v]format=rgba,fade=t=in:st=210.000:d=0.500:alpha=1,fade=t=out:st=221.500:d=0.500:alpha=1[o7];
[v6][o7]overlay=0:0:enable='between(t,210.000,222.000)'[v7];
[8:v]format=rgba,setpts=PTS+240.000/TB,tpad=stop_mode=clone:stop_duration=13.000,fade=t=in:st=240.000:d=0.500:alpha=1,fade=t=out:st=251.500:d=0.500:alpha=1[o8];
[v7][o8]overlay=0:0:enable='between(t,240.000,252.000)'[v8];
[9:v]format=rgba,fade=t=in:st=286.000:d=0.500:alpha=1[ocard];
[v8][ocard]overlay=0:0:enable='between(t,286.000,294.320)'[vcard];
[vcard]format=yuv420p[vout]
```

Deux formes de branches, à ne pas confondre :

- **séquence** (panneaux 01, 02, 04, 05, 06, 08) :
  `format=rgba,setpts=PTS+{t0}/TB,tpad=stop_mode=clone:stop_duration=13.000,fade=in,fade=out`
- **statique** (panneaux 03, 07) : entrée `-loop 1 -framerate 25`, donc pas de `setpts`
  ni de `tpad` — `format=rgba,fade=in,fade=out` suffit.

`stop_duration` = `(t1 - t0) + 1 s` : il doit couvrir le fondu de sortie situé à `t1 - 0,5 s`.
`fade` de sortie à `t1 - 0,5 s`, `enable` borné à `[t0, t1]` — les deux bornes se terminent ensemble.

## Commande complète

```
ffmpeg -hide_banner -v warning -stats -y \
  -i ANIMA_tete_finale.mp4 \
  -framerate 25 -start_number 1 -i calques_v7\ov_01_f%02d.png \
  -framerate 25 -start_number 1 -i calques_v7\ov_02_f%02d.png \
  -loop 1 -framerate 25 -i calques_v7\ov_03.png \
  -framerate 25 -start_number 1 -i calques_v7\ov_04_f%02d.png \
  -framerate 25 -start_number 1 -i calques_v7\ov_05_f%02d.png \
  -framerate 25 -start_number 1 -i calques_v7\ov_06_f%02d.png \
  -loop 1 -framerate 25 -i calques_v7\ov_07.png \
  -framerate 25 -start_number 1 -i calques_v7\ov_08_f%02d.png \
  -loop 1 -framerate 25 -i calques_v7\ov_card.png \
  -filter_complex <le graphe ci-dessus> \
  -map "[vout]" -map 0:a -c:a copy \
  -c:v libx264 -pix_fmt yuv420p -movflags +faststart -r 25 \
  -t 294.120 -crf 18 -preset slow ANIMA_v7_final_v7.mp4
```

Mesures du rendu de référence : 7353 images, 3 min 37 s (1,35x temps réel), 131 913 189 o.

## Variantes conservées (autres mises en page validées)

- **plein écran 1920x1080, 30 s, fondu enchaîné 0,3 s** : `_work_2c\build_v6.py` +
  `_work_2c\plein_ecran_v6\`, avec en plus une couche `color=c=0x0e1420:s=1920x1080:r=25`
  posée SOUS les panneaux (`fade` alpha à 29,5 s et 269,8 s) pour que les fondus enchaînés se
  fassent sur fond sombre et que la personne ne réapparaisse jamais entre deux panneaux.
- **pop-up 900x500 en (960, 290), coins 24 px** : `_work_2c\make_calques_v6.py` +
  `_work_2c\build_v6.py` (ancienne forme), rétention moindre (30 s plein écran).
