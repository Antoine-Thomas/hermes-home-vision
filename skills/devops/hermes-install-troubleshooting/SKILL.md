---
name: hermes-install-troubleshooting
description: "Diagnose Hermes update/install failures and dual installs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, install, update, troubleshooting, diagnosis]
    related_skills: [hermes-agent]
---

# Hermes Install & Update Troubleshooting

## When to Use

Load when `hermes update` errors, `hermes --version` reports an unexpected version,
`hermes doctor` disagrees between runs, or you suspect more than one Hermes install
on the machine. Hermes can be installed several ways (git clone + venv via the curl
installer, `pip install hermes-agent`, zip-updated copies) and a single box often
holds more than one.

## Safe update procedure (this user's setup)

- `hermes update` CAN be run from an agent terminal — it force-stops gateway processes itself ("Stopping Windows gateway process(es) before updating Hermes"). That self-stop is not a substitute for the supported preflight: stop every profile's gateway first (`hermes gateway stop` AND `hermes -p <profile> gateway stop`) so no writer holds the DB during the swap, then run `hermes update --plan` (read-only) before the real run. Full sequence in the `hermes-operations` skill. Note `hermes update` accepts no `--restart` flag (it is rejected as an unrecognised argument).
- **`git pull` on the live `hermes-agent` checkout is BLOCKED from inside a running Hermes session.** The terminal tool refuses with:
  `Blocked: \`git pull\` would rewrite Hermes's live source checkout (...) and can mix module versions in this running process. ... To change this checkout, stop Hermes, run the command externally, then restart Hermes.`
  The block is intentional: a pull swaps modules under the live interpreter. To update the checkout manually, stop Hermes first (close the app / stop the gateway / kill the `hermes.exe` tree), run `git -C "$HERMES_HOME/hermes-agent" pull` in a plain external shell, then restart. For inspection or a side build without stopping Hermes, use a separate worktree or a shared clone (`git clone --shared <checkout> <scratch>`), never a pull in place.
- **The user expects a pre-update audit and an explicit go-ahead before any change.** Report: any running GPU jobs (LatentSync, HuggingFace grafting, assembly, watchdog), `git status` of both the home and the agent checkout, locally patched scripts the update could overwrite, dependency versions (Python, CUDA, ffmpeg, key packages), and the exact backup size before launching it. Then stop and wait for approval; do not start the update in the same turn.
- **Commit the home repo's local changes to a dedicated branch before updating the agent.** The home (`$HERMES_HOME`) and the agent checkout (`$HERMES_HOME/hermes-agent`) are separate git repos; a branch such as `patchs-locaux-<date>` on the home gives a restore point for config/skills if the update breaks something. Sequence: `git checkout -b patchs-locaux-<date> && git add -A && git commit -m "Patchs locaux avant update" && git checkout main`. Verify the agent checkout itself has no local modifications before pulling (`git -C "$HERMES_HOME/hermes-agent" status --short`); if it does, show the user what is there before pulling.
  **Le `git checkout main` final RETIRE de l'arbre les fichiers qui n'etaient pas suivis.** Le `git add -A` de l'etape precedente les committe : ils deviennent suivis SUR LA BRANCHE, et comme `main` ne les connait pas, git les **supprime du disque** au retour. Tout contenu vivant jamais committe (skills crees a la main, scripts dans un dossier encore non suivi) disparait alors du parc — pas de la machine : il reste recuperable dans le commit de la branche. Donc, AVANT de traiter la branche comme un simple point de restauration : lister ce qu'elle capte (`git show --stat <sha>`), et APRES le retour sur `main`, prouver la presence des chemins concernes (recherche par nom de fichier, ou le compte de skills actifs si des skills sont en jeu). Restauration : `git checkout <branche> -- <chemins>` puis commit dedie — **jamais un merge global** de la branche, qui peut aussi porter une version ANCIENNE d'un fichier modifie depuis (`git diff --stat main..<branche>` le montre : le fichier apparait des deux cotes).
