1|---
2|name: claude-code
3|description: "Delegate coding to Claude Code CLI (features, PRs)."
4|version: 2.2.0
5|author: Hermes Agent + Teknium
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [Coding-Agent, Claude, Anthropic, Code-Review, Refactoring, PTY, Automation]
11|    related_skills: [codex, hermes-agent, opencode]
12|---
13|
14|# Claude Code — Hermes Orchestration Guide
15|
16|Delegate coding tasks to [Claude Code](https://code.claude.com/docs/en/cli-reference) (Anthropic's autonomous coding agent CLI) via the Hermes terminal. Claude Code v2.x can read files, write code, run shell commands, spawn subagents, and manage git workflows autonomously.
17|
18|## Prerequisites
19|
20|- **Install:** `npm install -g @anthropic-ai/claude-code`
21|- **Auth:** run `claude` once to log in (browser OAuth for Pro/Max, or set `ANTHROPIC_API_KEY`)
22|- **Console auth:** `claude auth login --console` for API key billing
23|- **SSO auth:** `claude auth login --sso` for Enterprise
24|- **Check status:** `claude auth status` (JSON) or `claude auth status --text` (human-readable)
25|- **Health check:** `claude doctor` — checks auto-updater and installation health
26|- **Version check:** `claude --version` (requires v2.x+)
27|- **Update:** `claude update` or `claude upgrade`
28|
29|## Two Orchestration Modes
30|
31|Hermes interacts with Claude Code in two fundamentally different ways. Choose based on the task.
32|
33|### Mode 1: Print Mode (`-p`) — Non-Interactive (PREFERRED for most tasks)
34|
35|Print mode runs a one-shot task, returns the result, and exits. No PTY needed. No interactive prompts. This is the cleanest integration path.
36|
37|```
38|terminal(command="claude -p 'Add error handling to all API calls in src/' --allowedTools 'Read,Edit' --max-turns 10", workdir="/path/to/project", timeout=120)
39|```
40|
41|**When to use print mode:**
42|- One-shot coding tasks (fix a bug, add a feature, refactor)
43|- CI/CD automation and scripting
44|- Structured data extraction with `--json-schema`
45|- Piped input processing (`cat file | claude -p "analyze this"`)
46|- Any task where you don't need multi-turn conversation
47|
48|**Print mode skips ALL interactive dialogs** — no workspace trust prompt, no permission confirmations. This makes it ideal for automation.
49|
50|### Mode 2: Interactive PTY via tmux — Multi-Turn Sessions
51|
52|Interactive mode gives you a full conversational REPL where you can send follow-up prompts, use slash commands, and watch Claude work in real time. **Requires tmux orchestration.**
53|
54|```
55|# Start a tmux session
56|terminal(command="tmux new-session -d -s claude-work -x 140 -y 40")
57|
58|# Launch Claude Code inside it
59|terminal(command="tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter")
60|
61|# Wait for startup, then send your task
62|# (after ~3-5 seconds for the welcome screen)
63|terminal(command="sleep 5 && tmux send-keys -t claude-work 'Refactor the auth module to use JWT tokens' Enter")
64|
65|# Monitor progress by capturing the pane
66|terminal(command="sleep 15 && tmux capture-pane -t claude-work -p -S -50")
67|
68|# Send follow-up tasks
69|terminal(command="tmux send-keys -t claude-work 'Now add unit tests for the new JWT code' Enter")
70|
71|# Exit when done
72|terminal(command="tmux send-keys -t claude-work '/exit' Enter")
73|```
74|
75|**When to use interactive mode:**
76|- Multi-turn iterative work (refactor → review → fix → test cycle)
77|- Tasks requiring human-in-the-loop decisions
78|- Exploratory coding sessions
79|- When you need to use Claude's slash commands (`/compact`, `/review`, `/model`)
80|
81|## PTY Dialog Handling (CRITICAL for Interactive Mode)
82|
83|Claude Code presents up to two confirmation dialogs on first launch. You MUST handle these via tmux send-keys:
84|
85|### Dialog 1: Workspace Trust (first visit to a directory)
86|```
87|❯ 1. Yes, I trust this folder    ← DEFAULT (just press Enter)
88|  2. No, exit
89|```
90|**Handling:** `tmux send-keys -t <session> Enter` — default selection is correct.
91|
92|### Dialog 2: Bypass Permissions Warning (only with --dangerously-skip-permissions)
93|```
94|❯ 1. No, exit                    ← DEFAULT (WRONG choice!)
95|  2. Yes, I accept
96|```
97|**Handling:** Must navigate DOWN first, then Enter:
98|```
99|tmux send-keys -t <session> Down && sleep 0.3 && tmux send-keys -t <session> Enter
100|```
101|
102|### Robust Dialog Handling Pattern
103|```
104|# Launch with permissions bypass
105|terminal(command="tmux send-keys -t claude-work 'claude --dangerously-skip-permissions \"your task\"' Enter")
106|
107|# Handle trust dialog (Enter for default "Yes")
108|terminal(command="sleep 4 && tmux send-keys -t claude-work Enter")
109|
110|# Handle permissions dialog (Down then Enter for "Yes, I accept")
111|terminal(command="sleep 3 && tmux send-keys -t claude-work Down && sleep 0.3 && tmux send-keys -t claude-work Enter")
112|
113|# Now wait for Claude to work
114|terminal(command="sleep 15 && tmux capture-pane -t claude-work -p -S -60")
115|```
116|
117|**Note:** After the first trust acceptance for a directory, the trust dialog won't appear again. Only the permissions dialog recurs each time you use `--dangerously-skip-permissions`.
118|
119|## CLI Subcommands
120|
121|| Subcommand | Purpose |
122||------------|---------|
123|| `claude` | Start interactive REPL |
124|| `claude "query"` | Start REPL with initial prompt |
125|| `claude -p "query"` | Print mode (non-interactive, exits when done) |
126|| `cat file \| claude -p "query"` | Pipe content as stdin context |
127|| `claude -c` | Continue the most recent conversation in this directory |
128|| `claude -r "id"` | Resume a specific session by ID or name |
129|| `claude auth login` | Sign in (add `--console` for API billing, `--sso` for Enterprise) |
130|| `claude auth status` | Check login status (returns JSON; `--text` for human-readable) |
131|| `claude mcp add <name> -- <cmd>` | Add an MCP server |
132|| `claude mcp list` | List configured MCP servers |
133|| `claude mcp remove <name>` | Remove an MCP server |
134|| `claude agents` | List configured agents |
135|| `claude doctor` | Run health checks on installation and auto-updater |
136|| `claude update` / `claude upgrade` | Update Claude Code to latest version |
137|| `claude remote-control` | Start server to control Claude from claude.ai or mobile app |
138|| `claude install [target]` | Install native build (stable, latest, or specific version) |
139|| `claude setup-token` | Set up long-lived auth token (requires subscription) |
140|| `claude plugin` / `claude plugins` | Manage Claude Code plugins |
141|| `claude auto-mode` | Inspect auto mode classifier configuration |
142|
143|## Print Mode Deep Dive
144|
145|### Structured JSON Output
146|```
147|terminal(command="claude -p 'Analyze auth.py for security issues' --output-format json --max-turns 5", workdir="/project", timeout=120)
148|```
149|
150|Returns a JSON object with:
151|```json
152|{
153|  "type": "result",
154|  "subtype": "success",
155|  "result": "The analysis text...",
156|  "session_id": "75e2167f-...",
157|  "num_turns": 3,
158|  "total_cost_usd": 0.0787,
159|  "duration_ms": 10276,
160|  "stop_reason": "end_turn",
161|  "terminal_reason": "completed",
162|  "usage": { "input_tokens": 5, "output_tokens": 603, ... },
163|  "modelUsage": { "claude-sonnet-4-6": { "costUSD": 0.078, "contextWindow": 200000 } }
164|}
165|```
166|
167|**Key fields:** `session_id` for resumption, `num_turns` for agentic loop count, `total_cost_usd` for spend tracking, `subtype` for success/error detection (`success`, `error_max_turns`, `error_budget`).
168|
169|### Streaming JSON Output
170|For real-time token streaming, use `stream-json` with `--verbose`:
171|```
172|terminal(command="claude -p 'Write a summary' --output-format stream-json --verbose --include-partial-messages", timeout=60)
173|```
174|
175|Returns newline-delimited JSON events. Filter with jq for live text:
176|```
177|claude -p "Explain X" --output-format stream-json --verbose --include-partial-messages | \
178|  jq -rj 'select(.type == "stream_event" and .event.delta.type? == "text_delta") | .event.delta.text'
179|```
180|
181|Stream events include `system/api_retry` with `attempt`, `max_retries`, and `error` fields (e.g., `rate_limit`, `billing_error`).
182|
183|### Bidirectional Streaming
184|For real-time input AND output streaming:
185|```
186|claude -p "task" --input-format stream-json --output-format stream-json --replay-user-messages
187|```
188|`--replay-user-messages` re-emits user messages on stdout for acknowledgment.
189|
190|### Piped Input
191|```
192|# Pipe a file for analysis
193|terminal(command="cat src/auth.py | claude -p 'Review this code for bugs' --max-turns 1", timeout=60)
194|
195|# Pipe multiple files
196|terminal(command="cat src/*.py | claude -p 'Find all TODO comments' --max-turns 1", timeout=60)
197|
198|# Pipe command output
199|terminal(command="git diff HEAD~3 | claude -p 'Summarize these changes' --max-turns 1", timeout=60)
200|```
201|
202|### JSON Schema for Structured Extraction
203|```
204|terminal(command="claude -p 'List all functions in src/' --output-format json --json-schema '{\"type\":\"object\",\"properties\":{\"functions\":{\"type\":\"array\",\"items\":{\"type\":\"string\"}}},\"required\":[\"functions\"]}' --max-turns 5", workdir="/project", timeout=90)
205|```
206|
207|Parse `structured_output` from the JSON result. Claude validates output against the schema before returning.
208|
209|### Session Continuation
210|```
211|# Start a task
212|terminal(command="claude -p 'Start refactoring the database layer' --output-format json --max-turns 10 > /tmp/session.json", workdir="/project", timeout=180)
213|
214|# Resume with session ID
215|terminal(command="claude -p 'Continue and add connection pooling' --resume $(cat /tmp/session.json | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"session_id\"])') --max-turns 5", workdir="/project", timeout=120)
216|
217|# Or resume the most recent session in the same directory
218|terminal(command="claude -p 'What did you do last time?' --continue --max-turns 1", workdir="/project", timeout=30)
219|
220|# Fork a session (new ID, keeps history)
221|terminal(command="claude -p 'Try a different approach' --resume <id> --fork-session --max-turns 10", workdir="/project", timeout=120)
222|```
223|
224|### Bare Mode for CI/Scripting
225|```
226|terminal(command="claude --bare -p 'Run all tests and report failures' --allowedTools 'Read,Bash' --max-turns 10", workdir="/project", timeout=180)
227|```
228|
229|`--bare` skips hooks, plugins, MCP discovery, and CLAUDE.md loading. Fastest startup. Requires `ANTHROPIC_API_KEY` (skips OAuth).
230|
231|To selectively load context in bare mode:
232|| To load | Flag |
233||---------|------|
234|| System prompt additions | `--append-system-prompt "text"` or `--append-system-prompt-file path` |
235|| Settings | `--settings <file-or-json>` |
236|| MCP servers | `--mcp-config <file-or-json>` |
237|| Custom agents | `--agents '<json>'` |
238|
239|### Fallback Model for Overload
240|```
241|terminal(command="claude -p 'task' --fallback-model haiku --max-turns 5", timeout=90)
242|```
243|Automatically falls back to the specified model when the default is overloaded (print mode only).
244|
245|## Complete CLI Flags Reference
246|
247|### Session & Environment
248|| Flag | Effect |
249||------|--------|
250|| `-p, --print` | Non-interactive one-shot mode (exits when done) |
251|| `-c, --continue` | Resume most recent conversation in current directory |
252|| `-r, --resume <id>` | Resume specific session by ID or name (interactive picker if no ID) |
253|| `--fork-session` | When resuming, create new session ID instead of reusing original |
254|| `--session-id <uuid>` | Use a specific UUID for the conversation |
255|| `--no-session-persistence` | Don't save session to disk (print mode only) |
256|| `--add-dir <paths...>` | Grant Claude access to additional working directories |
257|| `-w, --worktree [name]` | Run in an isolated git worktree at `.claude/worktrees/<name>` |
258|| `--tmux` | Create a tmux session for the worktree (requires `--worktree`) |
259|| `--ide` | Auto-connect to a valid IDE on startup |
260|| `--chrome` / `--no-chrome` | Enable/disable Chrome browser integration for web testing |
261|| `--from-pr [number]` | Resume session linked to a specific GitHub PR |
262|| `--file <specs...>` | File resources to download at startup (format: `file_id:relative_path`) |
263|
264|### Model & Performance
265|| Flag | Effect |
266||------|--------|
267|| `--model <alias>` | Model selection: `sonnet`, `opus`, `haiku`, or full name like `claude-sonnet-4-6` |
268|| `--effort <level>` | Reasoning depth: `low`, `medium`, `high`, `max`, `auto` | Both |
269|| `--max-turns <n>` | Limit agentic loops (print mode only; prevents runaway) |
270|| `--max-budget-usd <n>` | Cap API spend in dollars (print mode only) |
271|| `--fallback-model <model>` | Auto-fallback when default model is overloaded (print mode only) |
272|| `--betas <betas...>` | Beta headers to include in API requests (API key users only) |
273|
274|### Permission & Safety
275|| Flag | Effect |
276||------|--------|
277|| `--dangerously-skip-permissions` | Auto-approve ALL tool use (file writes, bash, network, etc.) |
278|| `--allow-dangerously-skip-permissions` | Enable bypass as an *option* without enabling it by default |
279|| `--permission-mode <mode>` | `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` |
280|| `--allowedTools <tools...>` | Whitelist specific tools (comma or space-separated) |
281|| `--disallowedTools <tools...>` | Blacklist specific tools |
282|| `--tools <tools...>` | Override built-in tool set (`""` = none, `"default"` = all, or tool names) |
283|
284|### Output & Input Format
285|| Flag | Effect |
286||------|--------|
287|| `--output-format <fmt>` | `text` (default), `json` (single result object), `stream-json` (newline-delimited) |
288|| `--input-format <fmt>` | `text` (default) or `stream-json` (real-time streaming input) |
289|| `--json-schema <schema>` | Force structured JSON output matching a schema |
290|| `--verbose` | Full turn-by-turn output |
291|| `--include-partial-messages` | Include partial message chunks as they arrive (stream-json + print) |
292|| `--replay-user-messages` | Re-emit user messages on stdout (stream-json bidirectional) |
293|
294|### System Prompt & Context
295|| Flag | Effect |
296||------|--------|
297|| `--append-system-prompt <text>` | **Add** to the default system prompt (preserves built-in capabilities) |
298|| `--append-system-prompt-file <path>` | **Add** file contents to the default system prompt |
299|| `--system-prompt <text>` | **Replace** the entire system prompt (use --append instead usually) |
300|| `--system-prompt-file <path>` | **Replace** the system prompt with file contents |
301|| `--bare` | Skip hooks, plugins, MCP discovery, CLAUDE.md, OAuth (fastest startup) |
302|| `--agents '<json>'` | Define custom subagents dynamically as JSON |
303|| `--mcp-config <path>` | Load MCP servers from JSON file (repeatable) |
304|| `--strict-mcp-config` | Only use MCP servers from `--mcp-config`, ignoring all other MCP configs |
305|| `--settings <file-or-json>` | Load additional settings from a JSON file or inline JSON |
306|| `--setting-sources <sources>` | Comma-separated sources to load: `user`, `project`, `local` |
307|| `--plugin-dir <paths...>` | Load plugins from directories for this session only |
308|| `--disable-slash-commands` | Disable all skills/slash commands |
309|
310|### Debugging
311|| Flag | Effect |
312||------|--------|
313|| `-d, --debug [filter]` | Enable debug logging with optional category filter (e.g., `"api,hooks"`, `"!1p,!file"`) |
314|| `--debug-file <path>` | Write debug logs to file (implicitly enables debug mode) |
315|
316|### Agent Teams
317|| Flag | Effect |
318||------|--------|
319|| `--teammate-mode <mode>` | How agent teams display: `auto`, `in-process`, or `tmux` |
320|| `--brief` | Enable `SendUserMessage` tool for agent-to-user communication |
321|
322|### Tool Name Syntax for --allowedTools / --disallowedTools
323|```
324|Read                    # All file reading
325|Edit                    # File editing (existing files)
326|Write                   # File creation (new files)
327|Bash                    # All shell commands
328|Bash(git *)             # Only git commands
329|Bash(git commit *)      # Only git commit commands
330|Bash(npm run lint:*)    # Pattern matching with wildcards
331|WebSearch               # Web search capability
332|WebFetch                # Web page fetching
333|mcp__<server>__<tool>   # Specific MCP tool
334|```
335|
336|## Settings & Configuration
337|
338|### Settings Hierarchy (highest to lowest priority)
339|1. **CLI flags** — override everything
340|2. **Local project:** `.claude/settings.local.json` (personal, gitignored)
341|3. **Project:** `.claude/settings.json` (shared, git-tracked)
342|4. **User:** `~/.claude/settings.json` (global)
343|
344|### Permissions in Settings
345|```json
346|{
347|  "permissions": {
348|    "allow": ["Bash(npm run lint:*)", "WebSearch", "Read"],
349|    "ask": ["Write(*.ts)", "Bash(git push*)"],
350|    "deny": ["Read(.env)", "Bash(rm -rf *)"]
351|  }
352|}
353|```
354|
355|### Memory Files (CLAUDE.md) Hierarchy
356|1. **Global:** `~/.claude/CLAUDE.md` — applies to all projects
357|2. **Project:** `./CLAUDE.md` — project-specific context (git-tracked)
358|3. **Local:** `.claude/CLAUDE.local.md` — personal project overrides (gitignored)
359|
360|Use the `#` prefix in interactive mode to quickly add to memory: `# Always use 2-space indentation`.
361|
362|## Interactive Session: Slash Commands
363|
364|### Session & Context
365|| Command | Purpose |
366||---------|---------|
367|| `/help` | Show all commands (including custom and MCP commands) |
368|| `/compact [focus]` | Compress context to save tokens; CLAUDE.md survives compaction. E.g., `/compact focus on auth logic` |
369|| `/clear` | Wipe conversation history for a fresh start |
370|| `/context` | Visualize context usage as a colored grid with optimization tips |
371|| `/cost` | View token usage with per-model and cache-hit breakdowns |
372|| `/resume` | Switch to or resume a different session |
373|| `/rewind` | Revert to a previous checkpoint in conversation or code |
374|| `/btw <question>` | Ask a side question without adding to context cost |
375|| `/status` | Show version, connectivity, and session info |
376|| `/todos` | List tracked action items from the conversation |
377|| `/exit` or `Ctrl+D` | End session |
378|
379|### Development & Review
380|| Command | Purpose |
381||---------|---------|
382|| `/review` | Request code review of current changes |
383|| `/security-review` | Perform security analysis of current changes |
384|| `/plan [description]` | Enter Plan mode with auto-start for task planning |
385|| `/loop [interval]` | Schedule recurring tasks within the session |
386|| `/batch` | Auto-create worktrees for large parallel changes (5-30 worktrees) |
387|
388|### Configuration & Tools
389|| Command | Purpose |
390||---------|---------|
391|| `/model [model]` | Switch models mid-session (use arrow keys to adjust effort) |
392|| `/effort [level]` | Set reasoning effort: `low`, `medium`, `high`, `max`, or `auto` |
393|| `/init` | Create a CLAUDE.md file for project memory |
394|| `/memory` | Open CLAUDE.md for editing |
395|| `/config` | Open interactive settings configuration |
396|| `/permissions` | View/update tool permissions |
397|| `/agents` | Manage specialized subagents |
398|| `/mcp` | Interactive UI to manage MCP servers |
399|| `/add-dir` | Add additional working directories (useful for monorepos) |
400|| `/usage` | Show plan limits and rate limit status |
401|| `/voice` | Enable push-to-talk voice mode (20 languages; hold Space to record, release to send) |
402|| `/release-notes` | Interactive picker for version release notes |
403|
404|### Custom Slash Commands
405|Create `.claude/commands/<name>.md` (project-shared) or `~/.claude/commands/<name>.md` (personal):
406|
407|```markdown
408|# .claude/commands/deploy.md
409|Run the deploy pipeline:
410|1. Run all tests
411|2. Build the Docker image
412|3. Push to registry
413|4. Update the $ARGUMENTS environment (default: staging)
414|```
415|
416|Usage: `/deploy production` — `$ARGUMENTS` is replaced with the user's input.
417|
418|### Skills (Natural Language Invocation)
419|Unlike slash commands (manually invoked), skills in `.claude/skills/` are markdown guides that Claude invokes automatically via natural language when the task matches:
420|
421|```markdown
422|# .claude/skills/database-migration.md
423|When asked to create or modify database migrations:
424|1. Use Alembic for migration generation
425|2. Always create a rollback function
426|3. Test migrations against a local database copy
427|```
428|
429|## Interactive Session: Keyboard Shortcuts
430|
431|### General Controls
432|| Key | Action |
433||-----|--------|
434|| `Ctrl+C` | Cancel current input or generation |
435|| `Ctrl+D` | Exit session |
436|| `Ctrl+R` | Reverse search command history |
437|| `Ctrl+B` | Background a running task |
438|| `Ctrl+V` | Paste image into conversation |
439|| `Ctrl+O` | Transcript mode — see Claude's thinking process |
440|| `Ctrl+G` or `Ctrl+X Ctrl+E` | Open prompt in external editor |
441|| `Esc Esc` | Rewind conversation or code state / summarize |
442|
443|### Mode Toggles
444|| Key | Action |
445||-----|--------|
446|| `Shift+Tab` | Cycle permission modes (Normal → Auto-Accept → Plan) |
447|| `Alt+P` | Switch model |
448|| `Alt+T` | Toggle thinking mode |
449|| `Alt+O` | Toggle Fast Mode |
450|
451|### Multiline Input
452|| Key | Action |
453||-----|--------|
454|| `\` + `Enter` | Quick newline |
455|| `Shift+Enter` | Newline (alternative) |
456|| `Ctrl+J` | Newline (alternative) |
457|
458|### Input Prefixes
459|| Prefix | Action |
460||--------|--------|
461|| `!` | Execute bash directly, bypassing AI (e.g., `!npm test`). Use `!` alone to toggle shell mode. |
462|| `@` | Reference files/directories with autocomplete (e.g., `@./src/api/`) |
463|| `#` | Quick add to CLAUDE.md memory (e.g., `# Use 2-space indentation`) |
464|| `/` | Slash commands |
465|
466|### Pro Tip: "ultrathink"
467|Use the keyword "ultrathink" in your prompt for maximum reasoning effort on a specific turn. This triggers the deepest thinking mode regardless of the current `/effort` setting.
468|
469|## PR Review Pattern
470|
471|### Quick Review (Print Mode)
472|```
473|terminal(command="cd /path/to/repo && git diff main...feature-branch | claude -p 'Review this diff for bugs, security issues, and style problems. Be thorough.' --max-turns 1", timeout=60)
474|```
475|
476|### Deep Review (Interactive + Worktree)
477|```
478|terminal(command="tmux new-session -d -s review -x 140 -y 40")
479|terminal(command="tmux send-keys -t review 'cd /path/to/repo && claude -w pr-review' Enter")
480|terminal(command="sleep 5 && tmux send-keys -t review Enter")  # Trust dialog
481|terminal(command="sleep 2 && tmux send-keys -t review 'Review all changes vs main. Check for bugs, security issues, race conditions, and missing tests.' Enter")
482|terminal(command="sleep 30 && tmux capture-pane -t review -p -S -60")
483|```
484|
485|### PR Review from Number
486|```
487|terminal(command="claude -p 'Review this PR thoroughly' --from-pr 42 --max-turns 10", workdir="/path/to/repo", timeout=120)
488|```
489|
490|### Claude Worktree with tmux
491|```
492|terminal(command="claude -w feature-x --tmux", workdir="/path/to/repo")
493|```
494|Creates an isolated git worktree at `.claude/worktrees/feature-x` AND a tmux session for it. Uses iTerm2 native panes when available; add `--tmux=classic` for traditional tmux.
495|
496|## Parallel Claude Instances
497|
498|Run multiple independent Claude tasks simultaneously:
499|
500|```
501|