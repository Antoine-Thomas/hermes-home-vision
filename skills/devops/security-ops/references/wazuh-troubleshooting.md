<!-- Source: wazuh-troubleshooting/SKILL.md -->
---
name: wazuh-troubleshooting
description: "Wazuh Docker deployment troubleshooting: 403 dashboard errors, Opensearch security config, agent enrollment, and diagnostics for single-node Wazuh stacks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, windows]
metadata:
  hermes:
    tags: [wazuh, opensearch, security, docker, siem, agent-enrollment]
---

# Wazuh Docker Troubleshooting & Security Configuration

## Overview

Troubleshoot Wazuh single-node Docker deployments (indexer, dashboard, manager).
Primary scenarios: dashboard 403 errors, Opensearch security role mapping fixes,
securityadmin.sh invocation, API credential discovery, and agent enrollment.

## OMATHS Security Monitoring Stack (the other half of "Wazuh")

On the OMATHS host, Wazuh is only the data source. Alert *delivery* to Telegram
runs through **3 Windows Scheduled Tasks** that call Python scripts which push
via `hermes send`. If the user says "la surveillance est éteinte" / "@omaths_watch_bot
ne répond plus", check these BEFORE blaming Wazuh:

```
Get-ScheduledTask | Where-Object { $_.TaskName -match 'SecurityMonitoring' } |
  Select-Object TaskName,State,@{n='Last';e={(Get-ScheduledTaskInfo $_).LastRunTime}},
    @{n='Result';e={(Get-ScheduledTaskInfo $_).LastTaskResult}}
```

| Task | Script | Freq | Role |
|------|--------|------|------|
| `SecurityMonitoring-LogMonitor` | `data/security-monitoring/monitors/log_monitor.py --telegram` | 2 min | scan agent.log / errors.log / gateway.log |
| `SecurityMonitoring-PortMonitor` | `monitors/port_monitor.py --telegram` | 10 min | listen ports + backdoor check |
| `SecurityMonitoring-AlertBridge` | `telegram/alert_bridge.py` | 5 min | Wazuh API -> Telegram (lvl>=10) |

- They use `C:\Users\searc\AppData\Local\Programs\Python\Python310\python.exe`.
- **Re-enable** if `State: Disabled`: `Enable-ScheduledTask -TaskName <name>`.
- `config.json` has `"password": ""` + reads `WAZUH_API_PASSWORD` (a **USER-level**
  env var, NOT in .env). Verify auth without the secret file:
  `curl -k --config <(echo 'user = "wazuh-wui:<pw>"') "https://localhost:55000/security/user/authenticate?raw=true"`.
- The interactive bot `@omaths_watch_bot` (replies to `/watch`, `/status`) is a
  **separate Telegram bot hosted on a VPS** — NOT on OMATHS, no code/token here.
  If it's down, you need the VPS access; the 3 tasks above are just *push* alerts
  through the main Hermes gateway bot (`TELEGRAM_BOT_TOKEN=8802352038`).

### False positives to NOT escalate
- Port **7680/tcp** (svchost.exe) = Windows Delivery Optimization / Update service. Legit.
- Ports **20128-20132/tcp** (node.exe, `omniroute/dist/server-ws.mjs`) = the OmniRoute
  LLM router. Legit. Do not flag as backdoors.
- Gateway Hermes log line `email_imap_fetch_failed: The read operation timed out`
  (Gmail IMAP throttle) recurs ~hourly and **self-heals in seconds** — not an attack.
- `Motif d'attaque potentiel` (lvl12) on `Tool terminal returned error` is a
  mis-classified internal-tool error, not an intrusion.

Full architecture + reproduction recipe: `references/omaths-monitoring-stack.md`.

## References

- `references/omaths-monitoring-stack.md` — OMATHS monitoring stack: 3 Scheduled Tasks,
  `WAZUH_API_PASSWORD` (USER env var, not .env), VPS bot vs gateway bot split, false
  positives (7680/20128 ports, Gmail IMAP throttle), MSYS `find` pitfalls.

## Activation / Cold Start (Docker Desktop not running)

When the user asks to "activer"/"démarrer" Wazuh and `docker ps` fails with
`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`,
the Docker Desktop daemon is stopped. Start it cold:

### 1. Launch Docker Desktop (detached, from git-bash)

Hermes blocks `&` backgrounding in terminal commands. Use one of:

```bash
# Option A — cmd start (most reliable)
cmd //c start "" "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"

# Option B — PowerShell
powershell -Command "Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'"
```

