# Multi-Agent Collaboration — Hermes + Kimi K3

Pattern for coordinating work between Hermes (primary, DeepSeek) and Kimi K3 (secondary, Moonshot) on WordPress theme projects. Kimi is used only as a fallback when Hermes cannot resolve a problem.

## When to Use

- Hermes encounters a blocking error, unit test failure, or timeout (30s+)
- Kimi has domain expertise that complements Hermes (creative CSS/JS, SVG generation, animation design)
- The user has Kimi credits available and wants structured collaboration
- You need to catalogue prompts, track which solutions work, and auto-learn from successes/failures

## The `final-collab.json` Structure

Place this at the theme root (e.g., `child-lagoon/final-collab.json`). It serves as the shared brain between agents.

### v2.0 Full Structure (with Policies)

```json
{
  "version": "2.0.0",
  "policies": {
    "fallback_policy": {
      "cost_threshold_usd": 0.5,
      "max_kimi_calls_per_day": 5,
      "error_codes": {
        "EX_JS_SYNTAX": "node --check non-zero",
        "EX_SVG_PARSE": "xml.etree.ElementTree exception",
        "EX_TIMEOUT": "operation >30s",
        "EX_FORM_FAIL": "Devis sandbox POST non-200",
        "EX_HEADLESS_RENDER": "Puppeteer render failed",
        "EX_CSS_MISMATCH": "CSS braces opens!=closes",
        "EX_PHP_LINT": "php -l syntax error"
      }
    },
    "sandbox": {
      "enabled": true,
      "clone_path_template": "%TEMP%/child-lagoon-sandbox-{{ts}}",
      "auto_tag_before_commit": true
    },
    "learning": {
      "learn_after_successes": 2,
      "forget_after_failures": 2,
      "time_weight_hours": 168
    },
    "audit": {
      "log_kimi_calls": true,
      "kimi_credit_alert_threshold_usd": 0.5,
      "record_command_stdout_stderr": true
    }
  },
  "kimi_credit_after": 0.888,
  "kimi_calls_this_session": 0,
  "kimi_call_log": [],
  "collaborators": { "...": "..." },
  "git": { "...": "..." },
  "catalogue": { "...": "..." },
  "validation_summary": { "...": "..." },
  "kimi_artefacts": { "...": "..." },
  "checksums": { "...": "..." }
}
```

Key v2.0 additions over v1.0:
- **`policies.fallback_policy`**: formal error codes (`EX_JS_SYNTAX`, `EX_SVG_PARSE`, etc.), cost threshold per call, daily call cap
- **`policies.sandbox`**: isolated validation before commit, auto-tag snapshot
- **`policies.learning`**: time-weighted (`time_weight_hours: 168` — recent successes weighted higher)
- **`policies.audit`**: per-call logging, credit alert threshold, stdout/stderr capture
- **`kimi_credit_after`**: tracked balance after each session
- **`kimi_call_log[]`**: per-call entries with prompt, estimated cost, actual cost, result

### v1.0 Legacy Structure (for reference)

