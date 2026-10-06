---
name: wordpress-site-complet
description: "Orchestrer un site WordPress : création, config, deploy."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wordpress, automation, sites]
---

# WordPress site complet

## When to Use

Quand un site WordPress doit etre cree, configure, sauvegarde puis deploye : un seul
point d'entree pour les 5 skills WordPress au lieu de les appeler dans le desordre.

## Quick Reference

```
Orchestre : local-flywheel-setup -> wordpress-site-management -> wordpress-suite
            -> wordpress-backup-restore -> wordpress-deployment
WP-CLI    : C:\wp-cli\wp.bat (PHP de Local)
Local     : 10.1.2 (PHP 8.2.29 / MySQL 8.4), sites sous %APPDATA%\Local
Dossier   : hermes-wordpress-skills (depot local)
```

## Procedure

1. **Creation** : `local-flywheel-setup` — site, PHP, MySQL, certificat local.
2. **Configuration** : `wordpress-site-management` + `wp-cli-automation` (extensions, reglages).
3. **Qualite / SEO** : `wordpress-suite` (SEO, performance, securite).
4. **Sauvegarde** : `wordpress-backup-restore` — fichiers + base.
5. **Deploiement** : `wordpress-deployment` vers le serveur distant.

## Pitfalls

- Toujours utiliser `C:\wp-cli\wp.bat`, pas `wp` nu (un fichier vide de 0 octet le masque dans System32).
- Sauvegarder avant toute mise a jour majeure ou deploiement.
- Les identifiants vivent dans `.env`, jamais en clair dans un skill ou un commit.

## Verification

- Le site repond sur son URL locale, WP-CLI renvoie `Success`.
- La sauvegarde existe sur disque (fichiers + dump SQL).
