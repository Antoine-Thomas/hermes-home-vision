---
name: python-dependency-guard
description: "Auto-install missing Python packages when an import fails."
version: 1.0.0
author: Hermes Agent
platforms: [windows]
---

# Python Dependency Guard

Auto-repair for missing Python modules on Windows. Checks critical deps, installs missing ones.

## Critical Modules

| Module | Pip Package | Why |
|--------|------------|-----|
| `concurrent_log_handler` | `concurrent-log-handler` | Hermes logging subsystem |

## Check Script

```bash
"C:\Users\searc\AppData\Local\Programs\Python\Python311\python.exe" -c "
import importlib, subprocess, sys
deps = {
    'concurrent_log_handler': 'concurrent-log-handler',
}
for mod, pkg in deps.items():
    try:
        importlib.import_module(mod)
        print(f'[OK] {mod}')
    except ImportError:
        print(f'[MISSING] {mod} - installing {pkg}...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
"
```

## Pitfalls

- System Python path may change. Verify with `hermes version`.
- May need `--user` flag if running without admin.
