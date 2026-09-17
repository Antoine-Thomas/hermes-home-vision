---
name: wordpress-backup-restore
description: Sauvegarder et restaurer un site WordPress complet (fichiers plus base de donnees) en une archive
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - wordpress
  - sauvegarde
  - restauration
  - reprise-apres-sinistre
---

# WordPress Backup & Restore

Skill pour creer des sauvegardes completes (fichiers + base de donnees) et restaurer un site WordPress local.

## Pre-requis

- Site WordPress provisionne dans Local by Flywheel
- WP-CLI accessible pour l'export de la base
- Espace disque : compter 2 a 3 fois la taille du site

## Scripts

| Script | Role | Exemple |
|--------|------|---------|
| `backup_site.py` | Sauvegarde complete (fichiers + base) en `.tar.gz` ou dossier | `python backup_site.py --site mon-site --compress` |
| `restore_site.py` | Restaure un site depuis une sauvegarde | `python restore_site.py --site mon-site --backup ./backups/mon-site_backup_20260101_030000.tar.gz` |
| `list_backups.py` | Liste les sauvegardes disponibles avec date et taille | `python list_backups.py --site mon-site` |

## Contenu d'une sauvegarde

```
mon-site_backup_<horodatage>.tar.gz
└── mon-site_backup_<horodatage>/
    ├── files/
    │   ├── wp-config.php
    │   ├── .htaccess
    │   └── wp-content/            # plugins, themes, uploads
    ├── database.sql
    └── metadata.json              # date, version WP, URL source, PHP
```

`metadata.json` permet de savoir quoi restaurer et d'ou venait la sauvegarde :

```json
{
  "site_name": "mon-site",
  "backup_date": "2026-01-01T03:00:00",
  "wordpress_version": "6.6.2",
  "site_url": "http://mon-site.local",
  "php_version": "8.2",
  "backup_type": "full"
}
```

## Utilisation

### Sauvegarder

```bash
# Archive compressee (recommande)
python scripts/backup_site.py --site mon-site --output ./backups --compress

# Dossier brut, plus rapide, utile en local
python scripts/backup_site.py --site mon-site --output ./backups

# Exclure les uploads (sauvegarde legere de code + base)
python scripts/backup_site.py --site mon-site --compress --exclude-uploads
```

### Lister

```bash
python scripts/list_backups.py --site mon-site --backup-dir ./backups
```

### Restaurer

```bash
# Simulation : verifie l'archive et affiche ce qui serait fait
python scripts/restore_site.py --site mon-site --backup ./backups/mon-site_backup_20260101_030000.tar.gz --dry-run

# Restauration reelle (demande confirmation)
python scripts/restore_site.py --site mon-site --backup ./backups/mon-site_backup_20260101_030000.tar.gz

# Sans confirmation
python scripts/restore_site.py --site mon-site --backup ./backups/xxx.tar.gz --force
```

## Procedure de reprise recommandee

1. **Arreter le site** dans Local (ou `manage_site.py --action stop`).
2. **Sauvegarder l'etat actuel** avant d'ecraser quoi que ce soit.
3. Restaurer l'archive souhaitee.
4. Redemarrer le site.
5. Verifier : page d'accueil, back-office, permaliens, images.
6. Si le site vient d'un autre environnement, reecrire les URL avec `search_replace.py` du skill `wordpress-deployment`.

## Sauvegarde planifiee

Linux/macOS (cron) :

```bash
0 3 * * * cd /chemin/skills/wordpress-backup-restore && \
  python scripts/backup_site.py --site mon-site --output ./backups --compress
```

Windows (Planificateur de taches) : creer une tache quotidienne appelant

```
python C:\chemin\skills\wordpress-backup-restore\scripts\backup_site.py --site mon-site --output C:\backups --compress
```

Purger les archives anciennes (exemple : plus de 30 jours) :

```bash
find ./backups -name "mon-site_backup_*.tar.gz" -mtime +30 -delete
```

## Erreurs courantes

| Erreur | Cause | Correction |
|--------|-------|------------|
| `wp-config.php` introuvable | Site non provisionne | Verifier le chemin `app/public` |
| Export de base vide | Site arrete | Demarrer le site dans Local |
| `Permission denied` a la restauration | Fichiers verrouilles | Arreter le site avant de restaurer |
| Archive enorme | `wp-content/uploads` volumineux | Utiliser `--exclude-uploads` ou exclure les backups de plugins |
| Restauration partielle | Archive corrompue | Verifier avec `tar -tzf archive.tar.gz` avant restauration |

## References

- [Sauvegarder WordPress](https://wordpress.org/documentation/article/wordpress-backups/)
- [wp db export](https://developer.wordpress.org/cli/commands/db/export/)
- voir `references/backup-strategy.md`

## Licence

MIT
