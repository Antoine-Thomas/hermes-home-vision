---
name: wordpress-local-flywheel-publishing
description: Publish WordPress Hermes skills and Local by Flywheel tools to GitHub.
tags: [wordpress, local-flywheel, hermes-skills, github, publishing]
related_skills: [hermes-agent, github]
---

# Publishing WordPress Hermes Skills & Local by Flywheel Tools to GitHub

## When to Use

User wants to publish a collection of **Hermes Agent skills** for WordPress and Local by Flywheel development tools to a public GitHub repository. This is a specific repo-creation workflow with WordPress/Local/Hermes-specific considerations.

## Repo Structure

```text
hermes-wordpress-skills/
 README.md
 LICENSE
 .gitignore
 .gitattributes
 .env.example
 skills/              # Hermes skills (each with SKILL.md, scripts/, references/)
    local-flywheel-setup/
    wordpress-site-management/
    wp-cli-automation/
    wordpress-backup-restore/
    wordpress-deployment/
 templates/
    skill-template/    # Boilerplate SKILL.md for new skills
 .github/
    workflows/
        validate-skills.yml   # CI: validate SKILL.md frontmatter + structure
    scripts/
        validate_skills.py    # YAML frontmatter validator
        validate_structure.py # Directory structure validator
 tools/
    local-flywheel/   # (optional) Local-specific scripts, blueprints
 docs/
    faq.md
```

## .gitignore for WordPress + Local by Flywheel + Hermes Skills Repo

```gitignore
# --- Local by Flywheel ---
Local Sites/
app/
conf/
logs/
*.log
*.sql
*.sql.gz

# --- WordPress ---
wp-config.php
wp-content/uploads/
wp-content/upgrade/
wp-content/cache/
wp-content/ai1wm-backups/
wp-content/et-cache/
wp-content/debug.log

# --- Secrets / env ---
.env
.env.*
*.pem
*.key

# --- Node / Composer ---
node_modules/
vendor/
package-lock.json
composer.lock

# --- OS / IDE ---
.DS_Store
Thumbs.db
.vscode/
.idea/

# --- Python ---
__pycache__/
*.py[cod]
*.so
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
ENV/
env/

# --- Git ---
.gitattributes
```

**Important**: Do NOT ignore `wp-content/plugins/` or `wp-content/themes/` entirely if they contain CUSTOM code. Only ignore third-party/vendor plugins/themes.

## Pre-push Secret Scan

```bash
grep -RniE "DB_PASSWORD|AUTH_KEY|SECURE_AUTH_KEY|API_KEY|SECRET|TOKEN" . --exclude-dir=.git
```

Remove or replace any findings with environment variables.

## README Template

```markdown
# WordPress + Local by Flywheel Toolkit

Guide complet pour installer WordPress en local avec Local by Flywheel,
utiliser les outils fournis et appliquer les skills WordPress.

##  Volet 4  Guide principal

 [Comment monter son WordPress avec Local by Flywheel](volet4/README.md)

##  Contenu du dépôt

- `volet4/` : guide pas-à-pas (téléchargement, installation, outils, skills)
- `skills/` : skills WordPress prêts à l'emploi
- `tools/local-flywheel/` : scripts et blueprints pour Local by Flywheel
- `docs/` : FAQ et documentation complémentaire

##  Prérequis

- Local by Flywheel (https://localwp.com/)
- WP-CLI
- Git
- Node.js / npm (si applicable)
- Composer (si applicable)

##  Licence

MIT
```

## Git Commands (Windows Git Bash)

```bash
cd /c/chemin/vers/hermes-wordpress-skills

git init
git add .
git commit -m "Initial commit: 5 WordPress skills for Hermes Agent with Local by Flywheel"
git branch -M main
git remote add origin https://github.com/USER/hermes-wordpress-skills.git

# PAT fine-grained cannot create repo — create on web first (https://github.com/new)
git push -u origin main

# If remote has README (created on web): pull --rebase, resolve, force-push
# git pull origin main --rebase && git push -u origin main --force
```

## GitHub Push — PAT Limitation & Workaround

The fine-grained PAT used by `gh auth` **cannot create repositories** (no `createRepository` scope). Workflow:

1. **Create repo on GitHub web UI** (https://github.com/new) — name, Public, empty (no README/.gitignore/license).
2. **Push from local**:
   ```bash
   cd /path/to/repo
   git remote add origin https://github.com/USER/REPO.git
   git branch -M main
   git push -u origin main
   ```
3. If remote already has a README (created on web): `git pull origin main --rebase`, resolve conflicts, `git push -u origin main --force`.
4. Verify: `gh repo view USER/REPO`, `gh api repos/USER/REPO/contents --jq '.[].name'`, `gh run list --repo USER/REPO`.

**If `gh repo create` fails with `Resource not accessible by personal access token`**: the token lacks repo creation. Either create on web (above) or re-auth with `gh auth login --web` (device flow gives broader token).

## Local by Flywheel Blueprint

If tools create a pre-configured WordPress site, include `tools/local-flywheel/blueprint.json` — Local by Flywheel can import this to recreate the site with predefined plugins/themes.

## Key Pitfalls

1. **Don't commit entire Local Sites folder** — Too large, contains secrets, environment-specific paths.
2. **Scan for wp-config.php salts** — Always run secret scan before push.
3. **Use forward slashes in paths** — Git Bash on Windows requires `/c/Users/...` not `C:\\Users\\...` for git commands.
4. **Include only custom code in wp-content** — Third-party plugins/themes go in .gitignore.
5. **Blueprint paths** — Blueprint.json must reference relative paths or Local-managed assets.

## Volet 4 Integration

If this repo accompanies a video series (Volet 4), the `volet4/` folder contains the step-by-step guide that the video references. Keep it in sync with video content.
