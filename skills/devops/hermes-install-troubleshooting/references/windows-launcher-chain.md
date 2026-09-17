# Windows `hermes` launcher resolution chain

Diagnosed on a Windows 11 git-bash (MSYS) host. Useful when `which hermes` points
somewhere surprising and you need to know what actually runs.

## The launcher is a Node shim, not Python

`pip install hermes-agent` on Windows drops shims into a directory on PATH. In the
observed case that was `C:\nvm4w\nodejs\hermes` (a bash wrapper) plus `hermes.cmd`,
`hermes.ps1`, and `hermes-agent` / `hermes-agent.cmd` / `hermes-agent.ps1`.

The bash wrapper (`#!/bin/sh`) execs `node <dir>/node_modules/hermes-agent/bin/hermes.js`.

`bin/hermes.js` is tiny:
```js
const { runHermes } = require("../lib/python-launcher");
runHermes("hermes", process.argv.slice(2));
```

## `lib/python-launcher.js` resolution order

1. `findPython()` tries candidates in order: `py -3`, then `python`, then `python3`.
   Each is probed with `-c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"`.
2. For the `hermes` bin it runs `python -c "from hermes_cli.main import main; raise SystemExit(main())"`.
3. **`import hermes_cli.main` resolves via normal Python sys.path** — site-packages
   first, but **CWD first for `-c`**. This is the shadowing mechanism: run from inside a
   git checkout and the local source wins; run from anywhere else and the pip-installed
   package wins.

So "which python does `hermes` use?" is answered by "which python has `hermes_cli.main`
importable, given the current CWD", not by `which hermes` alone.

## Gateway process (the definitive "which install is live" probe)

The gateway is a Scheduled Task `Hermes_Gateway`, not a Windows service. Find its PID
with `hermes gateway status`, then:

```
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<PID>' | Select-Object -ExpandProperty CommandLine"
```

Observed output on the dual-install machine:
```
C:\Users\<user>\AppData\Local\Programs\Python\Python311\python.exe -m hermes_cli.main gateway run --replace
```
i.e. the gateway runs the pip-installed copy in Python 3.11 site-packages, NOT the
git clone at `%HERMES_HOME%\hermes-agent`.
