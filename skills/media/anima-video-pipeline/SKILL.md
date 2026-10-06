---
name: anima-video-pipeline
description: "Use when rebuilding the ANIMA video montage."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [video, anima, ffmpeg, overlays, matplotlib, charte, latentsync]
    category: media
---

# ANIMA — pipeline du montage panneaux + tête parlante (série Hermès)

## When to Use / Quand l'utiliser

Reconstruire ou modifier le montage d'un volet ANIMA : 8 panneaux illustrés incrustés sur une
tête parlante, avec animations d'entrée (flèches qui se dessinent, révélation ligne à ligne) et
sortie, plus une carte de fin. Vaut aussi pour toute variante « panneaux sur vidéo » de la série.

Ce skill est né de deux jours de réglages sur le volet 7 : il fixe les chemins, la palette, les
positions et surtout les six pièges qui ont coûté le plus de tours.

## Les 4 étapes, chemins exacts

Racine du projet : `C:\Users\searc\Desktop\ANIMA` — scripts dans `_work_2c\`.

| # | Rôle | Script | Sortie |
|---|------|--------|--------|
| 1 | Panneaux illustrés (PNG 1920x1080 transparents) | `C:\Users\searc\Desktop\ANIMA\make_schemas_v2.py` | `schemas_v2\panneau_01..08.png` |
| 2 | Calques animés + habillage panneau | `C:\Users\searc\Desktop\ANIMA\_work_2c\make_calques_v7.py` | `_work_2c\calques_v7\` (100 PNG) |
| 3 | Montage ffmpeg | `C:\Users\searc\Desktop\ANIMA\_work_2c\build_v7_final.py` | `ANIMA_v7_final_v7.mp4` |
| 4 | Vérification objective | `C:\Users\searc\Desktop\ANIMA\_work_2c\check_v7.py` | captures + tableau de mesure |

`make_schemas_v2.py` et `_work_2c\make_panneaux_v2.py` sont le MÊME fichier (sha256
`fbb752dfd1834054ecd43d1b23563c43c93b4dae3c91568b8055a23059b082be`) — n'en corriger qu'un.

Les versions antérieures (`make_calques_v6.py`, `make_plein_ecran_v6.py`, `build_v6.py`,
`check_plein_ecran.py`) correspondent à d'autres mises en page validées puis abandonnées
(pop-up 900x500, plein écran 1920x1080) : ne pas les confondre avec la version courante.

## ÉTAPE 1 — palette exacte de la charte

À reprendre telle quelle (source : `make_schemas_v2.py`, lignes 18-32) :

```
BOX_FACE #1f2a44   BOX_DARK #2b2d42   BOX_EDGE #4f6f9f   TEXT  #ffffff
MUTED    #c9d6e8   CYAN     #4cc9f0   TEAL     #2ec4b6   GREEN #06d6a0
ACCENT   #ffd166   RED      #e63946   RED_BG   #3a1f2b   RED_TC #ffb3b3
GREEN_BG #12332a   PURPLE   #b388ff
```

Fond de la vidéo et des cartes : **#0e1420** (plus sombre que BOX_FACE, pour que les boîtes se
détachent). Les 8 panneaux : titre en haut (`y=0.955`), boîtes et flèches au centre, sous-titre
bas (`y=0.075-0.20`). Carte de fin : `ANIMA_v7_carte_fin.png` (1920x1080 opaque).

Titre exact de chaque panneau (c'est ce qui s'affiche à l'écran, à réutiliser dans les timers
YouTube) :

```
01 Le problème : l'hallucination      05 JEV — décision typée
02 Mémoire hiérarchique à 4 niveaux   06 Laya — modèle local
03 SiYuan = Obsidian                  07 Pourquoi j'ai changé de moteur TTS
04 Recherche hybride + RRF            08 Les 5 principes anti-hallucination
```

## ÉTAPE 2 — calques animés (réglages qui ont été validés)

- Rendu matplotlib à **`GEN_DPI = 150`** (figure `figsize=(19.2, 10.8)` -> 2880x1620) puis
  **réduction**. Le contenu est toujours réduit (facteur 0,57-0,68), jamais agrandi : c'est ce qui
garde le texte net.
- Recadrage sur la bbox du canal alpha, puis ajustement à **94 % de la dimension contraignante**.
- **Panneau : 1600x900 posé en (160, 90)** (centré dans 1920x1080).
- **Coins arrondis 30 px**, **ombre portée alpha 130, flou 14 px, décalage +8 px**, fond **#0e1420**
  opaque à l'intérieur de la carte. Le décor et la personne restent visibles autour.
- Séquences d'images (habillage appliqué à CHAQUE image) :
  - panneaux 01, 02, 04, 05, 06 -> **13 images** (0,52 s), flèches qui se dessinent ;
  - panneau 08 -> **26 images** (1,04 s), les 5 principes apparaissent un à un ;
  - panneaux 03, 07 -> 1 image statique ; carte de fin -> 1 image plein écran.
- Pour animer un panneau il faut régénérer le panneau avec un paramètre de fraction : `arrow()`
  accepte `af` (0..1) qui raccourcit l'extrémité, et `p08(nlines)` ne dessine que k principes.

Autre mise en page possible (déjà validée par l'utilisateur, réutilisable) : 900x500 en (960, 290)
coins 24 px — c'était la version « pop-up ».

## ÉTAPE 3 — montage ffmpeg

Timing validé (vidéo 294,120 s = 7353 images à 25 fps) :

```
P1 30-42   P2 60-72   P3 90-102  P4 120-132
P5 150-162 P6 180-192 P7 210-222 P8 240-252   carte 286 -> fin
12 s de panneau, 18 s de respiration entre panneaux (le personnage parle).
```

Entrées : 1 tête parlante (`-i ANIMA_tete_finale.mp4`) puis, dans l'ordre des panneaux, soit
`-framerate 25 -start_number 1 -i ov_XX_f%02d.png` (séquence), soit `-loop 1 -framerate 25 -i ov_XX.png`
(statique), puis la carte. **L'index d'entrée du panneau N est N** : le panneau 1 est l'entrée 1, la
carte l'entrée 9.

Sortie : `-c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -movflags +faststart -r 25 -t 294.120`,
audio **`-map 0:a -c:a copy`**.

Le graphe `filter_complex` complet, à copier tel quel : `references/filtre-ffmpeg-v7.md`.

Usage du script : `python build_v7_final.py test36 | preview | full` (test36 = 36 s pour la
capture témoin, preview = 294 s en ultrafast pour valider le graphe, full = livrable CRF 18 slow).

## Les 6 pièges (mesurés, pas supposés)

1. **`tpad=stop_mode=clone` OBLIGATOIRE avant le `fade` de sortie d'une séquence.** Sans lui, la
   chaîne ne voit que les images de la séquence (13 images = 0,52 s) : le fondu de sortie prévu à
   `t1-0,5 s` n'est jamais appliqué, et `overlay` (`eof_action=repeat`) fige la dernière image à
   alpha 1 jusqu'à la coupure `enable` -> disparition sèche. Vérifié : c'est le premier piège
   rencontré sur ce projet.
2. **`overlay=0:0:enable='between(t,t0,t1)'`** : c'est ce qui borne l'apparition d'un panneau. Les
   bornes sont sur la timeline PRINCIPALE ; le `setpts=PTS+{t0}/TB` de la séquence aligne l'entrée
   sur la même timeline.
3. **`-c:a copy` pour un audio bit-à-bit.** La preuve se fait avec `-c copy` :
   `ffmpeg -i X -map 0:a -c copy -f md5 -`. Sans `-c copy` ffmpeg décode en PCM et le digest change
   (mesuré : `7e8f3770...` avec copie, `cfe122ab...` sans) -> le contrôle ne prouve plus rien.
4. **`-t` seul inclurait une image de trop** (règle souvent citée). NON reproduit sur ce build
   (ffmpeg n9.0.1) : `-t 2` sur une source 25 fps -> exactement 50 images ; `-t 294.120` sur le
   livrable -> exactement 7353 images. On garde `-t` ; `overlay=...:shortest=1` n'est pas
   nécessaire quand l'entrée principale est finie.
5. **`-frames:v` tronque l'audio.** Mesuré : `-frames:v 25` -> audio 0,998 s / 44 trames contre
   1,000 s / 45 trames avec `-t 1`. Effet réel mais faible (~1 trame AAC, 23 ms) ; la règle tient
   quand même : borner la durée avec `-t`, jamais avec `-frames:v`.
6. **`crop` ne réévalue pas ses expressions par image.** `h='790*t/294'` -> « Error when evaluating
   the expression » ; `h='2*n'` -> hauteur figée à 2 px, sans message. Un volet ou un balayage
   temporel ne passe donc PAS par `crop` : produire une séquence d'images (ce que fait l'étape 2).

## ÉTAPE 4 — vérification : on croit les pixels, jamais la vision seule

La vision se trompe à pleine échelle, et de façon reproductible : sur une carte 1600x900 à coins de
30 px elle a annoncé « coins droits » et « bordures dures / débordement » (les deux faux), et sur une
capture elle a décrit un décor absent. Toujours contrôler par la mesure.

Commande exacte :

```
python C:\Users\searc\Desktop\ANIMA\_work_2c\check_v7.py
```

Elle imprime un tableau `t(s) | % fond #0e1420 | lecture` et écrit les captures dans
`_work_2c\_verif_v7\`. Version générique réutilisable : `scripts/verif_pixels.py`.

Ce qu'il faut contrôler, et comment :

- **Présence/absence des panneaux** : compter les pixels du fond charte `#0e1420` (tolérance 8) —
  élevé pendant un créneau, ~2 % entre les panneaux. Attention : le décor contient des objets
  sombres, donc la **bbox** des pixels sombres est polluée ; pour l'emprise réelle du panneau,
  différencier la capture avec la frame de base au même instant.
