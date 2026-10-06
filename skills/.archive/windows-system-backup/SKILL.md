---
name: windows-system-backup
description: "Create Windows system image backups via wbadmin."
version: 1.0.0
author: hermes-curator
---

# Windows System Backup (wbadmin / WindowsImageBackup)

## When to use
User asks to create a full Windows system image backup (WindowsImageBackup on a local disk), restore it, list existing backups, or check disk space / service readiness before backing up.

## Preflight (all read-only, batch into scripts)
1. **Disk target**: must be NTFS local disk with enough free space. Check free space + filesystem + drive type:
   `Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='D:'" | Select DeviceID, VolumeName, FileSystem, DriveType` (DriveType 3 = local fixed; 4 = removable/network). wbadmin wants a local fixed NTFS disk.
2. **Admin rights**: confirm `[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)`.
3. **Service**: `Get-Service -Name wbengine` — it stays Stopped but starts on demand; presence is what matters, not status.
4. **Existing backups**: `wbadmin get versions -backupTarget:D:` and check `D:\WindowsImageBackup`. NEVER overwrite/delete existing backups unless the user explicitly asks.

## CRITICAL PITFALL — client vs Server wbadmin syntax
- `-allVolumes` is **valid only on wbadmin Server edition**. On Windows 10/11 **client** wbadmin 1.0 it fails with: `ERREUR - L'une des options ou des paramètres spécifiés n'est pas valide : allVolumes`, then prints the help screen.
- The client equivalent that includes every critical system volume (C:, EFI System partition, Recovery) is **`-allCritical`**.
- Correct client command: `wbadmin start backup -backupTarget:D: -include:C: -allCritical -quiet`
  (`-include:` explicit + `-allCritical` ensures EFI/recovery are captured too — same intent as the requested `-allVolumes`.)
- A syntax error makes wbadmin exit quickly and dump its help text — if the background job returns almost immediately with help output, treat it as a failed invocation, not a finished backup.

## Execution
- Backup of the full C: image is a LONG operation (up to tens of minutes). Run it in the background with output logged via `Start-Transcript` so progress and the final ExitCode survive without blocking.
- Then confirm real progress via `Get-WBJob | Select JobState, PercentComplete`, or just let the transcript lines (`Récupération des informations de volume...`, then per-volume `... (100%) copiés`) confirm volumes are being written.

## Verify + report
- List backup: `wbadmin get versions -backupTarget:D:`
- Confirm exact location `D:\WindowsImageBackup\<computername>\Backup YYYY-MM-DD HHMMSS`, date + size. Check the folder with `Get-ChildItem` and measure size.
- Report to the user: date, size, exactly what was captured (which volumes), and the target path.

## General gotcha — PowerShell via bash/terminal
When running PowerShell through the Hermes bash terminal, `$_`, `$id` etc. get eaten by bash (extends to `$_`/`$var`/`1GB`). ALWAYS write the PS code to a `.ps1` file first, then run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <path>` — do not inline multi-statement PS with `$` into a terminal command. For a long background job add `-WindowStyle Hidden`.
