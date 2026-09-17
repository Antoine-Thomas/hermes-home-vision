# Reading Wazuh alerts + Windows agent flat-file gotchas (4.7.3)

Session learnings from setting up API-log monitoring on a Windows host with the
single-node Docker stack. Corrections and additions to the main SKILL.md.

## 1. There is NO GET /alerts endpoint in Wazuh 4.7.3

The manager REST API does NOT expose a read endpoint for alerts:
- `GET /alerts` → 404 `{"title":"Not Found","detail":"404: Not Found"}`
- `GET /manager/alerts` → 404
- `GET /events` → 405 (POST-only; it INGESTS events into analysisd, it does not list them,
  and ingestion via POST /events does not reliably produce alerts either)

Alerts live in:
- The manager's JSON-lines file `/var/ossec/logs/alerts/alerts.json` (rotated daily), and
- The indexer (OpenSearch) at `:9200/wazuh-alerts-*/_search` (needs indexer admin creds,
  NOT the wazuh-wui API creds).

Read recent alerts without extra credentials:
```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.manager-1 tail -n 1000 /var/ossec/logs/alerts/alerts.json
```

Each line is one alert object: `timestamp`, `rule.level`, `rule.description`, `rule.id`,
`agent.name`, `location`, `id`, `data.*`. Filter in Python with `json.loads()` per line,
then select `rule.level`.

### Alert-distribution query (fastest way to see what's actually firing)
```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.manager-1 python3 -c "
import json
from collections import Counter
c=Counter()
for l in open('/var/ossec/logs/alerts/alerts.json'):
    l=l.strip()
    if not l: continue
    try: a=json.loads(l)
    except: continue
    c[a.get('rule',{}).get('id','?')]+=1
print(c.most_common(20))
"
```
If every alert is an eventchannel rule (60106, 60642, 61102, 61104, ...) and none carry
your flat file's location, flat-file collection is not working (see §2).

### Verify custom rules loaded after deploying a rules file
```bash
curl -k -s -H "Authorization: Bearer <TOKEN>" "https://localhost:55000/rules?rule_ids=100100,100101"
```
Deploy a custom rules file with `docker cp file manager:/var/ossec/etc/rules/NAME.xml`
then `docker exec manager /var/ossec/bin/wazuh-control restart`. A malformed rules file
makes analysisd fail to start — confirm `wazuh-control status` shows analysisd `running`.

## 2. Windows agent: flat-file `<localfile>` can silently collect nothing

Observed: the Windows agent (4.7.3, Win11) produced 180 eventchannel alerts but ZERO
alerts from any `<localfile>` flat file — including Wazuh's own active-responses.log,
and even with correct CRLF line endings. The files are registered (`Analyzing file: '...'`
in `C:\Program Files (x86)\ossec-agent\ossec.log`) but their contents never reach the
manager. Confirm via the alert-distribution query above.

Reliable fallback (no agent dependency): a Python tailer that reads each log file itself,
tracks byte offsets (persisted to a state file), regex-classifies new lines (ERROR / FATAL
/ 401|403 / SQL-injection / path-traversal), and alerts via Telegram. Same detection logic
as the Wazuh rules, applied client-side — see `monitors/log_monitor.py` in
`data/security-monitoring/`.

## 3. Editing agent ossec.conf on Windows via PowerShell can truncate to 0 bytes

`Get-Content -Raw -Encoding UTF8` followed by `-replace '</ossec_config>', ...` produced an
EMPTY string, and `[System.IO.File]::WriteAllText` then wrote 0 bytes — the agent failed to
start. Use .NET I/O + String.Replace and guard the sizes:

```powershell
$c   = [System.IO.File]::ReadAllText($path)
if ($c.Length -lt 500) { throw "refusing: file too short" }
$new = $c.Replace('</ossec_config>', $snippet + "`r`n</ossec_config>")   # String.Replace, NOT -replace
[System.IO.File]::WriteAllText($path, $new, (New-Object System.Text.UTF8Encoding($false)))  # UTF-8 no BOM
# verify size after write; restore backup if < 500
```

Rules: snapshot the original first; write UTF-8 WITHOUT BOM (a BOM can break Wazuh's XML
parser); verify non-empty before restarting the service. The default Windows agent
ossec.conf is recoverable from Wazuh docs or a fresh MSI install if the original is lost.

## 4. `hermes send` on Windows: PATH launcher may lack python-telegram-bot

`hermes send --to telegram` failed with "python-telegram-bot not installed" even though
the library (22.x) IS present in `.venv`. Cause: the `hermes` launcher on PATH resolves to
a stale `venv/` (a `venv/` vs `.venv/` dual-install). Working form:
```bash
".venv/Scripts/python.exe" -m hermes_cli.main send --to telegram "msg"
```
`hermes send --list telegram` confirms the target (e.g. `telegram:Thomas Leroyer [<id>]`).
