# Changelog — Version 1.3 — Hermes Psychopomp

## [1.3] — 2026-09-22

### Les changements en détail

#### 1. Skill TypeSafe Jev

Jev est un skill d'aide à la décision installé dans Hermes. Il expose trois
primitives : `noul` (poser un jugement), `choice` (trancher entre N options) et
`score` (noter une option). Il sert à ne plus improviser sur les choix rapides et
à garder une trace écrite de la décision prise. Mesures : latence 0,37–0,44 s (mesuré) par
appel, coût ~0,000013 $ par appel. Fichiers : `skills/typesafe-ai/SKILL.md`,
`skills/typesafe-ai/scripts/jev_helper.py`,
`skills/typesafe-ai/references/config-hermes.md`.

#### 2. Wiki L1 non-agentique dans le second cerveau

Le wiki L1 est compilé (16 pages FR) par un script Python non-agentique
(`wiki/scripts/compile_wiki.py`), puis synchronisé dans SiYuan. La raison du
choix non-agentique est mesurable : un run d'agent envoie ~16 K tokens de prompt
système à chaque tour, ce qui sature les paliers gratuits en débit/minute ; un
script Python fait **UN SEUL** appel LLM et écrit lui-même les pages, l'index et
le log. Côté cron, le job « LLM Wiki compile » tourne en `no_agent=True`,
timeout 3600 s, lanceur `scripts/wiki_compile.py`. Fichiers : `wiki/`,
`wiki/scripts/compile_wiki.py`, `scripts/wiki_compile.py`.

#### 3. Usage de Jev pour les choix rapides

Jev s'utilise quand le choix est binaire ou compte 3-4 options, que les critères
sont objectifs et que la décision est récurrente. Exemples : `eco` ou
`nvidia-stack` en primaire, quel notebook SiYuan utiliser, créer une page ou en
réutiliser une. Il ne faut **pas** l'utiliser pour des questions ouvertes, de la
recherche, du diagnostic, de la création, au-delà de 5 options, sur des choix
sans critères, ni pour des décisions à impact global (`config.yaml`, changement
de provider). Exemple d'appel :

```python
from jev_helper import choice
decision = choice(
    question="Quel modèle en primaire ?",
    options=["eco", "nvidia-stack", "free-openrouter"],
    criteria=["gratuit", "stable sur gros prompt", "latence < 30 s"],
)
# → {"choice": "eco", "reason": "...", "confidence": "high"}
```

### Ajouté
- Skill TypeSafe Jev (3 primitives)
- Helper Python `jev_helper.py` + `references/config-hermes.md`
- Wiki L1 : 16 pages FR + script de compilation non-agentique
- Lanceur cron `wiki_compile.py` (no_agent=True)
- Skills `devops/hermes-provider-config/`
- Skills `research/wiki-router/`
- `skills/research/llm-wiki/references/compilation-non-agentique.md`

### Modifié
- README.md : bandeau v1.3 + tableau 3 versions
- config.yaml : `model.default: eco` + `model.provider: omniroute`
  (était deepseek-flash payant)
- fallback_providers : eco → nvidia-stack → free-openrouter → deepseek-flash
- Hermes : passage v0.21.4 c7c2df1a → fde4997f (414 commits)
- Skills `devops/omniroute-gateway/SKILL.md` et
  `skills/research/llm-wiki/SKILL.md` (leçons mesurées consignées)

### Corrigé
- Fallback réduit à 1 étage (restauré à 4)
- Daemon OmniRoute tué par `unhandledRejection` cloudflare-ai
- `auto/best-reasoning` retiré de la chaîne : l'alias résout vers
  `openrouter/anthropic/claude-opus-5` (PAYANT, ~274 jetons d'entrée
  par tour, 30+ tentatives par appel)
- Marker `.update-incomplete` purgé

### Supprimé
- 9 candidats morts dans `scripts/probe_omniroute.py`
- Skills obsolètes archivés (airtable, arxiv, computer-use, dogfood,
  google-workspace, humanizer, manim-video, maps, notion, p5js,
  simplify-code, songwriting, TDD, xlsx, wordpress-*)

### Notes de migration
- Depuis v1.2 : aucune action obligatoire. Redémarrer le gateway
  pour que la nouvelle chaîne s'applique.
- Rollback : `git checkout ce1a77d` (dernier commit avant v1.3).