`tasklist //FI` does NOT work in git-bash — `//FI` is rejected as an invalid
argument. Use `tasklist | grep -i docker` to confirm the process launched.

### 2. Wait for the daemon (poll, don't blind-sleep)

```bash
for i in $(seq 1 18); do
  docker info >/dev/null 2>&1 && { echo "ready after ~$((i*10))s"; break; }
  sleep 10
done
docker info --format 'Server: {{.ServerVersion}}'
```

Daemon typically comes up ~10s after the Docker Desktop window appears, but can
take 1-2 min on first launch. Docker Desktop itself may need several seconds to
spawn the process — confirm with `tasklist | grep -i docker` before polling.

### 3. Containers auto-start (restart policy)

Verify all three are `Up`:
```bash
docker ps -a --filter "name=single-node-wazuh" --format "{{.Names}}\t{{.Status}}"
```
The single-node compose file sets `restart: always`, so manager, indexer and
dashboard come back on their own once the daemon is up. If one is `Exited`,
bring it up with `docker start <container>`.

### 4. Verify manager daemons

```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.manager-1 /var/ossec/bin/wazuh-control status
```
Critical daemons must be `running`: analysisd, remoted, syscheckd, logcollector,
monitord, modulesd, authd, db, execd. `not running` for clusterd, maild,
agentlessd, integratord, dbd is NORMAL for a single-node stack without mail config.

### 5. Verify dashboard

```bash
docker logs single-node-wazuh.dashboard-1 2>&1 | grep -E "listening|statusCode:200" | tail -5
```
Expect `Server running at https://0.0.0.0:5601`. Access at https://localhost:5601
(login `admin`). API on https://localhost:55000.

## When to Use

- User asks to start/activate Wazuh after a reboot (Docker Desktop stopped) — see "Activation / Cold Start"
- Dashboard returns 403 "no permissions for [indices:data/read/search]"
- User "admin" cannot access index patterns or saved objects
- Need to modify Opensearch security roles_mapping in the indexer
- Agent enrollment/registration troubleshooting
- Writing/deploying CUSTOM detection rules (own ID range) — see "Authoring Custom Detection Rules"
- A custom rule "does not fire" even though the event reaches the manager
- Collecting Wazuh cluster diagnostics across containers
- Running anti-espionage scans on suspect hosts (network, processes, alerts)
- Automating ticket creation from scan results (Jira/ServiceNow/generic webhook)

## Core Workflow: Fix 403 Dashboard Error

### Phase 1: Identify the Root Cause

The dashboard user "admin" must be mapped in `roles_mapping.yml` inside the
**indexer** container under the `all_access` role's `users:` list. Having it
only in `backend_roles:` is insufficient — the dashboard authenticates without
backend_roles populated, so the mapping must be explicit via `users:`.

**Verification command:**
```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.indexer-1 cat \
  /usr/share/wazuh-indexer/opensearch-security/roles_mapping.yml
```

Check that `all_access` contains both `users:` and `backend_roles:` entries.
If `users:` is missing or doesn't contain "admin" — that's the cause.

### Phase 2: Fix roles_mapping.yml

**Always** save a timestamped backup first:
```bash
BACKUP_DIR="$HOME/wazuh-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.indexer-1 cat \
  /usr/share/wazuh-indexer/opensearch-security/roles_mapping.yml > \
  "$BACKUP_DIR/roles_mapping.yml.original"
```

Create the corrected file. The `all_access` block must include:
```yaml
all_access:
  reserved: false
  backend_roles:
  - "admin"
  users:
  - "admin"
  - "kibanaserver"
  description: "Maps admin to all_access"
```

Copy to container and replace:
```bash
# Copy to container
MSYS_NO_PATHCONV=1 docker cp /path/to/roles_mapping.yml.modified \
  single-node-wazuh.indexer-1:/tmp/roles_mapping.yml

# Backup inside container, then replace
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.indexer-1 cp \
  /usr/share/wazuh-indexer/opensearch-security/roles_mapping.yml \
  /usr/share/wazuh-indexer/opensearch-security/roles_mapping.yml.bak

MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.indexer-1 cp \
  /tmp/roles_mapping.yml \
  /usr/share/wazuh-indexer/opensearch-security/roles_mapping.yml

# chown (root:root may fail; wazuh-indexer:wazuh-indexer is acceptable)
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.indexer-1 chown \
  wazuh-indexer:wazuh-indexer \
  /usr/share/wazuh-indexer/opensearch-security/roles_mapping.yml
```

