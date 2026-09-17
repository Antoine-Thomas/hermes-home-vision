#!/usr/bin/env python3
"""Verify the log_monitor.py EXCLUDE regex still does its job:
- SPAM lines (false positives) must classify to None (excluded).
- GENUINE lines (attack/auth/crash) must still fire a rule.

Run from anywhere. Extend SPAM/GENUINE with new samples before/after editing EXCLUDE.
"""
import sys
from pathlib import Path

MONITORS = Path.home() / "AppData" / "Local" / "hermes" / "data" / "security-monitoring" / "monitors"
sys.path.insert(0, str(MONITORS))
import log_monitor as lm  # noqa: E402

SPAM = [
    "ERROR email: [Email] IMAP fetch error: [Errno 11001] getaddrinfo",
    "ERROR gateway.run: Fatal email adapter error (email_imap_fetch_failed): [Errno 11001]",
    "ERROR telegram.ext: Network Retry Loop (Bootstrap delete Webhook): Failed run 0",
    "Traceback (most recent call last):",
    "with map_exceptions(exc_map):",
    "self.gen.throw(typ, value, traceback)",
    "The above exception was the direct cause of the following exception:",
]
GENUINE = [
    "ERROR api: 401 unauthorized access detected",
    "CRITICAL server: out of memory killer",
    "ERROR db: union select * from users",
]


def classify(line):
    if lm.EXCLUDE.search(line):
        return None
    for level, regex, group, desc in lm.RULES:
        if regex.search(line):
            return (level, group, desc)
    return None


ok = True
for line in SPAM:
    r = classify(line)
    status = "EXCLUDED ✓" if r is None else f"STILL FIRES ✗ -> {r}"
    print(f"{status:32} {line[:60]}")
    ok = ok and (r is None)
for line in GENUINE:
    r = classify(line)
    status = "DETECTED ✓" if r else "MISSED ✗"
    print(f"{status:32} {line[:60]}")
    ok = ok and bool(r)

sys.exit(0 if ok else 1)
