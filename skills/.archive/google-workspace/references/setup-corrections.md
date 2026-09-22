# OAuth Setup — Commandes réelles

La version actuelle (v1.1.0) du script `setup.py` n'accepte PAS les flags
`--services` ni `--format json`. Voici les commandes qui fonctionnent réellement :

```bash
GSETUP="python $HOME/AppData/Local/hermes/skills/productivity/google-workspace/scripts/setup.py"

# Vérifier l'état
$GSETUP --check
# → NOT_AUTHENTICATED ou AUTHENTICATED

# Charger le client_secret
$GSETUP --client-secret "C:\Users\searc\Downloads\client_secret_XXXXX.json"
# → OK: Client secret saved

# Obtenir l'URL d'autorisation (SANS flags --services/--format)
$GSETUP --auth-url
# → https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=...

# Échanger le code
$GSETUP --auth-code "URL_OU_CODE_COLLÉ_PAR_L_UTILISATEUR"
```

**Piège :** Le SKILL.md mentionne `--services email` et `--format json` mais ces
flags ne sont pas reconnus par setup.py v1.1.0. Toujours utiliser `--auth-url` seul.
Le scope Gmail (readonly + send + modify) est inclus par défaut.
