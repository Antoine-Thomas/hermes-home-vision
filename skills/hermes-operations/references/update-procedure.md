<!-- Extrait de hermes-operations/SKILL.md, lignes 411-430 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Update procedure

Voir `references/update-preflight.md` pour la séquence complète : précaution (multiplex_profiles, snapshot frais, arrêt des writers), contrôles post-update, et récupération des pièges d'exécution Windows (gateway tué par Job Object → `schtasks /Run /TN Hermes_Gateway` ; serveur long-running → `cmd //c "start /b …"` car `setsid` absent de git-bash et background terminal timeout). frais, arrêt des writers).

`hermes update` has NO `--restart` flag — this fails silently and confusingly. The correct sequence:

**Editing config.yaml: use `hermes config set KEY value`, never patch/write_file.** `patch` and `write_file` refuse `config.yaml` as security-sensitive ("Agent cannot modify security-sensitive configuration"). `hermes config set gateway.multiplex_profiles false` is the sanctioned path; verify placement with `hermes config get KEY` and by grepping the section (a dotted key can land under a sibling heading — confirm it is under the right section, not just that it resolves).

**Post-update gateway dies on Windows (Job Object #91675): recover with `schtasks /Run /TN Hermes_Gateway`, not `hermes gateway start`.** The cold-start gateway spawned inside `hermes update`'s shell is killed when that shell exits because it sits in a Windows Job Object. `schtasks /Run /TN <task>` starts the task-scheduler task OUTSIDE any Job Object, so it survives. The task name is `Hermes_Gateway` for the default profile. **Ne pas supposer qu'une tache par profil existe** : avec `gateway.multiplex_profiles: true`, le gateway `default` sert TOUS les profils (`hermes gateway list` → « veille — served by the default multiplexer ») et les taches `Hermes_Gateway_watch` / `Hermes_Gateway_veille` n'existent legitimement pas — il n'existe pas non plus de VBS par profil (`gateway-service/` ne contient que `Hermes_Gateway.vbs`, qui lance `gateway run` sans argument de profil). Lire `hermes gateway list` avant de conclure qu'une tache manque, et ne recourir a `schtasks /Query /FO CSV /TN <task>` que pour une tache censee exister. Verify with `hermes gateway status` → look for `✓ Gateway process running (PID: …)`.

The correct sequence:

1. **Pre-check (read-only)**: `hermes update --plan` — shows what will be updated, which services will restart, and the install method. Safe on live fleet.
2. **Run update**: `hermes update -y` (auto-accepts config migration prompts).
3. **Verify**: `hermes doctor` — check for "mixed sys.modules" warning.
4. **Fix if needed**: `hermes gateway restart` if doctor warns about modules.
5. **Confirm**: `hermes gateway status` + `hermes doctor` clean output.

**state.db cleanup after repair**: if state.db was repaired (`.pre_repair`, `.corrupted` files exist), purge them ONLY after `PRAGMA integrity_check` returns `ok` on the current `.db`. These backups can be 400+ MB each.