- **A running `hermes.exe serve` (dashboard/backend) BLOCKS the update before the updater's own serve-stop step.** The `Another hermes.exe is running` guard fires first, so the run aborts immediately; the updater then RELAUNCHES the serve backend it stopped, which re-arms the same block on the next attempt (observed looping over two runs). Working order: stop the serve wrapper tree yourself (`Stop-Process -Id <pid>` on `venv\Scripts\hermes.exe ... serve ...` **and** its python children, then confirm the port is free), run `hermes update -y`, then relaunch with `schtasks /Run /TN "Hermes - serve backend"` and confirm the headless signature on `http://127.0.0.1:9119/` (`web UI disabled — use 'hermes dashboard'`). A stray `venv\Scripts\python.exe` from outside the checkout (editor/LSP helper) trips the `Other Hermes processes are running from this install's venv` guard the same way — kill it instead of reaching for `--force-venv`.
- **Ce garde-fou annule le run APRES avoir arrete la gateway — et le run annule relance la gateway puis se termine.** Version et HEAD restent donc **inchanges** (`hermes --version` + `git rev-parse HEAD` avant/apres) : ce n'est pas une install partielle, le code n'a pas bouge, tuer le detenteur du venv puis relancer est sur. Ne jamais conclure « mise a jour echouee » depuis le seul code de sortie : lire le log du run.
- **Un run lance en arriere-plan n'ecrit rien dans le terminal.** Rediriger sa sortie vers un fichier choisi dans le home Hermes (`hermes update > "$LOCALAPPDATA/hermes/update_$(date +%s).log" 2>&1 &`) et lire ce log : c'est la seule source de la cause reelle (garde-fou venv, `serve` vivant, verrou concurrent).
- **Ne jamais lancer un second `hermes update` pendant que le premier tourne.** L'updater tient un verrou plusieurs minutes (il attend jusqu'a 190 s le drainage de la gateway) ; le second run avorte aussitot avec `Another Hermes update is already running (started <duree> ago, process <pid>)` / `Running two at once would corrupt the install`. Verifier d'abord que le processus a quitte (table des processus, cf. `windows-path-handling`), pas seulement que la version n'a pas bouge : un run encore vivant et un run termine sont indiscernables depuis `hermes --version`.
- **`updates.pre_update_backup: false` (this host) means the updater takes NO backup at all.** Check it first; when false, make the timestamped copies yourself (config.yaml, .env per profile, `memories/`, and each `state.db` via `sqlite3.Connection.backup` rather than a plain `cp` — the gateways are writing). The key also takes MODE strings — `quick` (state snapshot only, the code default) and `full` (zip of the whole HERMES_HOME) — overridden per run by `--no-backup` / `--backup`; the targeted set above weighs ~330 Mo on this host versus a multi-GB zip on a home with a heavy `data/`.
- **Two venvs can coexist in the checkout and only ONE is synced.** Here `hermes-agent/venv` (installer, on PATH) and `hermes-agent/.venv` (legacy/dev, used by some sessions) share the git checkout: the code is identical after an update but the dependency sets are not (`venv` 175 pkgs vs `.venv` 135, several shared pkgs older). Compare with `pip freeze` on both and report the drift — an update does not fix `.venv`.
- **L'update reecrit les LANCEURS du home et deplace le venv de reference.** Apres un run, le checkout `hermes-agent` reste propre mais le home devient sale : `gateway-service\Hermes_Gateway.cmd|.vbs` sont reecrits pour pointer `VIRTUAL_ENV` et le python sur `tools\python-<ver>-...\python.exe` (et non plus `hermes-agent\venv`), et `hermes doctor` annonce un venv runtime stage sous `installs\<id>\environments\<hash>\venv`. Consequence : « quel python sert la gateway » se lit sur le lanceur REEECRIT + la table des processus, jamais sur le venv du PATH ; et ces fichiers SUIVIS du depot home se committent comme etape a part (`chore(gateway): launchers rafraichis par l'update`) — un `git status` propre avant l'update ne le reste pas apres.
- **Identify which venv a running session uses, and which one a launcher targets, before deciding anything.** Session: `Get-CimInstance Win32_Process -Filter "Name='hermes.exe'" | Select-Object -ExpandProperty CommandLine` — a session started by hand from a venv path leaves NO shortcut, scheduled task or `Run` key behind — but do NOT conclude "no launcher targets venv X" from grepping the home, `.lnk` files and `Run` keys alone: that sweep missed a live `.vbs` that launched the serve backend from the STALE venv. The authoritative check is the process table + the scheduled-task action list + who owns the port:
```
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hermes-agent\.venv*' } | ForEach-Object { "$($_.ProcessId) $($_.Name) << $($_.CommandLine)" }
Get-ScheduledTask | Where-Object { $_.TaskName -like '*ermes*' } | ForEach-Object { "$($_.TaskName) | $(($_.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }))" }
(Get-NetTCPConnection -LocalPort 9119 -State Listen).OwningProcess    # then read that PID's CommandLine
```
Grep sweeps over the hermes home must exclude what is huge: `--exclude-dir=skills` (`.hub/index-cache/hermes-index.json` is a single-line ~100k-entry JSON whose matches alone return >100 MB and destroy the tool result), plus `hermes-agent`, `node_modules`, `cache`, `sessions`, `.archive`; pair with `-rlI --include='*.py' --include='*.ps1' --include='*.vbs'` and print file names (`-l`), not matching lines. Match on the FULL venv-qualified path (`hermes-agent\.venv\`), never the generic `.venv\Scripts` substring: the substring also matches OTHER projects' venvs (`data/hermes-optim/.venv`, `data/sdxl_lora/kohya_ss/.venv`, `data/rag/venv`) and produced both a false "no launcher references it" and a false "three scripts reference it" in one audit. Observed chains: `references/windows-launcher-chain.md`. Launchers: read the strings embedded in the `uv` trampoline — `bin\hermes.exe` carries an ABSOLUTE shebang (`#!...\venv\Scripts\python.exe`) while `venv\Scripts\hermes.exe` carries the relative `#!python.exe`, so the PATH shim always lands on `venv`. A stale venv is also betrayed by `pyvenv.cfg` (`home` = an older `.hermes-runtime\python\generation-*`) and by its `hermes_agent-<ver>.dist-info` (0.20.5 vs 0.21.3). Compare required deps (`pyproject.toml` `dependencies` vs `pip freeze` per venv): a version drift with NO missing dep is harmless, so don't touch it mid-session.
- **Never sync or delete a venv out from under the session running in it.** `pip install -r` from the healthy venv's freeze rewrites `site-packages` under a live interpreter (lazy imports break mid-run) and can DOWNGRADE toolchain packages (here torch 2.14.0 → 2.4.1+cu118). Retire a stale venv only after EVERY process using it is gone, by reversible rename (`Rename-Item .venv .venv.retired-<ver>`), then re-verify `hermes --version` + `hermes doctor` through the PATH shim. **Windows REFUSES that rename while any process holds files inside the venv** (`System.IO.IOException` / "L'accès au chemin … est refusé"), and the agent's own session is one of those processes — a rename attempted from inside the session always fails, so do not report it as done. Working order: repoint every launcher that names the stale venv (`.vbs`/task action, keep a `.bak`), restart that service so the port is served from the good venv (kill the old tree, confirm the port is free, then `schtasks /Run /TN "Hermes - serve backend"`), and hand the user a ready-to-run script to execute from a plain PowerShell — template: `templates/retire-stale-venv.ps1` (this host: `$HERMES_HOME\docs\retirer_venv_legacy.ps1`). Keep the retired dir ~30 days; rollback is the reverse rename.
- **Stash audit (`hermes-update-autostash-*` leftovers).** Export every entry as a patch first (`git stash show -p stash@{N} > stashN.patch`), then preserve real code in a branch pointing AT the stash commit (`git branch hermes/autostash-<label> stash@{N}`): no worktree, no write to the live tree, and the commit stays reachable after `git stash drop`. Verify with `git diff --stat <branch>^1 <branch>` (diffing the branch against `main` shows thousands of upstream files; `^1` shows exactly the stashed change). `git stash show -p -w` separates whitespace/EOL churn (droppable) from content, and drops must go highest index first since indices shift.
- All user customizations live OUTSIDE the git checkout: config.yaml, .env, skills/, scripts/, sessions/, state.db, memories/ are in the hermes home dir, not `hermes-agent/` (the checkout). A git pull / `hermes update` therefore never touches them — verify with `git status` (clean) rather than assuming.
- Before updating, copy with timestamp: config.yaml, state.db, memories/ (`cp <x> <x>.bak.update_$(date +%Y%m%d_%H%M%S)`).
- OmniRoute combos can't be backed up via `curl http://127.0.0.1:20128/api/combos` — it requires auth (AUTH_001); combos live on the OmniRoute server, unaffected by a Hermes update.
- Post-update checks for this user: `hermes --version` advanced, `fallback_providers: []` still empty in config.yaml, OmniRoute launcher (omniroute-launch.vbs) still serves combos.
  - **Lire la version et l'etat du service dans `gateway_state.json` (RACINE), pas dans un PID annonce.** Un PID de gateway cite par l'utilisateur ou par une etape precedente est perime des que le service a redemarre une seconde fois (frequent juste apres un update) : `gateway.pid` / `gateway_state.json` donnent le PID courant, `code_version`, `code_sha` et l'etat par plateforme. `hermes_agent.egg-info/PKG-INFO` et `pip show` restent sur l'ancienne valeur — ne pas les citer comme preuve de version.
  - **Un hash « attendu » pour un fichier local identifie presque toujours une revision INTERMEDIAIRE.** Avant de declarer qu'un patch local a ete ecrase par l'update, hasher AUSSI les `.bak.<horodatage>` voisins : l'attendu egale en general le backup pris a l'etape citee, et le fichier en service a legitimement avance depuis (une etape validee plus tard a reecrit le meme fichier). L'ecart de SHA n'est une regression qu'apres cette verification — et il se RAPPORTE, il ne se « corrige » pas.
  - **Verifier qu'un fichier livre est intact par ses marqueurs, pas seulement par son SHA** : `grep` des traits distinctifs ajoutes (nom de la cle d'etat, commentaire du correctif) prouve la presence du changement la ou le hash ne dit que « different ».
