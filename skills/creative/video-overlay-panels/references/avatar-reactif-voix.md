# Avatar reactif a la voix (overlay a fond transparent)

Complement des panneaux PNG : un avatar qui PULSE avec la piste voix, a poser dans un coin du montage.
A ouvrir quand la demande est « une presence visuelle / un avatar en bas a droite » sans montrer de
visage ni produire un vrai talking-head.

## Outil : Yapatar

- Source `https://github.com/modem-dev/yapatar`, licence **MIT** (lue dans le README du depot) : piste
  audio + image d'avatar -> video a fond transparent (halo, anneaux sur les transitoires, contour deforme
  par le spectre). Pas de keying, pas de fond vert.
- Prerequis : Node 20+ et `ffmpeg` sur le PATH.
- `npm install` ; `node src/make-avatar.js` (avatar de remplacement) ; `node src/serve.js` pour regler
  l'aspect dans un apercu navigateur ; `node src/render.js --audio <wav> --avatar <png> [--codec prores]`.
- Sortie : `out/avatar_alpha.mov` (ProRes 4444 + alpha + l'audio source) = LE fichier a importer.
  `out/preview_opaque.mp4` est un aplatissement sur fond plein, pour l'oeil seulement : l'importer met
  un rectangle gris sur l'image.
- MIT + rendu 100 % local : compatible avec une chaine monetisee, aucune dependance a un service.

Statut : source, licence et prerequis verifies (depot accessible, README lu, node et ffmpeg presents) ;
la chaine de rendu n'a PAS encore ete executee ici. Ne pas presenter le rendu comme valide avant de
l'avoir produit et inspecte.

## Pieges du poste de montage

- Importer sur une piste AU-DESSUS de la capture, echelle ~15-20 % de la hauteur, puis **couper l'audio
  de la piste avatar** (ou re-rendre avec `--no-audio`) : le fichier porte la piste voix et se recale par
  la forme d'onde — le laisser actif double l'audio du montage.
- **Alpha premultiplied par defaut**, c'est ce que composite Resolve/Premiere. Un halo blanc ou un
  lisere lumineux autour de l'avatar = alpha straight composite comme premultiplied (re-rendre avec le
  reglage par defaut) ; un halo sombre ou trouble = le cas inverse.
- Codec : `hevc` exige `hevc_videotoolbox`, **macOS seulement**. Ailleurs `--codec prores` ou
  `--codec png` — le renderer verifie au demarrage les codecs reellement disponibles.
- RAM : croissance lineaire avec la duree (pic ~1,2 Go sur 30 min d'audio). Negligeable sur un short,
  a surveiller sur un long.
- Aucune etape ne modifie la video source : l'overlay est un fichier separe, remplacable sans re-rendre
  le montage.

## Quand l'utiliser

Format court : oui — la presence visuelle est un atout et l'avatar aide l'identification immediate dans
un feed. Analyse longue : non — l'avatar occupe l'oeil sans servir le propos, et sans lip-sync il peut
lire comme un gadget. Sur les formats longs, l'habillage (cartouche de titre, bandeau de chapitre, carton
de signature) couvre le besoin d'identite visuelle sans cet effet. Pour un vrai visage qui parle
(lip-sync), ce sont les pipelines talking-head / latentsync, pas cet overlay.
