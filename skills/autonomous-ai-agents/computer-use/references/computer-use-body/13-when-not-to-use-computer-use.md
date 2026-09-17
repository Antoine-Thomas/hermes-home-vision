<!-- Source: autonomous-ai-agents/computer-use/SKILL.md · section 'When NOT to use `computer_use`' -->

## When NOT to use `computer_use`

- **Web automation you can do via separate headless `browser_*` tools** — those use a
  real headless Chromium and are more reliable than driving the user's
  GUI browser. Reach for `computer_use` specifically when the task
  needs the user's actual native apps (Finder/Explorer/Files, Mail/
  Outlook/Thunderbird, native chat clients, Figma, Logic, games,
  anything non-web).
- **File edits** — use `read_file` / `write_file` / `patch`, not
  `type` into an editor window.
- **Shell commands** — use `terminal`, not `type` into Terminal.app /
  Windows Terminal / gnome-terminal.