```json
{
  "version": "1.0.0",
  "created": "ISO-8601 timestamp",
  "created_by": "Hermes Agent (DeepSeek v4 Pro)",
  "theme": "child-lagoon",
  "project": "Searching Murphy — Theme Cards v1.0",
  "collaborators": {
    "hermes": { "model": "deepseek-v4-pro", "role": "Primary — orchestration, validation, reporting" },
    "kimi": { "model": "Kimi K3", "provider": "moonshot", "role": "Secondary — fallback solutions", "remaining_credit_usd": 0.888 }
  },
  "git": {
    "repo_root": "/path/to/themes/",
    "head_sha": "abc1234",
    "recent_commits": ["commit messages..."]
  },
  "catalogue": {
    "prompts_tested": [
      {
        "id": "P001",
        "prompt": "Description of what was requested",
        "agent": "kimi|hermes",
        "date": "YYYY-MM-DD",
        "result": "success|fail",
        "validation": "How it was verified",
        "artefact": "path/to/file",
        "notes": "Context, limitations, known issues"
      }
    ],
    "solutions_validated": [
      {
        "id": "S001",
        "description": "What the solution does",
        "files": ["path/to/file"],
        "pattern": "Key pattern or approach used",
        "verified": true,
        "consecutive_successes": 1
      }
    ],
    "fallback_rules": {
      "triggers": ["blocking_error", "unit_test_fail", "timeout_30s"],
      "protocol": {
        "step1": "Hermes attempts to solve",
        "step2": "If fail: build targeted prompt describing exact problem",
        "step3": "Delegate to Kimi K3 (max $0.03/call)",
        "step4": "Execute Kimi solution + validate automatically",
        "step5": "Record result in final-collab.json",
        "step6": "Apply learning rules: 2 successes = learned, 2 failures = obsolete"
      }
    },
    "learning_log": {
      "auto_learning": {
        "rule": "2 consecutive successes → learned. 2 consecutive failures → obsolete.",
        "learned_solutions": [],
        "obsolete_prompts": []
      }
    }
  },
  "validation_summary": {
    "js_syntax": {"file.js": "pass|fail"},
    "css_brace_count": {"file.css": "X/Y pass|fail"},
    "svg_parse": {"N files": "N/N pass|fail"},
    "php_lint": "status",
    "qa_headless": "status",
    "git_apply_check": "status"
  },
  "kimi_artefacts": {
    "archive_path": "work-in-progress/kimi-output-archive.zip",
    "archive_size_mb": 2.2,
    "extracted_path": "work-in-progress/kimi/",
    "total_files": 242
  },
  "checksums": {
    "assets/js/theme-cards.js": "a1b2c3d4e5f6a7b8"
  }
}
```

## Fallback Protocol (step-by-step)

```
┌─────────────────────────────────────┐
│ HERMES tente de résoudre le problème │
└──────────────┬──────────────────────┘
               │
        ┌──────▼──────┐
        │  Succès ?    │─── OUI ──► Valider + Commit
        └──────┬──────┘
               │ NON
        ┌──────▼──────────────────────┐
        │ Construire un prompt CIBLÉ   │
        │ (décrire le problème exact,  │
        │  pas "refais tout le thème") │
        └──────┬──────────────────────┘
               │
        ┌──────▼──────┐
        │ Appeler KIMI  │  (max $0.03/appel)
        │ pour ce prompt │
        └──────┬──────┘
               │
        ┌──────▼──────────────────────┐
        │ Exécuter la solution Kimi    │
        │ + VALIDER automatiquement :  │
        │  • node --check (JS)         │
        │  • Python brace count (CSS)  │
        │  • ET.parse (SVG)            │
        │  • git apply --check (patch) │
        └──────┬──────────────────────┘
               │
        ┌──────▼──────┐
        │  OK ?        │─── OUI ──► Enregistrer SUCCESS
        └──────┬──────┘              dans final-collab.json
               │ NON
        ┌──────▼──────┐
        │ Enregistrer   │
        │ FAIL + raison │
        └──────────────┘
```

## Learning Rules

- **Learned**: Any solution that succeeds 2 consecutive times is promoted. Future sessions prioritize it.
- **Obsolete**: Any prompt that fails 2 consecutive times is deprecated. Stop proposing it.
- Both lists live in `final-collab.json → catalogue.learning_log.auto_learning`

## Cost Management

- Kimi K3 charged per API call (~$0.01-$0.03 for a typical CSS/JS prompt)
- **Cost cap per call**: `policies.fallback_policy.cost_threshold_usd` (default $0.50) — refuse calls exceeding this
- **Daily cap**: `policies.fallback_policy.max_kimi_calls_per_day` (default 5)
- Track `kimi_credit_after` in `final-collab.json` — updated after each session
- Log every call to `kimi_call_log[]` with: prompt, estimated cost, actual cost, result
- **Alert threshold**: `policies.audit.kimi_credit_alert_threshold_usd` (default $0.50) — warn user when credit drops below
- If credit drops below $0.10, refuse all non-critical calls

