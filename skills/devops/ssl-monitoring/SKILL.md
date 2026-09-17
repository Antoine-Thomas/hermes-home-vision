---
name: ssl-monitoring
description: "Surveiller et verifier l'expiration des certificats SSL/TLS."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [ssl, tls, monitoring]
    category: devops
    created: "2026-09-10"
    umbrella_of: [ssl-expiry-check, ssl-monitor]
prerequisites:
  commands: [openssl]
---

# SSL Monitoring

Surveillance et verification de l'expiration des certificats TLS.

## When to Use

- "mes certificats SSL expirent quand ?" / "verifie le HTTPS de mes sites"
- Surveillance periodique (alerte 30j avant expiration)
- Avant mise en production

## Procedure — check ponctuel

```bash
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null \
  | openssl x509 -noout -enddate
```

Boucle sur une liste :

```bash
for d in $(cat domaines.txt); do
  echo "== $d"
  echo | openssl s_client -servername "$d" -connect "$d:443" 2>/dev/null \
    | openssl x509 -noout -enddate
done
```

## Procedure — monitoring recurrent

1. Lancer `openssl s_client -connect … -servername …` puis lire la date avec `openssl x509 -noout -enddate`.
2. Envoyer le resultat via `hermes send --to telegram` si pertinent.
3. Planifier un cron hebdomadaire.

## Pieges

- Sans `-servername` le SNI n'est pas envoye : certificat par defaut retourne.
- Un port ferme fait echouer openssl en silence : verifier le code de sortie.
- Ne pas utiliser `curl` seul : il ne renvoie pas la date d'expiration.
- Wildcard : la verification casse si le SNI n'est pas passe.

## Verification

```bash
openssl version
# verifier que la sortie contient notAfter
```

## References

- `references/ssl-expiry-check.md` — procedure detaillee de verification ponctuelle
- `references/ssl-monitor.md` — procedure de monitoring et alerting Telegram
