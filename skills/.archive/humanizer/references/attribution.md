# Attribution

> Source: `creative/humanizer/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

This skill is ported from [blader/humanizer](https://github.com/blader/humanizer) (MIT licensed), which is itself based on [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup. The patterns documented there come from observations of thousands of instances of AI-generated text on Wikipedia.

Original author: Siqi Chen ([@blader](https://github.com/blader)). Original repo: https://github.com/blader/humanizer (version 2.5.1). Ported to Hermes Agent with Hermes-native tool references (`read_file`, `patch`, `write_file`) and guidance for when to load the skill. The original 29 patterns come from the source, and the before/after examples (including the full worked example) are kept as demonstrations. Patterns 30-34 and the "marketing and blog clichés" list added to pattern 7 are Hermes additions and are not part of the upstream source. The skill's own instructional prose has also been lightly edited to follow its own guidance (for example, removing em dashes and negative parallelism from the narration) so the skill models the writing it asks for. Original MIT license preserved in the `LICENSE` file alongside this `SKILL.md`.

Key insight from Wikipedia: "LLMs use statistical algorithms to guess what should come next. The result tends toward the most statistically likely result that applies to the widest variety of cases."