- **Emprise du panneau** : `|capture - base| > 25` doit donner x[160..1759] y[90..989] = 1600x900.
  Hors panneau et hors ombre (marge 25 px), l'écart doit être ~0,5/255 : le décor et la personne
  sont intacts.
- **Conformité au calque** : recalculer `base*(1-a) + calque*a` dans la boîte du panneau et comparer
  à la capture. Attendu ~1,5-2,2/255 (l'encodage H.264 seul).
- **Animations** : compter les pixels de la couleur `ACCENT #ffd166` dans la séquence
  (ex. `ov_01_f01` = 0 px, `f04` = 124, `f08` = 244, `f13` = 404) puis dans le montage.
- **Intégrité de la base** : `sha256sum` de la source == celui du fichier annoncé intact.
- **Audio** : md5 avec `-c copy` identique base/livrable.

## Pièges de mesure (à ne pas refaire)

- Comparer une capture à une frame de base **prise à un autre instant** : la personne bouge, on
  croit à un défaut de compositing (écart 9/255 au lieu de 0,5). Toujours apparier les instants.
- Comparer une capture RGB à un calque RGBA : les zones transparentes du calque ont des valeurs RGB
  arbitraires (souvent 0,0,0) et l'écart global explose (15/255). Comparer dans la boîte du panneau,
  ou recomposer le calque sur la base.
- Se fier au bbox des pixels « sombres » : la pièce contient des objets sombres, la bbox s'étend
  jusqu'aux bords de l'image.
- Sur Windows, un chemin `/c/...` passé à un outil natif (ffmpeg, python) n'est pas converti :
  utiliser `C:/...` ou `C:\\...`.

## Greffe HF — masque « bande bouche/dents » : ABANDONNÉ (résultat mesuré)

Le post-traitement haute fréquence de la sortie LatentSync (`_work_2c\latentsync\_greffe_hf.py`)
corrige le manque de netteté du bas du visage :
`sortie = clip(cible + alpha * (src - flou(src)) * masque)`. La configuration retenue pour v7 est
**masque `visage`, alpha 2,0, keep 0,70**.

Une variante « masque `bande` » (bande resserrée sur la bouche/les dents, `BANDE_RX=0,40`,
`BANDE_RY=0,14`) a été testée pour monter l'amplitude de la bouche sans toucher au reste du visage.
Balayage alpha {1,5 ; 2,0 ; 2,5} x keep {0,70 ; 0,85} sur 10 frames instrumentées (`_pilote_bande.py`,
preuves : `_work_2c\latentsync\_pilote_bande\resultats.json` + `run_final.log`) :

| masque / réglage | amp bouche | amp visage | corr visage |
|---|---|---|---|
| visage a2,0 k0,70 (= v7) | 0,768 | 0,938 | 0,882 |
| bande a2,0 k0,85 | 1,025 | 0,489 | 0,521 |
| bande a2,5 k0,85 | 1,266 | 0,543 | 0,531 |

Verdict : la bande monte bien l'amplitude bouche (>1 = sur-restauration) mais **effondre le visage**
(amp 0,94 -> 0,43-0,54 ; corr 0,88 -> 0,48-0,53). Le critère d'adoption était « amp bouche >= 0,90
SANS dégrader le visage (amp >= 0,90 ET corr >= 0,90) » : **aucune combinaison ne le remplit**.

Cause : sur ce rendu, LatentSync régénère tout le visage (règle 62) — le détail haute fréquence utile
n'est pas localisé dans la bande bouche/dents, donc rétrécir le masque prive le reste du visage de la
restauration sans gain exploitable.

Règle à retenir : garder le masque `visage` (alpha 2,0, keep 0,70) ; ne pas chercher à gagner en
netteté de bouche en rétrécissant le masque. Contrôle anti-bruit maintenu : le bloc plat hors visage
reste à la valeur de la source (Laplacien 1,042, aucun bruit ajouté) quel que soit l'alpha.

## Livrables de référence

- `ANIMA_v7_final_v7.mp4` — 294,120 s, 1920x1080, 25 fps, 7353 images, sha256
  `4930be99ed3c508316b66deaccb8271feb289a0714297da4d3368557f1e8723c`, 131 913 189 o.
- `ANIMA_v7_final_v6.mp4` — version plein écran conservée comme archive.
- `_work_2c\calques_v7\` — 100 PNG, tous 1920x1080.
