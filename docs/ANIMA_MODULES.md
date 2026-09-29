# ANIMA 0.1 — Modules

Chaque composant : rôle, port, sonde de santé, dépendances.

## Critiques (une panne dégrade l'état global)

| Module | Rôle | Port/URL | Sonde (health_anima) | Dépendances |
|---|---|---|---|---|
| gateway | Réception/dispatch des messages | processus | heartbeat ≤ 120 s | — |
| profils | Profils actifs | — | liste des profils | — |
| omniroute | Routeur de modèles, combos | 127.0.0.1:20128 | taux succès ≥ 80 % sur 200 appels, connexions actives | providers (openrouter, nvidia, …) |
| ollama | Modèles locaux | 127.0.0.1:11434 | génération réelle si modèle en VRAM | modèles ollama |
| rag | Index + recherche | 127.0.0.1:8200 | `/sante` + `/search` → document attendu dans le top 3 | index e5-base |
| siyuan | Notes structurées | 127.0.0.1:6806 | version + nb docs | — |
| wazuh | SIEM | 9200 / 8443 | cluster + dashboard + manager | — |
| fallback | Chaîne de repli | config.yaml | chaîne complète, étages disponibles, repli activé | fallback_providers |
| reindex | Reconstruction de l'index RAG (03:00) | tâche planifiée | fraîcheur (age ≤ 26 h) | rag |
| memoire | Budget mémoire | USER.md / MEMORY.md | occupation < 90 % (user_char_limit) | — |

## Secondaires

| Module | Rôle | Port/URL | Sonde |
|---|---|---|---|
| nim_proxy | Proxy NVIDIA NIM | local | réponse HTTP |
| laya | Décision locale ONNX (CPU) | module | décision réelle retournée |
| jev | Décideur mémoire | plugin jev-skill-router | décision `source=jev` dans la fenêtre 7 j ; abstention ≠ panne |
| cron | Jobs planifiés | — | aucun job actif en erreur |
| couts | Coûts (state.db) | state.db | cumul par profil + coût 24 h |

## Plugin anima-memoire-router (étape 10)

- Rôle : hook `pre_llm_call` — route la question (router_memoire → JEV/repli
  regex), interroge le RAG si niveau 3 requis, injecte `<rag_context>` dans le
  contexte du LLM. Fail-open (un routeur cassé ne casse jamais un tour).
- Fichiers : `plugins/anima-memoire-router/{plugin.yaml,__init__.py,tests/test_hook.py}`.
- Réglage : `mode` (`off` par défaut, `on` pour activer) ; `rag_url` (défaut
  `http://127.0.0.1:8200`), `rag_k` (3), `timeout_s` (4), `max_chars` (4000).
- CLI : `hermes anima-memoire-router {on|off|status|check}`.
- Journal : `logs/anima-memoire-router.log` (une ligne JSON par décision).

## Modules de routage / supervision (data/)

- `data/rag/router_memoire.py` — routeur mémoire hiérarchique (JEV + repli regex),
  journalise `data/route_ia_fix/jev_routing.jsonl`.
- `data/route_ia_fix/health_anima.py` — sondes ANIMA (services, routing, RAG, JEV,
  Laya, jobs, coûts, fallback), seuils documentés, produit `health_anima.json`.
- `data/route_ia_fix/health_architecture.py` — clés historiques (ports, tâches,
  fraîcheur, verrous, orphelins) + anti-spam Telegram (`health_state.json`).
- `scripts/sante_combos.py` — sonde les combos chat (nvidia-stack), sans LLM,
  état `data/route_ia_fix/sante_combos.json`.
