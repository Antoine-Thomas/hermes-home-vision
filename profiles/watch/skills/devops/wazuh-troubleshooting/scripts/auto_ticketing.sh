#!/usr/bin/env bash
#=============================================================================
# Hermes Auto-Ticketing Script - Wazuh SIEM connector
# Lit scan_results.csv, mappe action_taken vers tickets (Jira/ServiceNow/Webhook)
# Usage: ./auto_ticketing.sh <csv_path> [--dry-run]
#=============================================================================
set -euo pipefail

CSV="${1:-scan_results.csv}"
DRY_RUN="${2:-}"
WEBHOOK_JIRA="${WEBHOOK_JIRA:-https://jira.example.com/rest/api/2/issue}"
WEBHOOK_SNOW="${WEBHOOK_SNOW:-https://servicenow.example.com/api/now/table/incident}"
AUTH="${AU...N}"
TICKET_SYSTEM="${TICKET_SYSTEM:-jira}"

#=============================================================================
# Mapping action_taken -> ticket
#=============================================================================
declare -A PRIORITY_MAP=(
    ["isolate-host"]="P0"
    ["forensics-image"]="P0"
    ["revoke-keys"]="P1"
    ["rotate-passwords"]="P1"
    ["monitor"]="P2"
    ["clean-up"]="P2"
    ["notify-owner"]="P3"
)

declare -A TYPE_MAP=(
    ["isolate-host"]="Incident"
    ["forensics-image"]="Forensic Request"
    ["revoke-keys"]="Credential Rotation"
    ["rotate-passwords"]="Credential Rotation"
    ["monitor"]="Investigation"
    ["clean-up"]="Remediation"
    ["notify-owner"]="Notification"
)

declare -A SUMMARY_TEMPLATE=(
    ["isolate-host"]="ISOLATE HOST: HOSTNAME (IP)"
    ["forensics-image"]="FORENSIC IMAGE: HOSTNAME"
    ["revoke-keys"]="REVOKE KEYS: HOSTNAME"
    ["rotate-passwords"]="ROTATE PASSWORDS: HOSTNAME"
    ["monitor"]="MONITOR: HOSTNAME - enhanced surveillance"
    ["clean-up"]="CLEANUP: HOSTNAME - malware remediation"
    ["notify-owner"]="NOTIFY: HOSTNAME owner"
)

#=============================================================================
# Ticket creation functions
#=============================================================================
create_ticket_jira() {
    local summary="$1" desc="$2" priority="$3" issue_type="$4"
    local payload
    payload=$(jq -n \
        --arg s "$summary" \
        --arg d "$desc" \
        --arg p "$priority" \
        --arg t "$issue_type" \
        '{fields:{project:{key:"SEC"},summary:$s,description:$d,issuetype:{name:$t},priority:{name:$p}}}')
    if [ "$DRY_RUN" = "--dry-run" ]; then
        echo "[DRY-RUN] Jira: $summary"
        echo "$payload" | jq .
        return 0
    fi
    curl -s -u "$AUTH" -H "Content-Type: application/json" \
        -X POST --data "$payload" "$WEBHOOK_JIRA" | jq -r '.key // .errorMessages[0]'
}

create_ticket_snow() {
    local summary="$1" desc="$2" priority="$3"
    local urgency
    case "$priority" in P0) urgency=1 ;; P1) urgency=2 ;; *) urgency=3 ;; esac
    local payload
    payload=$(jq -n \
        --arg s "$summary" \
        --arg d "$desc" \
        --arg u "$urgency" \
        '{short_description:$s,description:$d,urgency:$u,assignment_group:"SOC"}')
    if [ "$DRY_RUN" = "--dry-run" ]; then
        echo "[DRY-RUN] ServiceNow: $summary"
        echo "$payload" | jq .
        return 0
    fi
    curl -s -u "$AUTH" -H "Content-Type: application/json" \
        -X POST --data "$payload" "$WEBHOOK_SNOW" | jq -r '.result.number // .error'
}

create_ticket_generic() {
    local summary="$1" desc="$2" priority="$3" action="$4"
    local payload
    payload=$(jq -n \
        --arg action "$action" \
        --arg host "$HOST" \
        --arg ip "$IP" \
        --arg s "$summary" \
        --arg d "$desc" \
        --arg p "$priority" \
        '{action:$action,host:$host,ip:$ip,summary:$s,description:$d,priority:$p,timestamp:now}')
    if [ "$DRY_RUN" = "--dry-run" ]; then
        echo "[DRY-RUN] Generic webhook: $summary"
        echo "$payload" | jq .
        return 0
    fi
    curl -s -H "Content-Type: application/json" \
        -X POST --data "$payload" "${WEBHOOK_GENERIC:-http://localhost:9999/webhook}"
}

#=============================================================================
# CSV Processing
#=============================================================================
echo "=== Hermes Auto-Ticketing ==="
echo "CSV: $CSV | System: $TICKET_SYSTEM | Dry-run: ${DRY_RUN:-OFF}"
echo ""

TICKET_COUNT=0
while IFS=, read -r host ip date_scan os role conn_ext conn_int procs hashes files agents_wazuh alerts filebeat recommendation action_taken notes; do
    [[ "$host" == "host" ]] && continue
    export HOST="$host" IP="$ip"
    IFS=';' read -ra actions <<< "$action_taken"
    for act in "${actions[@]}"; do
        act=$(echo "$act" | xargs)
        [[ -z "$act" ]] && continue
        priority="${PRIORITY_MAP[$act]:-P3}"
        issue_type="${TYPE_MAP[$act]:-Task}"
        summary_tpl="${SUMMARY_TEMPLATE[$act]:-$act: HOSTNAME}"
        summary=$(echo "$summary_tpl" | sed "s/HOSTNAME/$host/g; s/IP/$ip/g")
        desc="Action: $act
Host: $host ($ip)
Date: $date_scan | OS: $os | Role: $role
Connections external: $conn_ext
Wazuh alerts recent: $alerts
Recommendation: $recommendation
Evidence: /tmp/${host}_evidence.tar.gz.gpg
Notes: $notes"
        echo "-> $act | Priority: $priority | Type: $issue_type"
        case "$TICKET_SYSTEM" in
            jira)    create_ticket_jira "$summary" "$desc" "$priority" "$issue_type" ;;
            snow)    create_ticket_snow "$summary" "$desc" "$priority" ;;
            generic) create_ticket_generic "$summary" "$desc" "$priority" "$act" ;;
            *)       echo "ERROR: Unknown TICKET_SYSTEM=$TICKET_SYSTEM" >&2 ;;
        esac
        TICKET_COUNT=$((TICKET_COUNT + 1))
        echo ""
    done
done < "$CSV"

echo "=== Done: $TICKET_COUNT tickets processed ==="
