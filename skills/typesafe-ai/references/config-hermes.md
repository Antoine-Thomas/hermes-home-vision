# Configuration TypeSafe / Jev pour Hermes (pas Claude Code)

Adaptation locale du skill officiel `typesafe-ai` à l'installation Hermes CLI de
Thomas Leroyer. Le skill lui-même est **agnostique** : il renvoie aux docs live,
il n'utilise aucune commande `claude plugin`. Seul ce fichier et `scripts/jev_helper.py`
sont spécifiques à Hermes.

## Provenance

| Élément | Valeur |
| --- | --- |
| Dépôt officiel | https://github.com/typesafe-ai/skills |
| Commit installé | `65a39f39` — Release v0.5.7 (2026-09-12) |
| Contenu amont | `skills/typesafe-ai/SKILL.md` + `LICENSE` (aucun fichier de référence amont) |
| `SKILL.md` | **verbatim amont**, + la section « Hermes — accès à Jev » ajoutée en fin de fichier |
| Fichiers Hermes | `references/config-hermes.md` (ce fichier), `scripts/jev_helper.py` |
| Installation | 2026-09-22, `%LOCALAPPDATA%\hermes\skills\typesafe-ai\` |
| Mise à jour | `git clone https://github.com/typesafe-ai/skills.git` → remplacer `SKILL.md`/`LICENSE` par la version amont, puis ré-appendre la section Hermes (le reste de l'arbre local n'est pas touché) |

## Accès à Jev

