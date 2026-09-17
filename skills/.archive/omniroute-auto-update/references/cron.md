# Cron invisible — veille + ajout auto des nouvelles IA gratuites

Le cron s'exécute dans le scheduler Hermes, SANS fenêtre console.

## Configuration actuelle (vérifiée 2026-09-05)

- **Job** : `a86c7c7f0721` — « OmniRoute découverte IA gratuites »
- **Schedule** : `every day at 9am` (quotidien)
- **Script** : `watch_free_models.py` (dans `~/AppData/Local/hermes/scripts/`)
- **no_agent** : `true` (le script EST le job)
- **deliver** : `telegram,local` (notification Telegram + fichier local)
- **Comportement** : le wrapper exécute `discover_free_models.py --apply`
  (sonde + AJOUTE les modèles validés au combo eco, avec backup avant écriture)
  puis n'imprime un message QUE si au moins un modèle a été ajouté, et affiche
  un popup local. Sortie vide = silence total (watchdog).

## Scripts

- `scripts/discover_free_models.py` (skill) — découverte + probe + `--apply` + journal `model_verdicts.md`.
- `~/AppData/Local/hermes/scripts/watch_free_models.py` — wrapper cron (sortie vide si rien).

## Vérification

```bash
hermes cron list   # job daily 9h, deliver telegram,local
# journal des verdicts :
cat C:\Users\searc\AppData\Local\hermes\skills\omniroute-auto-update\references\model_verdicts.md
# combo eco (nombre de modèles) :
curl -s -H "Authorization: Bearer $OMNIROUTE_API_KEY" http://127.0.0.1:20128/api/combos
```

## Ajout manuel (même effet que le cron)

```bash
python C:\Users\searc\AppData\Local\hermes\skills\omniroute-auto-update\scripts\discover_free_models.py --apply
```