### Phase 3: Apply via securityadmin.sh

Certificates are at `/usr/share/wazuh-indexer/certs/` (NOT under `config/`).
The script has permissions 640 owned by wazuh-indexer — invoke it with `bash`.

**Method A: Target specific file with `-f` + `-t` (recommended for single fix):**
```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.indexer-1 bash -c '
export JAVA_HOME=/usr/share/wazuh-indexer/jdk
bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh \
  -cacert /usr/share/wazuh-indexer/certs/root-ca.pem \
  -cert /usr/share/wazuh-indexer/certs/admin.pem \
  -key /usr/share/wazuh-indexer/certs/admin-key.pem \
  -h localhost -p 9200 -nhnv \
  -f /usr/share/wazuh-indexer/opensearch-security/roles_mapping.yml \
  -t rolesmapping 2>&1'
```

**Method B: Apply entire config directory with `-cd` (bulk update):**
```bash
MSYS_NO_PATHCONV=1 docker exec -e JAVA_HOME=/usr/share/wazuh-indexer/jdk \
  single-node-wazuh.indexer-1 bash -c \
  "bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh \
  -cd /usr/share/wazuh-indexer/opensearch-security/ -icl -nhnv \
  -cacert /usr/share/wazuh-indexer/certs/root-ca.pem \
  -cert /usr/share/wazuh-indexer/certs/admin.pem \
  -key /usr/share/wazuh-indexer/certs/admin-key.pem \
  -h localhost -p 9200" > securityadmin_output.log 2>&1
```
Note: `-cd` processes ALL config files (roles.yml, roles_mapping.yml, internal_users.yml, etc.),
not just the one you changed. Use `-f` + `-t` for targeted changes.

**Success criteria:** output MUST contain:
```
SUCC: Configuration for 'rolesmapping' created or updated
Done with success
```

If securityadmin.sh fails, collect logs and stop — do not proceed.

### Phase 4: Restart Dashboard

```bash
docker restart single-node-wazuh.dashboard-1
# Wait 120 seconds
sleep 120
```

Verify logs show 200 instead of 403 for index-pattern requests:
```bash
MSYS_NO_PATHCONV=1 docker logs single-node-wazuh.dashboard-1 2>&1 | \
  grep "index-pattern" | tail -10
# Should show statusCode:200, NOT 403
```

### Phase 5: Note on Filebeat Backlog

After fixing roles_mapping, filebeat (in the manager container) may take
~10 minutes to reconnect due to exponential backoff. The manager logs will
show 403s during this period — this is expected and self-resolving.
Look for: `Connection to backoff(elasticsearch(...)) established`

## Finding API Credentials

The Wazuh API user is `wazuh-wui`. The password is stored in the dashboard
container's wazuh config file, NOT as an environment variable:

```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.dashboard-1 cat \
  /usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml | \
  grep -A5 "password\|username"
```

API auth is JWT-based. First get a token, then use Bearer auth:
```bash
# Get token
curl -k -s -u "wazuh-wui:<PASS>" \
  "https://<MANAGER_IP>:55000/security/user/authenticate?raw=true"

# Use token for subsequent calls
curl -k -s -H "Authorization: Bearer ***  "https://<MANAGER_IP>:55000/agents"
```

## Agent Enrollment

### Finding the enrollment method

Wazuh 4.7.3 (open source) does **NOT** expose REST API endpoints for enrollment
tokens. All of these return 404:
- `GET/POST /agents/enrollment_tokens`
- `GET/POST /security/enrollment_tokens`
- `GET/POST /agents/enroll`
- `GET/POST /agents/registration`
- `GET/POST /agents/register`

**However**, `POST /agents/insert` DOES work for pre-creating agent entries:
```bash
curl -k -H "Authorization: Bearer *** -X POST \
  "https://<MANAGER_IP>:55000/agents/insert" \
  -H "Content-Type: application/json" \
  -d '{"name":"agent-auto-test","ip":"any"}'
# Returns: {"data":{"id":"002","key":"MDAyIGFnZW50..."},"error":0}
```
The returned `key` is the agent's enrollment key (base64-encoded). The agent
will have status `never_connected` until the actual agent software connects.

**Fallback:** Use `agent-auth` binary directly against the authd service.

### Managing agents via CLI

