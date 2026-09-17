---
name: auto-heal
description: "Auto-heal system: check and fix common issues at startup."
version: 1.0.0
author: Hermes Agent
platforms: [windows]
---

# Auto-Heal

Comprehensive health check and auto-repair for the Hermes Windows environment.
Run at startup or on demand to detect and fix common issues.

## Checks Performed

| # | Check | Auto-Fix |
|---|-------|----------|
| 1 | Python critical modules | `pip install` missing packages |
| 2 | Hermes gateway running | Restart if stopped |
| 3 | Disk space (>5 GB free) | Alert only |
| 4 | GPU status (nvidia-smi) | Alert if abnormal |
| 5 | Key paths exist | Report missing |

## Run the Full Health Check

```bash
echo "=== AUTO-HEAL v1.0 ==="
echo ""

# 1. Python modules
echo "[1/5] Python dependencies..."
"C:\Users\searc\AppData\Local\Programs\Python\Python311\python.exe" -c "
import importlib, subprocess, sys
deps = {
    'concurrent_log_handler': 'concurrent-log-handler',
    'yaml': 'pyyaml',
    'requests': 'requests',
}
fixed = 0
for mod, pkg in deps.items():
    try:
        importlib.import_module(mod)
    except ImportError:
        print(f'  FIX: installing {pkg}...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])
        fixed += 1
if fixed:
    print(f'  Installed {fixed} missing package(s).')
else:
    print('  All OK.')
"

# 2. Hermes gateway
echo ""
echo "[2/5] Hermes gateway..."
if tasklist /FI "IMAGENAME eq hermes.exe" 2>NUL | find /I "hermes.exe" >NUL; then
    echo "  Gateway running."
else
    echo "  Gateway STOPPED — attempting restart..."
    hermes gateway start 2>&1
fi

# 3. Disk space
echo ""
echo "[3/5] Disk space..."
python -c "
import shutil
free_gb = shutil.disk_usage('C:\\\\').free / (1024**3)
status = 'OK' if free_gb > 5 else 'LOW'
print(f'  Free: {free_gb:.1f} GB [{status}]')
"

# 4. GPU
echo ""
echo "[4/5] GPU status..."
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used --format=csv,noheader 2>&1
else
    echo "  nvidia-smi not available."
fi

# 5. Key paths
echo ""
echo "[5/5] Key paths..."
for p in "$HOME" "$HOME/Desktop" "$HOME/AppData/Local/hermes"; do
    if [ -d "$p" ]; then
        echo "  [OK] $p"
    else
        echo "  [MISSING] $p"
    fi
done

echo ""
echo "=== Auto-Heal complete ==="
```

## Quick (import-only) Check

Use the `python-dependency-guard` skill for a faster modules-only check.
Use this full `auto-heal` skill for the comprehensive system scan.

## Pitfalls

- `hermes gateway start` may fail if Hermes isn't installed as a service. Use `hermes gateway install` first.
- `nvidia-smi` requires NVIDIA drivers to be installed and in PATH.
- Python path is hardcoded — verify with `hermes version` after updates.
