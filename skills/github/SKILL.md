---
name: github
description: "Complete GitHub workflow: auth, PR lifecycle, code review, issues, and repo management via gh CLI or git+curl fallback."
version: 1.0.0
author: Hermes Agent (consolidated from github-auth, github-pr-workflow, github-code-review, github-issues, github-repo-management)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Pull-Requests, Code-Review, Issues, Repositories, Git, gh-cli, CI/CD]
---

# GitHub — Complete Workflow Guide

Everything you need to work with GitHub repositories, PRs, issues, and CI — via `gh` CLI or `git` + `curl` fallback.

## When to Use

Load this skill for ANY GitHub task: setting up auth, creating PRs, reviewing code, managing issues, forking repos, monitoring CI, creating releases, or configuring repository settings.

## Quick Decision Tree

| Task | Reference File |
|------|---------------|
| Set up authentication | Section below (Auth Setup) |
| Create / push / merge a PR | `references/pr-workflow.md` |
| Review code (local or PR) | `references/code-review.md` |
| Create / triage / manage issues | `references/issues.md` |
| Clone / create / fork / configure repos | `references/repo-management.md` |
| Troubleshoot CI failures | `references/ci-troubleshooting.md` |
| Look up API endpoints | `references/github-api-cheatsheet.md` |
| Carry an issue to a verified PR | `references/issue-to-pr.md` |

## Auth Setup

This is the shared auth block used by ALL GitHub workflows. Run this detection once at the start of any GitHub session.

```bash
# Check what's available
git --version
gh --version 2>/dev/null || echo "gh not installed"
gh auth status 2>/dev/null || echo "gh not authenticated"

# Determine auth method
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

# Extract owner/repo from git remote (needed for curl fallback)
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ -n "$REMOTE_URL" ]; then
  OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
  OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
  REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
fi

echo "Auth: $AUTH | Owner: ${OWNER:-unknown} | Repo: ${REPO:-unknown}"
```

### If Not Authenticated

**HTTPS Token (works everywhere, no sudo):**
1. User creates token at https://github.com/settings/tokens (scopes: `repo`, `workflow`, `read:org`)
2. Configure: `git config --global credential.helper store`
3. First push prompts for username + token (paste token as password)

**gh CLI:**
```bash
gh auth login           # interactive browser login
# or headless:
echo "<token>" | gh auth login --with-token
gh auth setup-git
```

**SSH:**
```bash
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub  # add to https://github.com/settings/keys
ssh -T git@github.com      # test
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

**Using the token for curl API calls:**
```bash
export GITHUB_TOKEN="<token>"
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

## Reference Files

Detailed workflows are in the reference files. Load the one matching your task:

- **[references/pr-workflow.md](references/pr-workflow.md)** — full PR lifecycle: branch, commit, push, create PR, monitor CI, auto-fix failures, merge. Covers conventional commits, draft PRs, auto-merge, and CI polling.
- **[references/code-review.md](references/code-review.md)** — code review: local pre-push review, PR review on GitHub, leaving inline comments, submitting formal reviews (approve/request changes), and the review checklist (correctness, security, quality, testing, performance, docs).
- **[references/issues.md](references/issues.md)** — issues management: create, view, search, triage, label, assign, comment, close, bulk operations. Includes bug report and feature request templates.
- **[references/repo-management.md](references/repo-management.md)** — repository management: clone, create, fork, sync forks, configure settings, branch protection, secrets management, releases, GitHub Actions workflows, and gists.
- **[references/issue-to-pr.md](references/issue-to-pr.md)** — carry a GitHub issue to a tested, verified PR: premise validation, duplicate sweeps, class-level fixes, honest CI reporting.

## Templates

Ready-to-use templates for common GitHub artifacts:

- **[templates/pr-body-bugfix.md](templates/pr-body-bugfix.md)** — PR description for bug fixes
- **[templates/pr-body-feature.md](templates/pr-body-feature.md)** — PR description for features
- **[templates/bug-report.md](templates/bug-report.md)** — GitHub issue bug report
- **[templates/feature-request.md](templates/feature-request.md)** — GitHub issue feature request

## Reference Tables

- **[references/github-api-cheatsheet.md](references/github-api-cheatsheet.md)** — quick lookup: action → gh command → curl endpoint
- **[references/ci-troubleshooting.md](references/ci-troubleshooting.md)** — diagnosing and fixing CI failures
- **[references/conventional-commits.md](references/conventional-commits.md)** — commit message format reference
- **[references/review-output-template.md](references/review-output-template.md)** — structured code review output format

## Scripts

- **[scripts/gh-env.sh](scripts/gh-env.sh)** — source this for autodetection of gh auth + token extraction

## Pitfalls

- **GitHub disabled password auth for git** — use a personal access token AS the password, or switch to SSH
- **curl fallback requires `GITHUB_TOKEN`** — extract from `~/.git-credentials` or `.env` if not set
- **`gh` credential persistence** — run `gh auth setup-git` after login to wire credentials into git
- **API rate limits** — unauthenticated: 60/hr; authenticated: 5,000/hr
- **`/issues` endpoint returns PRs too** — filter with `'pull_request' not in item` in Python parsing
- **Secrets encryption** via curl requires PyNaCl — `gh secret set` is dramatically simpler
- **Branch protection APIs** require admin access on the repo
- **Workflow dispatch** requires the workflow to have `workflow_dispatch:` trigger defined
