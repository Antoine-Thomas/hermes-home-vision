# Wiki Schema

> Conventions structurantes. Le skill `llm-wiki` lit ce fichier AVANT toute
> opération (ingestion, requête, lint). Toute règle ici est contraignante.
> Dernière révision : 2026-09-22.

## Domain

Infrastructure et stack IA **locale** de Thomas Leroyer (Searching Murphy, Caen) :
Hermes Agent (v0.21.4, profil `default`), OmniRoute (routeur de modèles, port
20128), SiYuan (second cerveau, port 6806), RAG maison sur `data/`, Jev /
TypeSafe (primitives de décision), GPU locale RTX 3070 Ti 8 Go, pipelines
vidéo/TTS locaux, bibliothèque de skills, crons de maintenance, WordPress.

Le wiki compile ce qui est **déjà synthétisé**. Il ne remplace pas la recherche
brute : voir la section « Architecture L1 / L2 » ci-dessous.

## Architecture L1 / L2 (rôle de ce wiki)

| Niveau | Support | Usage |
| --- | --- | --- |
| **L1** | ce wiki | Connaissances compilées, stables, cross-référencées. Répondre sans re-fouiller. |
| **L2** | RAG sur `data/` (e5-base, cache TTL 24 h, serveur 8200) | Recherche brute, détail précis, source primaire. |
| Routeur | `scripts/jev_router.py` (Jev, primitive `choice`) | Décide `wiki` \| `rag` \| `both` pour chaque question. |

Règle de coût : le routage Jev est payant (~1,3 × 10⁻⁵ $/question) mais 50× moins
cher qu'une réponse LLM complète. On route **avant** de générer.

## Conventions

- Noms de fichiers : minuscules, tirets, sans espaces (`jev-routeur-l1-l2.md`).
- Chaque page wiki commence par un **frontmatter YAML** (voir plus bas).
- `[[wikilinks]]` entre pages, **minimum 2 liens sortants** par page.
- À chaque modification d'une page, **incrémenter `updated`**.
- Toute nouvelle page est ajoutée à `index.md` dans la bonne section, par ordre alphabétique.
- Toute action est ajoutée à `log.md` (append-only, format `## [YYYY-MM-DD] action | sujet`).
- **Provenance** : sur une page qui synthétise 3+ sources, suffixer `^[raw/notes/source.md]`
  aux paragraphes dont les faits viennent d'une source précise. Optionnel sur les pages mono-source.
- Une page se lit en 30 secondes. Au-delà de ~200 lignes : découper.

## Extensions locales (hors canonique du skill)

Ces ajouts sont propres à cette installation. Ils complètent le canonique, ils
ne le remplacent jamais.

