<!-- Source: autonomous-ai-agents/hermes-agent/SKILL.md · section 'Surfaces & Other Capabilities' -->

## Surfaces & Other Capabilities

Beyond the CLI and gateway, a few things worth knowing about:

- **Desktop app** (`hermes desktop` / `hermes gui`) — native Electron app
  for macOS/Linux/Windows: streaming chat, session list, drag-and-drop +
  clipboard-paste files, Cmd+K palette, status-bar model picker,
  rebindable shortcuts, native notifications, live subagent watch-windows,
  VS Code Marketplace themes, and per-profile remote-gateway login (OAuth
  or username/password) so a thin local GUI can drive a heavy remote agent.
- **Web dashboard** (`hermes dashboard`) — full admin panel: configure
  every messaging channel, the MCP catalog, webhooks/hooks, memory, and a
  complete profile builder (model + skills + MCPs) from the browser, plus
  an embedded `hermes --tui` chat. Secured behind an OAuth/token gate.
- **OpenAI-compatible proxy** (`hermes proxy`) — exposes a
  `http://localhost:port` OpenAI API backed by whichever OAuth provider
  you're signed into (Claude Pro, ChatGPT Pro, SuperGrok). Point Codex
  CLI, Aider, Cline, Continue, or any script at it — no API key.
- **Automation Blueprints** — pick a named automation and Hermes asks for
  what it needs (no cron syntax). One definition renders as a dashboard
  form, a slash command, an agent conversation, and a docs-catalog entry.
- **`memory` tool batch operations** — pass an `operations` array of
  add/replace/remove edits applied atomically against the final character
  budget, so a single call can free space and add entries even when an add
  alone would overflow.
- **`session_search`** — FTS5-backed, no aux-LLM, effectively free. One
  tool, three modes inferred from which args are set: discovery (`query`),
  scroll (`session_id` + `around_message_id`), browse (no args).
- **xAI Grok via SuperGrok OAuth** — sign in with your xAI account (no API
  key); includes Cursor's `grok-composer-2.5-fast` coding model.

---
