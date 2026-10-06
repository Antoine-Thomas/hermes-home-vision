# Hermes Agent Integration

> Source: software-development/systematic-debugging/SKILL.md — split 2026-09-10.

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### Tool-Specific Debugging References

- **Node.js CDP debugging:** See `references/node-inspect-debugger.md` for Node's built-in V8 inspector CLI, CDP scripting with `chrome-remote-interface`, debugging Hermes ui-tui components, and heap/CPU profiling.
- **Python debugpy:** For Python debugging with VS Code / DAP protocol, see the `python-debugpy` skill if available on your platform.

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression
