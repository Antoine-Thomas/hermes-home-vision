# Pitfalls

> Source: software-development/simplify-code/SKILL.md — split 2026-09-10.

- **Don't fan out wider than 4.** More reviewers means more cost and more
  conflicting suggestions to reconcile, not better coverage. The four
  categories cover the space.
- **Give the WHOLE diff to each reviewer.** Splitting the diff across reviewers
  defeats the design — cross-file duplication and N+1s only show up with the
  full picture.
- **Reviewers search, they don't guess.** A reuse finding with no pointer to
  the existing utility ("there's probably a helper for this") is noise. Require
  `file:line` evidence; drop findings that lack it.
- **Apply ≠ rewrite.** This is cleanup of the user's recent changes, not a
  license to refactor the whole module. Keep edits scoped to what the diff
  touched plus the minimal surrounding change a fix requires. Altitude
  findings are the exception that proves the rule: when the right fix is
  deeper than the diff, FLAG it — don't unilaterally rebuild the shared
  mechanism inside a cleanup pass.
- **Don't drift into bug-hunting.** If a reviewer surfaces a genuine
  correctness bug, report it prominently — but as a separate "found a bug"
  note, not folded into cleanup fixes. Correctness review is a different
  pass with different verification standards.
- **Respect project conventions.** If the repo has AGENTS.md / CLAUDE.md /
  HERMES.md or a linter config, fold those rules into the reviewer prompts so
  suggestions match house style instead of fighting it.
- **Large diffs blow context.** If the diff is huge, scope it down before
  delegating — four subagents each carrying a 5000-line diff is expensive and
  may truncate.
- **Over-trusting dead code tools.** `knip`, `ts-prune`, and `depcheck` flag
  exports that ARE used dynamically (string-based imports, reflection). Always
  grep for the symbol name before removing — a clean tool report is not proof.
- **Renaming without checking public contracts.** Export names, API route
  paths, DB column names, and config keys are contracts — even if the name is
  bad, renaming breaks consumers. Tag public-contract changes as RISKY; never
  auto-rename them.
- **Removing "unnecessary" error handling.** An empty catch block or ignored
  error might be intentional — the error is expected and benign in that
  context. Flag it, don't remove it; let the human decide.
- **Not every special case is a band-aid.** Compat shims, staged migrations,
  and isolation layers around vendored code look like altitude violations but
  are deliberate design. Check `git blame` and surrounding comments before
  flagging; when the intent is unclear, mark `confidence: low`.
