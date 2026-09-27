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

## Le libellé « running » de `hermes profile list` est trompeur

`hermes profile list` affiche un statut Gateway par profil. Ce statut ne reflète **pas** la réalité du
gateway : un profil peut apparaître `running` sans qu'aucun canal ne le serve.

Mesure (27/09/2026) : `docs-writer` (profil créé à 12:36) affiche `running`, alors que
`logs/gateway-health.state.json` ne le liste dans **aucun** battement — 12:00:04 et 13:00:05, canaux
relevés : default, watch, surveillance_bot, veille. Aucun canal de messagerie n'est déclaré dans sa
config : aucun bot ne peut lui parler.

Ce que le libellé signifie réellement : le profil existe dans l'inventaire. Ce qu'il ne dit pas : le
gateway le sert. Pour savoir si un canal est servi, la source est `logs/gateway-health.state.json`,
jamais `hermes profile list`.

## Limite observée : deepseek-flash over-affirme

Sur une question de comptage (fichiers de `wiki/concepts/` contenant « Laya »), deepseek-flash a répondu
juste — 1 fichier, le bon — puis a ajouté une affirmation non vérifiée : « comptage identique en sensible
et insensible à la casse ». Mesure : 9 occurrences en sensible, 14 en insensible. La réponse était bonne,
le détail ajouté était faux.

À surveiller pour tout profil qui produit de la documentation : les chiffres, les dates et les noms de
fichiers doivent être relus contre la mesure. Le modèle comble les trous par plausibilité, pas par
mesure — un chiffre juste en tête de réponse n'authentifie pas ce qui le suit.
