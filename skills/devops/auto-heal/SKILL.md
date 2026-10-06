---
name: auto-heal
description: "Auto-heal system: check and fix common issues at startup."
version: 1.1.0
author: Hermes Agent
platforms: [windows]
---

# Auto-Heal

Comprehensive health check and auto-repair for the Hermes Windows environment.
Run at startup or on demand to detect and fix common issues.

The runnable body lives in `scripts/hermes-auto-heal.sh` (the block below is the same
checks, kept inline so the skill stays readable/auditable). Launch the script:

```bash
bash "$LOCALAPPDATA/hermes/skills/devops/auto-heal/scripts/hermes-auto-heal.sh"
```

Exit code: `0` = every check passed, `1` = at least one check FAILED.
A check that cannot be run counts as FAILED — never as a silent "All OK".

## Checks Performed

| # | Check | Auto-Fix | Must FAIL when |
|---|-------|----------|----------------|
| 1 | Python runtime + `yaml`, `requests`, `concurrent_log_handler` imported by the RESOLVED interpreter | `pip install <pkg>` into that interpreter, then re-import | no interpreter resolvable, or an import still fails after the repair attempt |
| 2 | Hermes gateway running (PID from `hermes gateway status`, confirmed in `tasklist`) | `hermes gateway start`, then re-check | no PID reported, and still no running gateway after the restart attempt |
| 3 | Disk space (>5 GB free) | Alert only | free < 5 GB |
| 4 | GPU status (`nvidia-smi --query-gpu`) | Alert only | never — a missing `nvidia-smi` is a warning, not a failure |
| 5 | Key paths exist (`$HOME`, Desktop, hermes home, hermes-agent) | Report missing | a required path is missing |

## Check 1 - resolve the Python runtime dynamically (no hardcoded path)

The interpreter Hermes runs on MOVES at every update and is NOT under
`%LOCALAPPDATA%\Programs\Python`. There is no `hermes --which-python` in v0.21.5; `hermes
--version` only prints the version line. The dynamic sources, in the order the script tries
them:

1. **the staged runtime venv on PATH** (`.../installs/*/environments/*/venv/Scripts`) - the
   interpreter `hermes` itself runs on, the authoritative one;
2. **the runtime venv `hermes doctor` reports** as *"Runtime venv staged (...)"* - used as
   cross-check, and as source 1 is expected to match it;
3. **the newest staged runtime venv directory** - `ls -1dt` on the venv DIRS, never on the
   `python.exe` files: extracted executables all share one filestamp, so sorting the files is
   a no-op and silently picks an alphabetical (possibly stale) environment;
4. **the CLI venv** `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe`;
5. **uv/tools CPython** `%LOCALAPPDATA%\hermes\tools\python-*\python.exe` - a BARE interpreter
   with no third-party packages: legit as a fallback, but it MUST make check 1 fail;
6. `python` on PATH.

Test hooks (both are honoured before any detection):
- `HERMES_AUTOHEAL_PYTHON=<path>` - force the interpreter (simulate a broken runtime);
- `HERMES_AUTOHEAL_NOFIX=1` - never pip-install (dry run / failure simulation, so a
  simulation cannot repair the venv it is supposed to observe as broken).

Check 1 is NOT a `--version` probe: it imports the three critical modules **in the resolved
interpreter** and exits non-zero if any is still missing after the repair attempt. Proving
"the interpreter answers" does not prove "the runtime can import its dependencies" - the old
hardcoded `Programs\Python\Python311\python.exe` had all three packages and reported
`All OK` while the real runtime venv was broken.

## Check 2 - gateway, git-bash compatible

`tasklist /FI "IMAGENAME eq hermes.exe" | find /I "hermes.exe"` is wrong twice on this host:

- the gateway runs as **python.exe** (never `hermes.exe`), so the filter matches nothing and
  the check always concludes "Gateway STOPPED" and tries a pointless restart;
- `find` under git-bash is GNU find, which walks the filesystem and never returns (the DOS
  builtin does not exist here).

The working form:

- take the PID from `hermes gateway status` (`grep -aoE 'PID:[[:space:]]*[0-9]+'`);
- confirm it with `tasklist /FO CSV /FI "PID eq <pid>"` - CSV is trivial to parse and the
  quoted field `"<pid>"` appears only if the process really exists (a no-match answers
  `INFORMATION: ... no tasks ...` on stdout with exit code 0, so test the field, not `$?`);
- pipe `tasklist` through `tr -d '\0'` and grep with `-a`: Windows tools answer in UTF-16LE
  or in the OEM codepage depending on host and on the `-FO` format, and a `grep` without `-a`
  answers "Binary file (standard input) matches" - misread as "no process" on a live gateway;
- PowerShell alternative when CSV parsing is inconvenient: `Get-Process -Id <pid>`.

## Run the Full Health Check

