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

## Which venv a launcher pins (dual-venv checkout)

When one checkout holds both `venv` and a stale `.venv`, "which one runs" is decided per
launcher, and the answers differ:

- `venv\Scripts\hermes.exe` — a `uv` trampoline with the RELATIVE shebang `#!python.exe`,
  so it always uses its own venv.
- `%HERMES_HOME%\bin\hermes.exe` — trampoline with an ABSOLUTE shebang
  (`#!...\hermes-agent\venv\Scripts\python.exe`), and `%HERMES_HOME%\bin` is on the USER
  PATH, so Win+R / Explorer / any shell lands on `venv`.
- Each scheduled task and `.vbs` hardcodes its own `VIRTUAL_ENV` + python path. Observed on
  a dual-venv host: `Hermes_Gateway.vbs`, `Hermes_Gateway_veille.vbs` and the
  "desaturer memoire" task named `venv`, while `gateway-service\Hermes_Serve.vbs` (the
  serve backend on :9119) still named `.venv` — the only launcher on the stale venv, and
  invisible to a `.lnk` / `Run`-key grep. The same `.vbs` is mirrored under `docs\hermes\`;
  repoint both copies and keep `.bak` files.

Read a launcher's target without running it:
```bash
python -c "import re,sys;d=open(sys.argv[1],'rb').read();print([s.decode() for s in re.findall(rb'[\x20-\x7e]{8,}',d) if b'python.exe' in s])" "$HERMES_HOME/bin/hermes.exe"
grep -nE 'VIRTUAL_ENV|python.exe' "$HERMES_HOME/gateway-service/"*.vbs
```

Edit those launchers by byte substitution, never `sed` — the Windows backslash is an escape
in sed's replacement field and `s|agent\\.venv|agent\\venv|g` silently writes a vertical
tab (`agent\x0benv`) into the `.vbs`. See the `windows-path-handling` skill.

Confirming a restart moved venvs: the parent process is the venv python, the child is the
`.hermes-runtime` python that OWNS the port
(`(Get-NetTCPConnection -LocalPort 9119 -State Listen).OwningProcess`, then read that PID's
CommandLine). Kill the wrapper with `/T` — killing only the parent leaves the port holder
alive — and relaunch only once the port is free, otherwise the new stack cannot bind and
exits silently. `curl` returning 404 still proves the service is UP (it answered); only a
connection failure means down.
