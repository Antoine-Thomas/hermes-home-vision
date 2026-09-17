#!/bin/sh
# Assert that each sample log line fires the expected Wazuh rule id.
#
# Usage:
#   docker cp test_rules.sh <manager>:/tmp/
#   MSYS_NO_PATHCONV=1 docker exec <manager> sh /tmp/test_rules.sh
#
# WHY THE PARSING LOOKS ODD
#   wazuh-logtest prints  "id: '100200'"  and  "level: '10'"
#   NOT                   "Rule id: ..."
#   Grepping for the wrong label makes a perfectly working rule look dead.
#
# LIMITATION — read this before trusting a pass/fail
#   logtest injects the line as a RAW log, so it exercises <match> and <regex>
#   rules only. It does NOT run the Windows eventchannel decoder, so rules built
#   on <field name="win.eventdata.data"> CANNOT be validated here. For those,
#   trigger the real emitter and inspect alerts.json:
#     grep -h '<MARKER>' /var/ossec/logs/alerts/alerts.json | tail -3
#   then confirm rule.id is yours and not 60602.

LOGTEST=/var/ossec/bin/wazuh-logtest
pass=0
fail=0

check() {
  expected="$1"
  line="$2"
  res=$(echo "$line" | $LOGTEST 2>&1)
  id=$(echo "$res"  | grep -o "id: '[0-9]*'"    | head -1 | grep -o "[0-9]*")
  lvl=$(echo "$res" | grep -o "level: '[0-9]*'" | head -1 | grep -o "[0-9]*")
  if [ "$id" = "$expected" ]; then
    pass=$((pass+1))
    printf "  PASS  %-7s level %-2s  %s\n" "$id" "$lvl" "$(echo "$line" | cut -c1-46)"
  else
    fail=$((fail+1))
    printf "  FAIL  expected %-7s got '%s'  %s\n" "$expected" "$id" "$(echo "$line" | cut -c1-46)"
  fi
}

echo "RULE FIRING TESTS"

# --- edit below: one check per rule -------------------------------------
# check <expected_rule_id> "<sample log line>"
check 100198 "MYMARKER CRITICAL_CODE project=demo detail=example"
# check 100200 "MYMARKER HIGH_CODE ..."
# check 100202 "MYMARKER MEDIUM_CODE ..."
# -----------------------------------------------------------------------

echo ""
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
