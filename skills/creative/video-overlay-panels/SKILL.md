---
name: video-overlay-panels
description: "Use when making illustrated video panels/overlays."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video, panels, matplotlib, overlays, png, charte]
    category: creative
---

# Panneaux illustres pour video (PNG transparents, matplotlib)

## When to use

Un lot de panneaux/schemas a incruster dans une video : une image par concept, fond transparent,
charte sombre, produits par matplotlib (backend Agg) et poses au montage. Vaut aussi pour tout lot
d'images de charte a livrer (vignettes, ecrans de titre, schemas d'architecture).

Un panneau = un GABARIT repetable, pas une figure dessinee a la main : la coherence du lot vient de
la palette et des helpers, pas d'une relecture panneau par panneau.

Incrustations ANIMEES posees sur des frames video (texte, bandeaux, zoom pixels, metrique recalculee
et affichee a chaque frame, assemblage ffmpeg) : voir `references/incrustations-cv2-video.md`.

Panneaux poses sur une video en creneaux horaires (fondus, fondu enchaine, animation par sequence
d'images), en POP-UP (calque transparent pose sur le sujet) ou en PLEIN ECRAN (calque opaque qui
masque le sujet) : voir `references/montage-overlay-ffmpeg.md`.

## Gabarit de figure

```python
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
W, H, DPI = 1920, 1080, 100
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
fig.patch.set_alpha(0)                                  # fond transparent
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
# ... placement ...
fig.savefig(chemin, transparent=True)
```

Tout se place en coordonnees 0..1, jamais en pixels : le code tient alors a n'importe quelle
definition, et une boite se decrit par `(x, y, w, h)` dans une seule unite. Boites =
`FancyBboxPatch(..., boxstyle="round,pad=0.01,rounding_size=0.02")`, fleches =
`FancyArrowPatch(..., arrowstyle="-|>", shrinkA=0, shrinkB=0)`, coches et croix = deux `Line2D`.

Charte a reprendre (`#1f2a44` face, `#2b2d42` face sombre, `#ffffff` texte, `#c9d6e8` texte discret,
`#4cc9f0` cyan, `#2ec4b6` teal, `#06d6a0` vert, `#ffd166` accent, `#e63946` rouge, `#b388ff` violet) :
un accent de couleur PAR niveau, le meme pour toutes les boites d'un meme niveau ; les fleches
prennent la couleur de la boite d'origine ou l'accent.

## Regle 1 — mesurer le debordement de texte AVANT de livrer

Un panneau se juge sur ses bounding boxes, pas a l'oeil. Un libelle qui sort de sa boite ou du bord
droit est ecreme par `savefig` sans un mot d'avertissement, et ca ne se voit pas sur une planche de
controle reduite. Le controle coute une fonction et trouve un defaut reel a chaque premier passage.

```python
PAIRS = []                                   # (patch, artiste texte) empiles par le helper box()

def box(ax, x, y, w, h, t, fc=..., ec=..., fs=28, track=True):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.02", ...)
    ax.add_patch(p)
    if not t:
        return
    txt = ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, ...)
    if track:
        PAIRS.append((p, txt))

def save(fig, ax, nom):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for p, t in PAIRS:                       # le texte doit tenir DANS sa boite
        pb, tb = p.get_window_extent(r), t.get_window_extent(r)
        if not (pb.x0 <= tb.x0 and tb.x1 <= pb.x1 and pb.y0 <= tb.y0 and tb.y1 <= pb.y1):
            print("DEBORDEMENT", t.get_text()[:40], "texte %.0fx%.0f boite %.0fx%.0f"
                  % (tb.width, tb.height, pb.width, pb.height))
    for t in ax.texts:                       # et tout texte dans la figure (titres compris)
        tb = t.get_window_extent(r)
        if tb.x0 < 0 or tb.x1 > W or tb.y0 < 0 or tb.y1 > H:
            print("HORS FIGURE", t.get_text()[:40])
    fig.savefig(nom, transparent=True)
    del PAIRS[:]
    plt.close(fig)
```

