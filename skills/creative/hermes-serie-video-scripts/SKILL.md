---
name: hermes-serie-video-scripts
description: "Use when writing Hermes series video scripts."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [video, script, youtube, hermes, serie]
    category: creative
---

# Scripts de la serie Hermes

## When to Use

Quand il faut ecrire ou reecrire un script video pour la serie YouTube Hermes (un « volet » par video). Complete `video-pipeline-complet` (voix, synchro, assemblage) : ce skill couvre la redaction du script.

## Entrees a reunir avant d'ecrire

- Documents techniques de l'episode (ex. `ANIMA_ARCHITECTURE.md`, `ANIMA_MODULES.md`) — source de verite pour les chiffres, ports, noms de modules.
- Script precedent obsolete, s'il existe, pour identifier ce qui change.
- Chemin de sortie : un `.md` dans le dossier de la video (ex. `C:\Users\searc\Desktop\ANIMA\ANIMA_protoagent_script.md`).

## Structure type d'un volet (7 blocs)

1. INTRO + RECAP (35 s) — accroche, rappel des volets precedents, annonce du sujet et des 3 armes.
2. LE PROBLEME (45 s) — le probleme que la video resout.
3. PILIER 1 (1 min 30) — explication technique detaillee.
4. PILIER 2 (1 min) — deuxieme pilier.
5. PILIER 3 (45 s) — troisieme pilier.
6. RECAP (45 s) — synthese en principes numerotes.
7. CTA FINAL (35 s) — lien GitHub, like/partage/abonnement.

Total vise : 5–6 min de voix parlee, soit 750–900 mots.

## Contraintes de ton

- Direct, tutoiement, technique mais accessible.
- Phrases courtes, rythme pose.

## Message central et repetition

- Identifier le message central de l'episode (ex. « ANIMA est un PROTOAGENT OPENSOURCE, pas une demo »).
- Le repeter au moins 3 fois : recap d'intro, un bloc technique, CTA final.
- Pour le volet 7, « OPENSOURCE » et « PROTOAGENT » devaient apparaitre au moins 3 fois chacun.

## Verification du budget de mots parles

Compter uniquement le texte parle (exclure titres, metadonnees, separateurs) :

    f="chemin/vers/script.md"
    grep -v '^#' "$f" | grep -v '^---' | grep -v '^$' | wc -w

Cible : 750–900 mots. Si depassement, retirer les redondances.

## Pitfalls

- Ne pas reecrire sans avoir lu les documents techniques de l'episode : les details cites a la voix doivent rester exacts.
- Verifier le compte de mots parles apres reecriture, pas seulement la presence des blocs.
- Le CTA doit citer le lien GitHub de la serie (`github.com/Antoine-Thomas/hermes-home-vision`) et rappeler le `git clone`.
- Le fichier script est souvent edite en entier : si `write_file` refuse l'ecrasement d'un fichier lu en mode pagine, voir `windows-path-handling` (Regle 13) — `patch` pour les modifications ciblees, `rm` puis `write_file` pour une reecriture integrale.

## Voir aussi

- `video-pipeline-complet` — orchestration voix, synchro, assemblage (skill utilisateur ; ne pas modifier sans son accord).
- `talking-head-video-8gb` — generation talking-head.