- **Revoir les skills bundled « user-modified » sans noyer le contexte.** L'update annonce les skills conserves ; `hermes skills diff <nom>` imprime stock vs yours. Rediriger vers `cache/scratch/diff_<nom>.txt` (15 a 60 ko par skill) et n'en extraire que : l'en-tete (compte de fichiers divergents), les paires `--- stock/…` / `+++ yours/…`, et les listes `only in stock:` / `only in your copy:`. Lecture qui tranche : une liste `only in stock` VIDE = la copie locale n'a rien perdu de l'amont (elle a juste ete decoupee autrement) → garder ; des fichiers presents seulement en stock = matiere amont AJOUTEE depuis le fork de l'utilisateur → copier ces fichiers precis, **pas** de `reset`, qui detruirait le decoupage et les references maison. La source « stock » est le bundle du checkout lui-meme : `hermes-agent/skills/<categorie>/<nom>/references/` — **aucune sous-commande `sync-reference` n'existe** (liste reelle : `trust, untrust, browse, search, install, inspect, list, check, update, audit, uninstall, reset, list-modified, diff, opt-out, opt-in, repair-official, publish, snapshot`) : on `cp` le fichier manquant puis on prouve la copie par `sha256sum` identique stock/local. **Verifier ensuite que la copie est COMMITTABLE avant d'annoncer un commit** : un dossier de skill bundled peut etre invisible pour git (cf. motif non ancre dans `hermes-home-git-baseline.md`) — `git check-ignore -v <chemin>` et `git ls-files <dossier>` tranchent.
- **Le constat npm de `hermes doctor` n'est pas corrigeable localement.** `_check_npm_audit` ignore son argument `should_fix` (aucune commande mutante n'est prescrite) et chaque `hermes update` relance un `npm ci` deterministe depuis le lockfile committe : un `npm audit fix` local ne persiste pas. Rapporter paquet + version de/vers + si le correctif est semver-major (dans `hermes-agent/package.json` et `package-lock.json`) et renvoyer a un bump de lockfile en amont ; ne pas lancer `--fix` en croyant le resoudre. Les arbres npm PREEMBALLES (`tools/<outil>-<ver>-<arch>/`) n'ont ni `node_modules` ni lockfile et ne sont pas audites : une vuln des deps racine du checkout ne touche pas les outils correspondants. **Avant de promettre une issue amont, chercher si elle existe deja** (`gh search issues "<paquet>" --repo NousResearch/hermes-agent`) : ce constat est suivi en amont en plusieurs exemplaires, une issue de plus est un doublon — la note dans `docs/` suffit alors.
- **Le report du rafraichissement `cua-driver` sous Windows est inconditionnel ; l'UAC n'est exige que si l'autostart a ete active.** L'update s'arrete sur `Windows cua-driver refresh deferred (autostart registration requires UAC)` et renvoie a `hermes computer-use install --upgrade`, mais la branche Windows de `_refresh_cua_driver_after_update()` ne teste PAS l'opt-in : le message est generique. Ce que la commande fait reellement : reconcilier le pin PM (`pm.ensure("cua-driver", explicit=True)` — **install reseau**, elle peut telecharger un binaire versionne), valider le runtime contract, puis, **seulement si `computer_use.autostart: true`**, inscrire la tache planifiee de logon `cua-driver-serve` via PowerShell eleve (`Start-Process -Verb RunAs` → `cua-driver autostart enable`). Aucun service Windows, aucune cle `Run` de registre. Donc sur un host a `autostart: false` (le defaut), la commande aboutit depuis un terminal NON eleve et n'inscrit rien : le dire avant de reclamer un shell admin, et ne pas modifier `computer_use.autostart` sans demande explicite. Verifications : `hermes computer-use status`, `hermes computer-use doctor`, `schtasks /Query /TN cua-driver-serve` (attendu : tache introuvable tant que l'opt-in est absent).
- **Pin `gateway.multiplex_profiles` before updating.** From the 0.21.x line its default flips to ON; on a host with several profiles (default + a second) write it explicitly first: `hermes config set gateway.multiplex_profiles false`, then confirm with `hermes config get gateway.multiplex_profiles` → `false`. Otherwise the profiles may be multiplexed at the next boot.
- **A traceback in `hermes update` output does NOT mean the update failed.** The updater hands the dependency install to the venv python and returns, so the SAME run can print `✓ Update complete! [main @ <sha>]` AND a `RuntimeError: Windows gateway relaunch after update was not verified alive`. Grep the output for `Update complete!`, then verify with `hermes --version` + `hermes doctor` (Required Packages). Do not re-run the update.
- **The respawned gateway is usually killed by the Windows Job Object** during updater teardown (#91675 / #48820): `hermes gateway status` reports `No gateway process detected`. Recover with `schtasks /Run /TN Hermes_Gateway`. **`--no-gateway-restart` existe et supprime le respawn automatique, mais l'updater imprime quand meme `✓ Gateway started via cold-start after update (PID: ...)`** : cette instance nait dans le Job Object du shell de l'agent et meurt avec lui. Ordre qui tient : tuer son arbre (`Stop-Process -Id <pid> -Force`, puis verifier qu'aucun process ne matche `gateway run`), `Enable-ScheduledTask` sur la tache, `schtasks /Run /TN Hermes_Gateway`, puis confirmer sur `logs/gateway.log` (`telegram connected`, `set_my_commands OK`) et sur le `gateway_state.json` RACINE. Ne jamais demarrer la tache avant d'avoir tue la precedente : deux instances qui pollent le meme jeton Telegram partent en 409 en boucle. If a second profile's task is DISABLED (`schtasks /Run` → "la tâche ... est désactivée"), use `hermes -p <profile> gateway start` instead. Verify BOTH profiles afterwards.
- **The update CAN migrate and rewrite config.yaml** — bumping `_config_version` (e.g. v44 → v45) and possibly dropping trailing commented blocks — but never report a rewrite as a fact: a pull of >1000 commits has left `config.yaml` byte-identical (same md5, same `_config_version`). Verify with `md5sum` + `diff` against the pre-update copy, re-check custom keys with `hermes config get <key>`, and report the measured result, not the expectation.

## Step 1 — identify which install is actually LIVE

Do this before touching anything. Batch these reads:

- `hermes --version` — the single most useful line: it prints **Install directory**
  and **Install method** (`git` / `docker` / `nix` / `unknown`).
- `which -a hermes` then read the launcher it points at. On Windows the launcher is
  often a Node shim that shells out to Python (see `references/windows-launcher-chain.md`).
- `pip show hermes-agent` — pip metadata Version + Location. NOTE: this can be STALE
  vs the code actually running (e.g. metadata says 0.16.0 while the code is 0.20.0
  because zip-updates overwrite source without updating pip metadata).
- Gateway command line (Windows): the gateway runs as a **Scheduled Task
  `Hermes_Gateway`**, not a service. Get its PID from `hermes gateway status`, then:
  `powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<PID>' | Select-Object -ExpandProperty CommandLine"`
  This shows definitively which `python.exe -m hermes_cli.main` the background agent uses.

### Resoudre l'interpreteur runtime actif (sans chemin code en dur)

`hermes --version` cite le python du CLI (`Python: 3.11.16` = venv du checkout), PAS celui du
runtime : la ligne peut rester identique alors que le venv stage a bouge, et les deux pythons
diffёrent. Aucune sous-commande ne l'imprime (`--which-python` n'existe pas) ; les sources reelles,
dans l'ordre qui marche :

