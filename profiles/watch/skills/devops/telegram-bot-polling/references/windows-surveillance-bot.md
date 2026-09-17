# Windows surveillance bot (@omaths_watch_bot) — diagnosis & restart playbook

Location: `C:\Users\searc\AppData\Local\hermes\data\surveillance\`
- `surveillance.ps1` — Telegram bot loop (`/watch`, `/stopcam`, `/video`) + ffmpeg capture.
- `stealth.ps1` — mute/unmute + screen off/on (Core Audio COM + user32 SendMessage).
- `README.md` — setup notes, Wake-on-LAN, HLS stream option.

Architecture: Telegram `getUpdates` loop. On `/watch` it mutes system audio, turns the
screen off, blocks sleep (`SetThreadExecutionState`), and captures a frame every 3 s +
an audio clip every 60 s via `ffmpeg -f dshow`; `/stopcam` restores sound/screen and
re-allows sleep; `/video` records a 15 s video+audio clip and sends it. A scheduled task
`SurveillanceBot` (ONLOGON trigger) runs:
`pwsh -NoProfile -WindowStyle Hidden -File ...\surveillance.ps1`

## CRITICAL — one bot token ≠ two pollers (2026-08-30 incident)

A Telegram bot has a SINGLE `getUpdates` offset stream. If two processes poll the same
token — e.g. the main Hermes gateway (python, PID 16900) AND `surveillance.ps1` — they
starve each other: whichever calls `getUpdates` last wins each cycle, so the surveillance
bot NEVER sees its `/watch` `/stopcam` `/video` commands (the gateway eats them). Symptom:
`/video` produces no file, `frame.jpg` never updates, yet `getMe` on the token is fine and
the pwsh process is "Running".

**Rule: the surveillance bot MUST have its own dedicated bot token**, separate from the
Hermes gateway bot. If a token was reused by mistake, do NOT try to "patch the gateway to
ignore those commands" — that still fails because the gateway consumes the offset first.
Fix = create a fresh bot via BotFather (`/newbot`) and point `surveillance.ps1` at it.
This session: old `@omaths_watch_bot` token was lost/redacted; the gateway token
`8802352038` (Hermes_assistante_2026_bot) was tried and starved the bot; fix was a new
bot **`@Omaths2_watch_bot`** (token `8967117033:...`), which runs cleanly on its own stream.

## Token externalization (so it survives copies/redactions)

`surveillance.ps1` line ~13 must NOT hardcode the token. Read it from a sidecar file +
env var, with fallback:

```powershell
$WORKDIR    = Split-Path -Parent $MyInvocation.MyCommand.Path   # MUST be defined BEFORE use
$TOKEN_FILE = Join-Path $WORKDIR 'token.sec'
$token = if (Test-Path $TOKEN_FILE) { (Get-Content $TOKEN_FILE -Raw).Trim() }
         elseif ($env:WATCHBOT_TOKEN) { $env:WATCHBOT_TOKEN }
         else { throw 'No bot token: set WATCHBOT_TOKEN or token.sec' }
```

`token.sec` lives next to the script; rights are restricted to the user. A redacted
`***` placeholder in the script no longer breaks anything because the real token is read
externally.

## PowerShell init-order pitfall ($WORKDIR crash)

If `surveillance.ps1` references `$WORKDIR` (e.g. to build `$TOKEN_FILE`) BEFORE the line
that defines it, the variable is `$null` at that point and `Join-Path $null 'token.sec'`
resolves to a bad path → the bot silently dies at startup with NO stdout error (the
catch only prints Telegram errors). Symptom: scheduled task shows `Running` briefly then
the pwsh process vanishes; the only clue is a missing "Bot prêt" message. Fix: define
`$WORKDIR = Split-Path -Parent $MyInvocation.MyCommand.Path` as the FIRST line of the
CONFIG block, before any use.

## ffmpeg webcam "device already in use"

`ffmpeg -f dshow` capture fails with *"Could not run graph (sometimes caused by a device
already in use by other application)"* if a previous capture (or another app — OBS,
NVIDIA Broadcast, a leftover ffmpeg) still holds the camera. A `/video` then writes a
0-byte or moov-less file. Always add `-movflags +faststart` so the file is valid if capture
succeeds, and ensure the prior ffmpeg process has fully exited before the next capture.

## Diagnosis checklist (when "the bot stopped responding")

1. **Is a pwsh process running the bot?**
   `Get-CimInstance Win32_Process -Filter "Name='pwsh.exe'" | ? { $_.CommandLine -like '*surveillance.ps1*' }`
   (Empty result = bot is down; that alone explains "not responding".)
2. **Scheduled-task health** (did it fire? what exit code?):
   `Get-ScheduledTask -TaskName SurveillanceBot` → State `Ready` vs `Running`.
   `Get-ScheduledTaskInfo -TaskName SurveillanceBot` → `LastRunTime`, `LastTaskResult`, `MissedRuns`.
   `LastTaskResult 0` = success. `0xC0000142` = STATUS_DLL_INIT_FAILED (process died at
   init — this is what killed the bot in the 2026-08 incident; relaunching via
   `Start-Process` worked fine, so the DLL failure was transient/launch-context-specific).
3. **Validate token + chat id WITHOUT echoing the token**: regex the `CONFIG` block,
   then `getMe` (expect `ok=true`, `@omaths_watch_bot`) and `getUpdates?offset=-1` to see
   pending commands + `chat.id`.
4. **Webcam / mic / ffmpeg present:**
   `ffmpeg -list_devices true -f dshow -i dummy`
   Expect video `"Microsoft LifeCam VX-800"` and audio `"Microphone (2- Microsoft LifeCam VX-800)"`.
5. **Test the full pipeline before declaring healthy**: capture 1 frame, 3 s audio,
   5 s video+audio, then `sendPhoto` — verify each file is non-empty and the photo lands
   on Telegram. This isolates hardware vs network failures from the bot logic.

## Restart (background, hidden window)

```
$p = Start-Process -FilePath pwsh `
    -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-File','...\surveillance.ps1') `
    -WindowStyle Hidden -PassThru
```
Confirm it stays alive after ~6 s (`Get-Process -Id $p.Id`); a `409 Conflict` on a probe
`getUpdates` means it is now actively polling.

Note: on startup with `offset=0` the bot replays ALL unconfirmed updates (old `/watch`,
`/stopcam`, `/video`), so it may briefly re-activate surveillance or record a video.

## Windows gotchas that bit here

- **`powershell` (5.1) vs `pwsh` (7) encoding**: `powershell.exe` reads a BOM-less `.ps1`
  as the system ANSI codepage, so UTF-8 emojis/accents break the parser ("Jeton inattendu",
  "Le littéral de hachage est incomplet"). `pwsh.exe` defaults to UTF-8. Run any `.ps1`
  containing emojis/accents with `pwsh`, never `powershell`. (The bot itself is fine — the
  scheduled task launches it under `pwsh`.)
- **`schtasks /Query` emits UTF-16** → piping to grep yields "Binary file matches". Prefer
  `Get-ScheduledTask` / `Get-ScheduledTaskInfo` instead.
- **MSYS git-bash mangles leading `/` args** of native Windows commands (`tasklist //FI`
  fails). Prefix with `MSYS_NO_PATHCONV=1`.
- **Run scripts from bash with `-ExecutionPolicy Bypass`** to avoid policy friction:
  `pwsh -NoProfile -ExecutionPolicy Bypass -File <script>`.
