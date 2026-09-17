---
name: wp-cli-automation
description: "Automatiser les taches WordPress via WP-CLI : mises a jour, plugins, themes, export et import de base de donnees"
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - wordpress
  - wp-cli
  - automatisation
  - maintenance
---

# WP-CLI Automation

Skill pour automatiser la maintenance d'un site WordPress : mises a jour du core, des plugins et des themes, export/import de la base de donnees, installation de plugins en lot.

## Pre-requis

- Un site WordPress local fonctionnel (voir `local-flywheel-setup`)
- WP-CLI accessible (shell du site dans Local, ou `wp-cli.phar`)
- Le site doit etre **demarre** dans Local, sinon MySQL ne repond pas

## Scripts

| Script | Role | Exemple |
|--------|------|---------|
| `update_plugins.py` | Met a jour un ou tous les plugins | `python update_plugins.py --site mon-site --dry-run` |
| `update_themes.py` | Met a jour un ou tous les themes | `python update_themes.py --site mon-site` |
| `update_core.py` | Met a jour le core WordPress | `python update_core.py --site mon-site --minor` |
| `export_db.py` | Exporte la base de donnees | `python export_db.py --site mon-site --gzip` |
| `import_db.py` | Importe une base (ecrase les donnees) | `python import_db.py --site mon-site --input dump.sql --confirm` |
| `install_plugins.py` | Installe des plugins en lot | `python install_plugins.py --site mon-site --plugins woocommerce,yoast-seo` |
| `wp_cli_helper.py` | Module partage (non executable) | importe par les scripts ci-dessus |

Tous les scripts acceptent `--site`, `--sites-dir` et `--dry-run` (sauf `export_db.py`, en lecture seule).

## Utilisation

### Mises a jour

```bash
# Verifier ce qui serait modifie
python scripts/update_plugins.py --site mon-site --dry-run
python scripts/update_themes.py --site mon-site --dry-run
python scripts/update_core.py --site mon-site --dry-run

# Appliquer
python scripts/update_plugins.py --site mon-site
python scripts/update_themes.py --site mon-site
python scripts/update_core.py --site mon-site --minor      # correctifs de securite seulement
python scripts/update_core.py --site mon-site --version 6.6
```

### Base de donnees

```bash
# Export simple / compresse
python scripts/export_db.py --site mon-site
python scripts/export_db.py --site mon-site --gzip --output ./dumps/mon-site.sql.gz

# Exclure des tables volumineuses
python scripts/export_db.py --site mon-site --exclude-tables wp_actionscheduler_logs,wp_wc_sessions

# Import (export de securite automatique avant ecrasement)
python scripts/import_db.py --site mon-site --input ./dumps/mon-site.sql --confirm
```

### Plugins en lot

```bash
python scripts/install_plugins.py --site mon-site --plugins woocommerce,yoast-seo,contact-form-7
python scripts/install_plugins.py --site mon-site --from-file plugins.txt --no-activate
```

Format de `plugins.txt` (un slug par ligne, `#` pour les commentaires) :

```
woocommerce
yoast-seo
# contact-form-7
```

## Automatisation planifiee

Exemple de tache hebdomadaire (cron Linux/macOS ou Planificateur de taches Windows) :

```bash
0 3 * * 1 cd /chemin/skills/wp-cli-automation && \
  python scripts/export_db.py --site mon-site --gzip --output ./dumps/mon-site.sql.gz && \
  python scripts/update_plugins.py --site mon-site
```

Toujours exporter la base **avant** une vague de mises a jour.

## Codes de sortie

Les scripts retournent `0` en succes et `1` si au moins une operation echoue : utilisable directement dans un pipeline CI ou un cron.

## Erreurs courantes

| Erreur | Cause | Correction |
|--------|-------|------------|
| `Error establishing a database connection` | Site arrete | Demarrer le site dans Local |
| `wp-config.php` introuvable | Site non provisionne | Provisionner le site dans Local |
| `Could not find plugin` | Slug errone | Verifier le slug sur wordpress.org/plugins |
| `Import refusee` | `--confirm` absent | Relancer avec `--confirm` apres sauvegarde |
| Telechargements lents | `--all` sur un site avec de nombreux plugins | Cibler les slugs un par un |

## References

- [WP-CLI - commands](https://developer.wordpress.org/cli/commands/)
- [Mise a jour de WordPress](https://wordpress.org/documentation/article/updating-wordpress/)
- voir `references/wp-cli-recipes.md`

## Licence

MIT
