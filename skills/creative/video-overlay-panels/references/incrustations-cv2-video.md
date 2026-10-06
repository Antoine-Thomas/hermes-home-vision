# Incrustations cv2 sur des frames video (metrique recalculee en direct)

Generer des frames composites avec cv2 (bandeaux, texte, zoom), une image par frame de video, puis
les assembler avec ffmpeg. Cas type : SOURCE et N sorties cote a cote pendant qu'une metrique est
RECALCULEE a chaque frame et affichee sous chaque colonne.
Implementation de reference : `_montage_explicatif.py` (skill video-fidelity-metrics, dossier
scripts/) — la lire avant de reecrire, la boucle complete y est. Le texte a l'ecran et le controle
d'emprise sont dans la regle 7 du SKILL.md. Un filtre ffmpeg ne calcule aucune metrique par frame :
l'assemblage ffmpeg seul ne peut pas produire ce montage.

## Ordre de travail qui evite les reprises

1. Calibrer sur une mesure de reference connue ; 2. rendre UNE frame et la faire relire ; 3. corriger
la mise en page ; 4. lancer les N frames ; 5. controler la sortie ENCODEE (pas les PNG) ; 6. rapporter
les ecarts mesures (frames tenues, frames perdues) sans les masquer.

## Calibration et alignement — avant de composer

Reproduire une valeur de reference deja connue (meme frame, meme bbox) : un ecart au dixieme veut dire
bbox, index de frame ou alignement faux, et tous les chiffres a l'ecran seraient faux.
Bbox detectee sur la SOURCE SEULE et appliquee a toutes les colonnes : les sorties sont alignees au
pixel, une bbox par video ferait diverger les zones comparees. Controler par
`MAD(src[i], clip[i]) = 0.000` ; un MAD non nul impose de retrouver le decalage reel, jamais
d'aligner « a l'oeil ».
Quand le run GPU est interdit : insightface en `CPUExecutionProvider` + `prepare(ctx_id=-1)` — la
detection de visages est un pretraitement, pas une inference de generation. Le prouver en citant la
ligne `Applied providers` dans le rapport.
Cache des bbox dans un `.npz` SIGNE (nombre de frames + chemin + taille + mtime de la source) :
~0,6 s par frame en CPU ; la deuxieme execution doit etre immediate, mais un cache non signe se
reutilise a tort apres un changement de source.

## Composition et assemblage

- Bandes de hauteur dont la somme tombe pile : 1920x720 = 56 (titre + compteur) + 40 (titre de
  colonne) + 360 (image 640x360) + 100 (bande de mesures) + 164 (bas) ; 3 colonnes de 640 = 1920/3.
- Lire les videos en sequentiel (`read()` frame par frame), jamais par seek aleatoire.
- Clip plus court que la duree demandee : repeter sa derniere image et lister les index tenus dans le
  JSON de sortie — ne pas inventer d'images, ne pas raccourcir la duree demandee.

```
ffmpeg -y -framerate 25 -i f_%04d.png -i <clip_audio> -frames:v 250 -t 10.000 \
  -map 0:v:0 -map 1:a:0 -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart sortie.mp4
```

`-t` en option de SORTIE borne l'audio a la duree exacte. Pas de `-shortest` (il coupe la video sur la
fin de l'audio).

## Controles (sur la sortie encodee, pas sur les PNG)

- ffprobe : dimensions, cadence, `nb_frames`, duree video EGALE a la duree audio.
- Images : extraction en 32x12 niveaux de gris, moyenne par frame -> 0 frame noire.
- Live : hasher la bande de mesures sur 5 frames reparties -> hash tous differents = preuve que la
  valeur est bien recalculee a chaque frame et pas figee sur une constante.
- Audio : correlation des PCM avec la piste d'origine — 0,999999 attendu apres re-encodage AAC
  (l'egalite d'octets est impossible). « l'audio a ete mappe » n'est pas une verification.

## Pieges de composition

- Borner l'echelle d'une incrustation AVANT de la coller :
  `min(3.0, (largeur_colonne-20)/largeur_zone, (hauteur-20)/hauteur_zone)`, puis coller avec rognage —
  sinon elle glisse dans la colonne voisine quand la zone grandit (une bbox de bouche change de taille
  a chaque frame quand le visage s'approche).
- Bande sombre derriere chaque libelle : pose a meme l'image, il devient illisible des que le contenu
  passe dessous.
- Un zoom doit porter sur la MEME zone que la metrique affichee : le lecteur voit le defaut exactement
  la ou le chiffre est mesure.
