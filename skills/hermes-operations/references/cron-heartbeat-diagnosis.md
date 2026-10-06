# Diagnostiquer un ticker cron figé / un gateway mort

Symptôme : plus aucun job cron ne s'exécute (ou ils sont tous « en retard ») sans qu'aucune erreur ne
soit remontée. Le heartbeat des jobs est écrit par le **thread scheduler du gateway** : si le gateway
meurt, le ticker s'arrête et `ticker_heartbeat` se fige. Un heartbeat figé veut dire **gateway mort**,
pas « cron en panne » — ne pas chercher la cause côté jobs.

## Où est l'état (chemins relatifs à `%LOCALAPPDATA%\hermes`)

| Fichier | Ce qu'il dit |
|---|---|
| `cron/ticker_heartbeat` | `<epoch> <pid>` du dernier battement. Périmé de plusieurs minutes = ticker arrêté. |
| `cron/ticker_last_success` | epoch du dernier tick réussi. |
| `cron/jobs.json` | tous les jobs : `enabled`, `state`, `next_run_at`, `last_run_at`, `last_status`, `last_error`. |
| `cron/executions.db` | table `executions` (`claimed_at`, `status`, `error`) et `cron_incidents` (ouverts / clos). |
| `gateway_state.json` | `pid`, `gateway_state` — source de vérité du processus gateway. |
| `logs/gateway-health.log` | battements / alertes du healthcheck. |

## Procédure

1. **Age du heartbeat** : lire `cron/ticker_heartbeat` (epoch + pid) et comparer à `date +%s`.
2. **Dernière exécution réelle** : `SELECT MAX(claimed_at) FROM executions`. Si elle précède le
   figement du heartbeat, tout s'est arrêté d'un coup — confirme la piste gateway.
3. **`hermes gateway status`** : annonce le PID mort « sans arrêt propre » et la commande de
   récupération recommandée.
4. **État périmé ?** Comparer le `pid` de `gateway_state.json` au processus réel
   (`Get-Process -Id <pid>` / `tasklist`). PID introuvable alors que le fichier dit
   `gateway_state: running` = état périmé : c'est le scénario du skill
   `hermes-gateway-healthcheck-fix` (corriger le PID).
5. **Jobs en retard** : dans `jobs.json`, pour chaque job `enabled`, comparer `next_run_at` à
   maintenant. Plusieurs retards = ticker arrêté.
6. **Surveillance vivante ?** `Get-ScheduledTask Hermes*` : si `Hermes_Gateway_HealthCheck` est
   `Disabled`, AUCUNE alerte n'est émise — la panne est silencieuse. `Hermes_Gateway` est la tâche de
   relance ; un « dernier résultat 0 » ne prouve PAS que le gateway est remonté.
7. **Récupération** : `schtasks /Run /TN Hermes_Gateway` (démarre hors Job Object, cf. skill
   `hermes-install-troubleshooting`) ou `hermes gateway restart`. Puis corriger le PID de
   `gateway_state.json`.

Toujours vérifier l'**effet** après une relance (le processus existe, le heartbeat repart), pas
seulement le code de retour de la tâche planifiée.

## Piège de requête sur `executions.db`

`claimed_at` est stocké en ISO-8601 **avec offset** (`2026-10-05T20:56:35.155601+02:00`). Toute
comparaison `WHERE claimed_at >= datetime('now','-15 minutes')` est une comparaison de CHAÎNES :
`'T'` (0x54) > `' '` (0x20), donc **toutes les lignes du même jour passent le filtre** — un « 15
 dernières minutes » rend alors les 187 lignes du jour. Prendre `MAX(claimed_at)` comme borne, ou
parser en Python (`datetime.fromisoformat`) et comparer des objets.

## Consigne

Sur une mission « rapport seul », NE PAS relancer le gateway ni modifier les jobs sans GO de
l'utilisateur : lire, dater, rapporter l'état et proposer la commande de récupération.
