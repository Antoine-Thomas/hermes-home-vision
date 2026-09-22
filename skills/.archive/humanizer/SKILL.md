---
name: humanizer
description: "Humanize text: strip AI-isms and add real voice."
version: 2.5.1
author: Siqi Chen (@blader, https://github.com/blader/humanizer), ported by Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [writing, editing, humanize, anti-ai-slop, voice, prose, text]
    category: creative
    homepage: https://github.com/blader/humanizer
    related_skills: [songwriting-and-ai-music]
---

# Humanizer: Remove AI Writing Patterns

Identify and remove signs of AI-generated text to make writing sound natural and human. Based on Wikipedia's "Signs of AI writing" guide (maintained by WikiProject AI Cleanup), derived from observations of thousands of AI-generated text instances.

**Key insight:** LLMs use statistical algorithms to guess what should come next. The result tends toward the most statistically likely completion, which is how the telltale patterns below get baked in.


## When to use this skill

Load this skill whenever the user asks to:
- "humanize", "de-AI", "de-slop", or "un-ChatGPT" a piece of text
- rewrite something so it doesn't sound like it was written by an LLM
- edit a draft (blog post, essay, PR description, docs, memo, email, tweet, resume bullet) to sound more natural
- match their voice in writing they're producing
- review text for AI tells before publishing

Also apply this skill to **your own** output when writing user-facing prose such as release notes, PR descriptions, docs, and summaries. Hermes's baseline voice already strips most of these, but a focused pass catches what slips through.

## References

This skill was split to meet the max 200-line rule. Details are in `references/`:

| Section | File |
|---------|------|
| How to use it in Hermes | `references/how-to-use-it-in-hermes.md` |
| Your task | `references/your-task.md` |
| Voice Calibration (optional) | `references/voice-calibration-optional.md` |
| PERSONALITY AND SOUL | `references/personality-and-soul.md` |
| CONTENT PATTERNS | `references/content-patterns.md` |
| LANGUAGE AND GRAMMAR PATTERNS | `references/language-and-grammar-patterns.md` |
| STYLE PATTERNS | `references/style-patterns.md` |
| COMMUNICATION PATTERNS | `references/communication-patterns.md` |
| FILLER AND HEDGING | `references/filler-and-hedging.md` |
| STYLE, RHYTHM, AND RHETORIC PATTERNS | `references/style-rhythm-and-rhetoric-patterns.md` |
| Process | `references/process.md` |
| Output Format | `references/output-format.md` |
| Full Example | `references/full-example.md` |
| Attribution | `references/attribution.md` |

> All reference files are verbatim extracts — no logic changed.

