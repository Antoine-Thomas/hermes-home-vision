# Sources officielles Hermes — skills

> **Statut** : actif
> **Dernière mise à jour** : 15/09/2026

## Fait

Trois sources officielles, à consulter **avant de dire « je ne sais pas »** :

| Source | URL | Contenu |
|---|---|---|
| **Skills Hub** | https://hermes-agent.nousresearch.com/docs/skills | Catalogue en ligne. Agrège « 88k+ skills across every registry ». Le catalogue se charge en JavaScript (la page seule ne contient pas la liste) : il faut passer par le CLI. |
| **Créer un skill** | https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills | Skill ou outil ? Structure `skills/<catégorie>/<nom>/SKILL.md` (+ `scripts/`, `references/`), frontmatter obligatoire, sections, `platforms`, blueprints. |
| **Utiliser les skills** | https://hermes-agent.nousresearch.com/docs/guides/work-with-skills | Lister, chercher, installer, utiliser un skill. C'est le guide des commandes du quotidien. |

### Le catalogue en ligne, tel qu'il se présente réellement

`hermes skills search <mots-clés>` interroge le Hub et rend un tableau
Nom / Description / Source / Confiance / Identifiant. Les sources disponibles
(`--source`) sont : `all`, `official`, `skills-sh`, `well-known`, `github`, `clawhub`,
`lobehub`, `browse-sh`, `nvidia`, `openai`, `anthropic`, `huggingface`, `voltagent`,
`gstack`, `minimax`.

Exemple réel (`hermes skills search video`) : 25 résultats, dont
`official/creative/ai-presenter-video` et `official/creative/comfyui`.

### Créer un skill : ce que dit le guide

- **Skill plutôt qu'outil** quand la capacité s'exprime en instructions + commandes shell + outils
  existants (arXiv, git, Docker, PDF, e-mail par CLI). **Outil** quand il faut une intégration
  complète (clés d'API, authentification, logique qui doit s'exécuter à l'identique à chaque fois).
- Structure : `skills/<catégorie>/<nom-du-skill>/SKILL.md` (obligatoire) + `scripts/` (optionnel).
- Frontmatter : `name`, `description`, `version`, `author`, `license`, et `platforms` en option
  (`[macos]`, `[linux]`, `[windows]` — un skill qui ne vise pas la plateforme est masqué de la
  liste et des commandes).
- Sections du corps : `When to Use`, `Quick Reference`, `Procedure`, `Pitfalls`, `Verification`.
- **Blueprint** : un skill ordinaire qui déclare en plus une planification dans son frontmatter
  (`metadata.hermes.blueprint.schedule`, `deliver`, `prompt`) devient une automatisation
  partageable. C'est le pont entre les skills et les tâches planifiées.

## Reste à faire

- Aucune vérification du Hub n'est possible sans le CLI : si `hermes skills search` ne répond pas,
  c'est le réseau ou le backend du Hub, pas la commande.
- Les sources tierces (`clawhub`, `lobehub`, `openai`…) n'ont pas été évaluées : la confiance
  affichée n'est pas un audit. Lire l'identifiant et la description avant d'installer.

## Pièges

- **Le Hub n'est pas dans le RAG** : ce document décrit le mécanisme, pas le catalogue. Le
  catalogue change, il se consulte en ligne à chaque fois.
- `hermes skills install` refuse une installation si le scan de sûreté rend un verdict bloquant
  (`--force` passe outre : à ne pas utiliser sans avoir lu le skill).
- Un skill installé arrive dans `%LOCALAPPDATA%\hermes\skills\<catégorie>\<nom>\` et **n'est pas
  dans le RAG** tant que l'indexation n'a pas été relancée (`indexer.py`).
- Le CLI signale parfois : « A previous `hermes update` pulled new code but did not restart running
  gateways ». C'est un avertissement d'état, pas une erreur de commande — il concerne le gateway,
  pas les skills.

## Commandes

```
# chercher dans le Hub (tableau : nom, description, source, confiance, identifiant)
hermes skills search <mots-clés>
hermes skills search <mots-clés> --source official --limit 20
hermes skills search <mots-clés> --json          # identifiants complets, pour un script

# explorer et inspecter
hermes skills browse
hermes skills inspect <identifiant>              # previsualiser sans installer
hermes skills list                               # skills installes

# installer
hermes skills install official/<categorie>/<nom>
hermes skills install <source>/<nom>
hermes skills install https://exemple.com/SKILL.md --name mon-skill
hermes skills install official/<categorie>/<nom> --yes      # sans confirmation (TUI)

# entretenir
hermes skills check                              # mises a jour disponibles
hermes skills update <identifiant>
hermes skills publish                            # publier un skill (tap)

# dans une session de chat
/skills            /skills search <mots-clés>     /skills browse
/skills install official/creative/songwriting-and-ai-music
```

Après toute installation ou création : relancer l'indexation du RAG
(`%LOCALAPPDATA%\hermes\data\rag\venv\Scripts\python.exe indexer.py`).
