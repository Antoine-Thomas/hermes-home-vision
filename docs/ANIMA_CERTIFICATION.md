# ANIMA 0.2 — Certification

- **Version** : ANIMA 0.2
- **Date** : 2026-09-29
- **Périmètre** : 4 profils (default, watch, veille, docs-writer) · 15 composants
  supervisés · 1 plugin E2E (`anima-memoire-router`)
- **Bascule documentaire vers 0.2** : 2026-10-07. **Aucune re-certification n'a été effectuée** :
  les mesures ci-dessus datent du 2026-09-29 et font foi pour cette date. L'état mesuré le
  2026-10-07 est `FAILED` (ollama et wazuh arrêtés) — détail dans
  [`CHANGELOG-ANIMA-v0.2.md`](CHANGELOG-ANIMA-v0.2.md).

## État des composants (supervision health_anima)

Dernier tick de supervision : 2026-09-29 17:11:13 (les valeurs marquées « re-mesuré »
sont confirmées directement après cette date).

**READY (12)** : gateway · profils · nim_proxy · rag · siyuan · laya · ollama ·
wazuh · reindex · jev · couts · memoire (84,5 % — sous le seuil de 90 %, re-mesuré
après l'étape 7)

**DEGRADED (3)** :
- omniroute — taux de succès 56,5 % (seuil 80 %), 5 connexions actives
- cron — 4 job(s) actif(s) en erreur
- fallback — repli payant activé récemment (dernier modèle deepseek-flash)

**FAILED** : aucun · **BLOCKED** : aucun (JEV sorti de l'état BLOCKED depuis l'étape 4)

**Aegis** (4ᵉ couche, sécurité) : vérifié par `docs/ARCHITECTURE_AEGIS.md`
(ACL 3 ACE, 0 secret versionné, Wazuh, ports). Dans la supervision, la couche Aegis
est représentée par le composant `wazuh` (READY).

## Tests

- `tests_health_anima.py` : **15/15 PASS**
- `plugins/anima-memoire-router/tests/test_hook.py` : **9/9 PASS**
- E2E : **T1** (nominal, réponse cite le RAG) · **T2** (JEV échec → repli regex) ·
  **T3** (RAG échec → fail-open) — tous OK

## Câblage E2E

Fonctionnel : le plugin `anima-memoire-router` (hook `pre_llm_call`) route la
question via `router_memoire` (JEV, repli regex), interroge le RAG si le niveau 3
est requis, et injecte `<rag_context>` dans le contexte du LLM.

## Limites documentées

- Flotte gratuite saturée : gemini 20 req/jour, NIM 16/16.
- Repli payant plafonné en surveillance : alerte si > 0,50 $/24 h.
- Sessions > 128K : la compression (seuil 0,4) ne suffit pas, il faut `/new`.

## État global

**DEGRADED** — causé par OmniRoute (et non par ANIMA lui-même). La couche ANIMA
(supervision + mémoire hiérarchique) est fonctionnelle.

## Empreintes SHA256 (fichiers clés)

```
9297200e456f2ea8c20048560e5650852812979e63d982530aff100f4f0b5030  data/route_ia_fix/health_anima.py
7872f237209447ecc1b260e3fa12fc44eef24c03278e22a2ca497d6f25c89673  data/rag/router_memoire.py
0e95e3f90f4ed51cece81faac0ab1d3d9a70546249ca2dcd29a5c54b8bf168aa  plugins/anima-memoire-router/__init__.py
a2f3a089f1c9545981407407c06426230e6ec8cbc2d302213481380b0913d615  config.yaml
```

## Notes / écarts

- La consigne listait « mémoire (84,5 %) » en DEGRADED : à 84,5 %, l'occupation de
  USER.md est SOUS le seuil de 90 % → l'état correct est **READY**. Le dernier tick
  (17:11) affichait encore 94,8 % (DEGRADED) avant l'étape 7 ; il se clarifiera au
  prochain tick.
- La consigne listait « Aegis » comme composant : Aegis est la **4ᵉ couche**
  (sécurité) de l'architecture, pas un composant supervisé ; elle est mappée au
  composant `wazuh` (READY).
- La supervision compte 16 entrées dans `services` : 15 composants + l'entrée de
  comptabilité `anomalies_historiques` (nb=0).
