# JEV (TypeSafe System One) — appeler, tester, verifier

Primitive de **decision** (pas de generation) utilisee pour trancher des choix courts : routage
RAG/SiYuan, choix de provider, classement. Trois primitives : `noul`, `choice`, `score`.

## Ou il vit

| Element | Chemin |
|---|---|
| Skill | `skills/typesafe-ai/SKILL.md` (+ `references/config-hermes.md`) |
| Helper | `skills/typesafe-ai/scripts/jev_helper.py` — `jev()`, `noul()`, `choice()`, `score()` |
| Routeur wiki/RAG | `wiki/scripts/jev_router.py` |
| Fiche | `wiki/concepts/jev.md` |
| Endpoint | `POST https://openrouter.ai/api/v1/systemone`, modele `typesafe/jev-1.13` (reponse datée, ex. `typesafe/jev-1.13-20260917`) |
| Cle | `OPENROUTER_API_KEY` — lue par le helper dans l'environnement puis dans `%LOCALAPPDATA%\hermes\.env` |

Aucun outil Hermes natif, aucune API locale : ce sont des fonctions Python appelees depuis un script.

## Signatures et pieges

- `jev(state, questions)` — `questions` = `{qid: {"type": "noul|choice|score", "instructions": str, "criteria": ...}}`.
- `noul(state, qid, instructions, criteria=None)` → `answers[qid]["noul"]` = probabilite 0..1.
- `choice(state, qid, instructions, options)` — **`options` est un DICT `{option: description}`**, pas une
  liste. Passer la liste en 3e position la met dans `instructions` et l'appel leve
  `TypeError: choice() missing 1 required positional argument: 'options'`.
- `score(state, qid, instructions, levels)` — `levels` est une **liste ordonnee** et le plafond est de
  **10 niveaux** : 11 niveaux → `HTTP 400 "Too many score levels. Must have at most 10 levels."`. Une
  echelle 1-10 s'ecrit `[str(i) for i in range(1, 11)]`.

## Lancer et mesurer

Auto-test des 3 primitives (affiche latence + cout, ne coute que quelques 1e-5 $) :

```bash
python "$LOCALAPPDATA/hermes/skills/typesafe-ai/scripts/jev_helper.py"
```

Mesure par appel : `time.perf_counter()` autour de l'appel **et** `r["_elapsed_s"]` (le helper le
renvoie) ; cout dans `r["usage"]["cost"]`.

Ordres de grandeur mesures sur 0.21.5 : `noul` ~0,34 s / 1,18e-05 $ ; `choice` ~0,31 s / 1,55e-05 $ ;
`score` ~0,26 s / 1,50e-05 $ ; 10 choix de routage RAG vs SiYuan → moyenne 0,316 s / 1,46e-05 $.
La fiche annonce 0,4 s et 1,3e-05 $ : latence conforme (meilleure), cout ~12 % au-dessus de l'annonce.
Un test de coherence (memes cas rejoues dans un autre ordre) a rendu 0 divergence.

## Verifier le cout reel cote OpenRouter

```bash
# depuis Python, cle lue par jev_helper._key() — ne jamais l'afficher
# GET https://openrouter.ai/api/v1/auth/key  (Authorization: Bearer <cle>)
```

Reponse utile : `data.usage_daily` / `usage_weekly` / `usage_monthly` (en dollars) et
`data.free_model_daily_requests` `{used, limit, remaining}`. **Le quota gratuit journalier est un
plafond dur** : une fois `remaining` a 0, les appels gratuits sont refuses jusqu'au reset — le
controler avant de lancer une campagne de tests, pas apres.

## Fallback local : trancher un candidat AVANT de l'installer

Quand JEV est rate-limite (quota gratuit epuise), le reflexe est de chercher un modele local exposant les
memes primitives. Le controle qui decide n'est pas la qualite du modele : c'est la **plateforme** et le
**runtime**. Lire le README et le `pyproject.toml` du candidat avant toute installation — `requires-python`
puis surtout la liste `dependencies`, ou un runtime proprietaire ferme la question a lui seul.

| Candidat | Primitives | Verdict |
|---|---|---|
| Laya Core ML (`aac6fef/*`, port Core ML de Laya) | `noul` / `choice` / `score` | **ecarte** : `coremltools` + Neural Engine = Apple Silicon uniquement (macOS 15+, Python 3.11-3.13, `compute_units` = `cpu_gpu` / `cpu_ne`), donc incompatible Windows — et une reecriture ne se justifie pas (perte de precision + plusieurs jours de travail). Verdict consigne dans la fiche `wiki/concepts/jev.md`. |

Un depot de ce genre se lit sans installer : `agent.py` (`load()` dispatche vers un `ANEAgent` quand le
manifest est `laya-coreml-ane`) et `common.py` (`QTYPES = {choice, score, noul}`) confirment a la fois les
primitives et le verrou de plateforme. Le clone d'exploration va dans `cache/scratch/` et se supprime des
que le verdict est rendu ; le verdict se documente dans la fiche du wiki et se committe en `docs(jev): …`.

Avant de recommander du credit ou une 2e cle pour un fournisseur rate-limite, mesurer la cle en place :
elle peut exister mais etre **vide**, et un fichier d'identifiants ne se lit pas avec l'outil de lecture
(passer par `grep` en shell pour la longueur, `hermes config get <CLE>` pour la valeur resolue) ; la
consommation reelle se lit cote fournisseur, pas dans une estimation.

## Est-ce cable dans le backend ?

Non, par defaut. `plugins/` et `hooks/` sont vides et un `grep -rn 'jev|typesafe'` scope sur
`hermes-agent/` ne remonte que `evals/compaction/`, `plugin-catalog/` et des tests — rien dans le
gateway ni dans un middleware. Verification d'absence dans les logs : `search_files` sur
`logs/agent.log`, `logs/gateway.log`, `logs/errors.log` → 0 occurrence.

Le catalogue propose deja les integreteurs : `jev.yaml`, `jev-skill-router.yaml`,
`jev-model-router.yaml`, `jev-judge.yaml`, `jev-memory-selector.yaml`, `jev-effort-router.yaml`,
`jev-cron-gate.yaml`, `jev-approvals.yaml`… les brancher est un **choix d'integration a faire
valider**, jamais un defaut a annoncer comme acquis.

## Piege du routeur livre

`wiki/scripts/jev_router.py` route `wiki` / `rag` / `both` — il **ne propose pas `SiYuan`**. Pour
tester un routage « SiYuan vs RAG », appeler `choice` directement avec les deux options plutot que le
routeur livre. **Le routeur a raison : c'est la documentation qui s'aligne, jamais l'inverse.**
`wiki` est le concept (le wiki L1 compile) et SiYuan n'est que l'outil qui l'heberge — une doc qui
annonce « routage RAG vs SiYuan » decrit mal le comportement reel. Corriger le README et la fiche
`wiki/concepts/jev.md`, **ne pas** toucher au routeur pour y introduire `SiYuan`. Autre comportement voulu, pas une panne : wiki vide (0 page compilee) ⇒ retour force
`rag` avec `forced: true` et cout 0, pour ne pas decider sans matiere.
