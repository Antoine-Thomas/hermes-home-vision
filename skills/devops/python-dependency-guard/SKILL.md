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

- **Ne jamais installer une bibliotheque d'evaluation/outillage dans un venv de production.** Ce qui a casse
  `data/rag/venv` : `pip install ragas` a ecrit 23 paquets (langchain*, openai, tiktoken, pandas 3.0.6, datasets 5.0.1…)
  dans le venv du RAG ; `sentence_transformers` importe `datasets` au chargement, `datasets` importe `pandas`, et le
  pandas installe exigeait `python-dateutil`/`tzdata` absents -> `ImportError` des que `import sentence_transformers`.
  Regle : une bibliotheque de mesure va dans un venv DEDIE (ex. `.../ragas_env`), jamais dans le venv qui sert en prod.
- **Avant tout `pip install` dans un venv existant, enregistrer `python -m pip freeze > <venv>\.freeze_avant_<date>.txt`.**
  Sans ce fichier, un `pip install` qui met a niveau des dependances (pandas/datasets ici) ne peut pas etre defait
  exactement : les anciennes versions sont ecrasees et le cache pip ne les conserve pas. Le freeze est le seul rollback.
- **Verifier apres toute installation : `python -m pip check`** (detecte les dependances declarees manquantes, comme les
  `python-dateutil`/`tzdata` de pandas 3.0.6) puis reimporter les modules critiques et refaire un test fonctionnel reel.
- **Ne pas lancer un python de venv depuis `execute_code`/`subprocess` sans purger l'environnement.** Le kernel Hermes
  exporte `PYTHONPATH` (et parfois `VIRTUAL_ENV`) vers le venv du runtime Hermes : l'enfant importe alors `fastapi`,
  `numpy`, etc. depuis `installs\<hash>\...\venv` au lieu du venv cible, ce qui produit des erreurs trompeuses. Utiliser
  `env = {k: v for k, v in os.environ.items() if k.upper() not in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV')}`, ou passer
  par l'outil `terminal` qui part d'un environnement propre.
- System Python path may change. Verify with `hermes version`.
- May need `--user` flag if running without admin.