```bash
#!/usr/bin/env bash
# Hermes auto-heal v1.1.0 - comprehensive health check for the Hermes Windows environment.
# Usage:  bash <path to this file>
# Env:    HERMES_AUTOHEAL_PYTHON=<path>   force the interpreter used by check 1
#         HERMES_AUTOHEAL_NOFIX=1         never pip-install (dry run / failure simulation)
# Exit:   0 = all checks passed, 1 = at least one check failed.

FAILED=0
norm() { printf '%s' "$1" | tr '\\' '/' | sed -E 's|^/([a-zA-Z])/|\1:/|; s|^([a-z]):|\U\1:|'; }
HOMEDIR="$(norm "${LOCALAPPDATA:-$HOME/AppData/Local}/hermes")"

echo "=== AUTO-HEAL v1.1.0 ==="
hermes --version 2>&1 | tr -d '\0' | head -1

# what `hermes doctor` calls the active runtime venv ("" if it cannot be read)
DV_RAW="$(hermes doctor 2>&1 | tr -d '\0' | grep -aoE 'installs[^)"]*venv' | head -1)"
DOCTOR_VENV=""
if [ -n "$DV_RAW" ]; then
    DV_RAW="$(norm "$DV_RAW")"
    DOCTOR_VENV="$HOMEDIR/$DV_RAW"
fi

# ---------------------------------------------------------------- [1/5] Python
echo ""
echo "[1/5] Python runtime & critical modules..."

resolve_python() {
    local p
    if [ -n "${HERMES_AUTOHEAL_PYTHON:-}" ]; then
        [ -f "$HERMES_AUTOHEAL_PYTHON" ] || echo "  WARN: HERMES_AUTOHEAL_PYTHON does not exist: $HERMES_AUTOHEAL_PYTHON" >&2
        echo "$HERMES_AUTOHEAL_PYTHON"; return
    fi
    # 1. the runtime venv Hermes itself runs on = the one on PATH
    #    (no grep -o: the WHOLE PATH entry is needed, not the matched fragment)
    p="$(printf '%s' "$PATH" | tr ':' '\n' | grep -aE '/environments/[a-f0-9]+/venv/Scripts$' | head -1)"
    if [ -n "$p" ] && [ -f "$p/python.exe" ]; then echo "$p/python.exe"; return; fi
    # 2. runtime venv reported by `hermes doctor` (active in this process)
    if [ -n "$DOCTOR_VENV" ] && [ -f "$DOCTOR_VENV/Scripts/python.exe" ]; then
        echo "$DOCTOR_VENV/Scripts/python.exe"; return
    fi
    # 3. staged runtime venv, newest venv DIRECTORY first
    #    (do not sort the python.exe files: extracted exes all share one mtime)
    while IFS= read -r p; do
        [ -f "$p/Scripts/python.exe" ] && { echo "$p/Scripts/python.exe"; return; }
    done < <(ls -1dt "$HOMEDIR"/installs/*/environments/*/venv 2>/dev/null)
    # 4. Hermes CLI venv
    p="$HOMEDIR/hermes-agent/venv/Scripts/python.exe"
    [ -f "$p" ] && { echo "$p"; return; }
    # 5. uv / tools CPython (bare interpreter: no third-party packages)
    while IFS= read -r p; do
        [ -f "$p" ] && { echo "$p"; return; }
    done < <(ls -1dt "$HOMEDIR"/tools/python-*/python.exe 2>/dev/null)
    # 6. last resort
    command -v python 2>/dev/null
}

PY="$(resolve_python)"
if [ -z "$PY" ]; then
    echo "  FAIL: no Python runtime resolved under $HOMEDIR"
    FAILED=1
else
    PY="$(norm "$PY")"
    echo "  Interpreter: $PY"
    case "$PY" in
        "$DOCTOR_VENV"*) echo "  Matches the runtime venv 'hermes doctor' reports (active runtime)." ;;
        *) [ -n "$DOCTOR_VENV" ] && echo "  NOTE: 'hermes doctor' reports runtime venv: $DOCTOR_VENV" ;;
    esac
    # yaml/requests/concurrent_log_handler MUST import in the RESOLVED interpreter.
    # A bare interpreter (tools\python-*) has none of them -> check 1 must FAIL there.
    HERMES_AUTOHEAL_NOFIX="${HERMES_AUTOHEAL_NOFIX:-0}" "$PY" -c '
import importlib, os, subprocess, sys
deps = {
    "concurrent_log_handler": "concurrent-log-handler",
    "yaml": "pyyaml",
    "requests": "requests",
}
nofix = os.environ.get("HERMES_AUTOHEAL_NOFIX", "0") == "1"
missing = []
for mod, pkg in deps.items():
    try:
        importlib.import_module(mod)
    except ImportError:
        missing.append((mod, pkg))
for mod, pkg in missing:
    if nofix:
        print("  MISSING (no-fix mode): " + mod + " -> would install " + pkg)
        continue
    print("  FIX: installing " + pkg + " into " + sys.executable)
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
still = []
for mod, pkg in missing:
    importlib.invalidate_caches()
    try:
        importlib.import_module(mod)
    except ImportError as e:
        still.append(mod + ": " + str(e))
if still:
    print("  FAIL: critical modules still not importable in this interpreter:")
    for s in still:
        print("    " + s)
    sys.exit(1)
print("  All OK." + (" (installed " + str(len(missing)) + " package(s))" if missing else ""))
'
    if [ $? -ne 0 ]; then
        echo "  Check 1 FAILED (interpreter: $PY)"
        FAILED=1
    fi
fi

# ---------------------------------------------------------------- [2/5] Gateway
echo ""
echo "[2/5] Hermes gateway..."
GW_STATUS="$(hermes gateway status 2>&1 | tr -d '\0')"
GW_PID="$(printf '%s\n' "$GW_STATUS" | grep -aoE 'PID:[[:space:]]*[0-9]+' | grep -aoE '[0-9]+' | head -1)"
GW_OK=0
if [ -n "$GW_PID" ]; then
    # tasklist CSV, git-bash safe: tr -d '\0' + grep -a (tasklist answers in
    # UTF-16LE or in the OEM codepage depending on host and on the -FO format)
    if tasklist /FO CSV /FI "PID eq $GW_PID" 2>&1 | tr -d '\0' | grep -aq "\"$GW_PID\""; then
        echo "  Gateway running (PID $GW_PID, confirmed via tasklist /FO CSV)."
        GW_OK=1
    else
        echo "  'hermes gateway status' reports PID $GW_PID but tasklist does not show it."
    fi
else
    printf '%s\n' "$GW_STATUS" | head -3 | sed 's/^/  /'
    echo "  No gateway PID found in 'hermes gateway status'."
fi
if [ "$GW_OK" -eq 0 ]; then
    echo "  Attempting restart: hermes gateway start"
    hermes gateway start 2>&1 | tr -d '\0' | head -5
    sleep 2
    if hermes gateway status 2>&1 | tr -d '\0' | grep -aqi 'running'; then
        echo "  Gateway restarted."
    else
        echo "  FAIL: gateway is not running."
        FAILED=1
    fi
fi

# ---------------------------------------------------------------- [3/5] Disk
echo ""
echo "[3/5] Disk space..."
"${PY:-python}" -c '
import shutil
free_gb = shutil.disk_usage("C:/").free / (1024 ** 3)
status = "OK" if free_gb > 5 else "LOW"
print("  Free: %.1f GB [%s]" % (free_gb, status))
raise SystemExit(0 if free_gb > 5 else 1)
'
if [ $? -ne 0 ]; then
    echo "  Check 3 FAILED: less than 5 GB free."
    FAILED=1
fi

# ---------------------------------------------------------------- [4/5] GPU
echo ""
echo "[4/5] GPU status..."
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used --format=csv,noheader 2>&1 | tr -d '\0' | sed 's/^/  /'
else
    echo "  WARN: nvidia-smi not available (warning only, not a failure)."
fi

# ---------------------------------------------------------------- [5/5] Paths
echo ""
echo "[5/5] Key paths..."
for p in "$HOME" "$HOME/Desktop" "$HOMEDIR" "$HOMEDIR/hermes-agent"; do
    if [ -d "$p" ]; then
        echo "  [OK] $(norm "$p")"
    else
        echo "  [MISSING] $(norm "$p")"
        FAILED=1
    fi
done

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "=== Auto-Heal complete: 5/5 OK ==="
else
    echo "=== Auto-Heal complete: AT LEAST ONE CHECK FAILED ==="
fi
exit "$FAILED"
```

