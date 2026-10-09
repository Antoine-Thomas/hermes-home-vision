# Multi-bot Telegram — deux bots = deux profils

Un seul `TELEGRAM_BOT_TOKEN` par `.env`. 1 token = 1 bot. Pour faire tourner
@Omaths2_watch_bot et @Hermes_assistante_2026_bot en parallèle sur la même machine,
utiliser deux profils Hermes distincts (pas deux entrées `channel_directory.json` dans le même profil).

## Procédure

1. Créer le profil watch (clone du default, conserve config/crons) :
   ```
   hermes profile create watch --clone
   ```
   `C:/Users/searc/.local/bin/watch.bat` est créé. `hermes -p watch` cible ce profil.
2. Mettre le token du 2e bot dans le `.env` du profil watch, ligne 486 active (dernière occurrence gagne) :
   ```
   TELEGRAM_BOT_TOKEN=8967...  # Omaths2_watch_bot
   TELEGRAM_ALLOWED_USERS=8956868107
   ```
   default garde `8802...` (Hermes_assistante_2026_bot). Ne pas laisser deux tokens actifs dans le même `.env`.
3. Copier les skills de surveillance si besoin :
   ```
   robocopy C:/Users/searc/AppData/Local/hermes/skills/photo C:/Users/searc/AppData/Local/hermes/profiles/watch/skills/photo /E
   robocopy .../record .../profiles/watch/skills/record /E
   ```
4. Démarrer chaque gateway :
   ```
   hermes gateway start              # default PID 27236
   hermes -p watch gateway start    # watch PID 2540
   hermes gateway status
   hermes -p watch gateway status
   ```
   Les deux Scheduled Tasks `Hermes_Gateway` et `Hermes_Gateway_watch` restent actives.

## Vérification

- `curl https://api.telegram.org/bot<TOKEN>/getMe` -> `{"ok":true,"result":{"id":8967117033,"username":"Omaths2_watch_bot"}}`
- `https://api.telegram.org/bot<TOKEN>/getWebhookInfo` -> `pending_update_count` doit être 0, pas d'url webhook.
- `gateway.log` doit montrer `telegram connected`, `polling confirmed healthy`, `set_my_commands OK 60 cmds`, `Gateway running 2 platforms`.
- `Channel directory built: 0 target(s)` au premier démarrage est normal — le DM s'appaire au premier message reçu.

### Lorsqu'un profil est servi par le gateway multiplexé

Lorsque plusieurs profils partagent un même gateway (configuration par défaut), les commandes suivantes permettent de vérifier l'état :

- `hermes gateway status` : affiche le PID du gateway principal et la liste des profils qu'il sert.
- `hermes gateway list` : montre l'état de chaque profil (tous servis par le même multiplexer).
- `hermes -p <profil> gateway status` : indique que le profil est servi par le gateway du profil par défaut (ex: `hermes -p watch gateway status`).
- Les logs du gateway (`logs/gateway.log`) montrent `telegram connected` et `polling confirmed healthy` pour chaque bot configuré.
- Le script de santé (`scripts/check_gateways.ps1`) signale les profils non surveillés lorsqu'ils n'ont pas de tâche planifiée dédiée (ce qui est normal en mode multiplexing).

## Pitfalls

- Éditer `profiles/watch/channel_directory.json` à la main pour injecter le DM est écrasé au redémarrage (`Channel directory built: 0 target(s)` reconstruit depuis le state DB). Envoyer `/ping` depuis Telegram (ID dans `TELEGRAM_ALLOWED_USERS`) pour appairer ; le fichier se remplit seul.
- `Gateway running 2 platforms` + `kanban dispatcher: another gateway already holds ... lock` est normal à deux gateways — un seul dispatche le kanban, les deux répondent sur Telegram.
- Token actif = dernière ligne `TELEGRAM_BOT_TOKEN=` non commentée dans le `.env` du profil. La ligne 338 commentée est ignorée.
- `Get-CimInstance Win32_Process ... like '*gateway*'` montre 2 process par gateway (parent `.venv` + enfant `.hermes-runtime`). Ne pas tuer l'enfant seul — le service passe en `No gateway process detected`.