| Élément | Rôle | Règle |
| --- | --- | --- |
| `raw/notes/` | Notes exportées depuis SiYuan (sources brutes) | **Immuable.** Une note SiYuan exportée n'est jamais réécrite ; une mise à jour SiYuan crée une nouvelle capture. |
| `syntheses/` | Synthèses transverses (plusieurs domaines, état de l'art, bilans datés) | Même frontmatter que `concepts/` ; `type: summary`. Différence avec `concepts/` : une synthèse répond à « où on en est ? », un concept répond à « qu'est-ce que c'est ? ». |
| `contradictions.md` | Registre lisible des contradictions détectées | **Complément**, pas remplacement : le frontmatter `contested: true` + `contradictions: [slug]` reste la source de vérité machine. Le fichier est mis à jour par le cron « contradictions » et par tout lint. |
| `scripts/` | Outils du wiki (`jev_router.py`) | Code, pas du contenu : jamais listé dans `index.md`. |
| `_archive/` | Pages archivées | Le déplacement suit la section « Archiving » du skill : `_archive/<chemin d'origine>`, retrait de `index.md`, remplacement des liens entrants par du texte + « (archived) ». |

## Frontmatter (pages wiki)

```yaml
---
title: Titre de la page
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [tags de la taxonomie ci-dessous]
sources: [raw/notes/source.md]
confidence: high | medium | low   # optionnel, recommandé
contested: true                   # si contradiction non résolue
contradictions: [slug-autre-page] # pages en conflit
---
```

`confidence: high` n'est posé que si le fait est corroboré par plusieurs sources.

## Frontmatter des sources (`raw/`)

```yaml
---
source_url: https://example.com/article   # si applicable
ingested: YYYY-MM-DD
sha256: <empreinte du corps seul, hors frontmatter>
---
```

`sha256` sert à détecter la dérive : à la ré-ingestion, si l'empreinte du corps est
identique on saute le traitement, si elle diffère on signale la dérive.

## Taxonomie des tags

**Règle : tout tag utilisé doit figurer ici. Un nouveau tag s'ajoute ICI d'abord.**

- Infrastructure : `hermes`, `omniroute`, `siyuan`, `rag`, `wiki`, `cron`, `skill`, `mcp`
- IA et modèles : `provider`, `model`, `jev`, `llm`, `tts`, `embedding`, `prompt`
- Matériel et OS : `gpu`, `vram`, `windows`, `docker`, `wsl`
- Contenu et marque : `jeu`, `video`, `lora`, `wordpress`, `veille`, `searching-murphy`
- Méta : `comparison`, `timeline`, `decision`, `incident`, `contradiction`, `cout`

## Seuils de création de page

- **Créer une page** : l'entité/le concept apparaît dans **2+ sources**, OU est
  **central à une seule source**.
- **Compléter une page existante** : la source parle d'un sujet déjà couvert.
- **Ne pas créer** : mention de passage, détail mineur, hors domaine.
- **Découper** : au-delà de ~200 lignes.
- **Archiver** : contenu entièrement remplacé → `_archive/`, retrait de `index.md`.

> Décision locale (2026-09-22) : seuil canonique du skill retenu (2+ sources OU
> 1 source centrale). Un seuil à 3 sources produirait un wiki vide sur les
> premières ingestions.

## Pages entités

Une page par entité notable (personne, organisation, produit, modèle, machine).
Overview / faits datés / relations (`[[wikilinks]]`) / références de source.

## Pages concepts

Une page par concept ou sujet. Définition / état des connaissances / questions
ouvertes / concepts liés.

## Pages comparaison

Analyses côte à côte. Objet et raison de la comparaison / dimensions (tableau
préféré) / verdict / sources.

## Politique de mise à jour

Quand une information nouvelle contredit le contenu existant :

1. Comparer les dates — une source plus récente supplante généralement l'ancienne.
2. Si la contradiction est réelle : noter **les deux** positions avec dates et sources.
3. Marquer le frontmatter : `contested: true`, `contradictions: [page]`.
4. Ajouter une ligne dans `contradictions.md` (registre local).
5. Signaler dans le rapport de lint, pour arbitrage humain.

Interdit : écraser silencieusement une information contradictoire.

## Archivage (90 jours)

Une page dont `updated` dépasse **90 jours** sans qu'aucune source récente ne
mentionne les mêmes entités est candidate à l'archivage. Le cron « archive »
les déplace dans `_archive/`, les retire de `index.md` et journalise l'action.
L'archivage n'est jamais automatique sans trace dans `log.md`.

## Maintenance planifiée (crons)

| Job | Cadence | Rôle |
| --- | --- | --- |
| LLM Wiki compile | `0 */6 * * *` | Ingérer les nouvelles sources de `raw/`, créer/mettre à jour les pages. |
| LLM Wiki contradictions | `0 3 * * *` | Comparer les pages, remplir `contradictions.md`, poser `contested:`. |
| LLM Wiki archive | `0 4 * * 0` | Archiver les pages à plus de 90 jours sans activité. |

Compilation en **eco / nvidia-stack (gratuit, OmniRoute)**, jamais sur le
modèle payant primaire.