The manager container has `manage_agents` at `/var/ossec/bin/manage_agents`:
```bash
# Interactive mode
docker exec -it single-node-wazuh.manager-1 /var/ossec/bin/manage_agents
# Options: (A)dd, (E)xtract key, (L)ist, (R)emove

# Remove an agent by ID (scripted)
docker exec single-node-wazuh.manager-1 bash -c '
/var/ossec/bin/manage_agents -r 002 <<< $"y"'
```

To delete an agent via API (only works for agents that have never connected,
or use `status=never_connected` and `older_than`):
```bash
curl -k -X DELETE -H "Authorization: Bearer *** \
  "https://<MANAGER_IP>:55000/agents?agents_list=002&status=all&older_than=0s"
```

### Agent authd configuration

Check the auth block in the manager:
```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.manager-1 \
  grep -A10 '<auth>' /var/ossec/etc/ossec.conf
```

Key fields:
- `<port>`: authd port (default 1515)
- `<use_password>`: if "no", agents register without credentials
- `<ssl_verify_host>`: hostname verification during enrollment

### Agent installation commands

Replace `<MANAGER_IP>` with the actual address. For local Docker/WSL, use the
host's LAN IP (e.g., 192.168.x.x), not the Docker internal IP (172.18.x.x).

**Linux (Debian/Ubuntu):**
```bash
curl -s https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_4.7.3-1_amd64.deb -o /tmp/wazuh-agent.deb
sudo dpkg -i /tmp/wazuh-agent.deb
sudo sed -i 's/MANAGER_IP/<MANAGER_IP>/' /var/ossec/etc/ossec.conf
sudo systemctl daemon-reload && sudo systemctl enable wazuh-agent && sudo systemctl start wazuh-agent
```

**Windows (PowerShell as Admin):**
```powershell
Invoke-WebRequest -Uri "https://packages.wazuh.com/4.x/windows/wazuh-agent-4.7.3-1.msi" -OutFile "$env:TEMP\wazuh-agent.msi"
msiexec /i "$env:TEMP\wazuh-agent.msi" /q WAZUH_MANAGER="<MANAGER_IP>" WAZUH_REGISTRATION_SERVER="<MANAGER_IP>" WAZUH_AGENT_NAME="agent-auto-test"
NET START WazuhSvc
```

**macOS:**
```bash
curl -so wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/wazuh-agent-4.7.3-1.pkg
echo "WAZUH_MANAGER='<MANAGER_IP>'" | sudo tee /tmp/wazuh_envs
sudo installer -pkg wazuh-agent.pkg -target /
sudo /Library/Ossec/bin/wazuh-control start
```

**Manual enrollment with agent-auth (fallback):**
```bash
/var/ossec/bin/agent-auth -m <MANAGER_IP> -p 1515 -A agent-auto-test
```

## Diagnostics and Log Collection

See `references/403-error-pattern.md` for exact error transcripts and
expected success output from securityadmin.sh.

See `templates/roles_mapping.yml` for a known-correct roles_mapping.yml
that includes the `users:` fix. Copy and deploy this template when the
indexer's all_access block is missing the users section.

Collect logs from all three containers:
```bash
docker logs single-node-wazuh.indexer-1 --tail 300 > indexer_logs.txt
docker logs single-node-wazuh.dashboard-1 --tail 300 > dashboard_logs.txt
docker logs single-node-wazuh.manager-1 --tail 300 > manager_logs.txt
```

List agents via API:
```bash
# Inside manager container with Python (avoids shell escaping issues):
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.manager-1 python3 -c "
import subprocess, json
r = subprocess.run(['curl', '-k', '-s', '-u', 'wazuh-wui:<PASS>',
    'https://localhost:55000/security/user/authenticate?raw=true'],
    capture_output=True, text=True)
token = r.stdout.strip()
r2 = subprocess.run(['curl', '-k', '-s', '-H',
    'Authorization: Bearer *** + token,
    'https://localhost:55000/agents'],
    capture_output=True, text=True)
data = json.loads(r2.stdout)
for a in data['data']['affected_items']:
    print(a['id'], a['name'], a['ip'], a['status'])
"
```

## Authoring Custom Detection Rules

Verified against Wazuh **4.7.3** (single-node Docker, Windows agent), 2026-08.

### The #1 failure: `<match>` never sees Windows eventchannel data

A rule like `<rule id="100200"><match>MYMARKER</match></rule>` will silently
never fire for events arriving from a **Windows agent eventchannel**, even
though the event definitively reaches the manager. Instead the built-in rule
**60602 "Windows application error event"** (level 9) fires.