## Quick (import-only) Check

Use the `python-dependency-guard` skill for a faster modules-only check.
Use this full `auto-heal` skill for the comprehensive system scan.

## Launch as a command

`hermes-auto-heal` is a 4-line wrapper in `%LOCALAPPDATA%\hermes\bin` (that directory is on
the git-bash PATH; it is NOT on the PowerShell/cmd PATH):

```bash
hermes-auto-heal          # 5/5 OK -> exit 0 ; any failed check -> exit 1
```

Equivalent direct launch, useful when `bin` is not on PATH:
`bash "$LOCALAPPDATA/hermes/skills/devops/auto-heal/scripts/hermes-auto-heal.sh"`

## Pitfalls

- `hermes version` is NOT a command (`hermes: 'version' is not a 'hermes' command.`); the
  version line comes from `hermes --version`.
- Never hardcode a Python path in this skill. `Programs\Python\Python311\python.exe` is an
  unrelated interpreter: it had yaml/requests/concurrent_log_handler installed and kept
  reporting `All OK` while the actual runtime venv could not import `yaml` at all. Resolve
  the interpreter dynamically and print the one actually used.
- The runtime venv directories are numerous (one per staged environment) and stale ones stay
  on disk. Detect the ACTIVE one via PATH or `hermes doctor`, not with a bare glob.
- Windows output codecs: strip NULs (`tr -d '\0'`) and grep with `-a` on every Windows tool
  whose output is parsed; otherwise a running process reads as absent.
- `hermes gateway start` may fail if Hermes isn't installed as a service. Use `hermes gateway install` first.
- `nvidia-smi` requires NVIDIA drivers installed and in PATH; a missing `nvidia-smi` is a
  warning, not a failure.
- Do not run the failure simulation (`HERMES_AUTOHEAL_NOFIX=1` plus a renamed package dir)
  without the no-fix flag: the pip auto-repair would reinstall the package and hide the very
  failure being tested.
