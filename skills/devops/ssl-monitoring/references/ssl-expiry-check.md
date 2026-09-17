<!-- Source: ssl-expiry-check/SKILL.md -->
---
name: ssl-expiry-check
description: "Verifier l'expiration des certificats SSL."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows,  linux,  macos]
metadata:
  hermes:
    tags: [ssl, tls, monitoring]
    category: devops
    created: "2026-08-25"
prerequisites:
  commands: [openssl]
---
# Verification d'expiration des certificats SSL

Controle la date d'expiration des certificats TLS d'une liste de domaines et
alerte quand il reste moins de N jours.

## When to Use — quand l'utiliser

- "mes certificats SSL expirent quand ?"
- "verifie le HTTPS de mes sites"
- avant une mise en production

## Procedure

### 1. Verifier un domaine

```bash
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null \
  | openssl x509 -noout -enddate
```

### 2. Boucler sur une liste

```bash
for d in $(cat domaines.txt); do
  echo "== $d"
  echo | openssl s_client -servername "$d" -connect "$d:443" 2>/dev/null \
    | openssl x509 -noout -enddate
done
```

## Pieges

1. **Sans -servername** le SNI n'est pas envoye : on recupere le certificat par
   defaut du serveur et non celui du domaine.
2. **Un port ferme fait echouer openssl en silence** : toujours verifier le code
   de sortie.

## Verification

```bash
openssl version
```
