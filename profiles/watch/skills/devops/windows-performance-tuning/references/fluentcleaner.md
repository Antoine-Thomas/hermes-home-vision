# FluentCleaner — management notes (Windows cleaner by builtbybel)

Official repo (ONLY source): https://github.com/builtbybel/FluentCleaner
⚠️ `fluentcleaner.org` is a FRAUDULENT site with no affiliation — the README itself warns against it. Never download from it.

## Two flavors (same cleaning engine + winapp2.ini parser, different runtime)

| | Modern (`FCleaner.exe`) | Classic (`FluentCleaner.Classic.exe`) |
|---|---|---|
| Framework | WinUI 3 (.NET 10 + Windows App SDK) | .NET Framework 4.8 WinForms |
| Version format | date-based, e.g. `26.08.01` | semantic, e.g. `1.13.137` |
| Install path | `%LocalAppData%\FluentCleaner\FCleaner.exe` | `C:\Program Files\FluentCleaner\FluentCleaner.Classic.exe` |
| Deployment | self-contained (~140 MB, bundles runtime) | framework-dependent (~3.5 MB) |
| Release asset | `FluentCleaner-win-x64.zip` | `FluentCleaner-Classic-net48.zip` |

Determine which one the user runs from the desktop-shortcut target and the exe name (`"fcleaner.exe"` = `FCleaner.exe` = modern). The two versions have SEPARATE settings files and can coexist.

## Version / release detection

- Exe file version: `powershell.exe -NoProfile -Command "(Get-Item 'C:\...\FCleaner.exe').VersionInfo.FileVersion"`
- Latest release: `curl -s https://api.github.com/repos/builtbybel/FluentCleaner/releases/latest`
- PITFALL: `/releases/latest` resolves to the newest release OVERALL, which can be a Classic-only tag (e.g. `classic-1.13.137`) that has NO modern asset. Query the explicit tag (`/releases/tags/26.08.01`) for the modern zip's download URL.
- winapp2.ini version lives in the file header: `; Version: 260730` + `; # of entries: 4,075`. Repo commits read "update Winapp2 to v260730".

## Clean update procedure (preserves user data)

1. Confirm the exe is not running (`tasklist`). User settings live in `%AppData%\Roaming\FluentCleaner\settings.json` — SEPARATE from the install dir, so a directory swap does NOT touch the saved selection.
2. Download the zip, verify size/SHA256 against the published asset, unzip to a temp dir. Confirm the new exe version + winapp2.ini header before installing.
3. Swap: `mv` old install dir → `<dir>.bak-<date>` (instant rollback on same volume), then `mv` new dir into place.
4. Restore user data from `.bak`: the `Custom/` folder (custom `.ini` cleaners + `.ps1` scripts) and any non-app subfolders (e.g. a stray `FluentCleaner-Classic-net48/`). MERGE, don't replace — keep both the release's sample files and the user's files.
5. Report the `.bak` path so the user can delete it after validating the new version.

## Command-line (silent / auto clean)

- `FCleaner.exe /AUTO` — silent clean using the SAVED selection, exits immediately (no UI, no prompts).
- `FCleaner.exe /AUTO /SHUTDOWN` — same + `shutdown.exe /s /t 0` after. `/SHUTDOWN` alone does nothing.
- Log: appended to `%AppData%\FluentCleaner\auto.log` (dir auto-created). Contains timestamp, deleted paths grouped by entry, and total freed size. It appears only after the first `/AUTO` run — do NOT trigger `/AUTO` just to test logging (it actually deletes files).
- No registry cleaner by design ("no fake registry magic").

## Scheduled task (weekly auto-clean)

Use the app's own task name so it never conflicts with the built-in scheduler UI: `FluentCleaner Modern AutoClean`.

Create from git-bash (see SKILL.md pitfalls for MSYS + quoting):
```
MSYS_NO_PATHCONV=1 schtasks /Create /TN "FluentCleaner Modern AutoClean" /TR "C:\Users\<user>\AppData\Local\FluentCleaner\FCleaner.exe /AUTO" /SC WEEKLY /D SUN /ST 03:00 /F
```
Verify:
```
MSYS_NO_PATHCONV=1 schtasks /Query /TN "FluentCleaner Modern AutoClean" /V /FO LIST | iconv -f CP850 -t UTF-8
```
Default `schtasks /Create` behavior (matches what the app itself does): runs only when the user is logged on (interactive) and does not start on battery. Fine for a desktop; note the caveat on a laptop.

## winapp2.ini / custom databases

- The built-in `Winapp2.ini` already derives from the community project https://github.com/MoscaDotTo/Winapp2 (release commits credit `@MoscaDotTo`). Keep the built-in by default; only switch to the full, unfiltered MoscaDotTo/Winapp2 database if the user wants more (but less curated) coverage.
- Custom DBs: `Settings > Database > Custom`, or drop `.ini` / `.ps1` files in the install's `Custom/` folder.

## Security

- Download ONLY from github.com/builtbybel/FluentCleaner. `fluentcleaner.org` is fraudulent.
- No registry cleaner (intentional), no spyware/scareware/dark-patterns/upsell.