Le suivi des paires boite/texte doit etre fait par le helper qui les CREE : un texte matplotlib n'est
pas enfant du patch, il n'y a aucun lien a retrouver apres coup. Reparer en reduisant la police ou en
deplacant l'element dans une boite dediee (un libelle qui debordait du bord droit est passe dans une
boite sous son parent, relie par une fleche) — jamais en rognant le texte.

## Regle 2 — texte blanc sur transparent : fond sombre obligatoire

La charte est en texte blanc : le panneau n'est lisible que pose sur un fond sombre. Le dire a
l'utilisateur, et **composer les planches de controle sur la couleur de fond REELLE** : un controle
visuel qui aplatit le PNG sur du blanc annonce « titre quasi illisible / filigrane » alors que le
panneau est correct. Un faux defaut de ce genre coute un tour de correction inutile.

Pose sur une VIDEO dont le fond est clair (piece blanche, exterieur), le panneau transparent est
invisible : composer un fond sombre charte (`#0e1420`) DANS la carte, sous le schema, avant d'arrondir
les coins et d'ajouter la bordure. Un fond ajoute se declare dans le rapport, il ne reste pas
implicite.

## Regle 3 — jamais de logo de marque

Aucun logo officiel ne se reproduit. Batir une forme vectorielle generique (polygone a facettes pour
un cristal, rectangle a lignes pour une base de connaissances) et l'annoncer comme telle dans le
rapport. Si l'utilisateur veut le vrai logo, lui demander le fichier PNG/SVG.

## Regle 4 — les formes decoratives restent hors du controle de debordement

Cristaux, pastilles, coches et croix se tracent en `Line2D`/`Polygon` et passent `track=False` :
elles ne sont pas censees tenir dans une boite et declareraient un faux debordement.

## Regle 5 — apparition progressive : le montage, pas le PNG

Une liste numerotee revelee ligne a ligne tient dans UN PNG ; le fondu se fait au montage. Livrer un
PNG unique et le dire, ou produire N variantes pretes a poser — demander, ne pas decider a la place
de l'utilisateur.

Mecanique cote ffmpeg (sequence d'images tenue par `tpad`, fleches qui se dessinent) :
`references/montage-overlay-ffmpeg.md`.

## Regle 6 — texte a l'ecran et texte parle divergent volontairement

Garder l'orthographe de la marque a l'ecran (`SiYuan`) et la graphie phonetique dans la voix
(`Si Yüan`) : deux contraintes distinctes. Ne pas « harmoniser » l'un sur l'autre sans le demander.

## Regle 7 — incrustations cv2 : ASCII seulement, et le controle se fait sur les pixels

`cv2.putText` (familles HERSHEY_*) ne rend pas les accents ni les guillemets francais : e accent, c
cedille, a grave, guillemets sortent en glyphes faux ou en carres. Translitterer le texte A L'ECRAN
et garder la virgule decimale francaise, qui est de l'ASCII ; le rapport ecrit, lui, garde les
accents. Un libelle ASCII est le seul rendu fiable sans embarquer une police externe.

Pour un defaut d'emprise ou de lisibilite, croire les PIXELS, pas une relecture d'image : compter les
pixels de la couleur exacte de l'incrustation et verifier leur bounding box (un cadre annonce
« debordant sur la colonne voisine » par une relecture visuelle etait en fait a 0 px hors de sa
colonne). Un faux defaut coute un tour de correction inutile, exactement comme un controle compose sur
fond blanc pour un panneau transparent (regle 2).

Sur une video, deux precautions de plus : bande sombre derriere chaque libelle (le contenu passe
dessous frame par frame) et echelle bornee par la place disponible AVANT de coller, sinon
l'incrustation deborde quand la zone source grandit.

## Regle 8 — montage pop-up : creneaux, fondus, et ce que `crop` ne fait pas

Un panneau pose sur un creneau `[t0, t1]` se monte par `overlay` pilote par `enable` plus un `fade`
alpha sur l'entree image :

```
[1:v]format=rgba,fade=t=in:st={tin}:d=0.5:alpha=1,fade=t=out:st={t1-0.5}:d=0.5:alpha=1[o1];
[v0][o1]overlay=0:0:enable='between(t,{tin},{t1})'[v1]
```

