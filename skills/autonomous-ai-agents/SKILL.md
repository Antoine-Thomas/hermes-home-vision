---
name: autonomous-ai-agents
description: "Orchestrate autonomous AI coding agents — delegate coding tasks to Claude Code, OpenAI Codex, or OpenCode with patterns for one-shot tasks, interactive sessions, parallel execution, PR reviews, and CI integration."
version: 1.0.0
author: Hermes Agent (consolidated from claude-code, codex, opencode)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Autonomous, Delegation, PTY, Automation, Code-Review, Refactoring, Multi-Agent]
---

# Autonomous AI Coding Agents

Delegate coding tasks to external AI coding agent CLIs — Claude Code (Anthropic), Codex (OpenAI), or OpenCode (provider-agnostic) — via Hermes terminal and process tools.

## When to Delegate

Use an autonomous agent when:
- The task spans multiple files and requires git operations
- You need a PR reviewed by an external perspective
- You want parallel execution across isolated worktrees
- The task is well-scoped and can be described in a single prompt
- You want to offload long-running work to background processes

**Do NOT delegate** for single-file edits, simple research, or tasks requiring user interaction (subagents cannot use `clarify`).

## Tool Selection

| Tool | Best For | Auth | Key Strength |
|------|----------|------|-------------|
| **Claude Code** | Complex multi-step refactors, structured JSON output, session resumption | `ANTHROPIC_API_KEY` or OAuth | Print mode (`-p`) for clean one-shots, rich CLI flags |
| **Codex** | Sandboxed feature builds, batch PRs, yolo mode for speed | `OPENAI_API_KEY` or OAuth | Sandbox safety, `--full-auto` for approved changes |
| **OpenCode** | Provider-agnostic tasks, cost tracking, TUI sessions | Any provider (OpenRouter, Anthropic, etc.) | Model flexibility, `opencode run` for simple one-shots |

Full CLI references, flags, and tool-specific workflows are in the reference files:
- **[references/claude-code.md](references/claude-code.md)** — Claude Code CLI complete reference
- **[references/codex.md](references/codex.md)** — Codex CLI complete reference
- **[references/opencode.md](references/opencode.md)** — OpenCode CLI complete reference

## Common Patterns

### One-Shot Task (Preferred)

For bounded, single-prompt tasks — use print/exec mode. No PTY needed. Cleanest integration.

**Claude Code:**
```
terminal(command="claude -p 'Add retry logic to API calls' --allowedTools 'Read,Edit' --max-turns 10", workdir="~/project", timeout=120)
```

**Codex:**
```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

**OpenCode:**
```
terminal(command="opencode run 'Refactor auth module'", workdir="~/project")
```

### Interactive Session (Multi-Turn)

For iterative work requiring follow-up prompts. Use background mode with PTY.

**Claude Code (via tmux):**
```
terminal(command="tmux new-session -d -s claude -x 140 -y 40")
terminal(command="tmux send-keys -t claude 'cd ~/project && claude' Enter")
# Wait ~5s for startup, handle trust dialog
terminal(command="sleep 5 && tmux send-keys -t claude Enter")
# Send task
terminal(command="tmux send-keys -t claude 'Refactor the auth module' Enter")
# Monitor
terminal(command="sleep 30 && tmux capture-pane -t claude -p -S -60")
# Kill when done
terminal(command="tmux kill-session -t claude")
```

**Codex (background + PTY):**
```
terminal(command="codex exec --full-auto 'Refactor auth module'", workdir="~/project", background=true, pty=true)
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")
```

**OpenCode (background + PTY):**
```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
process(action="submit", session_id="<id>", data="Implement OAuth flow")
process(action="poll", session_id="<id>")
process(action="write", session_id="<id>", data="\x03")  # Ctrl+C to exit
```

### Parallel Execution

Run multiple agents concurrently in isolated worktrees or workdirs:

```bash
# Create isolated worktrees
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

# Launch agents in parallel
terminal(command="claude -p 'Fix issue #78' --allowedTools 'Read,Edit,Bash' --max-turns 15", workdir="/tmp/issue-78", background=true)
terminal(command="codex exec 'Fix issue #99'", workdir="/tmp/issue-99", background=true, pty=true)

# Monitor all
process(action="list")
```

### PR Review Pattern

**Quick review (Claude Code print mode):**
```
terminal(command="git diff main...feature-branch | claude -p 'Review this diff for bugs, security, and style' --max-turns 1", timeout=60)
```

**Deep review with worktree isolation:**
```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && claude -p 'Thorough code review' --max-turns 10", timeout=180)
```

**OpenCode built-in PR command:**
```
terminal(command="opencode pr 42", workdir="~/project", pty=true)
```

**Batch PR reviews:**
```
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'")
terminal(command="codex exec 'Review PR #86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87'", workdir="~/project", background=true, pty=true)
```

## Rules for Hermes Agents

1. **Prefer one-shot mode** — print/exec is cleaner than interactive sessions
2. **Always set `workdir`** — keep the agent focused on the right project
3. **Use worktrees for parallel work** — avoids file conflicts between agents
4. **Set `--max-turns`** — prevents runaway loops and cost overruns
5. **Monitor long tasks** — use `process(action="poll")` to check progress
6. **Clean up sessions** — kill tmux sessions and background processes when done
7. **Report concrete outcomes** — summarize file changes, test results, and remaining risks
8. **Respect tool-specific requirements** — PTY for interactive sessions, git repo for Codex

## Pitfalls

- **Claude Code interactive mode REQUIRES tmux** — the TUI needs `send-keys` and `capture-pane` for orchestration
- **Codex requires a git repo** — use `mktemp -d && git init` for scratch work
- **OpenCode `/exit` is NOT a valid command** — it opens an agent selector. Use Ctrl+C (`\x03`) or kill instead
- **`--dangerously-skip-permissions` dialog defaults to "No"** — must send Down then Enter to accept
- **Parallel agents need isolated workdirs** — sharing a working directory causes merge conflicts
- **Background sessions persist** — always clean up to avoid resource leaks
- **Cost tracking varies by tool** — Claude Code: `--max-budget-usd`; OpenCode: `opencode stats`; Codex: check usage via API
