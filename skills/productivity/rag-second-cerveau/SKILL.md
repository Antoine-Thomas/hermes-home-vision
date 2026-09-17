---
name: rag-second-cerveau
description: Use when a past procedure or measure must be found.
version: 1.0.0
---

# RAG local (second cerveau)

Recherche vectorielle locale sur quatre sources, sans API ni GPU :

| source | contenu | fragments |
|---|---|---|
| `siyuan` | les documents du second cerveau (6 notebooks) | 182 |
| `skill` | tous les `SKILL.md` du dossier de skills | 1146 |
| `script_v4` | `Desktop\hermes_tuto_v4` (scripts, transcripts, journaux) | 643 |
| `wordpress` | le depot `hermes-wordpress-skills` | 89 |

Total : **2060 fragments**, 768 dimensions, index de 6 Mo. Modele
`intfloat/multilingual-e5-base` (multilingue FR/EN, CPU). Fragments de 900 caracteres : les
fragments longs (1600) noyaient la reponse precise dans du contexte (constate sur la question du
flou des levres).

Recherche **hybride** : vectoriel (FAISS) + lexical (BM25 maison), fusionnes par rang reciproque
(RRF), plus une expansion de requete par familles de synonymes du metier (flou/mou/nettete,
levres/bouche, token/api.token...). Le vectoriel seul ratait le jargon et les termes rares.

## Quand l'utiliser

**Avant de consulter le RAG, exécuter le routeur hiérarchique :**
```
python router_memoire.py "question de l'utilisateur"
```
Le routeur renvoie les niveaux à consulter selon la hiérarchie stricte :
1. MEMORY.md + USER.md (toujours)
2. SiYuan direct (projets, décisions, documentation structurée)
3. RAG filtré (technique : pièges, seuils, mesures)
4. Skills Hub externe (domaine non couvert)

**Le RAG (niveau 3) n'est consulté que si les niveaux 1-2 sont insuffisants.**

**Budget tokens par niveau (ne pas tout déclencher) :**
- Niveau 1 : 0 (déjà chargé)
- Niveau 2 : 500 tokens SiYuan
- Niveau 3 : 1500 tokens (5 × 300)
- Niveau 4 : 3000 tokens Skills Hub
- Ne monter au niveau supérieur QUE SI le niveau inférieur n'a rien donné.

**Fraîcheur :** chaque doc SiYuan porte une date « À revérifier ». Si dépassée,
relire avant de s'en servir. Le routeur signale avec `--fraicheur`.

**Contradictions :** si niveaux 1 et 2 donnent des valeurs différentes pour le
même sujet, ne pas choisir — signaler à l'utilisateur et demander lequel est correct.

Cas d'utilisation concrets :
- Avant de repondre "je ne sais pas" ou de refaire une recherche de zero
- Pour retrouver un piege deja paye, une mesure (temps, VRAM, MAD) ou un parametre de pipeline
- Pour eviter de remettre du contexte long dans le prompt : on cherche, on lit 3 fragments, on repond

Ne pas l'utiliser pour :
- Des questions factuelles simples (USER.md suffit)
- Des questions sur des projets documentés dans SiYuan (consulter directement)
- Du contenu absent des sources (actualité, dépôt non indexé)

## Commandes

```
cd "%LOCALAPPDATA%\hermes\data\rag"
./venv/Scripts/python.exe chercher.py "ma question"              # 5 meilleurs fragments
./venv/Scripts/python.exe chercher.py "ma question" -k 8         # 8 fragments
./venv/Scripts/python.exe chercher.py "ma question" -s skill     # siyuan|skill|script_v4|wordpress
./venv/Scripts/python.exe chercher.py "ma question" --complet    # fragments entiers

# reconstruire l'index (apres ajout de documents SiYuan, de skills ou de scripts)
./venv/Scripts/python.exe indexer.py
./venv/Scripts/python.exe indexer.py siyuan                      # une seule source
```

Le score affiche est un cosinus (0 a 1) : au-dessus de 0,85 la correspondance est generalement
fiable, entre 0,75 et 0,85 il faut lire le fragment avant de s'en servir.

## Pieges

- Les modeles de la famille **e5 exigent les prefixes** : `passage: ` a l'indexation et `query: ` a
la recherche. Les scripts les ajoutent ; une recherche ecrite a la main sans le prefixe voit sa
pertinence s'effondrer sans message d'erreur.
- **L'index ne se met pas a jour tout seul.** Apres avoir ecrit un document dans SiYuan ou modifie
un skill, relancer `indexer.py` (2 a 3 minutes) — sinon on interroge une version perimee.
- Le venv est en **torch CPU** volontairement : l'indexation prend quelques minutes et ne consomme
aucune VRAM, qui doit rester libre pour les rendus video.
- Ne pas indexer les venvs, les videos, les modeles (34 Go de LTX, 75 Go d'Ollama) ni la base de
sessions : volume enorme, contenu bruité, aucun gain de pertinence.
- Si la source `siyuan` revient vide (0 fragment), c'est que le noyau SiYuan ne tourne pas
(port 6806) : l'index perdrait 107 fragments en silence.

## API HTTP locale (port 8200)

Pour interroger le RAG depuis un autre programme (script, gateway, client compatible OpenAI) :

```
cd "%LOCALAPPDATA%\hermes\data\rag"
venv\Scripts\python.exe serveur_rag.py            # port 8200 — lancement MANUEL, aucune tache planifiee
venv\Scripts\python.exe serveur_rag.py --port 8201
```

| Endpoint | Corps | Rend |
|---|---|---|
| `GET /sante` | — | `{"status":"ok","fragments":N,"modele":"..."}` + repartition par source |
| `POST /search` | `{"question":"...","k":5,"source":"siyuan"}` | resultats : `score` (RRF), `cos`, `source`, `notebook`, `titre`, `partie`, `extrait` |
| `POST /v1/embeddings` | `{"input":"texte"}` (format OpenAI) | vecteurs de 768 dimensions, prefixe e5 `query: ` par defaut |
| `POST /recharger` | — | relit l'index sur disque |

Latence mesuree : **11,4 s au premier appel** (chargement du modele), **0,05 s ensuite**. Le serveur
memorise le modele et l'index au demarrage en enveloppant les deux chargeurs de `chercher.py` — sans
cela, chaque requete les rechargerait. Il ne surveille pas l'index : apres une reindexation, appeler
`POST /recharger`, sinon il sert l'ancienne version.

## Mise a jour

Apres toute modification des sources : `indexer.py`, puis verifier `manifeste.json` (compte par
source) pour confirmer que rien n'a disparu.
