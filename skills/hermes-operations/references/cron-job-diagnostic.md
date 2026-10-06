# Job de cron « bloqué » — diagnostic en lecture seule

Déclencheur : un job (lancé par le scheduler ou à la main via `hermes cron run <id>`) reste des dizaines de minutes sans produire de sortie, et l'UI affiche un état de départ (« starting »/« running ») qui ne bouge pas.

## 1. Établir l'état durable AVANT tout jugement

Chemins (HERMES_HOME = `%LOCALAPPDATA%\hermes`) :

| Fait | Où |
|---|---|
| Exécutions du job | `profiles/<profil>/cron/executions.db` — tables `executions` (id, job_id, source, pid, process_started_at, status, claimed_at, started_at, finished_at, error, delivery_outcome, scheduled_instant) et `cron_incidents` |
| État/planning du job | `profiles/<profil>/cron/jobs.json` — `next_run_at`, `last_status`, `last_error`, `failure_streak`, `last_dispatch`, `fire_claim.by` = `HOTE:PID:uuid` (PID qui détient le tir), `updated_at` |
| Journal de l'agent | `profiles/<profil>/logs/agent.log` (une ligne par appel API et par tool), `errors.log` |
| Gateway | `logs/gateway.log` ; PID courant dans `gateway.lock` (JSON, champ `pid`) |

`status` ne prend que 5 valeurs : `claimed`, `running`, `completed`, `failed`, `unknown`. **Il n'existe aucun état « starting » en base** : si l'UI en montre un, c'est la vue CLI/appelante qui n'a rien reçu — lire la ligne `executions` et se fier à `status` + `started_at`.

`status=unknown` avec `error` ≈ « Scheduler restarted after this execution's owner exited before a durable terminal state » = exécution précédente orpheline (propriétaire tué/fermé, effets de bord inconnus). Avant de relancer : vérifier qu'aucune autre ligne n'est déjà `running` pour ce job.

## 2. Interroger SQLite exactement (pas de binaire `sqlite3` sur cet hôte)

`read_file` sur un `.db` rend le schéma et quelques lignes, mais tronque les lignes longues et peut masquer les plus récentes. Pour un verdict fiable : écrire un `.py` dans le scratch puis l'exécuter.

```python
import sqlite3, json
c = sqlite3.connect(r"<...>\profiles\<profil>\cron\executions.db")
c.row_factory = sqlite3.Row
for r in c.execute("SELECT id,status,source,pid,claimed_at,started_at,finished_at,error,delivery_outcome "
                   "FROM executions WHERE job_id=? ORDER BY claimed_at DESC", ("<job_id>",)):
    print(json.dumps(dict(r), ensure_ascii=False))
```

Piège : `TMPDIR` n'est pas défini dans le kernel `execute_code` → écrire le script sous `C:\Users\<user>\AppData\Local\hermes\cache\scratch\`, pas sous `/tmp`.

## 3. Identifier le VRAI processus (suivre la chaîne parent/enfant)

`tasklist /FI "PID eq <n>"` ne suffit pas et induit en erreur : le PID détenteur affiché comme `bash.exe` à 0 CPU n'est souvent qu'un **emballage**. Un `hermes cron run <id> -p <profil>` lancé depuis une session Hermes donne :

```
bash.exe   (wrapper, CommandLine = bash -lic "set +m; cd <HERMES_HOME> && hermes cron run <id> ... 2>&1 | tail -N")
  └─ python.exe   (LE worker : hermes cron run <id> -p <profil>)   ← CPU/RSS à surveiller
```

Le gateway est un process distinct (voir `gateway.lock`). Réflexe qui tranche :

```
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<n>' | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine | Format-List"
```

La `CommandLine` dit qui est le worker, le wrapper, le gateway. **Liveness = le journal bouge** : comparer l'horodatage de la dernière ligne et l'index du dernier `API call #N` à quelques minutes d'intervalle — pas l'image `tasklist` (un process sain en attente réseau affiche « Unknown »/0 CPU).

## 4. Motifs de journal → cause probable

| Motif | Lecture |
|---|---|
| Beaucoup d'`API call #N` espacés de 40–110 s | Lenteur fournisseur + retries — **pas** un blocage applicatif |
| `[504] ... OmniRoute's local rate-limit execution expiration (…requestQueue.maxWaitMs=…)` | Deadline de file **locale** d'OmniRoute (ce n'est pas un timeout amont) sur le modèle cité → retries automatiques |
| `503 ... all targets were skipped by pre-dispatch filters` (+ `diagnostics.poolSize`, `attemptOrder` vide) | Tous les candidats filtrés **avant** dispatch (quota épuisé / injoignables) → échec rapide, `failure_streak` qui monte |
| `Fallback activated: <A> → <B>` | Chaîne de repli en cours ; un modèle gratuit saturé bascule le job sur un chemin lent |
| `Turn ended: reason=text_response` absent + aucun `write_file`/tool métier | Le job n'a pas encore produit son livrable : il explore (recherches web en boucle) |

Ne pas conclure « blocage sur le prompt » ni « flotte saturée » sans l'un de ces motifs : dire `établi` / `hypothèse` / `inconnu`, jamais plus fort que la preuve.

## 5. Verrous

- SiYuan : `data/siyuan/locks/` — vide = aucun verrou actif.
- `profiles/<profil>/cron/.fire-*.lock` : cibles flock (fichiers de 0 octet). **Leur présence n'est pas un conflit** — un job qui progresse a acquis le sien. C'est `jobs.json.fire_claim` qui identifie le détenteur du tir.

## 6. Verdict et recommandation

- **Progressant** (journal frais, index d'appel qui avance) → **attendre, ne pas tuer** : tuer laisse une exécution `unknown` orpheline de plus et des effets de bord inconnus.
- Fixer un **point de contrôle horaire** explicite (« si à HH:MM aucun <effet de bord attendu> et le journal n'avance plus ») plutôt qu'un avis vague ; alors tuer le **worker** (pas le wrapper) et relancer en arrière-plan, sans `| tail` qui masque la sortie.
- Diagnostic en lecture seule : produire le rapport (état, durée, processus, motifs, cause établie/hypothèse/inconnue, recommandation) puis **s'arrêter au GO** — pas de kill, pas de relance, pas de reindex.