Cause: the Windows decoder parses the event into **fields**, and leaves
`full_log` empty. `<match>` and `<regex>` test the raw log, so they match
nothing. Confirmed field layout from a real alert:

```
data.win.system.providerName   = MySourceName
data.win.system.message        = "MYMARKER CODE key=value ..."
data.win.eventdata.data        = MYMARKER CODE key=value ...
```

**Correct shape** — a level-0 parent that scopes to your event source, plus
children matching the decoded field:

```xml
<rule id="100199" level="0">
  <if_group>windows</if_group>
  <field name="win.system.providerName">^MySourceName$</field>
  <description>My events via the Windows log (parent, no alert)</description>
</rule>

<rule id="100200" level="10">
  <if_sid>100199</if_sid>
  <field name="win.eventdata.data">MYMARKER AUDIT_VULN</field>
  <description>...</description>
</rule>
```

Emit the events from PowerShell with a dedicated source, which the already-active
`Application` eventchannel `<localfile>` carries for free:

```powershell
if (-not [System.Diagnostics.EventLog]::SourceExists('MySourceName')) {
    New-EventLog -LogName Application -Source 'MySourceName'   # needs admin ONCE
}
Write-EventLog -LogName Application -Source 'MySourceName' `
               -EventId 9001 -EntryType Warning -Message "MYMARKER AUDIT_VULN pkg=x"
```

This eventchannel path is far more reliable on a Windows agent than adding flat
-file `<localfile>` entries. Keep a single generic `<match>` rule as a fallback
for the flat-file path rather than duplicating every child rule.

### Regex support is narrower than you expect

| Tag | Engine | Notes |
|---|---|---|
| `<match>` | substring | `|` acts as OR between literals |
| `<regex>` | **OS_Regex** | NO negated classes `[^...]`, NO optional `( )?`, NO `{n,m}` |
| `<field>` | OS_Match | substring against a decoded field — what you usually want |
| `<pcre2>` | **REJECTED in 4.7.3 rules** | `ERROR: Invalid option 'pcre2' for rule 'N'` |

An OS_Regex violation surfaces as
`ERROR: (5107): Syntax error on tag 'regex' in rule <id>`.

**Architectural consequence — do the hard matching in the collector.** Because
rule-side regex is weak, recognise complex patterns (`curl … | bash`,
`git+https://`, obfuscation) in PowerShell/Python where you have full regex,
then emit a *simple marker* the rule can match literally. This yields readable
rules with no false positives, and keeps the detection logic unit-testable
outside Wazuh.

### Validate before restarting — and roll back

`wazuh-logtest` has **no `-t` flag** (`error: unrecognized arguments: -t`).
The config test binary is `wazuh-analysisd`:

```bash
docker exec <manager> /var/ossec/bin/wazuh-analysisd -t
# exit 0 and no output = decoders + rules all valid
```

Deploy order that never leaves the manager blind:
1. Validate XML well-formedness on the host.
2. Check ID collisions against every other file in `/var/ossec/etc/rules/`.
3. `docker cp`, then `wazuh-analysisd -t`.
4. On failure: delete the new file, restore the timestamped `.bak`, stop.
5. On success: `wazuh-control restart`, then confirm
   `wazuh-analysisd is running` — if analysisd is down, the rules are bad.

`scripts/deploy_rules.ps1` implements exactly this. Run it instead of hand-copying.

### Two traps that cost real deploys

- **XML comments cannot contain `--`.** Writing `--frozen-lockfile` or a `--` in
  a comment yields
  `An XML comment cannot contain '--', and '-' cannot be the last character`.
  Rephrase inside comments; `--` in element *text* is fine.
- **Never hardcode the destination filename in a deploy script.** Derive it from
  the source basename. A script that always writes
  `/var/ossec/etc/rules/<one-fixed-name>.xml` will silently **overwrite an
  unrelated rule file** the next time it is used for a different rule set.

### Testing a rule without waiting for a real event

```bash
docker cp test_rules.sh <manager>:/tmp/ && \
  MSYS_NO_PATHCONV=1 docker exec <manager> sh /tmp/test_rules.sh
```
Each line pipes a sample log into `wazuh-logtest` and asserts the rule id.
Parse the output for `id: '<n>'` and `level: '<n>'` — note it is **not**
`Rule id:`, so a grep for the wrong label makes a firing rule look dead.
`scripts/test_rules.sh` is a ready-made harness.

