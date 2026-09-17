# Architecture du second cerveau

> **Statut** : actif
> **Dernière mise à jour** : 16/09/2026

Ce document décrit **ce qui constitue le second cerveau**, pour savoir quoi maintenir, quoi
surveiller et ce qu'on peut laisser tranquille.

## Section 1 — Composants actifs

| Composant | Rôle | Port | Tâche planifiée |
|---|---|---|---|
| **SiYuan kernel** | Base de connaissances structurée : 6 notebooks, 33 documents (projets, skills, vidéo, journal, veille, apprentissage) | **6806** | `SiYuan - noyau second cerveau` (ouverture de session, via le `.vbs` silencieux) |
| **Index RAG** | Recherche vectorielle (FAISS, e5-base) + lexicale (BM25), fusion RRF | — | `Hermes - Reindex RAG` (chaque nuit à 03h00, 2 194 fragments) |
| **API RAG** | Recherche HTTP pour les autres programmes (`/sante`, `/search`, `/v1/embeddings`, `/recharger`) | **8200** | aucune — lancement manuel (`serveur_rag.py`) |
| **Gateway Hermes** | Backend agent pour que le second cerveau reste interrogeable sans console | à préciser | **en attente** — l'installation a été bloquée par le garde-fou de sécurité le 16/09, décision à prendre |

Chaîne de dépendance : **SiYuan (6806) → index RAG → API RAG (8200) → Hermes**. Si le noyau SiYuan
est arrêté, la réindexation ne se lance pas (elle le détecte et le journalise) et la source `siyuan`
de l'index se viderait au prochain passage forcé.

## Section 2 — Outils clés

| Outil | Chemin exact | Ce qu'il fait | Quand | Dépendances critiques |
|---|---|---|---|---|
| `chercher.py` | `%LOCALAPPDATA%\hermes\data\rag\` | interroge l'index (vectoriel + lexical + RRF, expansion de requête) | à la demande | venv RAG, `index.faiss` + `chunks.jsonl` |
| `indexer.py` | `%LOCALAPPDATA%\hermes\data\rag\` | reconstruit l'index depuis SiYuan, les skills, les scripts v4 et WordPress | à la demande / planifié | **noyau SiYuan en écoute** (sinon la source `siyuan` revient vide) |
| `serveur_rag.py` | `%LOCALAPPDATA%\hermes\data\rag\` | expose le RAG en HTTP (FastAPI) | à la demande | venv RAG, port 8200 libre |
| `reindex_auto.py` | `%LOCALAPPDATA%\hermes\data\rag\` | enveloppe planifiée de `indexer.py` : vérifie SiYuan, verrou, journal | planifié 03h00 | noyau SiYuan, venv RAG |
| `publier.py` | `C:\Users\searc\SiYuan\` | crée ou remplace un document SiYuan depuis un fichier Markdown | à la demande | noyau SiYuan, `SIYUAN_TOKEN` |
| `construire_structure.py` | `C:\Users\searc\SiYuan\` | construit les 6 notebooks et leurs documents (extrait les skills, lit les sites Local) | ponctuel (reconstruction) | noyau SiYuan |
| `import_notes.py` | `C:\Users\searc\SiYuan\` | importe des notes Markdown externes | ponctuel | noyau SiYuan |
| `ajouter_piege.py` | `C:\Users\searc\SiYuan\` | ajoute une puce à la section « Pièges » d'un document existant | à la demande | noyau SiYuan |
| `replacer_puce.py` | `C:\Users\searc\SiYuan\` | déplace une puce mal placée dans un document | à la demande | noyau SiYuan |
| `supprimer_document_siyuan.py` | `C:\Users\searc\SiYuan\` | **nouveau** — supprime un document en enlevant les enfants d'abord, pour éviter le PANIC du noyau | à la demande | noyau SiYuan ; `--simuler` pour voir le plan |

Tous ces outils lisent `SIYUAN_TOKEN` et `SIYUAN_URL` dans `%LOCALAPPDATA%\hermes\.env`. Aucun ne
modifie `config.yaml`.

## Section 3 — Skills qui servent le second cerveau

| Skill | Version | Rôle | Dépendances | Dernier usage connu |
|---|---|---|---|---|
| `productivity/siyuan` | 1.0.0 | skill officiel : API SiYuan (notebooks, documents, SQL) | noyau SiYuan, jeton | 15/09 — interrogation de l'API |
| `productivity/siyuan-second-brain` | 1.0.0 | installer et câbler SiYuan : secrets, noyau, tâche planifiée, pièges | noyau, `.env`, tâche planifiée | 16/09 — ajout des pièges « barre oblique » et « PANIC » |
| `productivity/rag-second-cerveau` | 1.0.0 | interroger l'index ; API HTTP ; pièges e5 et réindexation | venv RAG, index, noyau | 16/09 — test des 4 requêtes |
| `productivity/recherche-skills-officiels` | 1.0.0 | chercher dans le Hub officiel avant de dire « je ne sais pas » | CLI `hermes skills`, réseau | 15/09 — création et indexation |
| `productivity/auto-revision-skills` | 1.0.0 | réviser périodiquement la bibliothèque de skills (doublons, références mortes, manques) | script `inventaire_skills.py` | 15/09 — 1ʳᵉ révision (96 skills) |

Les cinq sont indexés dans le RAG (source `skill`). Toute modification d'un skill n'entre dans
l'index qu'à la réindexation suivante (03h00, ou à la demande).

## Section 4 — Ce qui ne sert PAS au second cerveau

Ces ensembles vivent dans Hermes mais n'ont aucun lien avec la base de connaissances : on peut les
laisser tranquilles, ils ne participent ni à l'index (sauf mention contraire) ni aux tâches
planifiées.

| Ensemble | Contenu | Remarque |
|---|---|---|
| `media/`, `ai-video-pipeline`, `premiere-montage-comparatif` | vidéo talking-head, LTX-2.3, assemblage, montage | leurs **skills** sont indexés (c'est voulu : ils documentent des procédures), mais leurs modèles et venvs ne le sont pas |
| `mlops/` | XTTS, VibeVoice, clonage de voix, LLM locaux, SAM | l'essai XTTS est refermé ; le LoRA SDXL attend des images |
| `creative/` | ComfyUI, Manim, p5.js, diagrammes, ASCII, design | indépendant |
| `photo/`, `record/` | capture unique / enregistrement borné | indépendant |
| `wordpress/` (5 skills + `wordpress-suite`) | sites Local, déploiement, sauvegardes WP-CLI | la source `wordpress` de l'index vient du **dépôt local**, pas de ces skills |
| `social-media/`, `email/`, `maps/`, `notion/`, `airtable/`, `box/` | intégrations diverses | indépendant |
| `devops/` (sauf `siyuan-second-brain`) | SSL, sécurité, OmniRoute, Windows | indépendant ; seul `reindex_auto.py` touche au RAG |

**Ce qui compte pour la maintenance du second cerveau** : le noyau SiYuan, le venv du RAG, les trois
tâches planifiées (`SiYuan - noyau second cerveau`, `Hermes - Reindex RAG`, et le futur backend
Hermes), et les cinq skills ci-dessus. Le reste peut attendre.

---

*Établi le 16/09/2026 après les chantiers de nettoyage et d'inventaire. Chiffres : index à
2 194 fragments, SiYuan 3.8.2 sur 6806, 96 skills installés.*
