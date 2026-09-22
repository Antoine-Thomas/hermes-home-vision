# Process

> Source: `creative/humanizer/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

1. Read the input text carefully (use `read_file` if it's a file).
2. Identify all instances of the patterns above.
3. Rewrite each problematic section.
4. Ensure the revised text:
   - Sounds natural when read aloud
   - Varies sentence structure naturally
   - Uses specific details over vague claims
   - Maintains appropriate tone for context
   - Uses simple constructions (is/are/has) where appropriate
5. Present a draft humanized version.
6. Prompt yourself: "What makes the below so obviously AI generated?"
7. Answer briefly with the remaining tells (if any).
8. Prompt yourself: "Now make it not obviously AI generated."
9. Present the final version (revised after the audit).
10. If the text came from a file, apply the edit with `patch` (targeted) or `write_file` (full rewrite) and show the user what changed.
