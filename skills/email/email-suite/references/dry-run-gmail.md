# Envoi d'emails via Gmail API — Dry-Run + Confirmation

## Procédure

1. **Vérifier l'auth** : `$GSETUP --check` → doit afficher `AUTHENTICATED`
2. **Préparer le dry-run** : afficher TOUS les emails (destinataire, objet,
   aperçu du corps) avant d'envoyer
3. **Demander confirmation** explicite à l'utilisateur
4. **Envoyer** via `$GAPI gmail send`

## Commande d'envoi

```bash
GAPI="python $HOME/AppData/Local/hermes/skills/productivity/google-workspace/scripts/google_api.py"

$GAPI gmail send \
  --to contact@beapi.fr \
  --subject "WordPress × Design Défensif — synergie Caen ?" \
  --body "Bonjour l'équipe Be API,

Je suis Thomas Leroyer, développeur WordPress et designer basé à IFS/Caen.
..."
```

## Format du dry-run

```
═══════════════════════════════════════════════════════════════
  EXPÉDITEUR : Thomas Leroyer <searching.murphy@gmail.com>
  SIGNATURE  : Thomas Leroyer | searching-murphy.com | 06 XX XX XX XX
═══════════════════════════════════════════════════════════════

  #1 → contact@beapi.fr
  Objet : WordPress × Design Défensif — synergie Caen ?
  [aperçu du corps...]

  #2 → contact@ecedi.fr
  ...

═══════════════════════════════════════════════════════════════
  Confirmer l'envoi ? (oui/non)
═══════════════════════════════════════════════════════════════
```

## Pièges

- Les emails `privacy@` ou `dpo@` sont des adresses RGPD, pas commerciales.
  Toujours prévenir l'utilisateur si un destinataire a ce type d'adresse.
- Le Gmail API a un quota de 100 emails/jour pour les comptes gratuits.
- Utiliser `--from` uniquement si l'utilisateur a un alias configuré.
