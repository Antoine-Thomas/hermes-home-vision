---
name: fallback-intelligent
description: "Chaine de repli: gratuit d'abord, payant en secours."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [fallback, omniroute, resilience, cout, routing]
    created: "2026-08-26"
---

# Fallback intelligent (OmniRoute -> DeepSeek -> Kimi)

Chaine de repli a deux etages : OmniRoute route en interne (combos `fill-first`),
et Hermes rebascule vers un autre provider si OmniRoute entier tombe.

```
1. eco          (OmniRoute, combo fill-first)   <- primaire, gratuit d'abord
2. free-stack   (OmniRoute, combo fill-first)   <- fallback Hermes #1
3. deepseek-v4-pro (DeepSeek)                   <- fallback Hermes #2, payant
4. kimi-k3      (Kimi/Moonshot)                 <- fallback Hermes #3
```

## When to Use

Des qu'on veut minimiser le cout sans sacrifier la disponibilite : le trafic
part sur du gratuit, et ne tombe sur du payant que si le gratuit est sature.

## Configuration (verifiee)

```bash
# primaire
hermes config set model.provider omniroute
hermes config set model.default  eco
hermes config set model.base_url http://localhost:20128/v1

# chaine de repli (JSON accepte tel quel par config set)
hermes config set fallback_providers '[{"provider":"omniroute","model":"free-stack","base_url":"http://localhost:20128/v1"},{"provider":"deepseek","model":"deepseek-v4-pro"},{"provider":"kimi","model":"kimi-k3"}]'

hermes fallback list   # verifier
```

Timeout 30 s par etage. Il n'existe PAS de cle `agent.api_timeout` : la bonne
cle est `request_timeout_seconds`, au niveau du provider.

```bash
hermes config set providers.omniroute.request_timeout_seconds 30
```

## Pieges critiques

**Les alias ne marchent que sur `-z/--oneshot`.** Avec `-q`, `cli.py`
fuzzy-matche le nom et part ailleurs. Mesure faite :

| Commande | Combo reellement utilise |
|---|---|
| `hermes -z "..." --model eco` | `eco` ✅ |
| `hermes chat -q "..." --model omniroute/eco` | `free-stack` ❌ |

Toujours utiliser `-z` pour cibler un combo/alias precis.

**Les combos personnalises s'adressent en ID nu**, pas `auto/` :
`eco`, `free-stack` — alors que les combos integres sont `auto/best-coding`.
Un `auto/eco` renvoie 400.

**`model.base_url` doit pointer sur le proxy OmniRoute, jamais sur pollinations/openrouter.**
Si `model.default` est un nom de combo (`eco`) mais que `model.base_url` vaut
`https://text.pollinations.ai/openai`, le nom de combo part tel quel comme ID
modele vers la mauvaise API -> 404/400 `Model not found: eco`. Le bon
`base_url` pour le provider `omniroute` est `http://127.0.0.1:20128/v1`
(= `providers.omniroute.api`). Symptome typique : le combo fonctionne en direct
via OmniRoute (entetes `x-omniroute-*`, modele reel `oc/hy3-free` etc.) mais
Hermes renvoie 503/400 car il contourne le proxy.

**Les alias `auto/*` ne s'enveloppent PAS dans un combo custom.**
`auto/best-free`, `auto/best-chat` etc. sont eux-memes des routeurs : les placer
comme cibles d'un combo `priority` renvoie `503 all targets were skipped by
pre-dispatch filters`. Ils marchent UNIQUEMENT appeles directement comme modele
(`model: "auto/best-free"`). Pour un combo custom, utiliser des modeles concrets
(`oc/*-free`) avec le bon `providerId` (`oc`, `opencode`, ...).

**Pollinations (`pol/*`) exige une cle dans OmniRoute** : `pol/openai` renvoie
401 "valid API key required" sans cle. Le provider `pol` est desormais present
(modele `pol/openai`), mais inutilisable sans cle API Pollinations.

**`fallback_providers` ne se declenche que sur rate-limit / 5xx / erreur
reseau.** Un 400 (modele inexistant) n'active PAS la chaine : la requete
echoue directement. Ne pas compter dessus pour une faute de frappe.

## Verifier quel etage a servi

Le call log OmniRoute est la source de verite (les en-tetes ne sont pas
visibles depuis Hermes) :

```bash
cd ~/.omniroute/call_logs/$(date +%Y-%m-%d)
python -c "
import json,glob,os
for f in sorted(glob.glob('*.json'),key=os.path.getmtime,reverse=True)[:3]:
    s=json.load(open(f,encoding='utf-8')).get('summary',{})
    t=s.get('tokens',{})
    print(s.get('comboName'),'|',s.get('provider'),'|',s.get('model'),
          '| in=',t.get('in'),'| compressed=',t.get('compressed'))"
```

## Providers de repli : ce qui marche vraiment

Teste un par un (latence mesuree, aller-retour complet) :

| Cible | Etat | Latence |
|---|---|---|
| `kiro/claude-haiku-4.5` | ✅ 200 | ~1.4 s (le plus rapide) |
| `free-stack` (combo) | ✅ 200 | ~2.3 s |
| `oc/hy3-free` | ✅ 200 | ~2.9 s |
| `eco` (combo) | ✅ 200 | ~6.2 s |
| `oc/nemotron-3-ultra-free` | ⛔ timeout 90 s | a exclure |
| `tllm/*` (The Old LLM) | ⛔ 403 | inutilisable |
| `felo/felo-default` | ⛔ 400 | inutilisable |
| Pollinations | ⛔ absent du catalogue | non installable |

Ne pas mettre The Old LLM ni Pollinations dans une chaine de repli : le
premier renvoie 403, le second n'existe pas dans OmniRoute.

## Cout

`kiro/*` et `oc/*` remontent `x-omniroute-response-cost: 0.0000000000`.
`kiro/*` ne remonte pas l'usage en tokens (`tokens_in=0` dans les en-tetes) :
pour un chiffrage, lire `summary.tokens.in` du call log, pas l'en-tete.
