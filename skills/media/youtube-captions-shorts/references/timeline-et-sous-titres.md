# Timeline et sous-titres — recette

## 1. Choisir la bonne génération de segments

Un projet peut contenir plusieurs jeux : `segments.json` (texte v1), `segments_v2.json`,
`segments_v3.json`, et les durées `segments_generation*.json`. Seul un couple texte/durées
COHÉRENT produit une timeline juste.

- Durée audio de référence :
  `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 <audio.wav>`
- Somme annoncée d'une génération :
  `python -c "import json;print(sum(s['duree_s'] for s in json.load(open('segments_generation_vX.json'))['segments']))"`
- Retenir la génération dont la somme égale la durée audio à ~0,01 s près, puis prendre le
  `segments_vN.json` de MÊME numéro pour le champ `texte`.
- Vérifier la cohérence caractères : somme des `n_chars` ≈ longueur du script TTS (l'écart normal
  est de quelques dizaines de caractères de ponctuation/espaces).
- Un fichier peut aussi être plus court que le nombre de WAV présents (dossier `segments_v3/` avec
  90 wavs alors que le JSON n'en décrit que 73) : c'est le JSON qui fait foi, les wavs en trop sont
  des reprises.

## 2. Caler aux ancres

Le fichier d'alignement (`timestamp_align_*.json`) donne des `idx` de segment et un `debut_s` :

```
{"chapitres": [{"idx": 0, "debut_s": 0.0}, {"idx": 4, "debut_s": 59.56}, ...]}
```

Construction par intervalle : pour chaque paire d'ancres `[a, b)`,

```
scale = (t_b - t_a) / sum(duree_origine(a..b-1))
start(idx) = t_a + cumul des durées mises à l'échelle précédentes
```

Ajouter une ancre finale `(n_segments, durée_audio)` pour couvrir la fin. Vérifier ensuite que
`timeline[-1].end` égale la durée audio.

## 3. Découpe des sous-titres

Fonction de référence (42 car./ligne, 2 lignes max) :

```python
def split_text(text, max_chars=42, max_lines=2):
    words = ' '.join(text.split()).split()
    lines, cur = [], ''
    for w in words:
        if not cur: cur = w
        elif len(cur) + 1 + len(w) <= max_chars: cur += ' ' + w
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    subs, i = [], 0
    while i < len(lines):
        subs.append('\n'.join(lines[i:i+max_lines])); i += max_lines
    return subs
```

Répartition : `duree_chunk = duree_segment * (len(chunk) / somme_lens)`. Écrire en UTF-8 nu
(`open(path, 'w', encoding='utf-8')` — pas de BOM pour YouTube).

## 4. Tableau phonétique → standard (français)

Le script TTS est écrit pour la prononciation ; les sous-titres doivent revenir à l'orthographe.
Appliquer ces remplacements sur le texte AVANT la découpe (les phrases longues d'abord) :

| Phonétique (script TTS) | Standard (sous-titres) |
|---|---|
| `R T X trois mille soixante-dix Ti` | `RTX 3070 Ti` |
| `R T X` | `RTX` |
| `trois mille soixante-dix Ti` | `3070 Ti` |
| `i sept treize mille sept cents K` | `i7-13700K` |
| `vingt-quatre gigaoctets` | `24 Go` |
| `mille quatre cent quarante p` | `1440p` |
| `mille quatre-vingts p` | `1080p` |
| `soixante images par seconde` | `60 fps` |
| `quarante-cinq images par seconde` | `45 fps` |
| `D L S S` | `DLSS` |
| `Axi` | `Axii` |
| `C D Projekt Red` | `CD Projekt Red` |
| `Deux mille quinze` | `2015` |
| `The Witcher trois` | `The Witcher 3` |
| `six millions` | `6 millions` |
| `P S cinq Pro` | `PS5 Pro` |
| `Switch deux` | `Switch 2` |
| `G T A O` | `GTAO` |
| `quatre K` | `4K` |
| `Direct X douze` | `DirectX 12` |
| `P S S R` | `PSSR` |

Compléter au besoin : tout nombre écrit en toutes lettres dans le script TTS doit revenir en
chiffres dans les sous-titres.

## 5. Format de sortie

SRT :

```
1
00:00:00,000 --> 00:00:05,462
Première ligne
Deuxième ligne
```

VTT : en-tête `WEBVTT` puis `HH:MM:SS.mmm --> HH:MM:SS.mmm`. Horodatage : arrondir les
millisecondes et propager la retenue (60 s -> minute, 60 min -> heure), sinon on écrit
`00:00:60,000`.