Caveat: `wazuh-logtest` feeds the line as a raw log, so it exercises
`<match>`/`<regex>` rules but **cannot** simulate the Windows decoder. Verify
eventchannel/`<field>` rules end-to-end instead, by reading the real alerts:

```bash
docker exec <manager> sh -c "grep -h 'MYMARKER' /var/ossec/logs/alerts/alerts.json | tail -3"
```
Confirm `rule.id` is yours and not 60602. Full walkthrough in
`references/custom-rules-windows-eventchannel.md`.

### ID ranges

100000-120000 is the user range. Keep one file per concern with a documented
block (e.g. `100100-100105` APIs, `100198-100206` supply chain) and assert no
collision at deploy time — Wazuh does not warn, the later definition just wins.

## Anti-Espionage Scanning & Automated Ticketing Pipeline

### Overview

Run a complete security scan on a suspect host (network connections, processes,
Wazuh alerts, agent consistency) and automatically create tickets in Jira,
ServiceNow, or a generic webhook based on the `action_taken` column of the
results CSV.

### Scan Workflow

Execute in parallel where possible:

1. **Network connections** (Windows via PowerShell, Linux via `ss`):
   ```powershell
   Get-NetTCPConnection -State Established | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess | Sort-Object RemoteAddress -Unique
   ```

2. **Process list** — check for suspicious binaries, verify wazuh-agent is running:
   ```powershell
   Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 Id,ProcessName,CPU,Path
   ```
   Verify: wazuh-agent.exe path should be `C:\Program Files (x86)\ossec-agent\`.

3. **Wazuh alerts** — recent alerts, severity distribution, comparison API vs client.keys:
   Use the Python subprocess pattern (see Hermes tool workaround reference) to query
   `/alerts?limit=50&sort=-timestamp` and `/agents` inside the manager container.
   Flag any agents with `never_connected` status that don't appear in `client.keys`.

4. **Manager daemon status** — verify all critical daemons are running:
   Query `/manager/status` via API. Expected running: analysisd, authd, remoted,
   syscheckd, monitord, logcollector, apid, modulesd, db, execd.

5. **Output CSV** — produce `scan_results.csv` with these columns:
   ```
   host,ip,date_scan,os,role,connections_external,connections_internal,
   processes_suspects,process_hashes,files_modified_recently,
   agents_wazuh_non_reconnus,alerts_wazuh_recentes,filebeat_status,
   security_recommendation,action_taken,notes
   ```
   See `templates/scan_results.csv` for the template.

### Ticketing Pipeline

#### action_taken Mapping

| action_taken      | Priority | Ticket Type              | Key Fields |
|-------------------|----------|--------------------------|------------|
| isolate-host      | P0       | Incident/Containment     | summary: Host isolé; evidence path |
| forensics-image   | P0       | Forensic Request         | summary: Demande image disque |
| revoke-keys       | P1       | Credential Rotation      | summary: Révoquer clés; accounts affected |
| rotate-passwords  | P1       | Credential Rotation      | summary: Changer mots de passe; services |
| monitor           | P2       | Investigation            | summary: Surveillance renforcée; rules |
| clean-up          | P2       | Remediation              | summary: Nettoyage malware; hashes |
| notify-owner      | P3       | Notification             | summary: Informer propriétaire |

Multiple actions per row are semicolon-separated: `isolate-host;revoke-keys;notify-owner`.

#### Jira Webhook Payload

```json
{
  "fields": {
    "project": {"key": "SEC"},
    "summary": "ISOLATE HOST: omaths (192.168.1.11) - suspicious connections",
    "description": "Action: isolate-host\nHost: omaths\nIP: 192.168.1.11\nEvidence: /tmp/omaths_evidence.tar.gpg",
    "issuetype": {"name": "Incident"},
    "priority": {"name": "Highest"}
  }
}
```

#### ServiceNow Payload

```json
{
  "short_description": "ISOLATE HOST omaths 192.168.1.11",
  "description": "Action: isolate-host\nEvidence: s3://forensic-bucket/omaths_evidence.tar.gpg",
  "urgency": "1",
  "assignment_group": "SOC"
}
```

#### Automation Scripts

Two scripts are provided — use the one matching the runtime environment:

- `scripts/auto_ticketing.sh` — Bash (Linux/Docker/WSL). Requires `jq`, `curl`.
  Supports `--dry-run` mode. Configure via env vars:
  ```bash
  export TICKET_SYSTEM=jira  # jira | snow | generic
  export WEBHOOK_JIRA="https://jira.example.com/rest/api/2/issue"
  export AUTH=***
  ./auto_ticketing.sh scan_results.csv --dry-run
  ```

- `scripts/auto_ticketing.ps1` — PowerShell (Windows). Uses `Invoke-RestMethod`.
  ```powershell
  .\auto_ticketing.ps1 -CSV scan_results.csv -TicketSystem snow -DryRun
  ```

Both scripts read the CSV line-by-line, parse semicolon-separated `action_taken`,
map each action to the correct priority/type, and POST the appropriate payload.

See `references/ticketing-mapping.md` for the complete mapping table and
per-action payload details.

### Evidence Packaging

```bash
# Create encrypted evidence archive per host
tar czf /tmp/${HOST}_evidence.tar.gz /tmp/${HOST}_*.txt /tmp/${HOST}_capture.pcap
gpg --symmetric --cipher-algo AES256 --passphrase-file /secure/passphrase.txt \
  -o /tmp/${HOST}_evidence.tar.gz.gpg /tmp/${HOST}_evidence.tar.gz
