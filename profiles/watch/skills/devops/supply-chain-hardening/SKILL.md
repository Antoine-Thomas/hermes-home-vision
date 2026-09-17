---
name: supply-chain-hardening
description: "Harden npm/pnpm projects against supply chain attacks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [supply-chain, pnpm, npm, dependencies, security, lockfile]
    category: devops
    created: "2026-08-26"
---

# Supply Chain Hardening for Node Projects

Preventive configuration that stops a compromised dependency from executing on
the machine: release-age quarantine, lockfile trust, build-script approval,
blocking exotic sources, and a guard against AI agents bypassing all of it.

This is the *prevention* side. Detection/alerting on dependency events belongs
to `wazuh-troubleshooting` ("Authoring Custom Detection Rules"); after-the-fact
vulnerability scanning belongs to `security-audit`.

## When to Use — quand l'utiliser

- "sécurise mes projets", "supply chain", "protège mes dépendances"
- Setting up a new Node project and wanting safe defaults from the start
- After news of a compromised npm package, to add a quarantine window
- A dependency's `postinstall` needs approving/blocking
- Wanting to force AI coding agents (Claude Code, Codex, Cursor) to use a
  hardened install command instead of bare `npm install`

Do NOT use for: auditing what is already installed (that's `security-audit`),
or writing the Wazuh rules that alert on findings (that's `wazuh-troubleshooting`).

## The one thing to check first: version gates

**pnpm silently ignores settings it does not know.** A config that looks
hardened can be half-inert. Verified on 2026-08:

| Setting | Added in | Default | Notes |
|---|---|---|---|
| `minimumReleaseAge` | v10.16.0 | `1440` since v11, `0` before | minutes |
| `blockExoticSubdeps` | v10.26.0 | `true` | already on in v11 |
| `strictDepBuilds` | v10.3.0 | `true` | already on |
| `dangerouslyAllowAllBuilds` | v10.9.0 | `false` | already correct |
| `allowBuilds` | v10.26.0 | `{}` | replaces `onlyBuiltDependencies` |
| `minimumReleaseAgeStrict` | **v11.0.0** | true if age set | inert on v10 |
| `minimumReleaseAgeIgnoreMissingTime` | **v11.0.0** | `true` | inert on v10 |
| `trustPolicy` | **v11** | — | inert on v10 |
| `trustLockfile` | **v11.3.0** | `false` | inert on v10 |

So on pnpm 10.x, **four** of the commonly-recommended settings do nothing.
Check `pnpm --version` before writing the file and say plainly which lines are
inert if the version is too old.

**pnpm 11 requires Node >= 22.13.** Installing pnpm 11 on older Node yields a
hard refusal at every invocation:
`ERROR: This version of pnpm requires at least Node.js v22.13`.
With `nvm4w`, global npm packages are per-Node-version, so after
`nvm use <newer>` you must reinstall pnpm. Switching Node is reversible in one
command (`nvm use <previous>`) — say so when proposing it, it is what makes the
change acceptable.

## `audit:` is NOT a pnpm-workspace.yaml setting

A frequently-copied snippet adds:

```yaml
audit:
  level: high      # does nothing
```

There is no `audit`/`auditLevel` setting in the pnpm settings reference. The
audit threshold is a **CLI flag**, confirmed by `pnpm audit --help`:

```
--audit-level <severity>   info|low|moderate|high|critical. Default: low
```

Put it in `package.json` scripts instead:

```json
"scripts": { "audit": "pnpm audit --audit-level=high" }
```

## How to verify a setting is actually recognised

pnpm 11 validates **top-level** keys and warns on unknown ones. Exploit that as
an oracle — add a deliberately bogus key and see whether the tool complains:

```bash
printf 'minimumReleaseAge: 10080\nDELIBERATELY_BOGUS_KEY: 42\n' > pnpm-workspace.yaml
pnpm install
# [WARN] The following settings in pnpm-workspace.yaml are not recognized by
#        this version of pnpm and were ignored: "DELIBERATELY_BOGUS_KEY".
```

If your real keys are absent from that warning list, they are recognised.

**Caveat:** validation is top-level only. A bogus *nested* key (`audit.level`,
`foo.bar`) produces **no warning at all**, so silence about a nested key proves
nothing. Neither does `pnpm config get <key>`, which just echoes the YAML back.
For nested settings, check the docs.

## Prove the quarantine actually blocks

Do not ship this config without demonstrating it works. Pick a package whose
latest release is younger than the quarantine window:

```bash
python -c "
import json,urllib.request,datetime
d=json.load(urllib.request.urlopen('https://registry.npmjs.org/eslint'))
lt=d['dist-tags']['latest']; t=d['time'][lt]
dt=datetime.datetime.fromisoformat(t.replace('Z','+00:00'))
print(lt,(datetime.datetime.now(datetime.timezone.utc)-dt).days,'days old')"
```

Two expected outcomes, both worth showing the user:

```bash
pnpm add -D eslint            # -> resolves to an OLDER mature version, silently
pnpm add -D eslint@<fresh>    # -> ERR_PNPM_NO_MATURE_MATCHING_VERSION
```

The second is the hard proof. `trustLockfile: false` also announces itself on
every install with `✓ Lockfile passes supply-chain policies`.

Starter config: `templates/pnpm-workspace.yaml` (annotated, with version gates
and the reason for each line).

## Socket Firewall is a wrapper, not a hook

A widely-copied recipe suggests:

```json
"scripts": { "preinstall": "socket firewall" }   // broken by design
```

Two independent reasons it cannot work:

1. `preinstall` runs **before** dependencies are installed, so a `socket`
   devDependency does not exist yet on a fresh clone.
2. `sfw` describes itself as a *"Socket Firewall wrapper that verifies latest
   release and then runs npm with original args"* — it **wraps** the install
   command, it is not a lifecycle hook.

Correct usage is to wrap:

```json
"scripts": { "install:safe": "sfw pnpm install --frozen-lockfile" }
```

Package identities, verified against the registry:
- `socket` — official Socket.dev CLI (`github.com/SocketDev/socket-cli`)
- `sfw` — the firewall wrapper (`github.com/SocketDev/sfw-installer`)

Always confirm a security package's real identity on the registry before adding
it. Installing a plausibly-named package on faith is itself the attack.

## Build scripts

`strictDepBuilds: true` + `dangerouslyAllowAllBuilds: false` means no dependency
build script runs until reviewed. Approve interactively:

```bash
pnpm approve-builds          # writes the allowBuilds map
pnpm approve-builds --all    # only when you have actually reviewed them
```

Trace where a suspicious package came from before deciding:

```bash
pnpm why <package>
```

## Guarding against AI agents

Agents habitually run `npm install`, bypassing every pnpm setting above (npm
reads none of them). Two layers:

1. `packageManager` + `engines` in `package.json` so the wrong tool is at least
   visible:
   ```json
   "packageManager": "pnpm@11.24.0",
   "engines": { "node": ">=22.13" }
   ```
2. A wrapper on PATH ahead of the real `npm` that refuses (or rewrites to
   `pnpm install --frozen-lockfile`) and emits an event for detection. Route
   that event through the Windows event log so Wazuh sees it — see
   `wazuh-troubleshooting` → "Authoring Custom Detection Rules".

## Non-interactive / CI

Always `--frozen-lockfile` outside an interactive shell, so a tampered or stale
lockfile fails the build instead of being silently rewritten:

```json
"scripts": { "ci": "pnpm install --frozen-lockfile" }
```

## Wazuh detection — match the decoded FIELDS, not full_log

This is the pitfall that costs the most time, verified on Wazuh 4.7.3 the
26/08/2026.

Have the collector (PowerShell/Python) write findings to the **Windows event
log** with a dedicated source, and let the already-active `eventchannel`
localfile carry them. Flat `<localfile>` files are unreliable on a Windows
agent; the event log is not.

```powershell
New-EventLog -LogName Application -Source SupplyChainGuard   # admin, once
Write-EventLog -LogName Application -Source SupplyChainGuard -EventId 9003 `
               -EntryType Error -Message "SUPPLYCHAIN EXOTIC_SOURCE pkg=x spec=git+https://..."
```

An eventchannel event is **decoded**: the text is NOT in `full_log`, it lives in
fields. Inspect a real alert before writing any rule:

```bash
docker exec <manager> sh -c "grep -h SUPPLYCHAIN /var/ossec/logs/alerts/alerts.json | tail -1"
#   data.win.system.providerName = SupplyChainGuard
#   data.win.eventdata.data      = SUPPLYCHAIN <CODE> key=value ...
```

A `<match>` therefore sees nothing, and a BUILT-IN rule wins instead —
typically `60602` "Windows application error event", level 9. Symptom: the
events clearly arrive, but never with your rule id. Correct structure:

```xml
<rule id="100199" level="0">
  <if_group>windows</if_group>
  <field name="win.system.providerName">^SupplyChainGuard$</field>
  <description>parent, no alert of its own</description>
</rule>

<rule id="100201" level="12">
  <if_sid>100199</if_sid>
  <field name="win.eventdata.data">SUPPLYCHAIN SCRIPT_PIPE_SHELL</field>
  <description>postinstall piping a download into a shell</description>
</rule>
```

### Keep complex patterns OUT of the rules

Wazuh 4.7.3 **rejects `<pcre2>` in rules** (`Invalid option 'pcre2'`), and
`<regex>` uses OS_Regex: no negated classes `[^...]`, no optional groups
`( )?`, no `{n,m}`.

So do the real pattern matching (`curl|bash`, `git+https`) in the collector and
emit a stable marker the rule matches literally. Rules stay readable, produce
no false positives, and the detection logic becomes testable outside Wazuh.

### Deploy rules safely

```powershell
[xml]$null = Get-Content -Raw $RulesFile        # 1. well-formed XML
# 2. check ID collisions against the other files in /var/ossec/etc/rules/
#    (two files defining the same id = silent overwrite)
# 3. timestamped backup, then copy.
#    DESTINATION FILENAME = the SOURCE filename, never a hard-coded one
docker cp $RulesFile "${C}:/var/ossec/etc/rules/$(Split-Path -Leaf $RulesFile)"
docker exec $C /var/ossec/bin/wazuh-analysisd -t     # 4. exit 0 = valid
docker exec $C /var/ossec/bin/wazuh-control restart
docker exec $C /var/ossec/bin/wazuh-control status | grep analysisd
```

`wazuh-logtest` has **no `-t` option** (`unrecognized arguments: -t`). The
config test is `wazuh-analysisd -t`: exit 0, no output. Always plan the
rollback — remove the file and restore the backup on failure, because a
manager with `analysisd` stopped is blind.

Test a rule without deploying anything:

```bash
echo "SUPPLYCHAIN AUDIT_VULN pkg=x severity=critical" | \
  docker exec -i <manager> /var/ossec/bin/wazuh-logtest
# expect:  id: '100200'   level: '10'   then "Alert to be generated."
```

## Pitfalls

- **Wazuh: a `<match>` on an eventchannel event silently matches nothing** —
  use `<field name="win.eventdata.data">`. If alerts show rule `60602`, this is
  the cause. See the Wazuh section above.
- **An XML comment cannot contain `--`.** Writing `--frozen-lockfile` inside
  `<!-- -->` breaks the file (`An XML comment cannot contain '--'`). Common when
  documenting CLI flags in a rules file.
- **Wazuh supports only ONE level of wildcard** in `<localfile>` paths on
  Windows: `projects\*\x.log` works, `projects\**\x.log` does not.
- **An alert threshold hides low-level rules.** If the alert bridge filters on
  `level >= 10`, rules at level 7 and 3 exist but never notify. Say so
  explicitly instead of letting the user believe everything is forwarded.
- **Do not assume a copied config is valid.** Settings from blog posts and
  videos are often from a newer version than installed, or invented. Verify
  with the bogus-key probe, and state which lines are inert.
- **Several recommended settings are already the default** in pnpm 11
  (`blockExoticSubdeps`, `trustLockfile`, `strictDepBuilds`,
  `dangerouslyAllowAllBuilds`). Writing them explicitly is still worthwhile as
  documented intent and defence against a default change upstream — but do not
  present them to the user as new protection they just gained.
- **`minimumReleaseAgeIgnoreMissingTime: false` is stricter than default.** It
  will break installs from private registries/mirrors that omit the `time`
  field. Flag this when the user has an internal registry.
- **A 7-day quarantine delays legitimate security patches too.** Mention the
  trade-off; `minimumReleaseAgeExclude` / `trustPolicyExclude` exist for
  packages that must stay current.
- **Do not run a "fix" across all projects before proving it on one.** Build a
  demo project, prove blocking and detection there, then generalise.
- **Fabricated test fixtures are not test data.** Before building anything on a
  folder of sample files, check whether the contents are real — RFC 2606
  reserved domains (`example.com`, `example.org`, `test`, `invalid`) cannot
  receive mail and generally mark a fixture you or someone else generated.

## Verification

```bash
pnpm --version                       # >= 11.3 for the full setting set
node --version                       # >= 22.13 for pnpm 11
pnpm install                         # no [WARN] about unrecognized settings
pnpm add -D <pkg>@<version-from-today>   # must fail: ERR_PNPM_NO_MATURE_MATCHING_VERSION
pnpm audit --audit-level=high        # threshold as a FLAG, not YAML

# Wazuh side
docker exec <manager> /var/ossec/bin/wazuh-analysisd -t            # exit 0
docker exec <manager> /var/ossec/bin/wazuh-control status | grep analysisd
docker exec <manager> sh -c "grep -h SUPPLYCHAIN /var/ossec/logs/alerts/alerts.json | tail -1"
#   check rule.id: if it is 60602, the rule is matching full_log instead of
#   the win.* fields — see the Wazuh section.
```

## Reference implementation

A complete, tested implementation lives at
`~/AppData/Local/hermes/data/supply-chain-security/` :
`bin/securite-projet.ps1` (idempotent orchestrator), `bin/pnpm-guard.ps1`
(AI-agent shim, Block/Translate/Report), `bin/security_audit_deps.ps1` (daily
audit emitting the markers), `wazuh/searc_supply_chain_rules.xml` (rules
100198-100206), `wazuh/deploy_rules.ps1` (validation + rollback), and
`README_securite.md` (full French documentation including rollback).
