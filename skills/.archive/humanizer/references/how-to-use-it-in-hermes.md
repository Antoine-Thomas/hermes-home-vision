# How to use it in Hermes

> Source: `creative/humanizer/SKILL.md` — split on 2026-09-10 to meet max 200 lines rule.

The text usually arrives one of three ways:
1. **Inline.** The user pastes the text into the message. Work on it in place and reply with the rewrite.
2. **File.** The user points at a file. Use `read_file` to load it, then `patch` or `write_file` to apply edits. For a markdown doc in a repo, a targeted `patch` per section is cleaner than rewriting the whole file.
3. **Voice calibration sample.** The user provides a sample of their own writing (inline or by file path) and asks you to match it. Read the sample first, then rewrite. See the Voice Calibration section below.

Always show the rewrite to the user. For file edits, show a diff or the changed section instead of silently overwriting.
