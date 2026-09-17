<!-- Source: autonomous-ai-agents/computer-use/SKILL.md · section 'Managing what's focused' -->

## Managing what's focused

`list_apps` returns running apps with bundle IDs / process names, PIDs,
and window counts. `focus_app` routes input to an app without raising
it. You rarely need to focus explicitly — passing `app=...` to
`capture` / `click` / `type` will target that app's frontmost window
automatically.
