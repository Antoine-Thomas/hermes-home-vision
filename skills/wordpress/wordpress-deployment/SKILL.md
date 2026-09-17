---
name: wordpress-deployment
description: Deployer un site WordPress local vers un serveur distant (FTP, SSH/rsync) et reecrire les URL
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - wordpress
  - deploiement
  - ftp
  - ssh
  - migration
---

# WordPress Deployment

Skill pour publier un site WordPress developpe en local vers un serveur distant, et pour migrer une base d'un environnement a l'autre.

## Pre-requis

- Site local fonctionnel et **sauvegarde** (skill `wordpress-backup-restore`)
- Acces au serveur distant : FTP/FTPS ou SSH
- Python 3.8+ (le deploiement FTP utilise la bibliotheque standard `ftplib`)
- Pour SSH : `rsync` et `scp` (fournis avec OpenSSH) — sous Windows, utilises depuis Git Bash
- WP-CLI des deux cotes pour la base de donnees

## Scripts

| Script | Role | Exemple |
|--------|------|---------|
| `deploy_ftp.py` | Envoie les fichiers par FTP/FTPS (implementation ftplib, sans dependance externe) | `python deploy_ftp.py --site mon-site --host ftp.exemple.com --user bob --remote-path /www` |
| `deploy_ssh.py` | Envoie les fichiers par rsync (repli scp) | `python deploy_ssh.py --site mon-site --host bob@serveur.com --remote-path /var/www/html` |
| `search_replace.py` | Reecrit les URL dans la base (local -> production) | `python search_replace.py --site mon-site --old-url http://mon-site.local --new-url https://exemple.com` |
| `sync_database.py` | Exporte la base locale, l'envoie et l'importe a distance | `python sync_database.py --site mon-site --host bob@serveur.com --remote-path /var/www/html` |

## Procedure de deploiement recommandee

### 1. Sauvegarder et preparer

```bash
# Sauvegarde locale complete
python ../wordpress-backup-restore/scripts/backup_site.py --site mon-site --output ./backups --compress

# Sauvegarder aussi la base distante avant tout envoi (cote serveur)
ssh bob@serveur.com "wp db export ~/backup_avant_deploy.sql --path=/var/www/html"
```

### 2. Verifier l'URL de production avant l'envoi

```bash
# Simulation de la reecriture d'URL
python scripts/search_replace.py --site mon-site \
  --old-url http://mon-site.local --new-url https://exemple.com --dry-run
```

### 3. Envoyer les fichiers

```bash
# Simulation d'abord
python scripts/deploy_ftp.py --site mon-site --host ftp.exemple.com --user bob \
  --remote-path /www --dry-run

# Envoi reel
python scripts/deploy_ftp.py --site mon-site --host ftp.exemple.com --user bob \
  --remote-path /www
```

Le mot de passe est demande de facon interactive s'il n'est pas fourni (`--password` deconseille : il apparait dans l'historique du shell).

### 4. Migrer la base

```bash
python scripts/sync_database.py --site mon-site --host bob@serveur.com \
  --remote-path /var/www/html --keep-dump
```

### 5. Reecrire les URL et verifier

```bash
python scripts/search_replace.py --site mon-site \
  --old-url http://mon-site.local --new-url https://exemple.com

# Cote serveur
ssh bob@serveur.com "wp rewrite flush --path=/var/www/html && wp cache flush --path=/var/www/html"
```

## Options importantes

| Option | Script | Effet |
|--------|--------|-------|
| `--dry-run` | tous | Affiche les actions sans rien modifier |
| `--exclude` | `deploy_ftp.py`, `deploy_ssh.py` | Patterns a ne pas envoyer (`*.log`, `.git`) |
| `--delete` | `deploy_ssh.py` | Supprime a distance ce qui n'existe plus en local (danger : `--dry-run` conseille) |
| `--use-tls` | `deploy_ftp.py` | Utilise FTPS explicite |
| `--remote-command` | `sync_database.py` | Commande WP-CLI distante (defaut `wp`) |
| `--skip-backup` | `sync_database.py` | Ne pas exporter la base distante avant import |

## Fichiers a ne jamais deployer

- `wp-config.php` : contient les identifiants de la base **locale**. Le serveur a les siens.
- `.env`, cles SSH, certificats.
- `wp-content/uploads` en totalite lors d'une mise a jour de code (medias deja en production).
- `wp-content/cache`, `wp-content/upgrade`, logs.

Par defaut, `deploy_ftp.py` et `deploy_ssh.py` excluent `wp-config.php` : retirer cette exclusion est possible mais deconseille.

## Erreurs courantes

| Erreur | Cause | Correction |
|--------|-------|------------|
| `530 Login incorrect` (FTP) | Identifiants faux ou FTPS requis | Verifier, ajouter `--use-tls`, `--port 21` |
| `SSH: Permission denied (publickey)` | Cle absente ou non autorisee | `ssh-copy-id bob@serveur.com` |
| Back-office redirige vers `.local` | URL non reecrites | Lancer `search_replace.py` |
| Images manquantes | `uploads` non transferes | Synchroniser aussi `wp-content/uploads` |
| `Error establishing a database connection` apres import | Identifiants du serveur ecrases | Ne pas deployer `wp-config.php` |
| Erreur 500 apres deploiement | Mauvaise version PHP a distance | Verifier la version PHP de l'hebergeur |

## References

- [wp search-replace](https://developer.wordpress.org/cli/commands/search-replace/)
- [Migrer WordPress](https://wordpress.org/documentation/article/moving-wordpress/)
- [rsync](https://rsync.samba.org/)
- voir `references/deployment-guide.md`

## Licence

MIT
