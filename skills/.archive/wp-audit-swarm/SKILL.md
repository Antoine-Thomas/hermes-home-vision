---
name: wp-audit-swarm
description: "Use when auditing a WordPress site end-to-end in one shot."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wordpress, audit, multi-agent, security, performance, seo, code-review]
---

# WordPress Audit Swarm

## When to Use
- Full-site WordPress audit in one command (security + performance + SEO + code review).
- Transposes Ruflo's "coordinated swarms": run 4 audits in parallel, merge results.

## Steps
1. **Locate the site** — default `C:\Users\searc\Local Sites\searching-murphy\app\public` (memory); else ask the user for the path.
2. **Spawn 4 parallel subagents** via `delegate_task` (one `tasks` entry each, run concurrently), each pinned to a skill:
   - **Security** → skill `wordpress-security` (backdoors, hidden admins, mu-plugins, vulnerable plugins).
   - **Performance** → skill `wordpress-performance` (PageSpeed, Core Web Vitals, caching).
   - **SEO** → skill `seo-audit-wordpress` (metadata, sitemaps, structured data).
   - **Code review** → skill `code-review` (theme/plugin code: bugs, debt, security, tests).
   Each subagent must return findings as a list of `{severity, area, issue, evidence, fix}`.
3. **Merge** — collect the 4 results; dedupe overlapping issues (e.g. a vulnerable plugin appears in both security and code review); sort by severity (critical → high → medium → low).
4. **Deliver** — one prioritized report: critical issues first, then a per-area breakdown, then a recommended fix order.

## Pitfalls
- Subagents can't ask the user — pass the site path + any constraints in each task's `context`.
- Give each subagent an explicit output schema (JSON) so the merge step is mechanical.
- Verify the subagent claims yourself before reporting (subagent summaries are self-reports).