```
Reference the archive path in the ticket's evidence/description field.
Never send the passphrase in the same channel as the archive.

### Real-Time Options Without Heavy SIEM

- **Wazuh webhooks**: Configure `ossec.conf` to POST critical alerts (level >= 10)
  to an endpoint that calls the ticketing script.
- **Hermes cron**: Schedule periodic scans that produce new CSV rows, which the
  ticketing script picks up automatically.
- **Syslog -> Logstash -> Webhook**: Forward Wazuh alerts through a lightweight
  pipeline to trigger tickets.

**Support files:**
- `scripts/deploy_rules.ps1` — Hardened custom-rules deploy (derives destination name, ID-collision check, `analysisd -t` validation, auto-rollback)
- `scripts/test_rules.sh` — Rule-firing assertion harness for `wazuh-logtest`
- `templates/custom_rules_eventchannel.xml` — Known-good custom rule skeleton for Windows event sources
- `references/custom-rules-windows-eventchannel.md` — Why `<match>` fails on eventchannel, and the four-failure debugging transcript
- `scripts/auto_ticketing.sh` — Bash ticketing script (Jira/ServiceNow/generic)
- `scripts/auto_ticketing.ps1` — PowerShell equivalent for Windows
- `scripts/purge_reports.ps1` — Deployable evidence purge script with safety checks
- `templates/scan_results.csv` — CSV template with correct columns
- `templates/roles_mapping.yml` — Known-correct roles_mapping.yml with users: fix
- `references/ticketing-mapping.md` — Complete action_taken to ticket mapping table
- `references/403-error-pattern.md` — Exact error transcripts from 403 dashboard
- `references/hermes-tool-substitution-workaround.md` — *** stripping workaround

## Pitfalls

### MSYS path translation on Windows
On Windows with git-bash/MSYS, Docker paths like `/usr/share/...` get mangled
into `C:/Program Files/Git/usr/share/...`. Always prefix docker exec with
`MSYS_NO_PATHCONV=1`.

### Special characters in passwords break shell commands
Passwords containing `*`, `$`, `(`, `)` etc. cause shell glob expansion and
syntax errors in nested `bash -c` calls. The `***` pattern in particular gets
interpreted at multiple levels. Workarounds (in preference order):

1. **Run Python inside the container** instead of complex bash. Use
   `docker exec <container> python3 -c "..."` with `subprocess.run()`.
   This avoids all shell escaping issues.
   **CRITICAL for Hermes:** The Hermes tool layer strips `***` (backtick-
   dollar-parenthesis-backtick) from ALL commands before they reach the shell
   — this includes heredocs, `-c` strings, and even files written via
   `write_file`. The Python `subprocess.run()` approach inside the container
   is the only reliable workaround. Use string concatenation in Python
   (`auth = "Authorization: Bearer " + token`) instead of f-strings or
   backtick-based substitution.

2. **Write credentials to a temp file** inside the container, then read:
   ```bash
   docker exec <container> bash -c 'curl ... > /tmp/token.txt'
   docker exec <container> bash -c 'TOKEN=*** /tmp/token.txt); curl -H "Authorization: Bearer *** ...'
   # NOTE: The TOKEN=*** approach still fails in Hermes because *** is stripped.
   # Use Python subprocess inside the container instead.
   ```

3. **Use heredoc with single-quoted delimiter** for scripts:
   ```bash
   docker exec <container> bash -c "cat > /tmp/script.py << 'PYEOF'
   ...script content...
   PYEOF
   python3 /tmp/script.py"
   # NOTE: *** in heredoc content is STILL stripped by Hermes. Use Python
   # string concatenation as the ultimate workaround.
   ```

4. **Base64-encode** the value, pass it, decode inside the container.
   Works but adds complexity — the Python subprocess approach is simpler.

### securityadmin.sh permission denied
The script is 640 owned by wazuh-indexer. Run with `bash securityadmin.sh`,
not `./securityadmin.sh`.

### securityadmin.sh flag: -nhnv not --nhnv
The hostname-verification-disable flag is `-nhnv` (single dash). Using
`--nhnv` causes `ERR: Parsing failed. Reason: Unrecognized option`.

### Certificate path
Certificates are at `/usr/share/wazuh-indexer/certs/` (root-ca.pem,
admin.pem, admin-key.pem), not under `config/` as some documentation
suggests.

### chown root:root may fail
Inside Docker containers, chown to root:root may return "Operation not
permitted". Using the container's service user (wazuh-indexer:wazuh-indexer)
is acceptable — securityadmin.sh reads the file as long as it's readable.

### Password masked in docker inspect
`docker inspect` and `env` show passwords as `***` when Docker secrets
are used. The actual credentials are in the dashboard's wazuh.yml config file.

### Docker config persistence — ossec.conf is bind-mounted
**CRITICAL:** In Wazuh Docker single-node deployments, `/var/ossec/etc/ossec.conf`
inside the manager container is often a bind mount from the Windows host.
Changes made directly inside the container WILL BE OVERWRITTEN on restart.

**Find the real source file:**
```bash
docker inspect single-node-wazuh.manager-1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
# Look for the line ending in /ossec.conf
# Typical path: C:\Users\<user>\wazuh-docker\single-node\config\wazuh_cluster\wazuh_manager.conf
```

**Correct fix workflow:**
1. Edit the HOST file (e.g., `C:\Users\searc\wazuh-docker\single-node\config\wazuh_cluster\wazuh_manager.conf`)
2. Create backup: `cp wazuh_manager.conf wazuh_manager.conf.bak.$(date +%s)`
3. Apply change: `sed -i 's/<use_password>no/<use_password>yes/' wazuh_manager.conf`
4. Restart container: `docker restart single-node-wazuh.manager-1`
5. Verify: `docker exec single-node-wazuh.manager-1 grep use_password /var/ossec/etc/ossec.conf`

This applies to ANY config change in ossec.conf (authd, remoted, syscheck, etc.).

### Authd security remediation (use_password no → yes)
The authd service on port 1515 controls agent enrollment. Default Docker
deployments often have `use_password=no`, allowing ANY agent to register.

**Check current state:**
```bash
docker exec single-node-wazuh.manager-1 grep use_password /var/ossec/etc/ossec.conf
```

**Fix (follow the bind-mount workflow above):**
1. Find the host source file via `docker inspect` (see Docker config persistence pitfall)
2. Edit: change `<use_password>no</use_password>` to `<use_password>yes</use_password>`
3. Backup and restart
4. Verify: authd must show `running` and `use_password=yes`

**Post-fix verification:**
```bash
# Check config persisted
docker exec single-node-wazuh.manager-1 grep use_password /var/ossec/etc/ossec.conf
# Check daemon running
docker exec single-node-wazuh.manager-1 /var/ossec/bin/wazuh-control status | grep authd
# Verify agents still connected via API
curl -k -H "Authorization: Bearer TOKEN" https://localhost:55000/agents
```

### Windows registry hardening (Wazuh-managed machines)
For Windows agents monitored by Wazuh, apply these registry values to
harden update behavior:
```
HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate
  DisablePauseUXAccess = 1 (DWORD)
  DeferFeatureUpdates = 1 (DWORD)
  DeferFeatureUpdatesPeriodInDays = 180 (DWORD)
```
Apply via PowerShell:
```powershell
$path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'
if (-not (Test-Path $path)) { New-Item -Path $path -Force }
Set-ItemProperty -Path $path -Name 'DisablePauseUXAccess' -Value 1 -Type DWord
Set-ItemProperty -Path $path -Name 'DeferFeatureUpdates' -Value 1 -Type DWord
Set-ItemProperty -Path $path -Name 'DeferFeatureUpdatesPeriodInDays' -Value 180 -Type DWord
```
