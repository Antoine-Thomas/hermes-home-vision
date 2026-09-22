# Audit des stashes — dépôt `hermes-agent`

Date de l'audit : 2026-09-19
Dépôt : `C:\Users\searc\AppData\Local\hermes\hermes-agent` (branche `main`, arbre propre avant opération)
HEAD au moment de l'audit : `d4d9b76d8c`

## Contexte

L'updater (`hermes update`) met de côté les modifications locales dans un stash
`hermes-update-autostash-<horodatage>` avant chaque mise à jour, puis tente de les remettre.
Quatre de ces stashes datent de 02→08/09 et n'ont jamais été remis : l'updater lui-même les
signale comme « leftover update autostash entries more than 7 days old » (voir
`docs/snapshot/update_execution.log`).

Un cinquième stash (`stash@{4}`, un `WIP on main` du 29/07) traînait également.

## Méthode

1. `git stash list` + `git log -g --format='%ci %gs' refs/stash` pour dater chaque entrée.
2. `git stash show --stat` puis `git stash show -p` pour chaque entrée ; `-w` (ignore whitespace)
   pour distinguer le bruit de formatage du contenu réel.
3. Chaque stash a été **exporté en fichier patch** dans `docs/stash-audit/patches/` avant toute
   suppression (aucune perte possible).
4. Chaque stash « vrai code » a été **préservé dans une branche git dédiée** pointant sur le commit
   du stash (`git branch hermes/autostash-<label> stash@{N}`) — aucune écriture dans l'arbre de
   travail vivant, donc aucun risque pour la session CLI en cours.
5. Suppression (`git stash drop`) uniquement après vérification de la branche et du patch.

## Décisions (confirmation écrite avant exécution)