- `-loop 1 -framerate 25 -i calque.png` pour un panneau statique.
- Fondu enchaine entre deux panneaux consecutifs : avancer l'ENTREE du suivant de 0,3 s, et son
  `enable` de la meme valeur ; chacun garde son fondu de 0,5 s, les deux se recouvrent de 0,3 s.
- Une animation INTERNE (fleches qui se dessinent, lignes revelees une a une) se livre en SEQUENCE
  d'images (`-framerate 25 -start_number 1 -i seq_%02d.png`), recalee par `setpts=PTS+{tin}/TB` et
  TENUE par `tpad=stop_mode=clone:stop_duration=...`. Sans `tpad` le `fade` de sortie ne s'applique
  jamais : la chaine ne voit que les images de la sequence, et `overlay` (`eof_action=repeat`) fige
  la derniere image au lieu de la faire disparaitre en fondu.
- `crop` n'evalue pas ses expressions par image : `w`/`h` dynamiques (`t` ou `n` dedans) sont calcules
  UNE fois a la configuration — `h='...t...'` leve une erreur, `h='2*n'` fige la hauteur a 2 px sans
  rien dire. Un volet ou balayage temporel ne passe donc PAS par `crop` : livrer une sequence d'images
  (ou `geq`, `xfade`).
- Panneau qui recouvre le sujet : recadrer la zone du pop-up sur l'image de BASE et la regarder avant
  de livrer, puis rapporter le recouvrement mesure. L'ancrage absolu vient de la commande ; la
  validation se fait sur le resultat.

Controle : `scripts/verif_popups_timecodes.py <video> <hex> <t1,t2,...>` compte les pixels de la
bordure a chaque timecode. Piege : sur un timecode en PLEIN fondu la bordure est melangee au fond et
le compteur tombe a 0 — un 0 juste apres une borne de creneau est normal, ne pas le lire comme
« panneau absent ». Un audio « copie de flux » se prouve par `ffmpeg -i X -map 0:a -c copy -f md5 -` :
sans `-c copy` ffmpeg decode en PCM et le digest ne prouve plus la copie.

## Regle 9 — trois mises en page : pop-up, plein ecran, carte flottante

