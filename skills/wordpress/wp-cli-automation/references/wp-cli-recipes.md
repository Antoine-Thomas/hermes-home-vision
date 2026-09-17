# Reference - recettes WP-CLI

Recettes pretes a l'emploi pour les taches courantes de maintenance.

## Sauvegarder avant toute operation risquee

```bash
wp db export "avant_maj_$(date +%Y%m%d_%H%M%S).sql" --path=...
```

C'est la regle de base : jamais de mise a jour de masse sans export prealable.

## Mise a jour complete d'un site

```bash
# 1. Sauvegarde
python export_db.py --site mon-site --gzip --output ./dumps/avant_maj.sql.gz

# 2. Ce qui va changer
python update_core.py --site mon-site --dry-run
python update_plugins.py --site mon-site --dry-run
python update_themes.py --site mon-site --dry-run

# 3. Application
python update_core.py --site mon-site --minor
python update_plugins.py --site mon-site
python update_themes.py --site mon-site

# 4. Verification
wp core verify-checksums --path=...
wp site health status --path=...
```

## Detecter un site compromis

```bash
# Fichiers du core modifies
wp core verify-checksums --path=...

# Plugins inactifs ou abandonnes (a supprimer)
wp plugin list --status=inactive --field=name --path=...
wp plugin list --fields=name,status,update --path=...

# Administrateurs
wp user list --role=administrator --fields=ID,user_login,user_email --path=...

# Taches cron suspectes
wp cron event list --fields=hook,next_run_relative --path=...
```

## Migrer une base entre environnements

```bash
# Sur l'environnement source
python export_db.py --site mon-site --gzip --output ./dumps/source.sql.gz

# Sur la cible
python import_db.py --site mon-site --input ./dumps/source.sql.gz --confirm

# Reecrire les URL
python ../wordpress-deployment/scripts/search_replace.py \
  --site mon-site \
  --old-url http://mon-site.local \
  --new-url https://exemple.com
```

## Optimisation de la base

```bash
wp db optimize --path=...
wp transient delete --all --path=...
wp post delete $(wp post list --post_type=revision --format=ids --path=...) --force --path=...
wp db size --human-readable --path=...
```

## Gestion des utilisateurs

```bash
wp user list --fields=ID,user_login,display_name,roles --path=...
wp user create editeur editeur@exemple.com --role=editor --user_pass=motdepasse --path=...
wp user update 2 --role=author --path=...
wp user delete 5 --reassign=1 --yes --path=...
```

## Rechercher et remplacer du contenu

```bash
# Simulation
wp search-replace "ancien" "nouveau" --all-tables --dry-run --path=...

# Application
wp search-replace "ancien" "nouveau" --all-tables --precise --path=...

# Limiter aux tables de contenu
wp search-replace "ancien" "nouveau" wp_posts wp_postmeta --path=...
```

## Bonnes pratiques

1. Un `--dry-run` avant chaque operation destructive.
2. Un export de base avant chaque mise a jour de masse.
3. Mettre a jour les plugins un par un en cas de doute : si le site casse, on sait qui accuser.
4. Verifier `wp site health status` apres les mises a jour.
5. Toujours faire correspondre la version PHP de l'environnement local et de la production.

## Liens

- <https://developer.wordpress.org/cli/commands/>
- <https://make.wordpress.org/cli/handbook/how-to/>
