<!-- Source: autonomous-ai-agents/computer-use/SKILL.md · section 'Failure modes — what to do when things go sideways' -->

## Failure modes — what to do when things go sideways

| Symptom | Likely cause + remedy |
|---|---|
| `cua-driver not installed` | Run `hermes computer-use install`, or `hermes tools` and enable Computer Use |
| Captures consistently return empty / "no on-screen window" | On Linux: DISPLAY may not be set (X11) or you're on pure Wayland — ask the user to run `hermes computer-use doctor`. On Windows: you may be in Session 0 (SSH session) instead of the interactive desktop — see the cua-driver `WINDOWS.md` deep-dive |
| Element index stale ("Element N not in cache") | SOM indices are only valid until the next `capture`. Re-capture before clicking. The wrapper carries opaque `element_token`s for stale-detection; you'll see an explicit error rather than a wrong click |
| Click had no effect | Read the structured verdict. `effect:"unverifiable"` → fresh capture/state before retry, even with an escalation hint. `effect:"suspected_noop"` or a structured refusal → climb the recommended ladder: coordinate (px), then foreground. Browser chrome/native prompts remain native; page content is a separate toolset. Don't conclude the app is undrivable |
| Type text disappears into a terminal emulator | cua-driver detects terminals (Ghostty, iTerm2, Terminal.app, Windows Terminal, mintty, etc.) and routes through key-event synthesis — should "just work" on a recent cua-driver. If it doesn't, ask the user to run `hermes computer-use doctor` |
| `blocked pattern in type text` | You tried to `type` a shell command matching the dangerous-pattern block list (`curl ... \| bash`, `sudo rm -rf`, etc.). Break the command up or reconsider |
| Anything else weird | **First action: ask the user to run `hermes computer-use doctor`.** It runs the cua-driver `health_report` MCP tool and prints a structured per-check matrix. Their output tells you (and them) exactly what's wrong |
