---
name: windows-performance-tuning
description: "Optimize a Windows PC: audit, power/GPU tune, debloat."
version: 1.0.1
author: hermes-curator
---

# Windows Performance Tuning

## When to use
User asks to optimize / speed up / audit a Windows desktop or laptop (CPU, GPU, RAM, storage), update drivers, debloat, or "get maximum performance" for gaming/creation/heavy multitasking.

## Workflow (this order)
1. **Audit first (read-only)** — gather hardware + current state before touching anything. Full command bank in `references/windows-optimization-commands.md`. Confirm: CPU model, GPU (nvidia-smi), RAM speed + channel mode (InterleavePosition), disks + SMART, temps, active power plan, HAGS, HVCI/VBS, hypervisor state, TRIM.
1b. **Startup audit** — identify ALL console window sources and duplicate launchers. Run `scripts/audit-startup.ps1` to dump registry Run keys + logon-trigger scheduled tasks + Startup folder + action details (Hidden flag, WSH vs direct). Cross-check for duplicate Hermes gateway tasks (`HermesGateway` vs `Hermes_Gateway` both running). See `references/startup-audit.md` for full diagnostic pattern. Prevent Console Flashes — If scheduled tasks cause flashes, see `references/console-flash-prevention.md` (use wscript.exe //B wrapper or pwsh -WindowStyle Hidden).
2. **Report + honest plan** — split findings into "already optimal", "real levers", "myths". Flag the ONE critical tradeoff (HVCI / Hyper-V = 5-15% perf vs security + VM/WSL2 breakage) and ask before that specific change.
3. **Precautions** — create restore point (`Checkpoint-Computer`) + export drivers (`pnputil /export-driver * <dir>`) BEFORE any write. Also write a `restore.ps1` that undoes each change.
4. **Apply safe optimizations** — power plan (core parking off, boost aggressive), disable HVCI, disable telemetry (DiagTrack), visual effects → performance, cleanup (temp/recycle/DNS).
5. **Integrity checks in BACKGROUND** — `dism /online /cleanup-image /restorehealth` + `sfc /scannow` + `chkdsk` on non-system drives. Report results; don't ask user to sit through them.
6. **Reboot, verify** — show nvidia-smi / powercfg / disk space after reboot.

## WindowsImageBackup (full system image)

When asked to create a full system image backup (`WindowsImageBackup`):
1. Verify target drive: NTFS, ≥50 GB free, admin rights.
2. Check backup engine: `Get-Service wbengine` (Stopped is normal — starts on demand).
3. **CRITICAL PITFALL**: `wbadmin start backup -allVolumes` is Windows **Server** only. On Windows 11 client editions, use **`-allCritical`** instead — it includes all system-critical volumes (EFI, Recovery, C:). Same objective, different flag.
4. Run in background with logging — write a `.ps1` with `Start-Transcript`, `wbadmin start backup -backupTarget:D: -include:C: -allCritical -quiet`, `Stop-Transcript`. Execute with `powershell -WindowStyle Hidden -File`.
5. Verify: `wbadmin get versions -backupTarget:D:` — should list the backup with its recovery capabilities (Volume, File, Application, Full recovery, System state).

**PowerShell note**: avoid inline `$_` in bash — it gets mangled. Always write `.ps1` scripts and execute with `-ExecutionPolicy Bypass -File`.

## Honest vs myth — refuse the myths even when asked
REAL levers: HVCI/VBS off, power plan (High Performance + core parking off + boost Aggressive), HAGS on, NVIDIA "prefer max performance" + ultra low latency + shader cache, TRIM on, disable DiagTrack, visual effects → performance, Studio driver for creators.
MYTHS (apply nothing): `Win32PrioritySeparation=38` (leave default 2), `LargeSystemCache=1` (server setting, harms workstations), global Nagle/"gaming TCP" tweaks (nil on 1 Gbps LAN), RSS on Realtek GbE (unsupported), "disable VRAM compression" (no such control), forcing min-processor-state 100% for a "snappier" idle (just raises heat; turbo ramps instantly — min 5% + max 100% + Aggressive is equally fast and cooler).

## Pointer
- `references/windows-optimization-commands.md` — verified command bank (WMI/PowerShell/nvidia-smi/powercfg/registry/cleanup/integrity).
- `references/startup-audit.md` — startup audit patterns and duplicate detection.
- `references/console-flash-prevention.md` — fix scheduled-task console flashes.
- `scripts/audit-startup.ps1` — registry + task + folder audit.
- `scripts/restore.ps1` — undo script template.