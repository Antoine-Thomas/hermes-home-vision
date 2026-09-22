<!-- Source: autonomous-ai-agents/computer-use/SKILL.md · section 'The verify → escalate ladder (background-first)' -->

## The verify → escalate ladder (background-first)

cua-driver delivers input in the **background** by default (no focus steal),
but that is the first rung, not the only one. Every input action returns a
structured verdict; read it and climb only when the driver tells you to.

Returned fields (present when the driver supports them):
- `effect`: `"confirmed"` (driver read the result back — done), `"unverifiable"`
  (delivered, but confirm it yourself by re-capturing), or `"suspected_noop"`
  (ran but almost certainly did nothing).
- `escalation`: `{recommended: "px" | "foreground", reason}` — present
  only when there's a next rung to try.
- `code`: a structured refusal like `"background_unavailable"` or
  `"foreground_unsupported"`.
- `verified`: `true` only on AX read-back.

Walk it in order:

1. **Element, background (default).** `click(element=N)`. If `effect:"confirmed"`,
   you're done.
2. **Fresh verification.** `effect:"unverifiable"` means inspect a fresh
   capture/state before any retry. Do this even when `escalation.recommended`
   is present; it is advisory, not proof that successful input should repeat.
3. **Pixel, background.** After `effect:"suspected_noop"` or a structured
   refusal recommends `"px"` (or a `degraded` capture has no elements), click
   by `coordinate=[x,y]` instead of `element`.
4. **Foreground.** After `effect:"suspected_noop"`,
   `code:"background_unavailable"`, or a verified pixel no-op,
   re-issue the SAME action with `delivery_mode="foreground"`. This briefly
   raises the window and restores focus after; pair with `bring_to_front=True`
   for a short sequence to avoid per-call flashes. It needs its own approval
   (it's a visible focus change) and is only appropriate when the user isn't
   actively working. Classic cases: Electron/Chromium consent dialogs (e.g.
   tldraw offline's "Run Script"), DirectInput games, raw-input canvases.
5. **Keystrokes verified-lost on a KDE/Qt editor → use the app's own I/O.**
   Some Qt text components (KTextEditor: Kate, KWrite, KDevelop) discard
   SYNTHETIC X keystrokes entirely — foreground `type` reports ok
   ("Typed N characters into the focused widget", `effect:"unverifiable"`)
   but a fresh AX capture shows the text never arrived, and raw XTest fails
   identically (proven live, Aug 2026 — it is the toolkit, not the driver;
   the same foreground route works on kcalc/Chrome). After ONE such
   verified-lost round trip, stop retrying input rungs: write the file with
   terminal/file tools and let the editor reload it, or drive the app's
   DBus/CLI interface. Never loop the ladder against a surface that
   verifiably swallows synthetic input.

```
computer_use(action="click", element=7)
# → {effect: "suspected_noop", escalation: {recommended: "foreground", ...}}
computer_use(action="click", element=7, delivery_mode="foreground")
# → {effect: "unverifiable", path: "x11_pixel_fg"}   then re-capture to confirm
```

**Escalate to foreground as a REACTION to a returned signal, never as a
prediction** from the app being Electron/Chromium/GTK. A confirmed effect is
done and must not be duplicated. Different controls in
the same app behave differently. Do NOT silently retry the same rung, and do
NOT conclude "cua-driver can't drive this app" — climb the ladder. If
`delivery_mode="foreground"` returns `code:"foreground_unsupported"`, the live
action schema lacks that property; choose another verified rung without
inferring support from the executable's reported version.
