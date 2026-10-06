<!-- Extrait de hermes-operations/SKILL.md, lignes 772-815 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Pitfalls

- `/resume` in gateway is NOT ESTOP resume — it resumes a named session (`CommandDef resume [name]`, `argument_mode mixed`). Always use `/pause off` to lift ESTOP from Telegram; `hermes resume` only exists as CLI.
- `CommandDef pause` is `gateway_only` — it does not exist as CLI slash, and `hermes pause` does not exist as gateway slash. Use the right channel for each form.
- Assuming webhooks stop on pause — they do not; ESTOP has no hook into webhook dispatch. Verify with `grep -rn check_paused` if unsure whether a component respects ESTOP before claiming it is frozen.
- One Telegram channel (`channel_directory.json: platforms.telegram`) can back multiple bot usernames only if they share the same token. Two distinct bot tokens require two entries via `hermes gateway setup`; otherwise only one bot actually receives dispatch.
- `patch` tool refuses to write `config.yaml` (security guard) — edit Hermes config via `terminal` (Python read/write or `hermes config set`), never `patch` or `sed` range substitution which silently truncates on fragile boundaries.
- GPU-bound inference (LivePortrait/SadTalker at 100% GPU / ~95% VRAM) starves the gateway event loop and triggers `CRITICAL gateway.shutdown_watchdog: missed 3 liveness probes -> exit 75` — this is an intentional self-kill for the Task Scheduler to restart, not a code bug; recover with `hermes gateway restart` + verify `telegram connected` in `gateway.log`, never treat as auth/network failure.
- A gateway that died on its own with `gateway.log` ending in "Received UNKNOWN as a planned gateway stop — exiting cleanly" and "Shutdown context: signal=UNKNOWN parent_pid=... parent_cmdline='(unknown)'" orphaned because its parent (Task Scheduler spawn) died — not a code bug. Confirm with `gateway_state.json` showing `"gateway_state":"draining"` and `hermes gateway list` showing `✗ not running`, then restart with `hermes -p <profile> gateway start` (profile flag, not `gateway restart`). Distinct from the `exit 75` watchdog self-kill above. **`hermes doctor` ne signale pas ce cas** : sa section Profiles ne liste que les profils *autres* que le courant, donc un gateway `default` mort passe inaperçu — il faut le contrôler explicitement avec `hermes gateway status` (le profil courant affiche `✗ No gateway process detected` en tête, les autres sur la ligne `Other profiles: ✓ <nom> — PID …`).
- **Le tell de la mort avec le parent est dans `logs/gateway-exit-diag.log`, pas dans `gateway.log`.**
  Comparer le dernier enregistrement `gateway.start` aux démarrages sains : `"console_window_attached"`
  doit être `false` et `"breakaway"` `true`. Une instance née avec `"console_window_attached":true` et
  `"breakaway":null` a hérité de la console / du Job Object du shell qui l'a lancée (typiquement
  `hermes update`) : quand ce parent disparaît, elle reçoit `signal=UNKNOWN`, le traite comme un arrêt
  planifié, draine le tour en cours et sort — sans entrée `gateway.exit_clean`. C'est l'explication que
  le log principal ne donne jamais.
- **Le `gateway_state.json` en `"draining"` est inerte : ne pas le supprimer à la main.**
  `gateway/status.py` : `_RUNTIME_STATUS_STALE_TTL_S = 120`, donc un enregistrement vieux de plus de
  2 min n'est plus cru pour la vivacité ; et `derive_gateway_drainable` exige en plus un PID **vivant**
  et un état `running`. Un redémarrage réécrit le fichier (`starting` → `running`). Le supprimer
  n'apporte rien et détruit l'indice (PID, `start_time`, `exit_reason`).
- **Voie de redémarrage selon le profil** : `schtasks /Run /TN Hermes_Gateway` pour le profil `default`
  (démarrage hors Job Object) ; `hermes -p <profil> gateway start` pour un autre profil. Éviter
  `hermes gateway start` lancé depuis un shell pour le défaut : on recrée le piège du Job Object.
- **Deux tâches qui démarrent le même gateway au logon.** La canonique est reconnaissable :
  `Description` renseignée, action `wscript.exe //B //Nologo "…\gateway-service\<Profil>.vbs"`,
  `RestartOnFailure`, et elle apparaît dans `hermes gateway status` (`✓ Scheduled Task registered: …`).
  Un jumeau sans description, `Hidden`, dont l'action est `pwsh -NoProfile -Command "hermes gateway
  start"`, est un vestige artisanal : le désactiver explicitement (`Disable-ScheduledTask`), jamais le
  supprimer.
- `cron.scheduler: Job '...' failed: lost its durable fire claim ownership / _abort_if_fire_claim_lost` after a gateway restart is a benign abort of the in-flight fire, not a gateway crash — clean the orphaned job with `hermes cron remove <id>` and do not alert on it.
- `deliver=telegram` on heavy/background cron jobs blocks the gateway loop and amplifies spam via `security-monitoring/monitors/log_monitor.py` (each ERROR forwarded as lvl8 `Erreur API` per bot) — use `deliver=local` for GPU/monitoring jobs; extend `EXCLUDE` in `log_monitor.py` with `lost its durable fire claim|fire claim ownership lost|cron\.scheduler.*failed|_abort_if_fire_claim_lost` to suppress internal scheduler noise.
- **Redémarrer un gateway resté longtemps arrêté déclenche une rafale de rattrapage cron — ce n'est pas
  neutre.** Le scheduler reprend au premier tick tous les jobs en retard (`catch_up_occurrences` sous
  `cron/`), et parmi eux un job de maintenance mémoire qui **réécrit `MEMORY.md`** dès que le store
  dépasse ~90 %. Deux conséquences : (a) après tout redémarrage d'un gateway longtemps mort, relire
  `cron/executions.db` (`job_id`, `status`, `started_at`) et `cron/jobs.json` pour lister ce qui a
  réellement tourné **avant** d'affirmer une non-régression — et vérifier les effets de bord des jobs
  du parc (combos du routeur, fichiers d'état) ; (b) une consigne « mémoire inchangée » peut être
  violée par le parc lui-même sans qu'aucune action de l'agent n'y soit pour quelque chose : le dire
  avec la cause, la preuve (reconstruction de la version d'avant, structure et séparateurs `§`
  intacts) et la copie conservée, plutôt que de restaurer en boucle — restaurer remet l'usage
  au-dessus du seuil et le job re-consolide au tick suivant.

