---
name: smll-talk-podcast
description: "Use when writing or producing 'smll talk' podcast episodes."
---

# smll talk — podcast de fiction (story bible + production)

Podcast de fiction français de l'utilisateur, « smll talk », narré par sa voix clonée (MaVoix). Univers cyberpunk-fantasy. Cette skill porte le story bible, le style d'écriture et le workflow de production pour écrire/narrer un nouvel épisode (4, 5, …) sans reconstruire l'univers à chaque session. Pour la mécanique du moteur TTS, voir la skill `vibevoice-tts` (conteneur, VRAM, commandes exactes).

## Story bible (univers)

- **La Rouille** : maladie terrible qui dévore les implants cybernétiques, s'étend plus vite que jamais.
- **L'Anima** : ni une arme ni un remède — « l'âme du monde mécanique », conscience diffuse qui maintient en vie les âmes égarées des cyborgs. Révélation ép.3 : l'Anima EST le monde lui-même, endormi dans le cœur des vivants ; elle n'a jamais été « ailleurs ».
- **Kael** : jeune guerrière « au regard de feu », implants cybernétiques, contaminée par la Rouille. Protagoniste.
- **Le Guérisseur** : vieillard sage, gardien de l'Anima, assis au pied de l'Arbre-Monde. (Cliffhanger ép.3 : qui est-il vraiment ?)
- **L'Arbre-Monde** : arbre légendaire.
- **Le dodécaèdre de cristal noir** : artefact censé capturer l'Anima ; révélé (ép.3) comme un MIROIR qui reflète le chercheur, pas un piège.
- **Le sacrifice** : pour recevoir l'Anima, oublier son souvenir le plus cher.
- **Lieux** : la Cité de la Nuit (d'où viennent les habitants désespérés), la Cité-Forêt (cité tentaculaire de métal, titre de l'ép.2), l'Arbre-Monde, la clairière interdite, la forêt mécanique.
- **Factions** : les pillards (chef « colosse aux dents limées » + un second), les soldats d'Omnia (bien pires que les pillards — la vraie menace).

## Épisodes (état actuel)

- **Ép.1** — pas de texte complet sur disque, seulement le récap : la Cité de la Nuit meurt de la Rouille, Kael envoyée chercher l'Anima.
- **Ép.2 « La Cité-Forêt »** — texte : `C:\Users\searc\AppData\Local\hermes\data\vibevoice\episode2.txt`. Kael rencontre le Guérisseur, apprend la nature de l'Anima + le sacrifice ; les pillards attaquent ; elle vole le dodécaèdre et fuit ; « l'Anima n'était pas dans le dodécaèdre, elle était ailleurs depuis le début ». Cliffhanger : « Kael va-t-elle suivre le Guérisseur et trouver l'Anima ? »
- **Ép.3 « Le Prix de l'Âme »** — texte : `episode3.txt` (même dossier) + copie Bureau `the cypher\episode3_texte.txt`. Kael découvre que le dodécaèdre est un miroir ; les soldats d'Omnia attaquent ; elle sacrifie son souvenir le plus cher ; l'Anima était en elle. Cliffhanger : « qui est vraiment le Guérisseur ? »

## Style d'écriture (à respecter)

- Français, registre conte littéraire : passé simple + imparfait, pas d'argot.
- Dialogues en guillemets « », chaque réplique dans son propre paragraphe.
- Alternance narration / dialogues.
- Titre : « Épisode N — Sous-titre ».
- Une suite s'ouvre directement dans l'action (NE PAS réutiliser « Il était une fois » — c'est l'ouverture de l'ép.2 uniquement).
- Toujours finir sur un cliffhanger + « Vous le saurez au prochain épisode. »
- Garder les apostrophes intactes (l'Anima, n'était, s'élevaient…) — le TTS en a besoin.
- Longueur : ~800-1000 mots ≈ 4 min d'audio ≈ 4000-5000 caractères.

## Workflow de production (voix unique MaVoix)

1. Écrire le texte dans `<data>/episodeN.txt` : `Speaker 1: Épisode N — Titre` puis lignes vides + paragraphes (une seule prise = lecture fluide).
2. Vérifier la VRAM libre ≥ ~5,3 Go (`docker exec vibevoice-dev nvidia-smi --query-gpu=memory.free` — le host consomme aussi la carte et ça fluctue).
3. Synthèse en arrière-plan : `docker exec vibevoice-dev bash -c 'cd /workspace/repo && python demo/inference_from_file.py --model_path vibevoice/VibeVoice-1.5B --txt_path /workspace/episodeN.txt --speaker_names MaVoix_v2 --output_dir /workspace/outputs_episodeN'` (≈6-11 min ; `terminal(background=true, notify_on_complete=true)`).
4. Copier le WAV généré → `C:\Users\searc\Desktop\the cypher\episodeN_ma_voix.wav` ; copier aussi le texte → `episodeN_texte.txt`.
5. Vérifier avec ffprobe (durée + taille), puis rapporter chemin + durée + taille.

## Production multi-voix (existe pour l'ép.2)

`the cypher\episode2_voix_final\` contient un rendu multi-personnages : `NARR_*.wav` (Narrateur), `DIAL_*.wav` (Kael, Guerisseur, Chef_pillard, Second_pillard), `ACT_*.wav`, `OUTRO_*.wav`. Si l'utilisateur veut des voix de personnages distinctes (pas seulement MaVoix), c'est la structure de référence.

## Règles

- Ne JAMAIS écraser un WAV existant (exigence de l'utilisateur — il a déjà perdu un artefact validé). Utiliser `_v2`, `_v3` ou un nom episodeN neuf ; vérifier que la cible n'existe pas d'abord.
- Les fichiers de voix sont dans `C:\Users\searc\Desktop\the cypher\clone\mavoix1-6.wav` (PAS `...\smll talk\clone\` — ce chemin n'existe pas).
