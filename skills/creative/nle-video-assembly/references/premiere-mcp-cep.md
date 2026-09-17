# Premiere MCP CEP installer (premiere-pro-mcp)

The README may reference `npm run install-extension` — that script does not
exist in 1.15.0+. Use the CLI entry point.

## Install / diagnose / uninstall

```
npm install
npm run build
node dist/index.js --install-cep      # installs CEP panel
node dist/index.js --diagnose-cep     # check only
node dist/index.js --doctor           # local install check
node dist/index.js --uninstall-cep    # remove
```

* Source: `cep-plugin/`
* Destination: `%APPDATA%\Adobe\CEP\extensions\MCPBridgeCEP`
  (`C:\Users\<user>\AppData\Roaming\Adobe\CEP\extensions\MCPBridgeCEP`)
  Older docs mention `com.mcp.premiere.bridge` — that is stale; the installer
  uses `MCPBridgeCEP`.
* Needs `PlayerDebugMode=1` under every `HKCU\Software\Adobe\CSXS.<ver>` from
  CSXS.9 through CSXS.14 (CSXS.12 = 2024+). Set with:

  ```
  for ver in 9 10 11 12 13 14; do reg add "HKCU\Software\Adobe\CSXS.$ver" /v PlayerDebugMode /t REG_SZ /d 1 /f; done
  ```

## Activation

1. Fully restart Premiere Pro (Beta) — `tasklist | grep -i premiere` should be empty before relaunch.
2. `Window > Extensions > MCP for Adobe Premiere Pro` — expect green dot "Listening on 127.0.0.1:3030".
3. Run MCP tool `premiere_status` / `Verify Premiere connection` to confirm stdio bridge.

## Version detection

* Premiere Beta exe: `C:\Program Files\Adobe\Adobe Premiere Pro (Beta)\Adobe Premiere Pro (Beta).exe`
  Version via PowerShell:
  `[System.Diagnostics.FileVersionInfo]::GetVersionInfo('...exe').FileVersion`
* Registry: `HKCU\Software\Adobe\Premiere Pro (Beta)\27.0` etc.
* CSXS.* debug keys live under `HKCU\Software\Adobe`.