Confirmer laquelle AVANT de produire : passer de l'une a l'autre est une refonte (regeneration des
calques), pas un reglage — et la TAILLE se change en meme temps que la DUREE du creneau. POP-UP =
calque transparent, petit panneau pose sur le sujet (regle 8). PLEIN ECRAN = calque OPAQUE 1920x1080,
fond charte, sujet totalement masque pendant le creneau. CARTE FLOTTANTE = grande carte opaque a coins
arrondis (ex. 1600x900 posee en (160, 90)) : le sujet reste visible tout autour, sans que l'ecran soit
un rectangle dur. Dans le doute, demander la taille et la duree : c'est le reglage que l'utilisateur
itere le plus (le meme projet est passe de 900x500 a plein ecran a 1600x900, avec 30 s puis 12 s
d'affichage).

Plein ecran, trois regles fermes :

- contenu a ~94 % de la dimension CONTRAIGNANTE, ratio conserve, centre. Ne JAMAIS etirer pour
  remplir les deux axes : la deformation est refusee en bloc, alors que la marge sombre haut/bas
  est acceptee comme cadre naturel. Le remplissage en SURFACE reste donc inferieur (~80 % pour un
  contenu large) : le chiffrer dans le rapport au lieu de le corriger.
- rendre la source en surresolu (meme `figsize`, `dpi` x1,5) puis REDUIRE : le facteur final reste
  < 1 et le texte est net. Agrandir un panneau deja rendu en 1920x1080 rend le texte mou.
- un fond opaque charte pose SOUS les panneaux, actif sur toute la plage des creneaux et non
  panneau par panneau. Sans lui, pendant le fondu enchaine de 0,3 s les deux panneaux sont a
  alpha < 1 et le sujet repasse au travers.

Recette, seuils et controle : `references/montage-overlay-ffmpeg.md` sections 5 (plein ecran) et 7
(carte flottante).
Generateur de calques : `scripts/plein_ecran_94.py <src_dir> <out_dir> [motif] [fond_hex] [fill]`.

Parametrer, ne pas coder en dur : taille, position, rayon des coins, opacite et flou d'ombre sont des
variables d'UN generateur. Un script fige oblige a recopier toute la mise en page a chaque variante ;
un generateur parametre rend la variante en un appel. Coins arrondis + ombre portee sont ce qui fait
lire la carte comme un cartouche voulu plutot qu'un rectangle pose sur l'image.

Avant tout rendu long : un mode `test` qui ne sort que les ~46 premieres secondes, extraire
l'image du creneau a valider (`ffmpeg -ss <t> -i test.mp4 -frames:v 1`), la soumettre a la vision,
puis STOP et attendre le GO. Un graphe valide sur 46 s l'est sur 294 s : 25 s de controle evitent
un rendu de plusieurs minutes a refaire.

## Regle 10 — le brief se verifie contre le media

La consigne n'est pas une source de verite sur l'etat du disque ni sur la numerotation.

- Verifier que chaque fichier nomme existe (chemin, taille, duree). Un fichier annonce et absent se
  rapporte comme ecart de mesure ; ne pas lui substituer un autre fichier en silence, meme si le
  remplacant parait evident.
- Croiser la liste de captures demandee avec la table de creneaux : « capture a 3:45 (panneau 5) »
  contredit une table qui place le panneau 5 en 2:30. Suivre la table (c'est elle qui pilote le
  montage), livrer la capture au timecode du panneau nomme, et signaler l'incoherence du brief.

## Regle 11 — un calque pose se controle par la mesure, pas par la relecture

La vision n'est pas un instrument de mesure et se contredit selon l'echelle : sur une carte de 1600 px
elle a annonce « coins droits » pour un rayon de 30 px, « bordures dures / debordement » sans preuve,
et « pas d'ombre » pour une ombre faible mais reelle — puis, sur un zoom x4 du meme coin, elle a vu
l'arc. Soumettre l'image a la vision pour DECRIRE ; jamais pour trancher un defaut geometrique.

- Coins arrondis : relever ligne par ligne, dans le coin, le premier x ou le fond de la carte apparait,
  et comparer a la theorie du cercle (`r - sqrt(r^2 - (r - dy)^2)`). Un arc conforme a quelques px
  prouve le rayon. Joindre un ZOOM x4 du coin comme piece visuelle : c'est a cette echelle que l'arc
  devient perceptible.
- « Debordement » : borner le contenu utile DANS la carte en excluant un anneau de bord (rayon +
  marge). Un test naif compte le decor situe hors de la carte comme du contenu qui deborde.
- Ombre portee : comparer la luminance moyenne de la bande juste autour de la carte (capture vs image
  de base) a celle d'une bande temoin plus loin. Quelques niveaux d'ecart sur la bande et ~0 sur le
  temoin prouvent l'ombre ; « ombre legere » se chiffre, ne s'affirme pas.
- Comparaison capture / reference : extraire l'image de base au MEME timecode que la capture. Un
  timecode voisin fait bouger le sujet et fabrique un faux ecart de 10-15/255.
- Ne jamais differ un calque RGBA tel quel : ses zones transparentes portent des RGB a 0 et tout
  ecart global devient absurde. Composer d'abord sur l'image de base
  (`base*(1-alpha) + calque*alpha`), puis differ le resultat.

## Verification

`scripts/audit_panneaux.py <dossier> [motif] [fond_hex]` : par fichier — dimensions, mode RGBA,
alpha du coin (0 = transparent), taille en octets, SHA256 court ; signale tout ecart a 1920x1080
RGBA ; ecrit `_planche_controle.png` (grille 480x270 par case, empilee sur le fond donne).

Un lot n'est pas livre sans : 0 debordement de boite, 0 texte hors figure, planche regeneree apres
la derniere correction.

Un MONTAGE n'est pas livre sans : duree / definition / cadence / nombre d'images egaux a la base,
md5 audio de copie de flux egal a la base, presence du panneau a chaque creneau et absence hors
creneau (comptage de pixels), et ecart moyen avec le calque compose en numpy de 1-2/255 (l'encodage
seul).
