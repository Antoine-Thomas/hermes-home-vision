---
name: llm-wiki
description: "Karpathy's LLM Wiki: build/query interlinked markdown KB."
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wiki, knowledge-base, research, notes, markdown, rag-alternative]
    category: research
    related_skills: [obsidian, arxiv]
---

# Karpathy's LLM Wiki

Build and maintain a persistent, compounding knowledge base as interlinked markdown files.
Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Unlike traditional RAG (which rediscovers knowledge from scratch per query), the wiki
compiles knowledge once and keeps it current. Cross-references are already there.
Contradictions have already been flagged. Synthesis reflects everything ingested.

**Division of labor:** The human curates sources and directs analysis. The agent
summarizes, cross-references, files, and maintains consistency.

## References

- [When This Skill Activates](references/when-this-skill-activates.md)
- [Wiki Location](references/wiki-location.md)
- [Architecture: Three Layers](references/architecture-three-layers.md)
- [Resuming an Existing Wiki (CRITICAL — do this every session)](references/resuming-an-existing-wiki-critical-do-this-ev.md)
- [Initializing a New Wiki](references/initializing-a-new-wiki.md)
- [Core Operations](references/core-operations.md)
- [Working with the Wiki](references/working-with-the-wiki.md)
- [Pitfalls](references/pitfalls.md)
- [Related Tools](references/related-tools.md)
