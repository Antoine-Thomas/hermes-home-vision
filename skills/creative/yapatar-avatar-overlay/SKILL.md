---
name: yapatar-avatar-overlay
description: "Use when rendering a Yapatar voice-reactive avatar overlay."
version: "1.0.0"
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [yapatar, avatar, overlay, prores, alpha, ffmpeg, node, premiere, resolve]
    category: creative
---

# Yapatar — avatar reactif a la voix (overlay alpha)

## When to Use

- Produire un overlay d'avatar transparent a incruster dans un montage (short Cyberpunk, encart de chaine).
- Relancer un rendu Yapatar apres un changement d'audio, d'avatar, de style ou de palette.
- L'avatar Yapatar ne sort pas, sort en 403, ou le rendu echoue en 0,1 s sans message.

Transforme `audio + image` en une video a fond transparent ou l'avatar pulse avec la voix.
A poser sur une piste au-dessus du montage dans Premiere / Resolve / FCP. Pas de keying.

- Depot : `https://github.com/modem-dev/yapatar` — licence **MIT** (compatible monetisation).
- Clone de travail sur ce parc : `C:/Users/searc/Desktop/yapatar`.
- Sortie : `out/avatar_alpha.mov` (ProRes 4444 + alpha + audio PCM). **Le fichier a importer.**
  `out/preview_opaque.mp4` est un controle visuel aplati sur fond opaque — ne jamais l'importer.

## Boucle de travail

```bash
cd C:/Users/searc/Desktop/yapatar
npm install
node.exe src/make-avatar.js                 # placeholder -> assets/avatar.png (512x512)
node.exe src/render.js --audio extrait.wav --avatar avatar.png --codec prores
node.exe src/serve.js                       # apercu : http://localhost:8777/preview.html
npm test                                    # 33 tests (unit + e2e)
```

## Regle 1 — sur cet hote, ecrire `node.exe`, jamais `node`

`node` est un **alias bash** vers `winpty node.exe` (`type -a node` le montre). `winpty` exige un
TTY : des que stdin n'est pas un TTY — lancement en tache de fond, sortie d'un harnais — l'appel
meurt en **0,1 s avec `stdin is not a tty` et rc=1**, *avant* d'executer le script. Aucune erreur
metier n'apparait, ce qui fait accuser ffmpeg ou les chemins a tort.

- Appeler `node.exe` (ou le chemin complet) : l'alias n'est pas resolu, node demarre normalement.
- Meme piege pour d'autres outils : `curl -o /dev/null` sort en **exit 23 avec 0 octet** — ecrire
  dans un vrai fichier et lire sa taille est la seule mesure fiable.
- Un rendu de 45 s fait **20 s** (2,25x le temps reel) : pas besoin de fond pour un short ; au-dela
  de quelques minutes, oui.

## Regle 2 — `src/serve.js` : page d'apercu 403 sur Windows (bug du depot)

`serve.js` confine les fichiers statiques par
`if (!path.startsWith(ROOT + '/') && path !== ROOT) return 403`. Sous Windows `path.sep` vaut `\`,
donc `join()` fabrique `C:\...\yapatar\preview.html` que l'on compare a `C:\...\yapatar/` :
`startsWith` est **faux** et **toute** requete statique repond `{"error":"forbidden"}` en 403.
Le serveur ecoute bien, `/settings` repond — seul le statique casse. Invisible sur macOS/Linux.

Correctif local (2 lignes, non committe) :

```js
import { extname, join, normalize, basename, sep } from 'node:path';
// ...
if (!path.startsWith(ROOT + sep) && path !== ROOT) return json(res, 403, { error: 'forbidden' });
```

Revert : `git checkout -- src/serve.js`. Verifier apres correction : `preview.html` doit rendre
**22943 octets** en `text/html` (titre « Yapatar — live preview »).

## Regle 3 — codec

`--codec hevc` s'appuie sur `hevc_videotoolbox`, **macOS uniquement**. Sur Windows :
`--codec prores` (ProRes 4444, ~7,5 Mo/s de video, universellement lu) ou `--codec png`.
La liste des codecs reellement disponibles est donnee par `node.exe -e "import('./src/preflight.js').then(m=>console.log(m.checkCodec('prores')))"`.

## Mesures de reference (512x512, 30 fps, prores, pulse, 45 s d'audio)

| grandeur | valeur |
|---|---|
| `out/avatar_alpha.mov` | 342 868 294 o (327 Mo), 45,056 s, 1351 frames |
| video | prores, 512x512, `yuva444p12le` (alpha 12 bits) |
| audio | `pcm_s16le` 48 kHz mono, **bit-identique au wav source** (md5 PCM identique) |
| alpha | coins a 0, centre a 255 ; 73-81 % de l'image entierement transparente |
| duree du rendu | 20 s (2,25x le temps reel) |
| `preview_opaque.mp4` | 7 004 251 o, h264/aac, 45,033 s |

Le rendu est **deterministe** : deux passes successives donnent le meme md5 (video *et* preview).
Utile pour verifier une modification de style sans re-encoder deux fois.

## Integration Premiere / Resolve

1. Importer **`out/avatar_alpha.mov`** (jamais le `preview_opaque.mp4`).
2. Le poser sur une piste video **au-dessus** de la capture ; echelle ~15-20 % de la hauteur, coin
   bas droite. Alpha honore automatiquement, aucun mode de fusion a regler.
3. **Couper l'audio de la piste avatar** : l'overlay transporte la voix source (PCM identique)
   volontairement, pour caler a l'onde ou laisser Resolve synchroniser — sinon on l'entend deux fois.
   Alternative a la generation : `--no-audio`.
4. Autres leviers : `--size` (rendre a la taille d'affichage reelle plutot que 512 et re-echelonner),
   `--fps` (caler sur la timeline), `--alpha premultiplied` (defaut, ce que compositent les NLE),
   `--style pulse|constellation|waterfall|packets|handshake`, `--preset modem`.

Halo blanc autour de l'avatar = melange d'alpha : re-rendre avec `--alpha straight`, ou passer
`Clip Attributes -> Alpha Mode -> Straight` dans Resolve. Un liseré dur carre = le NLE ignore
l'alpha, pas un defaut du fichier.

## Pieges

- Regenerer le placeholder ecrase `assets/avatar.png` **suivi par git** : le restaurer ensuite
  (`git checkout -- assets/avatar.png`) et garder l'avatar de travail a la racine du depot.
- `git clone <url> .` echoue dans un dossier non vide : cloner dans un dossier temporaire puis
  deplacer le contenu (y compris `.git`).
- Le dossier de sortie est cree **avant** le decodage : un rendu qui echoue laisse un `out*/` vide a
  supprimer.
