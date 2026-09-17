# Profil veille — copie versionnée (audit)

- `config.yaml` : copie du fichier live. **Aucun secret** (les clés vivent dans `.env`, non versionné).
- `SOUL.md` : rôle du profil veille.
- `.env` du profil : **volontairement absent de ce dépôt** — contient
  `OMNIROUTE_API_KEY` (clé dédiée `hermes_veille`, restreinte) et `TELEGRAM_BOT_TOKEN`
  (bot dédié `@Hermesveille1_veille_bot`).

Restriction appliquée dans `config.yaml` :

```yaml
platform_toolsets:
  telegram: [web, skills, memory, session_search, todo]
```

Raison : la plateforme Telegram du profil veille n'expose ni shell, ni écriture de fichiers, ni
pilotage machine. La plateforme `cli` (utilisée par le cron `hermes -p veille -z`) garde
`terminal`/`file`, nécessaires pour écrire dans SiYuan.
