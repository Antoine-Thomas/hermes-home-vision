# Montage ffmpeg : panneaux PNG sur une video (pop-up et plein ecran)

Recette complete, validee de bout en bout : panneaux statiques ou animes poses sur des creneaux
horaires, avec fondus, fond enchaines, et audio conserve en copie de flux. Les sections 1 a 4
valent pour les DEUX mises en page ; la section 5 ajoute ce qui est propre au plein ecran.

## 1. Entrees ffmpeg

La BASE est l'entree 0 (elle porte la video et l'audio). Chaque calque de panneau suit : l'entree du
panneau `i` est a l'index `i`, la carte de fin a `len(PANELS)+1`.

```python
cmd = ["ffmpeg", "-hide_banner", "-v", "warning", "-stats", "-y", "-i", BASE]
for n in (1, 2, 3, 4, 5, 6, 7, 8):
    if n in SEQ:                       # panneau anime
        cmd += ["-framerate", "25", "-start_number", "1",
                "-i", ov("ov_%02d_f%%02d.png" % n)]
    else:                              # panneau statique (image infinie)
        cmd += ["-loop", "1", "-framerate", "25", "-i", ov("ov_%02d.png" % n)]
cmd += ["-loop", "1", "-framerate", "25", "-i", ov("ov_card.png")]
cmd += ["-filter_complex", graphe(), "-map", "[vout]", "-map", "0:a", "-c:a", "copy",
        "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-t", "%.6f" % DUR, "-r", "25", OUT]
```

`-c:a copy` garde l'audio de la base tel quel : c'est ce qui permet de prouver l'egalite des md5.
Ne PAS reencoder l'audio quand la commande dit « audio conserve ».

## 2. Graphe

```python
PANELS = [(1, 30, 60), (2, 60, 90), (3, 90, 120), (4, 120, 150),
          (5, 150, 180), (6, 180, 210), (7, 210, 240), (8, 240, 270)]
CROSS, FD = 0.3, 0.5

def graphe():
    g = ["[0:v]setpts=PTS-STARTPTS[v0]"]
    for i, (n, t0, t1) in enumerate(PANELS, start=1):
        tin = t0 - (0.0 if i == 1 else CROSS)      # fondu enchaine
        tout = t1 - FD
        if n in SEQ:
            g.append("[%d:v]format=rgba,setpts=PTS+%.3f/TB,"
                     "tpad=stop_mode=clone:stop_duration=%.3f,"
                     "fade=t=in:st=%.3f:d=%.3f:alpha=1,"
                     "fade=t=out:st=%.3f:d=%.3f:alpha=1[o%d]"
                     % (i, tin, (t1 - tin) + 1.0, tin, FD, tout, FD, n))
        else:
            g.append("[%d:v]format=rgba,fade=t=in:st=%.3f:d=%.3f:alpha=1,"
                     "fade=t=out:st=%.3f:d=%.3f:alpha=1[o%d]" % (i, tin, FD, tout, FD, n))
        g.append("[v%d][o%d]overlay=0:0:enable='between(t,%.3f,%.3f)'[v%d]"
                 % (i - 1, n, tin, t1, i))
    ic = len(PANELS) + 1
    g.append("[%d:v]format=rgba,fade=t=in:st=286:d=0.5:alpha=1[ocard]" % ic)
    g.append("[v8][ocard]overlay=0:0:enable='between(t,286,%.3f)'[vcard]" % (DUR + 0.2))
    g.append("[vcard]format=yuv420p[vout]")
    return ";\n".join(g)
```

Points non negociables :

- `fade=...:alpha=1` (et non un fade couleur) : le panneau doit devenir transparent, pas noir.
- Les bornes `st=` du `fade` sont sur la timeline de l'entree APRES `setpts`, donc en secondes
  absolues du montage ; `enable` est sur la timeline de la base. Les deux sont calees sur 0.
- La carte de fin se pose a `t1 = DUR + 0.2`, au-dela de la fin : sinon les dernieres images
  repassent sur le fond pendant que le muxer arrondit.

## 3. Panneaux animes : generer la sequence

Un PNG est fige : pour « des fleches qui se dessinent » ou « une liste revelee ligne a ligne », il
faut N variantes. On les produit depuis la MEME source matplotlib que les panneaux approuves, en
parametrant l'element anime — jamais en retouchant les PNG livres.

```python
def arrow(ax, x1, y1, x2, y2, af=1.0, color="#ffd166", lw=3, ms=24):
    """Fleche dessinee a la fraction af (0..1) : meme code, longueur parametree."""
    if af <= 0.001:
        return
    ax.add_patch(FancyArrowPatch((x1, y1), (x1 + af * (x2 - x1), y1 + af * (y2 - y1)),
                 arrowstyle="-|>", mutation_scale=ms, linewidth=lw, color=color,
                 shrinkA=0, shrinkB=0))
```

