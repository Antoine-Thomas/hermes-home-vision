# Merge Log — consolidation skills (état réel vérifié)

Dernière vérification: 2026-09-10 (session diagnostic + correction)

## Résultat final

- Actifs: 84 SKILL.md (hors `.archive/` et `_archive/`)
- Archivés: 65 skills vers `.archive/` (exclu du prompt par Hermes)
- `_archive/`: 0 SKILL.md (vidé — ancien emplacement NON reconnu par Hermes)
- Commandes slash enregistrées: 82 (audiocraft = Linux/macOS uniquement, kanban-system = environments:kanban → exclus sur Windows)

## Correction critique de cette session

Le stockage des sources consolidées dans `_archive/` (underscore) était INEFFICACE:

1. `_archive/` n'est PAS dans `EXCLUDED_SKILL_DIRS` de Hermes (seul `.archive/` l'est).
   → Les skills "archivés" restaient chargés dans le prompt et comptés actifs.
2. `tools.skills_sync._recover_renamed_skill` re-sème les skills "bundled"
   (byte-identiques au manifest) déplacés hors de leur chemin canonique, à chaque
   démarrage du gateway / spawn de sous-agent.
   → Les sources bundled "archivées" revenaient toutes seules en actif.

Correctif appliqué: migration vers `.archive/` (via `hermes curator archive`, qui
supprime aussi du re-seeding via `.curator_suppressed`), patch des chemins de
documentation `_archive/` → `.archive/`, copie des templates dans les umbrellas.

## Umbrellas créés (précédents pilotes — vérifiés intacts)

| Catégorie | Umbrella | Sources absorbées (refs verbatim) |
|-----------|----------|-----------------------------------|
| creative | diagram-suite | architecture-diagram, excalidraw, baoyu-infographic |
| creative | design-system | claude-design, popular-web-designs, design-md |
| creative | ascii-suite | ascii-art, ascii-video |
| software-development | code-quality | code-review, requesting-code-review |
| software-development | wordpress-suite | seo-audit-wordpress, wordpress-performance, wordpress-security, wp-audit-swarm, sparc-wp-dev, wordpress-theme |
| software-development | planning-workflow | plan, spike, verify-specs-before-implementing |
| devops | kanban-system | kanban-orchestrator, kanban-worker, sdlc-review |
| devops | omniroute-suite | compression-tokens, omniroute-cost-tracker, omniroute-auto-update |
| devops | ssl-monitoring | ssl-expiry-check, ssl-monitor |
| devops | security-ops | security-audit, wazuh-troubleshooting |
| devops | windows-ops | docker-gpu-windows |
| media | video-assembly | ffmpeg-music-montage, gif-search, video-api-integration |
| media | media-analysis | audio-event-detection, youtube-content |
| research | research-content | blogwatcher, company-research, polymarket |
| research | llm-wiki | (split structurel) |
| research | arxiv | (split structurel) |
| mlops | llm-ops | llama-cpp, serving-llms-vllm, evaluating-llms-harness, obliteratus |
| mlops | model-ops | huggingface-hub, nvidia-nim |
| productivity | prospecting-suite | business-outreach, contact-filtering, french-business-prospecting |
| productivity | office-documents | docx, xlsx, pdf, powerpoint, ocr-and-documents |
| productivity | action-items | document-to-action-items, meeting-action-items |
| productivity | planning-ops | session-librarian, weekly-review-planning |
| data-science | knowledge-ops | jupyter-live-kernel, obsidian |
| email | email-suite | email-campaign, email-inbox-triage, himalaya |
| autonomous-ai-agents | agent-tooling | quick-skill, merge-reconciler |
| github | github | github-issue-to-pr (+ doublon software-development/github supprimé) |

## Sources archivées (chemins exacts)

Voir `.archive/` (65 dossiers). Liste complète:
architecture-diagram, ascii-art, ascii-video, audio-event-detection, baoyu-infographic,
blogwatcher, business-outreach, claude-design, code-review, company-research,
compression-tokens, contact-filtering, design-md, docker-gpu-windows,
document-to-action-items, docx, email-inbox-triage, evaluating-llms-harness, excalidraw,
ffmpeg-music-montage, french-business-prospecting, gif-search, github-issue-to-pr,
github-sd-doublon, himalaya, huggingface-hub, jupyter-live-kernel, kanban-orchestrator,
kanban-worker, llama-cpp, macos-computer-use, meeting-action-items, merge-reconciler,
nvidia-nim, obliteratus, obsidian, ocr-and-documents, omniroute-auto-update,
omniroute-cost-tracker, pdf, plan, polymarket, popular-web-designs, powerpoint,
quick-skill, requesting-code-review, sdlc-review, security-audit, seo-audit-wordpress,
serving-llms-vllm, session-librarian, sparc-wp-dev, spike, ssl-expiry-check, ssl-monitor,
verify-specs-before-implementing, video-api-integration, wazuh-troubleshooting,
weekly-review-planning, wordpress-performance, wordpress-security, wordpress-theme,
wp-audit-swarm, xlsx, youtube-content.

## Références cassées

0 nouvelle référence cassée introduite par cette session.

Faux positifs du checker (références externes/exemples, pré-existantes):
- creative/ascii-suite: `references/ascii-video/{...}` (expansion brace, fichiers présents)
- research/research-content: `scripts/polymarket.py;` (fichier présent, ";" = ponctuation)
- skill-curator: `references/godmode-body/01-x.md`, `references/xxx.md` (exemples de doc)
- software-development/inspecting-hermes-desktop-dom: `scripts/eval.mjs`, `scripts/perf/lib/cdp.mjs`, `scripts/profile-typing-lag.md` (chemins du repo Hermes desktop, hors skill)

Pré-existantes (hors périmètre archiving, signalées sans correction):
- data-science/knowledge-ops: `scripts/jupyter_live_kernel.py` (script jamais présent, chemin mort du portage)
- devops/windows-performance-tuning: `scripts/restore.ps1` (template documenté mais jamais créé)

## Restauration

Backup complet: `skills_backup_20260910_131442` (126 SKILL.md avant consolidation).
