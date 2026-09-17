1|---
2|name: codex
3|description: "Delegate coding to OpenAI Codex CLI (features, PRs)."
4|version: 1.0.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
11|    related_skills: [claude-code, hermes-agent]
12|---
13|
14|# Codex CLI
15|
16|Delegate coding tasks to [Codex](https://github.com/openai/codex) via the Hermes terminal. Codex is OpenAI's autonomous coding agent CLI.
17|
18|## When to use
19|
20|- Building features
21|- Refactoring
22|- PR reviews
23|- Batch issue fixing
24|
25|Requires the codex CLI and a git repository.
26|
27|## Prerequisites
28|
29|- Codex installed: `npm install -g @openai/codex`
30|- OpenAI auth configured: either `OPENAI_API_KEY` or Codex OAuth credentials
31|  from the Codex CLI login flow
32|- **Must run inside a git repository** — Codex refuses to run outside one
33|- Use `pty=true` in terminal calls — Codex is an interactive terminal app
34|
35|For Hermes itself, `model.provider: openai-codex` uses Hermes-managed Codex
36|OAuth from `~/.hermes/auth.json` after `hermes auth add openai-codex`. For the
37|standalone Codex CLI, a valid CLI OAuth session may live under
38|`~/.codex/auth.json`; do not treat a missing `OPENAI_API_KEY` alone as proof
39|that Codex auth is missing.
40|
41|## One-Shot Tasks
42|
43|```
44|terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
45|```
46|
47|For scratch work (Codex needs a git repo):
48|```
49|terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
50|```
51|
52|## Background Mode (Long Tasks)
53|
54|```
55|# Start in background with PTY
56|terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
57|# Returns session_id
58|
59|# Monitor progress
60|process(action="poll", session_id="<id>")
61|process(action="log", session_id="<id>")
62|
63|# Send input if Codex asks a question
64|process(action="submit", session_id="<id>", data="yes")
65|
66|# Kill if needed
67|process(action="kill", session_id="<id>")
68|```
69|
70|## Key Flags
71|
72|| Flag | Effect |
73||------|--------|
74|| `exec "prompt"` | One-shot execution, exits when done |
75|| `--full-auto` | Sandboxed but auto-approves file changes in workspace |
76|| `--yolo` | No sandbox, no approvals (fastest, most dangerous) |
77|| `--sandbox danger-full-access` | No Codex sandbox; useful when the host service context breaks bubblewrap |
78|
79|## Hermes Gateway Caveat
80|
81|When invoking the Codex CLI from a Hermes gateway/service context (for example,
82|Telegram-driven agent sessions), Codex `workspace-write` sandboxing may fail even
83|when the same command works in the user's interactive shell. A typical symptom is
84|bubblewrap/user-namespace errors such as `setting up uid map: Permission denied`
85|or `loopback: Failed RTM_NEWADDR: Operation not permitted`.
86|
87|In that context, prefer:
88|
89|```
90|codex exec --sandbox danger-full-access "<task>"
91|```
92|
93|Use process boundaries as the safety layer instead: explicit `workdir`, clean git
94|status before launch, narrow task prompts, `git diff` review, targeted tests, and
95|human/agent confirmation before committing broad changes.
96|
97|## PR Reviews
98|
99|Clone to a temp directory for safe review:
100|
101|```
102|terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main", pty=true)
103|```
104|
105|## Parallel Issue Fixing with Worktrees
106|
107|```
108|# Create worktrees
109|terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
110|terminal(command="git worktree add -b fix/issue-99 /tmp/issue-99 main", workdir="~/project")
111|
112|# Launch Codex in each
113|terminal(command="codex --yolo exec 'Fix issue #78: <description>. Commit when done.'", workdir="/tmp/issue-78", background=true, pty=true)
114|terminal(command="codex --yolo exec 'Fix issue #99: <description>. Commit when done.'", workdir="/tmp/issue-99", background=true, pty=true)
115|
116|# Monitor
117|process(action="list")
118|
119|# After completion, push and create PRs
120|terminal(command="cd /tmp/issue-78 && git push -u origin fix/issue-78")
121|terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")
122|
123|# Cleanup
124|terminal(command="git worktree remove /tmp/issue-78", workdir="~/project")
125|```
126|
127|## Batch PR Reviews
128|
129|```
130|# Fetch all PR refs
131|terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")
132|
133|# Review multiple PRs in parallel
134|terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
135|terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)
136|
137|# Post results
138|terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
139|```
140|
141|## Rules
142|
143|1. **Always use `pty=true`** — Codex is an interactive terminal app and hangs without a PTY
144|2. **Git repo required** — Codex won't run outside a git directory. Use `mktemp -d && git init` for scratch
145|3. **Use `exec` for one-shots** — `codex exec "prompt"` runs and exits cleanly
146|4. **`--full-auto` for building** — auto-approves changes within the sandbox
147|5. **Background for long tasks** — use `background=true` and monitor with `process` tool
148|6. **Don't interfere** — monitor with `poll`/`log`, be patient with long-running tasks
149|7. **Parallel is fine** — run multiple Codex processes at once for batch work
150|