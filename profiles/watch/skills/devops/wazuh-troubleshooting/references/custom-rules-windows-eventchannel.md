# Custom rules for Windows eventchannel — real debugging transcript

Wazuh 4.7.3, single-node Docker on Windows 11, agent `OMATHS`.
Goal: alert on supply-chain markers emitted by a PowerShell collector.

This is the sequence of four failed deploys and what each taught, so a future
session skips straight to the working shape.

## Attempt 1 — XML rejected before it ever reached Wazuh

Rule file contained a comment reading `MOYEN : install sans --frozen-lockfile`.

```
Cannot convert value "..." to type "System.Xml.XmlDocument".
Error: "An XML comment cannot contain '--', and '-' cannot be the last
character. Line 63, position 44."
```

XML forbids `--` inside comments. `--` in element text is fine. Caught by a
host-side `[xml]$null = Get-Content -Raw $file` pre-check, before any copy.

## Attempt 2 — the validation step itself was wrong

The deploy script "validated" with `wazuh-logtest -t`:

```
usage: wazuh_logtest.py [-h] [-V] [-d] [-U rule:alert:decoder] [-l location] [-q] [-v]
wazuh_logtest.py: error: unrecognized arguments: -t
```

The script grepped the output for `error` and rolled back a *valid* deployment.
Two lessons: `wazuh-logtest` has no `-t`, and a validator must key off the
**exit code**, not a substring of stderr. Correct binary:

```bash
docker exec <manager> /var/ossec/bin/wazuh-analysisd -t   # exit 0, silent = OK
```

## Attempt 3 — OS_Regex is not PCRE

```xml
<regex>(curl|wget|iwr)[^|]*\|\s*(ba|z|d)?sh</regex>
```
```
ERROR: (5107): Syntax error on tag 'regex' in rule 100211
CRITICAL: (1220): Error loading the rules: 'etc/rules/searc_supply_chain_rules.xml'
```

`<regex>` uses OS_Regex: no negated character classes, no optional groups, no
`{n,m}`. Switching to `<pcre2>` failed too:

```
ERROR: Invalid option 'pcre2' for rule '100211'
```

`pcre2` is not accepted in **rules** on 4.7.3. Resolution: delete the
regex-heavy rule entirely and move that pattern recognition into the PowerShell
collector, which emits a literal marker instead.

## Attempt 4 — rules loaded, fired... the wrong one

Deploy succeeded, `analysisd` running, and `wazuh-logtest` confirmed all seven
rules matched sample lines. But real events from the agent produced:

```
ALERTE Wazuh : rule=60602 level=9  Windows application error event.
   agent : OMATHS | full_log :
```

`full_log` is **empty**. The Windows decoder had parsed everything into fields.
Dumping the alert JSON and searching for the marker showed where it actually lives:

```
data.win.system.providerName               SupplyChainGuard
data.win.system.message                    "SUPPLYCHAIN SCRIPT_PIPE_SHELL cmd=curl ... | bash ..."
data.win.eventdata.data                    SUPPLYCHAIN SCRIPT_PIPE_SHELL cmd=curl ... | bash ...
```

So `<match>` had nothing to match, the rules never engaged, and the generic
built-in Windows rule won.

### Diagnostic worth reusing

```bash
docker exec <manager> sh -c \
  "grep -h '<MARKER>' /var/ossec/logs/alerts/alerts.json | tail -1" \
| python -c "
import sys,json
a=json.loads(sys.stdin.read())
def walk(o,p=''):
    if isinstance(o,dict):
        for k,v in o.items(): walk(v,p+'.'+k if p else k)
    elif isinstance(o,list):
        for i,v in enumerate(o): walk(v,'%s[%d]'%(p,i))
    else:
        if '<MARKER>' in str(o): print('%-42s %s'%(p,str(o)[:110]))
walk(a)
"
```

Prints every JSON path containing your marker — i.e. exactly which field name to
put in `<field name="...">`. Do this **first** next time instead of guessing.

## Working shape

```xml
<rule id="100199" level="0">
  <if_group>windows</if_group>
  <field name="win.system.providerName">^SupplyChainGuard$</field>
  <description>parent, no alert</description>
</rule>

<rule id="100201" level="12">
  <if_sid>100199</if_sid>
  <field name="win.eventdata.data">SUPPLYCHAIN SCRIPT_PIPE_SHELL</field>
  <description>CRITICAL: install script piping a download into a shell</description>
  <group>supply_chain,malicious_script,</group>
</rule>
```

Plus one fallback for the flat-file transport, so a marker arriving by syslog
still raises something rather than nothing:

```xml
<rule id="100198" level="10">
  <match>SUPPLYCHAIN </match>
  <description>supply chain event seen in a log file (fallback path)</description>
</rule>
```

## Verified level mapping

Requested severity wording → Wazuh level, confirmed firing via logtest:

| Wording  | Level |
|----------|-------|
| CRITIQUE | 12    |
| ELEVE    | 10    |
| MOYEN    | 7     |
| INFO     | 3     |

## Windows agent: eventchannel vs flat localfile

The agent already ships `Application`, `Security`, `System` as
`<log_format>eventchannel</log_format>`. Routing your own events through
`Write-EventLog` with a dedicated source reuses that working pipe and needs **no
ossec.conf change on the agent at all** — which also means no agent restart and
no risk to existing monitoring. Prefer it over adding flat-file `<localfile>`
entries, which on this host have proven unreliable.