Pour une revelation ligne a ligne, parametrer le nombre de lignes dessinees
(`principes[:nlines]`), pas la geometrie. Meme chose pour l'habillage : chaque variante passe par
la MEME fonction d'habillage que les panneaux statiques.

Recuperer la figure en image sans passer par un fichier temporaire :

```python
fig.canvas.draw()
w, h = fig.canvas.get_width_height()
im = Image.frombytes("RGBA", (w, h), bytes(fig.canvas.buffer_rgba()))
plt.close(fig)
```

13 images a 25 fps = 0,52 s (fleches) ; 26 images = 1,04 s (revelation de lignes).

## 4. Habillage pop-up (PIL)

Calque 1920x1080 transparent, panneau pose a sa position, avec fond sombre, coins arrondis, bordure
et ombre portee — l'ombre deborde du panneau, d'ou un canevas plus grand que la carte :

```python
img = raw.convert("RGBA").resize((PW, PH), Image.LANCZOS)
face = Image.new("RGBA", (PW, PH), (14, 20, 32, 255))   # fond charte sous le schema
face.alpha_composite(img)
img = face
m = Image.new("L", (PW, PH), 0)
ImageDraw.Draw(m).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=24, fill=255)
img.putalpha(m)
ImageDraw.Draw(img).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=24,
                                      outline=(76, 201, 240, 255), width=4)
sh = Image.new("RGBA", (PW + 4 * 12, PH + 4 * 12), (0, 0, 0, 0))
ImageDraw.Draw(sh).rounded_rectangle([24, 24, 24 + PW - 1, 24 + PH - 1], radius=24, fill=(0, 0, 0, 120))
sh = sh.filter(ImageFilter.GaussianBlur(12))
canvas = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
canvas.alpha_composite(sh, (PX - 24, PY - 24 + 6))
canvas.alpha_composite(img, (PX, PY))
```

Le calque final est TOUJOURS 1920x1080 : `overlay=0:0` suffit, la position est dans le calque.
Un habillage a `900x500` depuis une source `1920x1080` (1,777) change le ratio en 1,80 — ecrasement
vertical de 1,25 %. Faire ce qui est demande et le chiffrer dans le rapport.

## 5. Variante plein ecran : calques opaques, sujet masque

Consigne type : « les panneaux sont plein ecran, la personne disparait pendant chaque creneau ».
Le calque n'est plus un trou transparent mais une image 1920x1080 OPAQUE. Trois consequences.

**a) Cadrage du contenu.** Recadrer la source sur la boite englobante du canal alpha, puis mettre a
l'echelle a ratio conserve pour tenir dans `FILL` (0,94) de la dimension contraignante, et centrer
sur le fond charte. Ne jamais etirer pour remplir les deux axes : la deformation est refusee en
bloc. Rendre la source en SURRÉSOLU (meme `figsize`, `dpi` multiplie par 1,5) puis reduire — le
facteur final est < 1, donc net. Un contenu de format large (2:1) ne remplit alors que ~80 % de la
SURFACE : c'est attendu, la marge sombre sert de cadre, et ca se chiffre dans le rapport.

```python
bb = raw.getchannel("A").getbbox()          # contenu utile du PNG transparent
content = raw.crop(bb)
cw, ch = content.size
s = min(FILL * 1920 / cw, FILL * 1080 / ch)  # jamais > 1 en pratique
content = content.resize((round(cw * s), round(ch * s)), Image.LANCZOS)
canvas = Image.new("RGBA", (1920, 1080), (14, 20, 32, 255))   # #0e1420, OPAQUE
canvas.alpha_composite(content, ((1920 - content.width) // 2, (1080 - content.height) // 2))
```

**b) Fond opaque SOUS les panneaux, sur toute la plage des creneaux.** Sinon, pendant le fondu
enchaine de 0,3 s, les deux panneaux sont a alpha < 1 et la personne repasse au travers.

```
color=c=0x0e1420:s=1920x1080:r=25,format=rgba,
  fade=t=in:st={BG_IN}:d=0.5:alpha=1,fade=t=out:st={BG_OUT}:d=0.5:alpha=1[obg];
[v0][obg]overlay=0:0:enable='between(t,{BG_IN},{BG_OUT+0.6})'[vb0];
```

