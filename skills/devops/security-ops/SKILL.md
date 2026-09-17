---
name: security-ops
description: "Audit de securite et troubleshooting Wazuh — scan deps/ports/secrets et stack SIEM."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [security, audit, wazuh, siem]
    category: devops
    created: "2026-09-10"
    umbrella_of: [security-audit, wazuh-troubleshooting]
---

# Security Ops — Audit & Wazuh

Audit de securite systeme et depannage de la stack Wazuh. Les skills proteges `security-monitoring` et `supply-chain-hardening` restent independants.

## When to Use

- Auditer deps, ports ouverts, logs web, secrets exposes (`security-audit`)
- Wazuh ne repond plus / 403 dashboard / Docker Desktop eteint (`wazuh-troubleshooting`)
- Ne pas utiliser pour monitoring Telegram spam (`security-monitoring`, protege)

## Security Audit — resume

- Fichiers cibles, procedure de scan, cron hebdomadaire.
- Limites du scanner et pieges rencontres.

Voir `references/security-audit.md` (214l, decoupee en refs par H2).

## Wazuh Troubleshooting — resume

- OMATHS Security Monitoring Stack, activation / cold start, Docker Desktop.
- Quand utiliser, core concepts, erreurs 403, indexation, agents.

Voir `references/wazuh-troubleshooting.md` (812l, decoupee en refs par H2).

## Proteges — non inclus

- `security-monitoring` (protege, 96l, 2026-09-09) — silencing alertes Telegram
- `supply-chain-hardening` (protege, 347l, 2026-09-10) — hardening npm/pnpm

## References

- `references/security-audit.md` — audit complet
- `references/wazuh-troubleshooting.md` — Wazuh complet
