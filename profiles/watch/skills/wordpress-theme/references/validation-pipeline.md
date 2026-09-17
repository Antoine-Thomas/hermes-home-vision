# Automated Validation Pipeline — Theme Assets

Quick, deterministic validation of theme files without requiring a running WordPress site.

## When to Use

- After bulk CSS/JS/SVG changes from any source (manual edit, AI agent, patch application)
- Before committing theme changes
- As part of a multi-agent handoff (validate another AI's output before integrating)
- When generating a `theme-cards.patch` or any git patch

## Pipeline Steps (run in order)

### 1. JavaScript Syntax — `node --check`

```bash
node --check "path/to/theme.js"
# Exit 0 = OK, no output
# Exit 1 = syntax error with line/column
```

No external deps. Works for any `.js` file including browser-targeted code.

### 2. CSS Brace Count — Python

**CRITICAL: Do NOT use `read_file` from `hermes_tools` inside `execute_code` — it silently truncates content.** Use raw Python:

```bash
python -c "
text = open('assets/css/theme-cards.css', encoding='utf-8').read()
opens = text.count('{')
closes = text.count('}')
print(f'Opens: {opens}, Closes: {closes}')
if opens != closes:
    # Stack-based mismatch finder
    lines = text.splitlines()
    stack = []
    for i, line in enumerate(lines, 1):
        for j, ch in enumerate(line):
            if ch == '{': stack.append((i, j+1))
            elif ch == '}':
                if stack: stack.pop()
                else: print(f'EXTRA CLOSE at line {i}')
    if stack:
        for ln, col in stack[:5]:
            print(f'UNCLOSED at line {ln}')
"
```

### 3. SVG Well-formedness — Python xml.etree.ElementTree

```python
import xml.etree.ElementTree as ET
import os

svg_dir = 'assets/img'
for f in os.listdir(svg_dir):
    if f.endswith('.svg'):
        try:
            ET.parse(os.path.join(svg_dir, f))
            print(f'OK: {f}')
        except Exception as e:
            print(f'FAIL: {f} — {e}')
```

### 4. PHP Lint — `php -l`

```bash
php -l "functions.php"
# Output: "No syntax errors detected in functions.php" = OK
```

**Windows git-bash caveat:** PHP is often not in the git-bash PATH even when installed. If `php: command not found`, try:
- Full path: `/c/path/to/php.exe -l file.php`
- Or skip with a note (manual review)

### 5. Git Patch Integrity — `git apply --check`

```bash
git apply --check theme-cards.patch
# Exit 0 = patch applies cleanly
# "already exists" errors = files already present (NOT a patch error)
# Other errors = investigate
```

Note: `git apply --check` on a patch that creates files already in the working tree will report "already exists" — this is expected and not a corruption error. The real test is applying to a clean checkout.

### 6. File Checksums — Python hashlib

Track file integrity across sessions:

```python
import hashlib
for f in ['assets/js/theme-cards.js', 'assets/css/theme-cards.css']:
    with open(f, 'rb') as fh:
        h = hashlib.sha256(fh.read()).hexdigest()[:16]
    print(f'{f}: {h}')
```

## One-Shot Validation Script

Save as `scripts/validate-theme.py` (Python, run from theme root):

```python
"""Validate theme assets: JS syntax, CSS braces, SVG parse, PHP lint."""
import subprocess, os, sys, hashlib, xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
results = {'pass': 0, 'fail': 0, 'skip': 0}

# JS
for js in ['assets/js/theme-cards.js', 'assets/js/theme-cards-fx.js']:
    r = subprocess.run(['node', '--check', os.path.join(ROOT, js)], capture_output=True)
    ok = r.returncode == 0
    results['pass' if ok else 'fail'] += 1
    print(f"{'OK' if ok else 'FAIL'}: node --check {js}")

# CSS
for css in ['assets/css/theme-cards.css', 'assets/css/theme-cards-fx.css']:
    with open(os.path.join(ROOT, css), encoding='utf-8') as f:
        text = f.read()
    ok = text.count('{') == text.count('}')
    results['pass' if ok else 'fail'] += 1
    print(f"{'OK' if ok else 'FAIL'}: braces {css} ({text.count('{')}/{text.count('}')})")

# SVG
svg_dir = os.path.join(ROOT, 'assets', 'img')
for f in sorted(os.listdir(svg_dir)):
    if f.endswith('.svg'):
        try:
            ET.parse(os.path.join(svg_dir, f))
            results['pass'] += 1
            print(f'OK: SVG {f}')
        except Exception as e:
            results['fail'] += 1
            print(f'FAIL: SVG {f} — {e}')

print(f"\nTotal: {results['pass']} pass, {results['fail']} fail, {results['skip']} skip")
sys.exit(0 if results['fail'] == 0 else 1)
```

## Pitfalls

- **`read_file` truncation in execute_code**: The `from hermes_tools import read_file` function inside execute_code blocks returns truncated content for files over ~800 lines. Always use raw Python `open()` for accurate file reading. A CSS file with 121 opening braces may appear to have only 94 — the `total_lines` count will be correct but `content` will be incomplete.
- **PHP not in git-bash PATH**: On Windows, `php` is often in the Local by Flywheel directory but not exposed to git-bash. Skip PHP lint rather than blocking, and note it.
- **`git apply --check` false positives**: "already exists in working directory" is a file-existence error, not a patch format error. Verify with `grep` for unexpected error types if unsure.
