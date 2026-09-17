---
name: local-flywheel-setup
description: Installer et configurer Local by Flywheel, puis creer un premier site WordPress local
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - wordpress
  - local-by-flywheel
  - installation
  - setup
---

# Local by Flywheel Setup

Skill pour installer **Local by Flywheel**, preparer sa configuration et creer un premier site WordPress local.

## Pre-requis

- Windows 10/11, macOS ou Linux
- Droits administrateur pour l'installation de l'application
- Connexion internet (telechargement de Local et de WordPress)
- 5 Go d'espace disque libre minimum

## Installation de Local

### Etape 1 - Telecharger Local

Site officiel : <https://localwp.com/>

Choisir l'installateur correspondant a votre systeme :

| Systeme | Fichier |
|---------|---------|
| Windows | `Local-x.x.x-windows.exe` |
| macOS (Intel) | `Local-x.x.x-mac-intel.dmg` |
| macOS (Apple Silicon) | `Local-x.x.x-mac-arm64.dmg` |
| Linux | `Local-x.x.x-linux.AppImage` |

### Etape 2 - Installer

Windows et macOS : lancer l'installateur et suivre l'assistant (installation globale, aucun droit admin requis sur macOS).

Linux : rendre l'AppImage executable puis la lancer.

```bash
chmod +x Local-*.AppImage
./Local-*.AppImage
```

### Etape 3 - Verifier

Au premier lancement, Local propose de creer un site. L'application embarque PHP, MySQL, nginx/Apache et WP-CLI : **aucune installation separee de ces composants n'est necessaire**.

## Creation du premier site

1. Ouvrir Local puis cliquer sur **Create a new site**.
2. Nom du site : minuscules, sans espaces (ex. `mon-site`).
3. Environnement : **Preferred** (versions recommandees par Local).
4. Identifiants WordPress : renseigner un utilisateur et un mot de passe admin.
5. Cliquer sur **Add Site** puis attendre la fin du provisionnement.
6. Cliquer sur **WP Admin** pour ouvrir le back-office.

## Scripts fournis

| Script | Role |
|--------|------|
| `install_local.py` | Telecharge l'installateur Local pour le systeme courant et l'installe |
| `configure_local.py` | Ecrit une configuration de reference pour un site (versions PHP/MySQL, admin, SSL) |
| `create_site.py` | Prepare l'arborescence et le fichier de configuration d'un nouveau site local |
| `list_sites.py` | Liste les sites presents dans le dossier `Local Sites` |
| `manage_site.py` | Demarre, arrete ou redemarre un site via le CLI Local ou Docker |

### Exemples

```bash
python scripts/create_site.py --name mon-site --domain mon-site.local --php-version 8.2
python scripts/list_sites.py
python scripts/manage_site.py --name mon-site --action start
```

## Emplacement des sites

| Systeme | Dossier |
|---------|---------|
| Windows | `C:\Users\<user>\Local Sites\` |
| macOS | `~/Local Sites/` |
| Linux | `~/Local Sites/` |

Chaque site contient `app/public` (racine WordPress), `conf/` (config serveur) et `logs/`.

## Depannage

| Symptome | Cause probable | Correction |
|----------|----------------|------------|
| Les ports 80/443 sont occupes | Un autre serveur web tourne | Local > Preferences > Advanced : changer les ports |
| Site inaccessible (`ERR_CONNECTION_REFUSED`) | Le site est arrete | Demarrer le site dans Local ou `manage_site.py --action start` |
| Le domaine local ne resout pas | Entree `hosts` absente | Local ecrit normalement dans `C:\Windows\System32\drivers\etc\hosts`; verifier les droits |
| Provisionnement bloque | Docker non demarre | Demarrer Docker Desktop puis relancer Local |
| Erreur SSL sur le domaine `.local` | Certificat non approuve | Local > Tools > Trust SSL, puis redemarrer le site |

## References

- [Documentation Local by Flywheel](https://localwp.com/help-docs/)
- [WP-CLI Handbook](https://make.wordpress.org/cli/handbook/)
- [Local CLI](https://localwp.com/help-docs/advanced/local-cli/)
- voir `references/local-by-flywheel.md`

## Licence

MIT
