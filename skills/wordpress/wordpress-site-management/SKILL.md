---
name: wordpress-site-management
description: Creer, lister, configurer et supprimer des sites WordPress locaux avec WP-CLI
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - wordpress
  - wp-cli
  - gestion-de-site
  - local
---

# WordPress Site Management

Skill pour administrer les sites WordPress locaux : creation, inventaire, configuration (plugins, themes, options) et suppression.

## Pre-requis

- Local by Flywheel installe (voir skill `local-flywheel-setup`)
- WP-CLI disponible (shell du site dans Local, ou dans le `PATH`)
- Sites presents dans `~/Local Sites/`

## Scripts

| Script | Role | Exemple |
|--------|------|---------|
| `create_site.py` | Telecharge WordPress et l'installe dans un dossier de site | `python create_site.py --name mon-site --domain mon-site.local` |
| `list_sites.py` | Inventaire des sites (version WP, theme actif, plugins actifs) | `python list_sites.py` |
| `configure_site.py` | Installe/active plugins et themes, met a jour des options | `python configure_site.py --site mon-site --plugins woocommerce,yoast-seo` |
| `delete_site.py` | Supprime le dossier d'un site, avec confirmation | `python delete_site.py --name mon-site` |

## Utilisation detaillee

### Creer un site

```bash
python scripts/create_site.py \
  --name mon-site \
  --domain mon-site.local \
  --wp-version latest \
  --admin-user admin \
  --admin-email admin@example.com
```

Options utiles :

- `--skip-install` : telecharge le core WordPress sans lancer l'installation.
- `--sites-dir` : racine des sites (defaut `~/Local Sites`).
- `--force` : autorise l'ecriture dans un dossier deja rempli.

### Inventaire

```bash
python scripts/list_sites.py
python scripts/list_sites.py --json > inventaire.json
```

### Configurer un site

```bash
# Plugins + theme
python scripts/configure_site.py --site mon-site --plugins woocommerce,yoast-seo --theme astra

# Options WordPress
python scripts/configure_site.py --site mon-site --option blogname=MonSite --option blogdescription="Demo locale"

# Desinstaller des plugins
python scripts/configure_site.py --site mon-site --remove-plugins hello,akismet
```

### Supprimer un site

```bash
python scripts/delete_site.py --name mon-site          # demande confirmation
python scripts/delete_site.py --name mon-site --force  # sans confirmation
```

## Commandes WP-CLI de reference

```bash
# Verifier l'integrite du core
wp core verify-checksums --path=/chemin/vers/public

# Plugins et themes
wp plugin list --path=...
wp plugin update --all --path=...
wp theme update --all --path=...

# Options
wp option get siteurl --path=...
wp option update blogname "Nouveau nom" --path=...

# Utilisateurs
wp user list --path=...
wp user create editeur editeur@example.com --role=editor --path=...

# Etat du site
wp site health status --path=...
```

## Erreurs courantes

| Erreur | Cause | Correction |
|--------|-------|------------|
| `This does not seem to be a WordPress installation` | Mauvais `--path` ou core absent | `--path` doit pointer sur `app/public` |
| `Error establishing a database connection` | Site arrete ou identifiants BDD invalides | Demarrer le site dans Local |
| `wp: command not found` | WP-CLI absent du `PATH` | Utiliser le shell du site Local ou installer `wp-cli.phar` |
| `Permission denied` a la suppression | Fichiers verrouilles par Local | Arreter le site avant de supprimer |
| Plugin non active | Slug errone | Verifier le slug sur wordpress.org/plugins |

## References

- [WP-CLI - commandes](https://developer.wordpress.org/cli/commands/)
- [WP-CLI Handbook](https://make.wordpress.org/cli/handbook/)
- voir `references/wp-cli-basics.md`

## Licence

MIT
