# Validation post-consolidation — checklist 9 étapes

Réutilisable après toute consolidation (126→84). Timeout global 5 min, lecture seule sauf étapes 6 et 8.

## 1. Inventaire frais (scan disque, pas cache)
```python
active = [p for p in root.rglob("SKILL.md") if "_archive" not in str(p)]
Counter(p.relative_to(root).parts[0] for p in active)  # par catégorie
# attendu: 84 actives, 65 archivées
```

## 2. Umbrellas (24)
Pour chaque umbrella: `wc -l ≤200`, frontmatter `name`+`description`, toutes `references/*.md`/`scripts/*` citées existent.
Liste: creative/diagram-suite, design-system, ascii-suite; SD/code-quality, wordpress-suite, planning-workflow; devops/ssl-monitoring, kanban-system, omniroute-suite (60l), security-ops, windows-ops; productivity/prospecting-suite, office-documents, action-items, planning-ops; email/email-suite; github (github/SKILL.md absorbe issue-to-pr); media/video-assembly, media-analysis; mlops/llm-ops, model-ops; research/research-content; data-science/knowledge-ops; autonomous/agent-tooling.

## 3. Test fonctionnel (5 requêtes, scoring name×10 + desc×5 + body×0.5)
- "auditer sécurité WordPress" → wordpress-suite
- "reviewer code Python" → code-quality
- "monter vidéo ffmpeg" → video-assembly
- "monitorer certificat SSL" → ssl-monitoring
- "héberger LLM local" → llm-ops

## 4. Refs cassées
Parser backticks `*.md` dans chaque SKILL.md, ignorer `*`/`{`/placeholders/`apps/`/`memories/`/`skills/`/`MEMORY.md`/`FINETUNING.md`. Vrai broken = `skill_dir/ref` manquant. Attendu 0 hors faux positifs hermes-operations et skill-curator.

## 5. Protégées >200l intactes
- hermes-install-troubleshooting 215l (2026-09-08)
- supply-chain-hardening 347l (2026-09-08)
- grounded-citations 257l (2026-09-08)
Vérifier `len(splitlines()) == attendu` et `mtime.date() < 2026-09-10`.

## 6. Catégories vides
Lister dossiers 0 SKILL.md. Supprimer seulement si vide ou seul `DESCRIPTION.md` (`shutil.rmtree`).

## 7. Backup
- `skills_backup_20260910_131442` existe, 126 SKILL.md, ~544M/568Mo (`du -sh` MSYS)
- Diff à blanc: comparer via pathlib `file_set` (backup vs skills hors _archive) — `diff -rq C:/...` échoue sur Windows natif, utiliser `bash -lc` ou Python. 0 commun modifié = intègre. 379 seulement-backup (archivés) + 593 seulement-skills (umbrellas) attendu.

## 8. Index
Générer `skills/_index.md` (~188l): header totaux + tableau umbrellas (sources, refs sur disque) + par catégorie `**name** — desc`.

## 9. Rapport
Tableau statuts (6 lignes: 84, 24, 0, 3, backup, index) + anomalies + commandes `cp -r backup -> skills`.

## Pitfalls
- Bare-filename après split → broken: toujours préfixer `references/`.
- `diff -rq C:/...` sur Windows: préférer pathlib ou `bash -lc "diff -rq ..."`.
- Ne jamais splitter une protégée >200l sans confirmation explicite.
