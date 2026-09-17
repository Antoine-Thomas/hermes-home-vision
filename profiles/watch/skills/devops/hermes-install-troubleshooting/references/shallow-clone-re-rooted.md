# Shallow clone with re-rooted history ("+1 carried commit" that isn't real)

Observed on a git-method install (`C:\Users\<user>\AppData\Local\hermes\hermes-agent`)
that the installer created as `git clone --depth 1`.

## Signature

- `hermes --version` reports a large "commits behind" count AND `(+1 carried commit)`.
- `git status` → "ahead 1, behind 1" (diverged), but `git log --oneline -3` shows only
  ONE local commit.
- `git show <local-sha> --stat` lists the ENTIRE repo as new files — the commit is a
  ROOT commit (empty parent). `git log --format='%H %P' -1 HEAD` prints no parent hash.
- `git merge-base HEAD origin/main` returns empty (unrelated histories).
- `git rev-parse --is-shallow-repository` → `true`; reflog shows repeated
  "reset: moving to origin/main".

## Root cause

A prior update/agent session committed a local change (e.g. an agent committing a
one-line regex fix) on top of the shallow boundary. That produces a re-rooted root
commit. The "carried commit" is usually a STALE snapshot with no unique content — the
fix its commit message names is almost always already merged upstream by the time the
next update runs. Example from a real session: the local commit was titled
`fix(skills_guard): --host flags no longer flagged as DNS exfiltration`, but
`git show origin/main:tools/skills_guard.py` proved the identical regex (with the
`(?<![-/])` negative lookbehind) was already in upstream at lines 177-179.

## Verify nothing is lost BEFORE trusting any reset

```bash
# is the named fix already upstream? (byte-identical => nothing to preserve)
git show origin/main:tools/skills_guard.py | grep '<pattern>'
# net delta is usually just upstream having grown, not a real local edit
git diff --stat origin/main HEAD
```

If the named change is byte-identical upstream, `reset --hard`/update loses nothing.

## Fix

Just run `hermes update`. On divergence the updater prints:

    Fast-forward not possible (history diverged), resetting to match remote...

then cleanly resets to origin/main, clears stale `__pycache__` dirs, venv-syncs, and
restarts the gateway. Verify from a NEUTRAL cwd (`cd /c/Windows/System32` first — see the
cwd-shadowing pitfall in SKILL.md):

- `hermes --version` → "Up to date", no more "+1 carried commit".
- `git log --oneline -1` → HEAD equals the `origin/main` tip.

## Non-issue to expect

The runtime Python patch version shifts (e.g. 3.11.9 → 3.11.16). That is the managed
uv runtime regenerating a new generation, not a regression. A transient
`UnicodeDecodeError` in a `threading._readerthread` while `hermes --version` runs is
benign — a subprocess reader decoding a binary stream; the command still exits 0 with
correct output.
