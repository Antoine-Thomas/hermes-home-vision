---
name: kimi-k3
description: "Kimi K3 fallback: when DeepSeek fails, user asks, premium."
version: 1.0.0
---

# Kimi K3 — Fallback & Premium Task Router

Kimi K3 (Moonshot) est le modèle de secours pour les tâches que DeepSeek v4
n'arrive pas à résoudre. PLUS CHER en tokens : **dernier recours uniquement**.

## Déclencheurs

1. **Demande explicite** — "passe sur Kimi", "Kimi K3", "kimi", "design magnifique".
2. **Échecs répétés** — DeepSeek a échoué 2+ fois sur le même problème.
3. **Code complexe** — algorithme lourd, refactoring profond.
4. **Design/UI** — "beau design", "UI soignée", CSS/HTML créatif.

## Règle d'or : isolement du prompt

**Ne JAMAIS envoyer toute la conversation.** Extraire uniquement :
- Le problème précis qui bloque
- Les fichiers concernés (parties pertinentes uniquement)
- Le message d'erreur exact
- La dernière tentative DeepSeek qui a échoué

Objectif : prompt < 2000 tokens.

## One-shot (mode unique)

```bash
hermes chat -q "PROMPT_ISOLE" --provider kimi --model kimi-k3
```

Le prompt doit contenir le contexte minimal + "retourne UNIQUEMENT le
code/patch, pas d'explications".

## Workflow

```
1. DeepSeek échoue 2x ou user demande Kimi
2. Isoler le prompt (< 2000 tokens)
3. hermes chat -q "PROMPT" --provider kimi --model kimi-k2.5
4. Récupérer le résultat → appliquer
5. Continuer avec DeepSeek
```

## Anti-gaspillage

- ❌ Ne pas switcher toute la session
- ❌ Ne pas envoyer l'historique
- ❌ Pas de tâches simples (lecture, grep)
- ✅ One-shot isolé, retour immédiat à DeepSeek
- ✅ Si Kimi échoue aussi → demander à l'utilisateur