## Collecting Kimi Artefacts

**CRITICAL: Verify before creating.** When taking over from another agent's session, always check what the other agent already implemented before re-implementing it. The user may ask you to "do X" when X is already done — your job is to verify, extend if needed, and document, not to recreate.

1. **Audit existing implementation** — grep the source files for the feature before writing any code:
   ```bash
   # Check if zoom CSS exists
   grep -n "zoom\|scale(1.0" assets/css/theme-cards.css
   # Check if mobile eye logic exists
   grep -n "MobileEye\|420\|sm-eye-img" assets/js/theme-cards.js
   # Check if tilt/parallax exists
   grep -n "tilt\|parallax\|perspective" assets/css/theme-cards-fx.css
   ```
2. **Report status honestly** — tell the user "X, Y, Z are already implemented by [agent]. A, B need work."
3. **Extend, don't replace** — add standalone modules rather than modifying the other agent's work.
4. **Locate Kimi-produced files** in the theme directory:
   - `THEME-CARDS-*.md`, `theme-cards.patch`
   - `assets/js/theme-cards*.js`, `assets/css/theme-cards*.css`
   - `assets/img/*.svg`, `assets/img/*.png`
   - Screenshots, `work-in-progress/*.html`, `work-in-progress/*.json`
5. **Archive**: `zip -r work-in-progress/kimi-output-archive.zip [all kimi files]`
6. **Extract for reference**: `unzip -o work-in-progress/kimi-output-archive.zip -d work-in-progress/kimi/`
7. **Catalogue** each artifact in `final-collab.json → catalogue.prompts_tested[]` and in `work-in-progress/catalogue-kimi.json` (inventory of all files with checksums)

## Validation Before Commit

Every solution, whether from Hermes or Kimi, must pass validation:

| Check | Command | Pass Condition |
|-------|---------|----------------|
| JS syntax | `node --check file.js` | Exit 0 |
| CSS braces | Python `text.count('{') == text.count('}')` | Opens == Closes |
| SVG parse | `xml.etree.ElementTree.parse(file)` | No exception |
| PHP lint | `php -l file.php` | "No syntax errors" |
| Patch integrity | `git apply --check theme-cards.patch` | Exit 0 (ignore "already exists") |

**See `references/validation-pipeline.md`** for the complete pipeline script.

## Pitfalls

- **Kimi-only mode**: Never use Kimi for tasks Hermes can handle. The fallback exists for blocked situations, not as a first resort.
- **Forgetting to update final-collab.json**: Every prompt, solution, and validation result must be recorded. A missed entry corrupts the learning log.
- **Cost blindness**: Check `kimi_credit_after` before each Kimi call. Don't burn the user's last $0.10 on a low-priority CSS tweak.
- **Archive duplication**: The kimi archive (`kimi-output-archive.zip`) and the extracted directory (`work-in-progress/kimi/`) are both committed to git. The zip is the authoritative backup; the extracted dir is for quick reference.
- **Re-implementing what's already done**: When the user asks you to "implement X, Y, Z," always audit the existing files first. Kimi (or another agent) may have already done it. Your job is to verify, extend if needed, and document — not to redo. Use `grep` to check for CSS rules, JS modules, and DOM elements before writing any code.
- **Sandbox clone on Windows times out**: `cp -r` of a WordPress theme with `node_modules/` can exceed 30s timeout. Instead of full directory copies, use `git tag` for snapshots and run validations directly on the working tree. The tag provides rollback safety without the copy overhead.
- **`catalogue-kimi.json` format**: Separates the inventory from the collaboration logic. `final-collab.json` tracks prompts/solutions/learning; `catalogue-kimi.json` tracks file listings and checksums. Keep them separate — the catalogue can be regenerated, the collab state is cumulative.
