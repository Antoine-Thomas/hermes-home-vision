---
name: wordpress-suite
description: Use when working on WordPress — SEO audit, performance, security, or SPARC feature dev.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [wordpress, seo, performance, security, sparc, audit]
platforms: [linux, macos, windows]
---

# WordPress Suite

One router for all WordPress workflows. Six references, no behavior change.

## When to use this skill

- SEO audit (metadata, duplicates, competitor) -> `references/seo-audit-wordpress.md`
- Performance / PageSpeed / Core Web Vitals -> `references/wordpress-performance.md`
- Backdoor / hidden admins / mu-plugins scan -> `references/wordpress-security.md`
- End-to-end site audit (one-shot) -> `references/wp-audit-swarm.md`
- Feature dev with SPARC workflow -> `references/sparc-wp-dev.md`

## Routing

| Request | Reference | Extra refs |
|---------|-----------|------------|
| SEO audit | `references/seo-audit-wordpress.md` | `references/seo-audit-wordpress/*.md` (2 files) |
| Performance | `references/wordpress-performance.md` | `references/wordpress-performance/*.md` (1 file) |
| Security | `references/wordpress-security.md` | `references/wordpress-security/*.md` (3 files) |
| Audit swarm | `references/wp-audit-swarm.md` | — |
| SPARC dev | `references/sparc-wp-dev.md` | — |
| Theme modification & optimization (child themes, CSS/PHP/JS, audits) | `references/theme.md` | `references/theme/*.md` (33 files) |

## Workflow

1. Identify WordPress task type.
2. Read the single matching reference.
3. Check `## When to use` / `## Routing` to pick the single matching reference.

## Notes

- All references are verbatim SKILL.md copies (header preserved).
