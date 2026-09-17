1|---
2|name: opencode
3|description: "Delegate coding to OpenCode CLI (features, PR review)."
4|version: 1.2.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
11|    related_skills: [claude-code, codex, hermes-agent]
12|---
13|
14|# OpenCode CLI
15|
16|Use [OpenCode](https://opencode.ai) as an autonomous coding worker orchestrated by Hermes terminal/process tools. OpenCode is a provider-agnostic, open-source AI coding agent with a TUI and CLI.
17|
18|## When to Use
19|
20|- User explicitly asks to use OpenCode
21|- You want an external coding agent to implement/refactor/review code
22|- You need long-running coding sessions with progress checks
23|- You want parallel task execution in isolated workdirs/worktrees
24|
25|## Prerequisites
26|
27|- OpenCode installed: `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`
28|- Auth configured: `opencode auth login` or set provider env vars (OPENROUTER_API_KEY, etc.)
29|- Verify: `opencode auth list` should show at least one provider
30|- Git repository for code tasks (recommended)
31|- `pty=true` for interactive TUI sessions
32|
33|## Binary Resolution (Important)
34|
35|Shell environments may resolve different OpenCode binaries. If behavior differs between your terminal and Hermes, check:
36|
37|```
38|terminal(command="which -a opencode")
39|terminal(command="opencode --version")
40|```
41|
42|If needed, pin an explicit binary path:
43|
44|```
45|terminal(command="$HOME/.opencode/bin/opencode run '...'", workdir="~/project", pty=true)
46|```
47|
48|## One-Shot Tasks
49|
50|Use `opencode run` for bounded, non-interactive tasks:
51|
52|```
53|terminal(command="opencode run 'Add retry logic to API calls and update tests'", workdir="~/project")
54|```
55|
56|Attach context files with `-f`:
57|
58|```
59|terminal(command="opencode run 'Review this config for security issues' -f config.yaml -f .env.example", workdir="~/project")
60|```
61|
62|Show model thinking with `--thinking`:
63|
64|```
65|terminal(command="opencode run 'Debug why tests fail in CI' --thinking", workdir="~/project")
66|```
67|
68|Force a specific model:
69|
70|```
71|terminal(command="opencode run 'Refactor auth module' --model openrouter/anthropic/claude-sonnet-4", workdir="~/project")
72|```
73|
74|## Interactive Sessions (Background)
75|
76|For iterative work requiring multiple exchanges, start the TUI in background:
77|
78|```
79|terminal(command="opencode", workdir="~/project", background=true, pty=true)
80|# Returns session_id
81|
82|# Send a prompt
83|process(action="submit", session_id="<id>", data="Implement OAuth refresh flow and add tests")
84|
85|# Monitor progress
86|process(action="poll", session_id="<id>")
87|process(action="log", session_id="<id>")
88|
89|# Send follow-up input
90|process(action="submit", session_id="<id>", data="Now add error handling for token expiry")
91|
92|# Exit cleanly — Ctrl+C
93|process(action="write", session_id="<id>", data="\x03")
94|# Or just kill the process
95|process(action="kill", session_id="<id>")
96|```
97|
98|**Important:** Do NOT use `/exit` — it is not a valid OpenCode command and will open an agent selector dialog instead. Use Ctrl+C (`\x03`) or `process(action="kill")` to exit.
99|
100|### TUI Keybindings
101|
102|| Key | Action |
103||-----|--------|
104|| `Enter` | Submit message (press twice if needed) |
105|| `Tab` | Switch between agents (build/plan) |
106|| `Ctrl+P` | Open command palette |
107|| `Ctrl+X L` | Switch session |
108|| `Ctrl+X M` | Switch model |
109|| `Ctrl+X N` | New session |
110|| `Ctrl+X E` | Open editor |
111|| `Ctrl+C` | Exit OpenCode |
112|
113|### Resuming Sessions
114|
115|After exiting, OpenCode prints a session ID. Resume with:
116|
117|```
118|terminal(command="opencode -c", workdir="~/project", background=true, pty=true)  # Continue last session
119|terminal(command="opencode -s ses_abc123", workdir="~/project", background=true, pty=true)  # Specific session
120|```
121|
122|## Common Flags
123|
124|| Flag | Use |
125||------|-----|
126|| `run 'prompt'` | One-shot execution and exit |
127|| `--continue` / `-c` | Continue the last OpenCode session |
128|| `--session <id>` / `-s` | Continue a specific session |
129|| `--agent <name>` | Choose OpenCode agent (build or plan) |
130|| `--model provider/model` | Force specific model |
131|| `--format json` | Machine-readable output/events |
132|| `--file <path>` / `-f` | Attach file(s) to the message |
133|| `--thinking` | Show model thinking blocks |
134|| `--variant <level>` | Reasoning effort (high, max, minimal) |
135|| `--title <name>` | Name the session |
136|| `--attach <url>` | Connect to a running opencode server |
137|
138|## Procedure
139|
140|1. Verify tool readiness:
141|   - `terminal(command="opencode --version")`
142|   - `terminal(command="opencode auth list")`
143|2. For bounded tasks, use `opencode run '...'` (no pty needed).
144|3. For iterative tasks, start `opencode` with `background=true, pty=true`.
145|4. Monitor long tasks with `process(action="poll"|"log")`.
146|5. If OpenCode asks for input, respond via `process(action="submit", ...)`.
147|6. Exit with `process(action="write", data="\x03")` or `process(action="kill")`.
148|7. Summarize file changes, test results, and next steps back to user.
149|
150|## PR Review Workflow
151|
152|OpenCode has a built-in PR command:
153|
154|```
155|terminal(command="opencode pr 42", workdir="~/project", pty=true)
156|```
157|
158|Or review in a temporary clone for isolation:
159|
160|```
161|terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && opencode run 'Review this PR vs main. Report bugs, security risks, test gaps, and style issues.' -f $(git diff origin/main --name-only | head -20 | tr '\n' ' ')", pty=true)
162|```
163|
164|## Parallel Work Pattern
165|
166|Use separate workdirs/worktrees to avoid collisions:
167|
168|```
169|terminal(command="opencode run 'Fix issue #101 and commit'", workdir="/tmp/issue-101", background=true, pty=true)
170|terminal(command="opencode run 'Add parser regression tests and commit'", workdir="/tmp/issue-102", background=true, pty=true)
171|process(action="list")
172|```
173|
174|## Session & Cost Management
175|
176|List past sessions:
177|
178|```
179|terminal(command="opencode session list")
180|```
181|
182|Check token usage and costs:
183|
184|```
185|terminal(command="opencode stats")
186|terminal(command="opencode stats --days 7 --models anthropic/claude-sonnet-4")
187|```
188|
189|## Pitfalls
190|
191|- Interactive `opencode` (TUI) sessions require `pty=true`. The `opencode run` command does NOT need pty.
192|- `/exit` is NOT a valid command — it opens an agent selector. Use Ctrl+C to exit the TUI.
193|- PATH mismatch can select the wrong OpenCode binary/model config.
194|- If OpenCode appears stuck, inspect logs before killing:
195|  - `process(action="log", session_id="<id>")`
196|- Avoid sharing one working directory across parallel OpenCode sessions.
197|- Enter may need to be pressed twice to submit in the TUI (once to finalize text, once to send).
198|
199|## Verification
200|
201|Smoke test:
202|
203|```
204|terminal(command="opencode run 'Respond with exactly: OPENCODE_SMOKE_OK'")
205|```
206|
207|Success criteria:
208|- Output includes `OPENCODE_SMOKE_OK`
209|- Command exits without provider/model errors
210|- For code tasks: expected files changed and tests pass
211|
212|## Rules
213|
214|1. Prefer `opencode run` for one-shot automation — it's simpler and doesn't need pty.
215|2. Use interactive background mode only when iteration is needed.
216|3. Always scope OpenCode sessions to a single repo/workdir.
217|4. For long tasks, provide progress updates from `process` logs.
218|5. Report concrete outcomes (files changed, tests, remaining risks).
219|6. Exit interactive sessions with Ctrl+C or kill, never `/exit`.
220|