1. le venv runtime present sur le PATH (`...\installs\<id>\environments\<hash>\venv\Scripts`) —
   l'interpreteur que `hermes` utilise lui-meme, la source autoritative ;
2. le venv runtime annonce par `hermes doctor` (« Runtime venv staged (...) (active in this
   process) ») — recoupement de 1, a afficher quand les deux divergent ;
3. le venv runtime le plus recent sous `installs\*\environments\*\venv` (trier les DOSSIERS) ;
4. le venv du checkout (`hermes-agent\venv\Scripts\python.exe`) ;
5. le CPython nu `tools\python-<ver>-<arch>\python.exe` — AUCUN paquet tiers : un controle de sante
   qui l'accepte ne teste rien ;
6. `python` du PATH.

Trois pieges mesures, tous silencieux : plusieurs environnements stages coexistent et les perimes
restent sur le disque (un glob nu prend le premier alphabetiquement, pas l'actif) ; `ls -1dt` sur
les `python.exe` extraits ne trie rien (horodatage d'archive commun) ; et le python des `tools` n'a
ni yaml ni requests. Corollaire : un controle de sante doit IMPORTER ses dependances critiques dans
l'interpreteur resolu et echouer si l'import casse — un `--version` qui repond ne prouve rien du
runtime.

## Pitfall — cwd shadows the install (version changes by directory)

`hermes` imports `hermes_cli.main` through Python's normal import path, and **CWD is
first on sys.path for `-c` invocations**. Running `hermes` from INSIDE a git checkout
of the source imports the LOCAL source (e.g. v0.19.0) instead of the installed package
(e.g. v0.20.0).

Symptom: `hermes --version` / `hermes doctor` report DIFFERENT versions depending on
the directory you ran them from. Always run diagnostics from a neutral directory
(e.g. `C:\Windows\System32` or `/tmp`), and re-check cwd before trusting any
version/doctor output. This shadowing cost real confusion during a diagnosis.

## Pitfall — `hermes update` fails at dep-sync when install method is "unknown"

Signature (stderr appears before the update banner):
```
error: Failed to inspect Python interpreter from active virtual environment at `venv\Scripts\python.exe`
  Caused by: Python interpreter not found at <install_dir>\venv\Scripts\python.exe
... subprocess.CalledProcessError: Command '[...uv.exe, pip, install, -e, .]' returned non-zero exit status 2
```

Root cause: the zip updater (`_update_via_zip`) sets `VIRTUAL_ENV=PROJECT_ROOT/venv`
and runs `uv pip install -e .` into it. A pip install into site-packages has **no venv
and no `.git`**, so `detect_install_method()` returns `unknown` and the dep-sync step
finds no interpreter.

Key nuance: the ZIP extraction (code refresh) SUCCEEDS before dep-sync fails. So after
this error the code is usually already current — re-check `hermes --version`, and verify
deps independently with `hermes doctor` (Required Packages). If all present, the failure
was benign that run.

## Install-method summary

| `hermes --version` "Install method" | Meaning | `hermes update` behavior |
|---|---|---|
| `git` | clone + venv (curl installer) | git pull + venv sync + SQLite runtime repair — works |
| `unknown` | pip into site-packages (no `.git`, no `.venv`) | ZIP extract works; dep-sync + SQLite repair FAIL |

`doctor` also flags a SQLite WAL-reset bug (SQLite < 3.44.6) when `state.db`/`kanban.db`
are in WAL mode; the only in-product repair is `hermes update` on a venv-managed install —
exactly the step that fails for a pip install.

## Pitfall — FTS5 index repair needs a QUESCENT DB (can't run from inside a session)

After `hermes update`, `doctor` may flag issue #1: `state.db FTS write corruption —
run 'hermes doctor --fix' (or 'hermes sessions repair')` (a "malformed inverted index
for FTS5 table main.messages_fts_trigram"). The actual session/message rows are intact —
only `session_search` is degraded. Verify with the non-destructive read-only inspect:

```bash
hermes sessions recover --source <state.db> --inspect-only   # "warnings": [] => data OK
```

`hermes sessions repair` (backs up first, preserves data, rebuilds FTS) REQUIRES a quiet
database. It refuses with `a live writer still holds state.db` when ANY Hermes process is
writing — the gateway OR an active agent session. Two hard truths:

1. `hermes gateway stop` is guarded from inside an agent session ("cannot stop the gateway
   from inside the gateway process") — the terminal tool blocks it. Stopping the gateway
   from an agent requires the Windows-native path: `schtasks /End /TN Hermes_Gateway` then
   `taskkill /PID <supervisor> /T /F` (the gateway runs as supervisor+worker python pair;
   `schtasks /End` alone does NOT kill them).
2. Even with the gateway dead, repair still fails because the agent's OWN session is the
   live writer (it holds `state.db-wal`). A schema/FTS rebuild cannot run while the process
   asking for it is writing to the DB.

Resolution: give the user a script to run from a PLAIN terminal when no Hermes session is
open — `hermes gateway stop` → `hermes sessions repair` → `hermes gateway start` (from a
plain shell none of these are guarded). The offline alternative (`sessions recover --output
recovered-state.db`) rebuilds a clean DB read-only but still needs quiescence to swap in.

Stale `<db>.repair.lock` / `<db>.fts_rebuild.lock` files are harmless: they are OS byte-range
locks (msvcrt/flock), auto-released on process exit — do not delete state.db or the backup.

## Direct FTS5 rebuild (works with a LIVE writer — no quiescence needed)

When only the FTS5 inverted index is corrupt (`PRAGMA integrity_check` →
`malformed inverted index for FTS5 table main.messages_fts_trigram`) and the
message/session rows are fine, skip `hermes sessions repair` entirely — its
quiescence guard refuses while any Hermes process holds the DB. Rebuild the
index in place with the FTS5 `rebuild` command, which reconstructs the index
from the content table and needs no quiet database:

```python
import sqlite3, os
db = os.path.expanduser('~/AppData/Local/hermes/state.db')
conn = sqlite3.connect(db)
conn.execute("INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild')")
conn.commit()
print(conn.execute('PRAGMA integrity_check').fetchall())  # expect [('ok',)]
```

- **Do NOT `DELETE FROM <fts_table>` first** — a DELETE against a corrupted FTS
  table itself fails with `database disk image is malformed`; the rebuild INSERT
  is the operation that actually fixes it. Go straight to `VALUES('rebuild')`.
- **Windows has no `sqlite3` CLI by default** — use Python's stdlib `sqlite3`
  module (no dependency) instead of hunting for a binary.
- **Backup first**: `cp state.db state.db.bak.$(date +%Y%m%d_%H%M%S)` before any
  write. The rebuild is non-destructive (index only), but back up on principle.
- Verify search works after: `SELECT count(*) FROM messages_fts_trigram WHERE
  messages_fts_trigram MATCH '<word>'` should return a plausible count.

## Fix directions (pick per setup; get consent before git surgery)

1. Migrate to the canonical git clone (usually `$HERMES_HOME/hermes-agent`):
   `git pull --rebase`, sync its venv, repoint CLI + gateway to it, then clean up the
   site-packages copy.
2. Clean reinstall via the official installer.
3. Leave as-is when the version is already latest and all deps are present.

## Rules of engagement

- Destructive git ops (`git reset --hard`, etc.) need explicit user approval — never
  silent. Prefer reversible `git pull --rebase`.
- The git clone's venv may be named `.venv` while the updater/PATH expect `venv` — check both.
- Don't report a fix as done until verified from a NEUTRAL cwd (see shadowing pitfall).

## Verification

- `hermes --version` from a neutral dir → expected Install directory + method + version.
- `hermes doctor` from a neutral dir → Required Packages all ✓, "Version files consistent".
- `hermes gateway status` → running, and its process cmdline points at the intended python.

## `hermes update` sur un home qui porte un gros `data/`

- **`--backup` zippe TOUT HERMES_HOME, `data/` inclus.** Sur un home charge en poids de
  modeles/video/RAG (mesure : 178 Go au total, 162 Go dans `data/`) l'archive a depasse
  16 Go en 17 min alors qu'elle etait encore en haut de l'arborescence — donc des heures
  et des dizaines de Go. Un orphelin `.pre-update-*.zip.*.partial` de plusieurs Go dans
  `backups/` est la signature d'un run anterieur qui a subi la meme chose. Sur un host a
  `updates.pre_update_backup: false`, lancer `hermes update --no-backup -y` et faire
  soi-meme les copies ciblees (config.yaml, `.env` par profil, `memories/`, chaque
  `state.db` via `sqlite3.Connection.backup`). Le snapshot rapide n'est pas perdu pour
  autant : il est deja ecrit dans `state-snapshots/<ts>-pre-update` et survit.
- **Ces partials sont des fichiers CACHES (prefixe `.`)** : `Get-ChildItem "<home>\backups\*.partial*"`
  et `ls <home>/backups/*.partial*` ne matchent **rien** et font conclure a tort « aucun orphelin ».
  Utiliser `Get-ChildItem <home>\backups -Force -Filter "*.partial*"` (ou `ls -a`) : il y en a souvent
  plusieurs (mesure sur ce host : 3, 14,9 Go a eux trois ; `backups/` retombe alors de 16 Go a 243 Mo).
- **Le log du run ne prouve RIEN pendant la sauvegarde** : la sortie de python est
  bufferisee par blocs quand elle est redirigee vers un fichier, le log reste donc sur sa
  derniere ligne pendant des minutes. Mesurer la progression sur la taille du fichier
  `backups/.pre-update-*.zip.<pid>-<tid>.partial`, ou sur le temps CPU du python enfant
  de `.hermes-runtime`.
- **`hermes profile stop` n'existe pas** (sous-commandes reelles : list/use/create/
  delete/describe/show/alias/rename/purge-identity/migrate-identity/export/import/
  install/update/info). Arreter les gateways par `hermes gateway stop` et
  `hermes -p <profil> gateway stop`.
- **Suspendre les taches planifiees REPETITIVES avant le run, les reactiver apres.**
  Meme tous les detenteurs tues, `Hermes_Gateway` (PT15M), `Hermes_Gateway_HealthCheck`
  (PT5M) et `Hermes_NVIDIA_NIM_Proxy` (PT15M) recreent un detenteur du venv en pleine
  mise a jour et re-arment le garde-fou : `Disable-ScheduledTask` → run →
  `Enable-ScheduledTask` + `Start-ScheduledTask`. Controle avant/apres avec
  `hermes update --list-venv-holders` (JSON, exit 3 si occupe) — la session de l'agent
  elle-meme est exclue de cette liste. **Un `[]` (exit 0) ne prouve PAS que le venv est libre** : mesure sur ce host, la commande est sortie vide alors que la gateway ET le backend `serve` tournaient depuis ce venv. L'inventaire qui tranche est la table des processus (`gateway run`, `hermes_cli.main serve`, le proxy NIM) — pas la sortie du garde-fou.
- **La synchro des dependances se differe quand le `hermes.exe` de l'agent tient le venv.**
  Le pull git est deja applique (le HEAD bouge), puis :
  `Could not quarantine hermes.exe (PermissionError: another process is holding it open)`
  → `The dependency install has been deferred`. Chaque commande `hermes` suivante
  reessaie et affiche la banniere ; l'app continue de tourner sur le venv courant.
  Avant d'annoncer au utilisateur de lancer la commande de reprise, mesurer si des deps
  manquent vraiment : comparer les `dependencies` de `pyproject.toml` a
  `venv\Scripts\python.exe -m pip freeze` et **ecarter celles conditionnees a la
  plateforme** (`sys_platform != 'win32'`) — un seul `ptyprocess` manquant sous Windows
  est un no-op, pas une install cassee. La commande de reprise donnee par l'outil :
  `venv\Scripts\python.exe -m pip install -e ".[all]"` depuis le checkout.
  Mais cette commande SEULE ne suffit pas : il faut d'abord arreter les detenteurs du venv, et
  `--list-venv-holders` en montre deux par service (un superviseur `venv\Scripts\python.exe` + un
  travailleur `.hermes-runtime\python\generation-<id>\python.exe`) — la session de l'agent tient le
  venv elle aussi sans figurer dans cette liste. Le marqueur du checkout, `.update-incomplete`
  (JSON, `{"attempts": N}`), ne se purge que quand la reprise reussit. Sequence complete, pieges
  et verification : `references/deferred-dependency-install.md`.
- **Verifier le HEAD annonce contre le depot distant avant d'y croire.** Une consigne
  peut nommer un commit qui n'a jamais ete `origin/main` : comparer
  `git rev-parse origin/main` (apres `git fetch origin`) au SHA annonce et rapporter le
  vrai. Un pull de plusieurs centaines de commits peut aussi laisser le NUMERO de version
  de `hermes --version` inchange (meme ligne de release) alors que `upstream <sha>`
  change — citer les deux.

## Known local patch — Telegram `updater.stop()` hangs during shutdown

Symptom (spams lvl8 alerts at gateway restart, ~03:00 nightly):
`[Telegram] Telegram updater.stop() did not finish` + `gateway.run: Fatal telegram
adapter error (telegram_network_error)`. Root cause: a race between `disconnect()`
and the polling error handler — `updater.stop()` blocks on a CLOSE-WAIT socket,
times out, and the `_polling_teardown_started` check runs only AFTER the fatal
error fires.

Fix: add a `_polling_teardown_started` check inside the
`except asyncio.TimeoutError` handler in `plugins/platforms/telegram/adapter.py`
so a hung `stop()` during teardown logs at DEBUG and returns instead of
escalating. Normal-operation recovery is unchanged.

Re-apply after any `hermes update` (local core edits are reverted):
```bash
cd "$HERMES_HOME/hermes-agent" && git apply "$HERMES_HOME/data/patches/telegram-stop-timeout.patch"
```
Patch copy: `references/telegram-stop-timeout.patch`.

**2026-09-19 re-check on `main` @ `d4d9b76d8c`: the guard is NOT in the timeout
branch — the earlier "now upstream" note below was wrong.** The only
`except asyncio.TimeoutError` around `updater.stop()` sits in
`_stop_updater_or_go_fatal` (adapter.py ~l.1961) and escalates unconditionally
(`_go_fatal_network` → retryable fatal + adapter rebuild). `_teardown_started` is
consulted by the CALLER just before (~l.2011) and just after (~l.2017) the call,
so a teardown starting DURING the 15 s `stop()` still escalates. The window is
narrow (the pre-call check must already have passed), which is consistent with the
nightly spam also coming from the non-teardown path. If `updater.stop() did not finish` STILL spams lvl8 alerts
nightly, it is the NON-teardown path — `stop()` hangs on a CLOSE-WAIT socket
outside a shutdown, the adapter correctly logs + rebuilds and recovers, so it is
BENIGN. `hermes gateway restart` does NOT fix it (it recurs at the next restart,
and it also cuts the live agent session). The right fix for the user-facing spam
is to FILTER the alert at the SecurityMonitoring log monitor, not patch the
adapter again: add the pattern to `EXCLUDE` in
`data/security-monitoring/monitors/log_monitor.py` (tested BEFORE the `RULES` in
`classify()`), e.g.
`updater\.stop\(\)\s+did\s+not\s+finish|Fatal\s+telegram\s+adapter\s+error\s+\(telegram_network_error\)`.
Verify genuine errors (Traceback / Exception / out of memory) still match after.

## Pitfall — `WinError 5` sur l'arbre d'install : une ACL par OBJET, presque jamais un fichier absent

Signature : un run non eleve s'arrete sur `[WinError 5] Acces refuse: '<home>\tools\python-<ver>-<arch>\python.exe'>`,
ou bien `uv venv` rend `Caused by: Could not find a suitable Python executable ... python.exe`, ou la
preparation de la source rend `python: install failed: [WinError 5] ... .previous-python-<ver>-<arch>\DLLs\<dll>`
— alors que le meme run lance ELEVE passe. Ces messages sont LE MEME probleme : la DACL des objets
sous `tools\` et `plugins\`, pas le code ni le python.

- **Le fichier n'est presque jamais absent.** Sur une DACL qui ne donne rien au jeton, `dir` repond
  `Fichier introuvable` (exit 1, PAS `Acces refuse`) et `icacls`/`listdir` repondent `chemin
  introuvable` (WinError 3). Prouver l'existence par `if exist` (cmd) ou un vrai essai d'ouverture,
  jamais d'un `dir` seul — et ne jamais rapporter « fichier inexistant » sur cette base.
- **Lire la DACL, pas le fichier** : `Get-Acl` -> `AreAccessRulesProtected` (heritage coupe) + les ACE
  par SID. Forme cassee mesuree sur ce parc :
  `D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)` = OWNER RIGHTS (S-1-3-4) + SYSTEM +
  Administrateurs, **aucune ACE pour l'utilisateur**.
- **OWNER RIGHTS profite au PROPRIETAIRE de l'objet** : c'est lui qui decide. Proprietaire
  `BUILTIN\Administrateurs` (objet cree par un processus eleve) -> un jeton non eleve (ou
  Administrators est `refus uniquement` sous UAC) n'a AUCUN droit -> WinError 5. Proprietaire =
  l'utilisateur -> il garde le controle total et l'objet **marche**. D'ou des outils du meme dossier
  qui fonctionnent et d'autres non : comparer les proprieteaires avant de conclure.
- **Ne jamais compter `BUILTIN\Administrateurs` (S-1-5-32-544) comme un droit utilisable** en evaluant
  une execution non elevee : SIDs utilisables = SID de l'utilisateur + Utilisateurs (545), Tout le
  monde (S-1-1-0), Utilisateurs authentifies (S-1-5-11), INTERACTIF (S-1-5-4), OUVERTURE DE SESSION
  DE CONSOLE (S-1-2-1).
- **Un terminal d'agent souvent ELEVE ne voit pas le probleme** : tout ce qui est lisible en admin ne
  dit rien du vecu non eleve. Reproduire avec un jeton restreint — `runas /trustlevel:0x20000
  "<scratch>\probe.bat"` ou le `.bat` redirige vers un fichier (sortie en UTF-16 : `tr -d '\0'`
  avant tout filtre), et verifier que le jeton est du bon type : `whoami /groups` doit afficher
  `BUILTIN\Administrateurs ... Groupe utilise pour les refus uniquement`.
- **Mesurer le PERIMETRE avant de reparer** : n'importe quel `tools\<outil>-<ver>-<arch>` et
  `plugins\<nom>` peut etre casse, pas seulement le chemin cite par l'erreur (mesure : ~1300 objets
  denies, dont `git` et `cua-driver`). Lancer `scripts/find-denied-tree.ps1 -Root <home>` : il liste
  chaque objet ou aucun SID utilisable n'apparait, agrège par zone et publie `TOTAL_ANOMALIES=N`.
- **Reparation** : `icacls "<dir>" /inheritance:e /grant "%USERNAME%:(OI)(CI)F" /T /C` — reactiver
  l'heritage suffit quand le parent porte encore `<utilisateur>:(OI)(CI)(F)` ; le verifier d'abord
  (`icacls "<parent>"`) et n'ajouter l'ACE que s'il ne l'a pas.
- **Ne pas reparer avant d'avoir identifie l'ECRIVAIN de la DACL** : le meme acteur reapplique la
  forme cassee au prochain install. Rapporter, puis attendre la validation avant tout `icacls` mutant.
- **Un update avorte laisse des enfants vivants qui continuent de muter l'arbre.** Mesure : pendant un
  diagnostic en lecture seule, un dossier de sauvegarde `.previous-python-*` et un `plugins\<nom>`
  presents a l'ouverture avaient disparu quelques minutes plus tard, avec des `python.exe` encore
  vivants issus du run avorte. Prendre un listing AVANT/APRES et re-verifier l'existence avant de
  conclure : un objet mesure present peut ne plus l'etre.
- Signature SDDL, table sain/casse, recette de reproduction, perimetre et pistes ELIMINEES :
  `references/windows-acl-denied-tree.md`.

## Supporting files

- `references/deferred-dependency-install.md` — finishing a deferred dependency install: the six
  venv holders (supervisor + `.hermes-runtime` worker per service), the `.update-incomplete`
  marker, the disable-tasks / kill / `pip install -e ".[all]"` / restart order, and the
  verification set.
- `references/windows-runtime-ops.md` — gateway restart on Windows (kill the
  detached `gateway run` python via PowerShell, then `schtasks /run`), reliable
  MSYS detach (`powershell Start-Process`, not `cmd //c start`), the fact that
  local edits to `hermes-agent/` core are reverted by `hermes update`, benign
  Windows startup warnings (`start_unix_server`, LSP `WinError 193`), the
  Gmail email-IMAP timeout fix (`EMAIL_POLL_INTERVAL` + adapter `timeout`),
  **killing ELEVATED background processes (foreground shell = access denied;
  use UAC `Start-Process -Verb RunAs`)**, and the MSYS single-slash flag pitfall.
- `templates/retire-stale-venv.ps1` — copy-and-adapt PowerShell for putting a stale venv out of service: aborts while any process still uses it, renames reversibly, then verifies `hermes --version`, the PATH shim, `doctor` and the backend port.
 - `scripts/find-denied-tree.ps1` — scanne une racine et liste chaque objet dont la DACL ne donne aucun
 droit a un jeton NON ELEVE (DACL protegee, aucune ACE utilisable) ; agrege par zone et publie
 `TOTAL_ANOMALIES=N`. A lancer avant toute reparation d'un `WinError 5` sur l'arbre d'install.
 - `references/windows-acl-denied-tree.md` — forensique ACL de l'arbre d'install : anatomie de la DACL
 casse (`OWNER RIGHTS + SYSTEM + Administrateurs`, proprietaire = Administrateurs), regle du
 proprietaire, SIDs utilisables par un jeton filtre, reproduction par jeton restreint, ordre de
 reparation, et causes deja eliminees par la mesure.