| Paramètre | Valeur |
| --- | --- |
| Route | OpenRouter |
| Endpoint | `POST https://openrouter.ai/api/v1/systemone` |
| Modèle (requête) | `typesafe/jev-1.13` — l'ID nu `jev-1.13` est aussi accepté et mappé sur `typesafe/` |
| Modèle (réponse) | `typesafe/jev-1.13-20260917` (ID daté : c'est lui qui doit être cité) |
| Auth | header `Authorization: Bearer <OPENROUTER_API_KEY>` |
| Clé | `OPENROUTER_API_KEY` dans `%LOCALAPPDATA%\hermes\.env` (73 car., préfixe `sk-`) — jamais en dur, jamais journalisée |
| Alias `jev-latest` | routé comme `~typesafe/jev-latest` (cible mouvante → ne pas s'en servir pour un seuil) |

### Mesures réelles (2026-09-22, `python scripts/jev_helper.py`)

| Primitive | Question | Réponse | Latence | Coût |
| --- | --- | --- | --- | --- |
| noul | « Is this urgent? » | `0.95` | 0,441 s | 1,218e-05 $ |
| choice | « Which team? » (billing/tech) | `billing` (0,96 ; conf. 0,92) | 0,389 s | 1,390e-05 $ |
| score | « Frustration? » (0-2) | `1.15` (0,85 au niveau « Frustrated ») | 0,370 s | 1,331e-05 $ |

Latence 0,37–0,44 s, coût ~1,2–1,4 × 10⁻⁵ $/requête (état de ~90 car., ~50 tokens
de sortie). Ordre de grandeur confirmé par rapport au test de référence
« 0,36 s / 0,000014154 $ » : l'ordre de grandeur est validé, pas la valeur exacte
(elle dépend de la taille de l'état et du nombre de questions).

## IA Hermes disponibles (config.yaml réelle, vérifiée)

| Rôle | Provider | Modèle | Coût | Latence indicative |
| --- | --- | --- | --- | --- |
| Primary | `deepseek` | `deepseek-flash` | payant | ~0,7 s |
| Fallback 1 | `omniroute` | `eco` | gratuit | dépend d'OmniRoute |
| Fallback 2 | `omniroute` | `nvidia-stack` | gratuit | dépend d'OmniRoute |

Providers déclarés : `ollama-launch`, `omniroute`, `groq`, `google` (+ `deepseek` en primary).
Bloc `openrouter:` présent dans la config (cache réponses 300 s) — la route Jev utilise
`OPENROUTER_API_KEY` directement, elle ne passe pas par ce bloc.

## Règles pour Hermes

- Jev ne **remplace pas** le LLM principal : c'est une primitive de décision, pas un rédacteur.
- Jev sert uniquement à : routage, scoring, vérification binaire, extraction de choix.
- Ne pas appeler Jev si la décision se prend en code pur (règle, calcul, lookup exact).
- Toujours valider les seuils sur le trafic réel — jamais sur les exemples de ce fichier.
- Garder questions et seuils dans **un seul** fichier (`scripts/jev_helper.py` ou un module du projet), pas dispersés dans les scripts.
- Coût ~1,3 × 10⁻⁵ $/requête : négligeable, mais un appel Jev reste un appel réseau — pas dans une boucle chaude.
- La clé reste côté serveur/local : jamais dans un script partagé, un log ou un cron exporté.

## 3 primitives Jev

| Primitive | Sens | Forme de la réponse |
| --- | --- | --- |
| **noul** | probabilité de « oui » (0-1) | `{"type":"noul","noul":0.95}` |
| **choice** | choix parmi N options nommées | `{"type":"choice","choice":"billing","probabilities":{...},"confidence":0.92}` |
| **score** | note sur échelle ordonnée | `{"type":"score","score":1.15,"legend":{...},"probabilities":{...},"confidence":0.78}` |

`noul` proche de 0,5 = indécision oui/non, **pas** une intensité moyenne.
`confidence` (choice/score) mesure la concentration de la distribution, pas la
justesse de la décision. Chaque question doit porter assez de `state` pour être
répondue seule : les questions d'une même requête ne voient pas leurs réponses mutuelles.

## Commandes Hermes

```bash
hermes skills list                 # vérifier que typesafe-ai apparaît
hermes skills list | grep -i typesafe
python "$LOCALAPPDATA/hermes/skills/typesafe-ai/scripts/jev_helper.py"   # auto-test
```

- Invoquer : demander à Hermes d'utiliser le skill `typesafe-ai` (le skill se charge seul quand la tâche colle à sa description).
- **Ne pas** utiliser `claude plugin` ni `npx skills add` : on n'est pas sur Claude Code.
- Le SKILL.md amont pointe vers les docs live (`https://docs.typesafe.ai/llms.txt`) : c'est la source de vérité pour l'API, les SDK et les cookbooks — ce fichier ne fige que ce qui est propre à cette installation.

## Cas d'usage pour ce setup (à valider sur trafic réel)

| Cas | Primitive | Remarque |
| --- | --- | --- |
| Routage des crons | `choice` | Jev choisit la classe de tâche ; l'ordonnancement reste au cron |
| Classification d'emails | `noul` (urgence) + `choice` (département) | 2 questions, 1 seule requête |
| Sélection de skill parmi ~84 | `choice` | Fournir la liste des noms + descriptions comme `state` |
| Gating sécurité | `noul` | Jamais seul sur une action destructive : doubler par une règle en code |
| Priorisation veille | `score` | Un `score` par article, comparables entre eux |

## Vérifications effectuées (2026-09-22)

| Point | Méthode | Résultat |
| --- | --- | --- |
| Dépôt amont réel | `git ls-remote` + clone | OK, `v0.5.7` / `65a39f39` |
| Endpoint `/api/v1/systemone` | docs OpenRouter « TypeSafe SDK » | conforme (l'endpoint `/api/alpha/decisions` vu sur des blogs tiers est faux/périmé) |
| Clé `OPENROUTER_API_KEY` | longueur seule (jamais affichée) | présente, 73 car., `sk-` |
| Appel réel | `python scripts/jev_helper.py` | 3/3 primitives répondues, modèle `typesafe/jev-1.13-20260917` |
| Détection par Hermes | `hermes skills list` | `typesafe-ai … enabled` |
| Snapshot de prompt | manifest vs disque (`agent/prompt_builder.py`) | auto-invalidé ⇒ reconstruction au prochain prompt, **aucun redémarrage gateway requis** |

## Limites connues

- Context window plus petit que l'API TypeSafe directe (`https://api.typesafe.ai/v1/systemone`) ; l'ID `jev-1.13` (sans préfixe) est refusé côté TypeSafe mais accepté ici.
- `client.models.list()` du SDK TypeSafe casse contre OpenRouter (`GET /api/v1/models` renvoie la forme OpenRouter) — sans effet ici, le helper parle HTTP direct.
- Réponse `usage` d'OpenRouter : `input_tokens`, `output_tokens`, `cost` (pas la forme TypeSafe seule).