| stash | date | contenu | décision | raison |
|---|---|---|---|---|
| `stash@{0}` | 2026-09-08 21:32 | `hermes_cli/commands.py` : ajout de `aliases=("com",)` sur la commande `/commands` (1 ligne) | **apply → branche** `hermes/autostash-20260908-193237` puis drop | vrai code (préférence locale), non présent en amont aujourd'hui ; préservé en branche |
| `stash@{1}` | 2026-09-08 19:35 | `apps/desktop/package.json` : `electron` `40.10.2` → `^40.10.6` (1 ligne) | **apply → branche** `hermes/autostash-20260908-173555` puis drop | vrai code mais mineur (dépendance de dev ; l'amont épingle une version exacte) ; préservé, pas réappliqué |
| `stash@{2}` | 2026-09-07 10:57 | 4 fichiers : `agent/lsp/client.py` (résolution du shim npm sans extension vers son `.cmd` — WinError 193), `gateway/shutdown_watchdog.py` (garde `os.name == "posix"` autour de `start_unix_server`), `plugins/platforms/email/adapter.py` (timeout IMAP 30 → 90 s), `plugins/platforms/telegram/adapter.py` (ne pas escalader en erreur fatale pendant un teardown déjà commencé) | **apply → branche** `hermes/autostash-20260907-085757` puis drop | vrai code (correctifs Windows) ; la garde posix est désormais en amont, les 3 autres hunks non |
| `stash@{3}` | 2026-09-02 18:21 | mêmes 3 premiers fichiers que `stash@{2}` (sans le hunk telegram), base de code plus ancienne (lignes 569/711/855 contre 573/685) | **apply → branche** `hermes/autostash-20260902-162153` puis drop | vrai code, version antérieure de l'ensemble `stash@{2}` ; on ne tranche pas à la place de l'utilisateur, donc conservé lui aussi |
| `stash@{4}` | 2026-07-29 02:52 | `WIP on main` (pas un autostash) : 835 fichiers — réécriture CRLF/whitespace de `website/*` et `docs/*` ; après `-w`, il ne reste que la suppression de 26 lignes `"peer": true` dans `package-lock.json` | **drop** (pas de branche) | bruit : quasi exclusivement des fins de ligne / whitespace ; l'updater réécrit ces fichiers à chaque update. Le diff non-whitespace (3,9 Ko) est conservé en patch |

Aucune suppression n'a été faite sans que le contenu soit simultanément (a) exporté en patch et
(b) référencé par une branche git.

## État des correctifs par rapport au code amont actuel (`d4d9b76d8c`)

- `agent/lsp/client.py` — résolution `.cmd` du shim npm **absente** en amont → correctif toujours utile.
- `gateway/shutdown_watchdog.py` — la garde `os.name == "posix"` **est déjà en amont**
  (`loop_heartbeat_forever`, ~ligne 347) → hunk obsolète.
- `plugins/platforms/email/adapter.py` — timeouts toujours à 30 s en amont → correctif toujours utile
  (réglage local).
- `plugins/platforms/telegram/adapter.py` — la garde `_polling_teardown_started` dans la branche
  `except asyncio.TimeoutError` de `_stop_updater_or_go_fatal` (~l.1961) est **absente** en amont :
  ce seul `except asyncio.TimeoutError` autour de `updater.stop()` escalade sans condition
  (`_go_fatal_network` → fatal retryable + reconstruction de l'adaptateur). `_teardown_started`
  n'est lu que par l'APPELANT, avant (~l.2011) et après (~l.2017) l'appel : un teardown qui démarre
  **pendant** les 15 s de `stop()` escalade donc encore. La fenêtre est étroite (le contrôle
  pré-appel doit déjà être passé), ce qui laisse penser que le spam nocturne vient aussi du chemin
  hors teardown. Correctif encore pertinent, mais d'effet limité — à arbitrer avant toute PR.
  (La note « le patch est passé en amont » du skill `hermes-install-troubleshooting` a été corrigée
  le 19/09 après vérification du code.)
- `hermes_cli/commands.py` — alias `com` absent en amont → préférence locale.
- `apps/desktop/package.json` — `electron` toujours épinglé à `40.10.2` en amont.

## Références

- Fichiers patch : `docs/stash-audit/patches/`
- Procédure de rejeu des patchs locaux : cf. `docs/patch_repo_plan.md` (section « Si PR impossible »)
- Journal d'update qui signale les stashes : `docs/snapshot/update_execution.log`

## Exécution (2026-09-19, 10:51)

Décisions ci-dessus appliquées dans l'ordre suivant : export des patchs **puis** création des
branches **puis** suppression. Rien n'a été supprimé avant que son contenu existe ailleurs.

Branches de préservation créées (elles pointent sur le commit d'origine du stash ; `git diff <branche>^1 <branche>`
redonne exactement le diff d'origine) :

| branche | commit | contenu vérifié | ex-stash (SHA supprimé) |
|---|---|---|---|
| `hermes/autostash-20260908-193237` | `ca3a65abbe` | `hermes_cli/commands.py` (1 insertion, 1 suppression) | `ca3a65abbe` |
| `hermes/autostash-20260908-173555` | `49dfd3f20c` | `apps/desktop/package.json` (1 insertion, 1 suppression) | `49dfd3f20c` |
| `hermes/autostash-20260907-085757` | `ca54c3e5ff` | 4 fichiers, 23 insertions / 5 suppressions | `ca54c3e5ff` |
| `hermes/autostash-20260902-162153` | `c1532613ad` | 3 fichiers, 13 insertions / 5 suppressions | `c1532613ad` |

Suppressions effectuées (`git stash drop`) : `stash@{4}` `ec649a3245`, `stash@{3}` `c1532613ad`,
`stash@{2}` `ca54c3e5ff`, `stash@{1}` `49dfd3f20c`, `stash@{0}` `ca3a65abbe`.

Résultat vérifié :

```
$ git -C <checkout> stash list
(vide — 0 entrée)
$ git -C <checkout> status --short --branch
## main...origin/main        (arbre de travail propre, aucune modification locale)
```

Patchs conservés dans `docs/stash-audit/patches/` :

| fichier | taille | contenu |
|---|---|---|
| `stash0_20260908-193237.patch` | 744 o | alias `com` |
| `stash1_20260908-173555.patch` | 413 o | bump electron |
| `stash2_20260907-085757.patch` | 3,7 Ko | 4 fichiers (lsp, watchdog, email, telegram) |
| `stash3_20260902-162153.patch` | 2,6 Ko | 3 fichiers (lsp, watchdog, email) |
| `stash4_20260729-wip_NONWHITESPACE.patch` | 3,9 Ko | bruit stash@{4} après `-w` (26 lignes `package-lock.json`) |

Le patch complet de `stash@{4}` (657 827 lignes, 28,7 Mo) n'a volontairement **pas** été conservé :
c'était une réécriture de fins de ligne sur `website/*`, sans contenu utile ; le diff non-whitespace
suffit comme trace.

Aucun stash n'a été conservé « par précaution » : les quatre entrées de vrai code sont dans des
branches, le bruit est documenté. `git stash list` est donc vide, conformément à l'objectif.
