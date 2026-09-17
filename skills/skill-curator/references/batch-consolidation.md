# Consolidation par lots — fan-out et corrections de refs

## Fan-out parallele sans conflit de chemins

Pour consolider N categories en parallele, deleguer N sous-agents sur des categories disjointes
(devops, productivity, media, mlops+research) et traiter le RESTE synchrone sur des chemins
disjoints (email, github, autonomous, singletons). Ne jamais chevaucher les chemins cibles
entre delegues et tache synchrone — tout chevauchement produit des moves/archives en conflit.

Delegation utilisee: `delegate_task` avec 4 taches, 150-230s chacune; comptage global
`find skills -name SKILL.md ! -path */_archive/* | wc -l` attendu 60-85 apres fusion.

## bare-filename refs -> broken links

Deux splits ont produit des refs sans prefixe `references/`:
- `comfyui`: SKILL.md listait `official-cli.md` au lieu de `references/official-cli.md`
- `diagram-suite`: routing listait `dark-mode.md`/`examples.md` au lieu de `references/excalidraw/*.md`

Pitfall: tout split H2 -> `references/<slug>.md` doit reecrire les pointeurs du SKILL.md
routeur avec le prefixe `references/` complet — un bare `xxx.md` pointe hors du skill et
apparait comme broken. Verifier apres split par re-parse `references/`/`scripts/`/`templates/`.

## Stubs pour refs manquantes sur skills protegees

Quand une SKILL.md protegee (mtime >= seuil 7j) reference `references/xxx.md` manquant,
ne pas modifier la SKILL.md — creer uniquement le fichier manquant en stub verbatim/
placeholder dans `references/`. Ex: `talking-head-video/references/minimax-provider.md`,
`tts-voice-cloning/references/french-diction-tricks.md`.

## Umbrella verbatim — header et supports

Chaque ref archivee porte `<!-- Source: <orig>/SKILL.md (archived YYYY-MM-DD) -->`
en premiere ligne, contenu byte-verbatim (verifie par diff). Copier aussi les supports
du skill source: `references/*.md`, `scripts/*`, `templates/*` vers l'umbrella — sinon
le router pointe vers des fichiers absents.

## Categories videes

Apres archivage, une categorie peut n'avoir plus que `DESCRIPTION.md` (ex: apple,
note-taking, smart-home) ou etre vide (snapshot). Conserver le repertoire et son
DESCRIPTION.md — ne pas supprimer la categorie, elle reste valide pour un futur skill.
