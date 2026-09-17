---
name: ssl-monitor
description: "Surveiller les certificats SSL de mes domaines."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: []
    category: devops
    created: "2026-08-25"
---
# Ssl Monitor

Surveiller les certificats SSL de mes domaines. Procedure reconstituee depuis une conversation de travail.

## When to Use — quand l'utiliser

- Voici la conversation ou j'ai demande de surveiller les certificats SSL de mes domaines.
- Je veux etre alerte 30 jours avant l'expiration.

Ne pas utiliser ce skill hors de ce cadre : preferer une commande directe si la demande est ponctuelle.

## Procedure

1. Il faut lancer `openssl s_client -connect example.com:443 -servername example.com` puis lire la date avec `openssl x509 -noout -enddate`.
2. Ensuite envoyer le resultat sur Telegram avec `hermes send --to telegram`.
3. Planifier un cron hebdomadaire.

## Commandes

```bash
openssl s_client -connect example.com:443 -servername example.com
openssl x509 -noout -enddate
hermes send --to telegram
```

## Pieges

- Attention : ne pas utiliser curl seul, il ne renvoie pas la date d'expiration.
- Le piege est que le certificat wildcard casse la verification si le SNI n'est pas passe.

## Verification

- Verifier que la sortie contient notAfter avant de conclure.

---

*Corps genere par `newskill.py --from-session` le 25/08/2026 a partir d'un resume de conversation. Relire avant de s'y fier : l'extraction est mecanique, elle ne comprend pas le contexte.*
