# OMATHS Security Monitoring Stack — detail & reproduction

## Architecture (verified 2026-08-30)

```
Wazuh Docker (single-node-wazuh.*)
  ├─ manager-1  (API :55000, alerts lvl>=10)
  ├─ indexer-1
  └─ dashboard-1 (https://localhost:5601)
        │  alerts
        ▼
SecurityMonitoring-AlertBridge  ──(every 5 min)──►  Wazuh API ──► common.send_telegram
SecurityMonitoring-LogMonitor   ──(every 2 min)──►  agent.log/errors.log/gateway.log
SecurityMonitoring-PortMonitor  ──(every 10 min)─►  Get-NetTCPConnection scan
        │
        ▼  (all call common.send_telegram → `hermes send --to telegram`)
Hermes Gateway (PID via `hermes gateway status`)  ──►  Telegram channel 8956868107 (Thomas)
```

`common.send_telegram` tries, in order:
1. `hermes-agent/.venv/Scripts/python.exe -m hermes_cli.main send --to telegram <msg>`
2. `hermes send --to telegram <msg>` (PATH launcher)

Both resolve to the **main Hermes gateway bot** (`TELEGRAM_BOT_TOKEN=8802352038:***`
in `AppData\Local\hermes\.env`). Confirmed delivered: `Flushing text batch ... dm:8956868107`.

## Two different "bots" — do not conflate

| Name | Type | Where | Replies to commands? |
|------|------|-------|----------------------|
| Hermes Gateway bot (`8802352038`) | Always-on gateway | OMATHS (gateway process) | yes (via Hermes conversation) |
| `@omaths_watch_bot` | Interactive monitor | **VPS (external)** | yes (`/watch`, `/status`) — DOWN if VPS off |

The 3 Scheduled Tasks push alerts through the Gateway bot. They are ONE-WAY.
If user says "@omaths_watch_bot est éteint" and expects `/watch` to work, that bot
lives on a VPS you cannot reach from OMATHS — ask for SSH/dashboard access.

## WAZUH_API_PASSWORD (NOT in .env)

`config.json`:
```json
{ "wazuh": { "user": "wazuh-wui", "password": "", "_password_note": "..." } }
```
Password is read from `WAZUH_API_PASSWORD`, a **USER-level** Windows env var
(`[Environment]::GetEnvironmentVariable('WAZUH_API_PASSWORD','User')`).

Verify auth works (no secret file needed) — PowerShell TLS12 + ignore cert:
```powershell
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
$p = [Environment]::GetEnvironmentVariable('WAZUH_API_PASSWORD','User')
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("wazuh-wui:$p"))
$t = Invoke-RestMethod -Uri 'https://localhost:55000/security/user/authenticate?raw=true' `
      -Headers @{Authorization="Basic $b64"} -TimeoutSec 25
# token length ~404 chars = OK
```
Or curl with `--config` writing `user = "wazuh-wui:<pw>"` to a temp file (avoids
putting the secret on the command line).

## Re-enable the 3 tasks (if Disabled)
```powershell
'SecurityMonitoring-AlertBridge','SecurityMonitoring-LogMonitor','SecurityMonitoring-PortMonitor' |
  ForEach-Object { Enable-ScheduledTask -TaskName $_ }
```
Then test live (messages WILL arrive on Telegram if gateway is up):
```bash
PY310="$LOCALAPPDATA/Programs/Python/Python310/python.exe"
"$PY310" monitors/port_monitor.py --telegram
"$PY310" monitors/log_monitor.py --telegram
"$LOCALAPPDATA/hermes/hermes-agent/.venv/Scripts/python.exe" -m hermes_cli.main send --to telegram "TEST omaths_watch"
```

## Known false positives (do NOT open an incident)
- `7680/tcp` svchost.exe → Windows Update / Delivery Optimization. Legit.
- `20128-20132/tcp` node.exe `omniroute/dist/server-ws.mjs` → OmniRoute LLM router. Legit.
- `email_imap_fetch_failed: timed out` in gateway.log → Gmail IMAP throttle, self-heals
  in seconds (reconnect attempt 1 succeeds). Recurs ~hourly. Not an attack.
- `Motif d'attaque potentiel` lvl12 on `Tool terminal returned error` → mis-classified
  internal tool error, not intrusion.

## MSYS/git-bash pitfalls
- `find /c/Users/... -name x` works, but `find /c/... | grep -c` or bare `find`
  with no path lists the whole drive (MSYS `find` quirk). Prefer
  `python -m pip list --outdated | tail -n +3 | grep -c .` for counting packages.
- `grep -rlnE` over `data/` can time out (>30s) — narrow the path or `timeout=` up.
- `tasklist //FI` is rejected in git-bash; use `tasklist | grep -i docker`.
