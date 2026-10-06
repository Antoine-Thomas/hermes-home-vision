# Phase 3: Hypothesis and Testing

> Source: software-development/systematic-debugging/SKILL.md — split 2026-09-10.

**Scientific method:**

### 1. Form Ranked Falsifiable Hypotheses

- Generate 3–5 plausible hypotheses before testing any single one.
- Rank them by likelihood and cheapness to falsify.
- State the prediction each hypothesis makes: "If X is the cause, then changing or observing Y should make Z happen."
- Discard or sharpen any hypothesis that does not make a testable prediction.

If the user is present, show the ranked list before testing. They may have domain knowledge that instantly re-ranks it. If the user is AFK, proceed with your ranking.

### 2. Test Minimally

- Test the highest-ranked hypothesis with the smallest possible probe.
- Change one variable at a time.
- Don't fix multiple things at once.
- Prefer debugger/REPL inspection when available; one breakpoint beats ten logs.
- If you add logs, tag every temporary line with a unique prefix such as `[DEBUG-a4f2]` so cleanup is a single search.

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---