Puis la chaine des panneaux part de `[vb0]` au lieu de `[v0]`. `BG_IN` 0,5 s AVANT l'entree du
premier panneau : a `t0` le sujet est deja totalement masque quand le fondu d'entree du panneau
demarre. `BG_OUT` ~0,3 s APRES la fin du dernier panneau : le panneau s'efface sur le fond, puis le
fond s'efface sur la personne.

**c) Le controle change de cible.** Sans bordure de carte, c'est le FOND CHARTE qui se compte :
`scripts/verif_popups_timecodes.py SORTIE 0e1420 t1,t2,...` avec un seuil absolu eleve, et on lit la
FRACTION (> 30 % panneau plein ecran, < 5 % sujet visible, entre les deux transition). Le seuil par
defaut du script (40 px) ne suffit plus : la scene du sujet contient deja quelques % de sombre.
Corollaire de rapport : le poids du livrable s'effondre (des minutes de panneaux quasi plats a CRF
constant, ~1/4 du poids de la meme duree de tete parlante). L'expliquer, ne pas le presenter comme
une anomalie.

## 6. Controle

1. `ffprobe -show_entries format=duration -show_entries stream=width,height,r_frame_rate,nb_frames`
   sur la sortie : duree, definition, cadence, nombre d'images egaux a la base.
2. `scripts/verif_popups_timecodes.py SORTIE 4cc9f0 15,30,45,60,75,...,290,293` : presence du panneau
   par creneau, 0 hors creneau, carte plein ecran sur la fin. En plein ecran il n'y a pas de
   bordure : compter le FOND CHARTE (`0e1420`), seuil eleve, et lire la fraction (section 5c).
3. Audio : `ffmpeg -i X -map 0:a -c copy -f md5 -` sur la base ET sur la sortie, digests egaux.
4. Ecart final vs (image de base + calque compose en numpy) dans la zone du pop-up : un ecart moyen
   de 1-2/255 est l'encodage seul ; au-dela, le calque n'est pas celui attendu.

La lecture d'image par un modele de vision n'est PAS un controle : deja vue annoncer un panneau
absent a un timecode ou le comptage de pixels donnait 0, et des fleches « pas entierement dessinees »
a un timecode ou elles l'etaient. Compter les pixels, puis regarder l'image seulement pour decrire.

5. Coins arrondis, ombre, absence de debordement : se mesurent (SKILL.md regle 11). Et comparer la
   capture et la reference au MEME timecode, apres avoir compose le calque RGBA sur l'image de base —
   un calque transparent differ tel quel, ou compare a l'image d'un autre instant, ne prouve rien.

## 7. Variante carte flottante : grande carte arrondie centree

Consigne type : « les panneaux sont trop grands, il faut un peu moins que 1080p, avec des bords
arrondis, on doit voir le decor autour ». Le calque reste TRANSPARENT (le sujet n'est pas masque),
mais la carte est grande et opaque.

```python
CARD, POS, R = (1600, 900), (160, 90), 30        # 1920-2*160 = 1600 ; 1080-2*90 = 900
sb = min(FILL * CARD[0] / cw, FILL * CARD[1] / ch)   # contenu a 94 % de la CARTE
card = Image.new("RGBA", CARD, (14, 20, 32, 255))
card.alpha_composite(content.resize((round(cw * sb), round(ch * sb)), Image.LANCZOS), centre)
card.putalpha(masque_arrondi(CARD, R))            # arrondi AVANT l'ombre, sinon l'ombre est carree
canvas = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
canvas.alpha_composite(ombre_floue(card, R, blur=14, alpha=130, dy=8), POS_decale_de_l_ombre)
canvas.alpha_composite(card, POS)
```

- Positions entieres : choisir des cotes qui donnent un centrage exact (`(1920 - w) / 2` et
  `(1080 - h) / 2` entiers). 1600x900 -> (160, 90).
- Ne pas confondre « la carte remplit sa boite » et « le contenu remplit la carte » : le contenu
  garde sa marge interne de 6 %, c'est ce qui rend le cartouche lisible.
- Creneaux courts + respiration : quand la consigne separe les panneaux par des plages de video
  normale, SUPPRIMER le fondu enchaine (`tin = t0`, pas de recouvrement de 0,3 s). Les panneaux ne
  se touchent plus ; un recouvrement laisserait deux cartes superposees a l'ecran. Un panneau de
  12 s est pleinement visible 11 s apres les deux fondus de 0,5 s.
- Duree d'affichage et bornes de creneau sont INDEPENDANTES : raccourcir l'affichage (30 s -> 12 s)
  ne deplace pas les departs de panneaux, donc les timecodes de chapitres d'une description restent
  valables. Reduire la duree d'affichage et allonger la respiration ameliore la retention : c'est le
  retour utilisateur qui motive la variante, pas un gout esthetique.
