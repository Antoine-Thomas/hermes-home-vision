# Windows Optimization — Verified Command Bank

All commands were run and verified on Windows 11 Pro via git-bash (MSYS). Run `powershell.exe -NoProfile -Command "..."` for anything with `$_` (escape as `\$_`) or write a `.ps1` and run with `-File`. Admin rights required for writes.

## Audit (read-only)

### CPU / motherboard / BIOS / OS
```bash
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,L2CacheSize,L3CacheSize | Format-List; Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,Version | Format-List; Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate | Format-List"
```

### RAM (speed, XMP, dual-channel)
```bash
powershell.exe -NoProfile -Command "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer,PartNumber,Capacity,Speed,ConfiguredClockSpeed,DeviceLocator,BankLabel,InterleavePosition | Format-Table -AutoSize"
```
- `Speed` == `ConfiguredClockSpeed` → XMP/DOCP active.
- `InterleavePosition` = 1 and 2 present across ChannelA/ChannelB → dual channel.

### GPU
```bash
nvidia-smi --query-gpu=name,driver_version,vbios_version,memory.total,temperature.gpu,pcie.link.gen.current,pcie.link.width.current --format=csv
nvidia-smi --query-gpu=pcie.link.gen.max,pcie.link.width.max --format=csv
powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,AdapterRAM | Format-List"
```

### Storage + SMART
```bash
powershell.exe -NoProfile -Command "Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,HealthStatus,@{n='SizeGB';e={[math]::Round(\$_.Size/1GB,1)}} | Format-Table -AutoSize; Get-Disk | Get-StorageReliabilityCounter | Select-Object DeviceId,Temperature,ReadErrorsTotal,WriteErrorsTotal,Wear,PowerOnHours | Format-Table -AutoSize"
```
- `Get-PhysicalDisk` HealthStatus is coarse; `Get-StorageReliabilityCounter` gives real read/write error counts and NVMe `Wear`.

### Temperatures (CPU) — often empty on desktops
```bash
powershell.exe -NoProfile -Command "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object InstanceName,@{n='TempC';e={[math]::Round((\$_.CurrentTemperature/10)-273.15,1)}} | Format-Table"
```

### Power / security / GPU state
```bash
powercfg /getactivescheme                       # active power plan
reg query "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v HwSchMode   # 2 = HAGS on
fsutil behavior query DisableDeleteNotify       # 0 = TRIM enabled
bcdedit /enum '{current}' | grep -i hypervisorlaunchtype
powershell.exe -NoProfile -Command "Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard | Select-Object VirtualizationBasedSecurityStatus,SecurityServicesRunning | Format-List; (Get-CimInstance Win32_ComputerSystem).HypervisorPresent"
powershell.exe -NoProfile -Command "Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity' -ErrorAction SilentlyContinue | Select-Object Enabled | Format-List"   # 1 = HVCI on
```

### Pending reboot / pending updates
```bash
powershell.exe -NoProfile -Command "if(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name PendingFileRenameOperations -ErrorAction SilentlyContinue){'REBOOT REQUIS'}else{'pas de reboot'}"
```

## Optimizations (admin)

### Precautions
```bash
powershell.exe -NoProfile -Command "Checkpoint-Computer -Description 'Avant optimisation' -RestorePointType MODIFY_SETTINGS"
pnputil /export-driver * "C:\path\drivers_backup"     # backup ALL 3rd-party drivers
```

### HVCI (Memory Integrity) OFF — reversible, VM-safe
```bash
reg add 'HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity' /v Enabled /t REG_DWORD /d 0 /f
```

### Disable telemetry
```bash
sc.exe config DiagTrack start= disabled
sc.exe stop DiagTrack
```

### Visual effects → performance
```bash
reg add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects' /v VisualFXSetting /t REG_DWORD /d 2 /f
reg add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' /v EnableTransparency /t REG_DWORD /d 0 /f
```

### Power plan — unpark cores + aggressive boost (alias form; no GUIDs to memorize)
```bash
powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMINCORES 100        # disable core parking
powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100
powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100
powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTMODE 2      # 2 = Aggressive (turbo)
powercfg -setactive SCHEME_CURRENT
```
GUIDs if aliases are unavailable: SUB_PROCESSOR `54533251-82be-4824-96c1-47b60b740d00`; CPMINCORES `0cc5b647-c1df-4637-891a-dec35c318583`; PROCTHROTTLEMIN `893dee8e-2bef-41e0-89c6-b55d0929964c`; PROCTHROTTLEMAX `bc5038f7-23e0-4960-96da-33abaf5935ec`; PERFBOOSTMODE `be337238-0d82-4146-a960-4f3749d470c7`.
Verify with `reg query` against the scheme GUID (the plan's embedded default shows nothing until you set it explicitly).

### Cleanup
```bash
powershell.exe -NoProfile -Command "Get-ChildItem \$env:TEMP -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Get-ChildItem C:\Windows\Temp -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
ipconfig /flushdns
```

### Integrity (BACKGROUND, sequential)
```bash
powershell.exe -NoProfile -Command "dism.exe /online /cleanup-image /restorehealth; sfc.exe /scannow"
```
`dism` shows live progress %; run `sfc` only AFTER `dism` finishes.

### Optional final lever — remove Hyper-V hypervisor (only if user has no WSL2/Docker/Hyper-V VMs)
```bash
bcdedit /set hypervisorlaunchtype off
dism /online /disable-feature /featurename:Microsoft-Hyper-V-All /norestart
```

## Notes
- `Get-NetAdapterRss` — Realtek GbE adapters generally don't expose RSS; don't force it.
- NVIDIA 3D global settings (low latency, prefer max performance, shader cache) are stored in the driver profile DB — not reliably scriptable; give a manual NVIDIA Control Panel checklist instead.
