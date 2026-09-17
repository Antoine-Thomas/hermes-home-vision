---
name: systematic-debugging
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, plan, subagent-driven-development]
---

# Systematic Debugging


## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## References

Details in `references/` (split to meet max 200 lines):

| Section | File |
|---------|------|
| The Iron Law | `references/the-iron-law.md` |
| The Feedback Loop Rule | `references/the-feedback-loop-rule.md` |
| When to Use | `references/when-to-use.md` |
| The Four Phases | `references/the-four-phases.md` |
| Phase 1: Root Cause Investigation | `references/phase-1-root-cause-investigation.md` |
| Phase 2: Pattern Analysis | `references/phase-2-pattern-analysis.md` |
| Phase 3: Hypothesis and Testing | `references/phase-3-hypothesis-and-testing.md` |
| Phase 4: Implementation | `references/phase-4-implementation.md` |
| Red Flags — STOP and Follow Process | `references/red-flags-stop-and-follow-process.md` |
| Common Rationalizations | `references/common-rationalizations.md` |
| Quick Reference | `references/quick-reference.md` |
| Hermes Agent Integration | `references/hermes-agent-integration.md` |
| Real-World Impact | `references/real-world-impact.md` |

