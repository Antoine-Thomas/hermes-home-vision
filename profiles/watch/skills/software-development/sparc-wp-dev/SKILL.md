---
name: sparc-wp-dev
description: "Use when developing a WordPress feature with SPARC workflow."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wordpress, methodology, sparc, development, planning]
---

# SPARC WordPress Development

## When to Use
- Building or changing a WordPress feature (theme template, plugin, CPT, block, AJAX).
- Transposes Ruflo's SPARC methodology to WordPress development.

## The SPARC Loop
Run these five phases in order; only write production code in the Refinement phase.

1. **S — Specification.** Write the feature spec: what it does, why, acceptance criteria, scope (which files to touch). Confirm scope before coding.
2. **P — Pseudocode.** Sketch the logic in plain language/pseudocode. Identify WordPress hooks (`add_action`, `add_filter`), template parts, and data flow.
3. **A — Architecture.** Map to WordPress primitives: template hierarchy, CPTs/taxonomies, shortcodes, AJAX (`admin-ajax.php` / REST), options vs. meta, enqueueing, nonces. Decide theme vs. plugin placement.
4. **R — Refinement.** Implement, then self-review: run `code-review` + `requesting-code-review` skills; keep edits minimal and to the requested files only.
5. **C — Completion.** Verify: syntax, the acceptance criteria, no side effects, and (for themes) live check on the Local site. Report what changed + how to verify.

## Rules
- Never start coding before phases 1–3 are written down.
- Respect the user's constraints: minimal diffs, only the requested files, no over-design.
- After Completion, offer to save any reusable procedure as a skill.
