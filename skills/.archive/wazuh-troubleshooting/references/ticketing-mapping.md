# Ticketing Mapping Reference — action_taken to Ticket Details

## Priority & Type Mapping

| action_taken      | Priority | Ticket Type              | Summary Template |
|-------------------|----------|--------------------------|------------------|
| isolate-host      | P0       | Incident / Containment   | ISOLATE HOST: {host} ({ip}) |
| forensics-image   | P0       | Forensic Request         | FORENSIC IMAGE: {host} |
| revoke-keys       | P1       | Credential Rotation      | REVOKE KEYS: {host} |
| rotate-passwords  | P1       | Credential Rotation      | ROTATE PASSWORDS: {host} |
| monitor           | P2       | Investigation            | MONITOR: {host} - enhanced surveillance |
| clean-up          | P2       | Remediation              | CLEANUP: {host} - malware remediation |
| notify-owner      | P3       | Notification             | NOTIFY: {host} owner |

## Description Template (all actions)

```
Action: {action}
Host: {host} ({ip})
Date: {date_scan} | OS: {os} | Role: {role}
Connections external: {connections_external}
Wazuh alerts recent: {alerts_wazuh_recentes}
Recommendation: {security_recommendation}
Evidence: /tmp/{host}_evidence.tar.gz.gpg
Notes: {notes}
```

## Jira Payload

```json
{
  "fields": {
    "project": {"key": "SEC"},
    "summary": "ISOLATE HOST: omaths (192.168.1.11) - suspicious connections",
    "description": "Action: isolate-host\nHost: omaths\nIP: 192.168.1.11\nEvidence: /tmp/omaths_evidence.tar.gpg\nRecommended: Isolate VLAN; revoke wazuh-wui creds",
    "issuetype": {"name": "Incident"},
    "priority": {"name": "Highest"}
  }
}
```

Priority mapping to Jira: P0=Highest, P1=High, P2=Medium, P3=Low.

## ServiceNow Payload

```json
{
  "short_description": "ISOLATE HOST omaths 192.168.1.11",
  "description": "Action: isolate-host\nEvidence: s3://forensic-bucket/omaths_evidence.tar.gpg\nImpact: potential data exfiltration",
  "urgency": "1",
  "assignment_group": "SOC"
}
```

Urgency mapping: P0=1, P1=2, P2-P3=3.

## Generic Webhook Payload

```json
{
  "action": "isolate-host",
  "host": "omaths",
  "ip": "192.168.1.11",
  "summary": "ISOLATE HOST: omaths (192.168.1.11)",
  "description": "Action: isolate-host\nHost: omaths\nIP: 192.168.1.11\n...",
  "priority": "P0",
  "timestamp": "2026-07-19T19:43:00Z"
}
```

## Multi-Action Rows

When a host requires multiple actions, separate them with semicolons:
```
action_taken: "isolate-host;revoke-keys;notify-owner"
```
Each action generates a separate ticket.

## Evidence Packaging

After scan, encrypt evidence before referencing in tickets:
```bash
tar czf /tmp/${HOST}_evidence.tar.gz /tmp/${HOST}_*.txt /tmp/${HOST}_capture.pcap
gpg --symmetric --cipher-algo AES256 --passphrase-file /secure/passphrase.txt \
  -o /tmp/${HOST}_evidence.tar.gz.gpg /tmp/${HOST}_evidence.tar.gz
```
Reference the `.gpg` path in the ticket evidence field. Never transmit the passphrase alongside the archive.
