---
name: mcp-server-setup
description: "Use when connecting an MCP server to Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [mcp, integration, tools, oauth, hermes]
    category: devops
---

# MCP server setup (Hermes)

Connect an external MCP server (remote OAuth or stdio) to Hermes so its tools
load into agent sessions. `hermes mcp` is the entry point: `add`, `login`, `list`,
`test`, `configure`, `reauth`, `remove`.

## Remote OAuth server (e.g. Scite)

1. `hermes mcp add <name> --url <endpoint> --auth oauth`
   `add` starts the OAuth flow immediately. In a non-interactive terminal it fails
   with « non-interactive environment and no cached tokens » then prompts
   « Continue without authentication? / Save config anyway? ». Pipe `y\ny` to save
   the config anyway (it lands as `enabled: false`).
2. `add` records `auth=None` when the OAuth flow failed (the « continue without
   auth » path). Reset it: `hermes config set mcp_servers.<name>.auth oauth`.
3. `hermes mcp login <name> --flow browser`
   Prefer `--flow device` ONLY when the server advertises RFC 8628 device
   authorization; many don't (error: « Server does not advertise device
   authorization »). `--flow browser` (PKCE) opens the PC browser; if the user is
   already signed in there it auto-completes (« ✓ Authenticated — N tool(s)
   available »).
4. `hermes config set mcp_servers.<name>.enabled true`
   Auth alone is not enough — a server saved by a failed `add` is `enabled: false`
   and loads no tools until this is flipped.
5. `hermes mcp test <name>` — expect `✓ Connected` + `✓ Tools discovered: N`.

## Pitfalls

- `config.yaml` is security-sensitive: the `patch`/`write_file` tools refuse to
  write it. Use `hermes config set <dotted.key> <value>` and
  `hermes config get <dotted.key>` instead.
- OAuth tokens expire; refresh with `hermes mcp reauth <name>`.
- A server at `enabled: false` loads no tools even after a successful login —
  `hermes mcp list` shows status `✗ disabled` while `hermes mcp test` still
  succeeds; flip `enabled` to fix.
