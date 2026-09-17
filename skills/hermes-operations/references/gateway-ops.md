# Gateway ops — double-process et restart

## Double-process normal

hermes gateway status affiche 1 PID mais Win32_Process montre 2 python.exe *gateway*:
- Parent: `...\.venv\Scripts\python.exe -m hermes_cli.main gateway run` PPID = Task Scheduler (PID 15536)
- Enfant: `...\.hermes-runtime\python\generation-...\python.exe -m hermes_cli.main gateway run` PPID = parent

Ne pas tuer l'enfant seul → "No gateway process detected". Seuls les stale generations (CreationDate < dernier schtasks /Run /TN Hermes_Gateway, ou PID ≠ hermes gateway status) sont à taskkill.

Vérifier avec:
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.CommandLine -like '*gateway*'} | Format-Table ProcessId,ParentProcessId,CreationDate -AutoSize
```

## Restart fiable

- `schtasks /Run /TN Hermes_Gateway` ou `hermes gateway restart` → attendre 7–9s
- Vérifier `hermes gateway status` ET `Get-Content "$env:LOCALAPPDATA/hermes/logs/gateway.log" -Tail 25` → chercher "telegram connected", "polling healthy", "set_my_commands OK"
- Log tail est autoritaire: status peut dire "No gateway process detected" pendant warmup 2s ("Turn machinery warmed")
- ESTOP: `Test-Path "$env:LOCALAPPDATA/hermes/ESTOP"` doit être False; sinon `Remove-Item -Force` puis re-vérifier
- Channel: 1 DM 8956868107 dans channel_directory.json (hermes-telegram). Si 2 tokens distincts → `hermes gateway setup` pour 2e canal.

## Mémoire quasi pleine

Limite 2200 chars. Avant d'ajouter photo/record/com, compacter le bloc Telegram en abrégeant (PID, NIM off, chemins courts), viser <2120. Runbook porte le détail (10750 chars après ajout surveillance).
