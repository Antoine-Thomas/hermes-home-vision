# Reference - bases WP-CLI

## Ou trouver WP-CLI

| Contexte | Emplacement |
|----------|-------------|
| Installation globale Windows | `C:\Program Files\Local\resources\extraResources\bin\wp-cli\wp-cli.phar` |
| Shell du site (Local) | `wp` directement disponible |
| Installation manuelle | `wp-cli.phar` telecharge depuis <https://make.wordpress.org/cli/handbook/guides/installing/> |

Appel direct du phar :

```bash
php wp-cli.phar core version --path=/chemin/vers/public
```

## Argument `--path`

Toute commande WP-CLI a besoin de savoir ou se trouve WordPress :

```bash
wp plugin list --path="C:/Users/<user>/Local Sites/mon-site/app/public"
```

Sous Windows avec Git Bash, utiliser des chemins `C:/...` (chemins natifs) pour les outils natifs.

## Commandes les plus utilisees

### Diagnostic

```bash
wp core version --path=...
wp core verify-checksums --path=...
wp plugin list --path=...
wp theme list --path=...
wp site health status --path=...
wp db check --path=...
```

### Plugins et themes

```bash
wp plugin install woocommerce --activate --path=...
wp plugin activate woocommerce --path=...
wp plugin deactivate woocommerce --path=...
wp plugin uninstall woocommerce --yes --path=...
wp plugin update --all --path=...

wp theme install astra --activate --path=...
wp theme update --all --path=...
```

### Base de donnees

```bash
wp db export sauvegarde.sql --path=...
wp db import sauvegarde.sql --path=...
wp db optimize --path=...
wp db search "ancien-texte" --path=...
```

### Options et contenus

```bash
wp option get siteurl --path=...
wp option update blogname "Mon Site" --path=...
wp post list --post_type=page --fields=ID,post_title --path=...
wp post create --post_type=page --post_title="Accueil" --post_status=publish --path=...
```

### Utilisateurs

```bash
wp user list --fields=ID,user_login,roles --path=...
wp user create editeur editeur@example.com --role=editor --path=...
wp user update 1 --user_pass=nouveau --path=...
```

### Maintenance

```bash
wp cache flush --path=...
wp rewrite flush --path=...
wp cron event list --path=...
wp transient delete --all --path=...
```

## Codes de sortie

| Code | Signification |
|------|---------------|
| 0 | Succes |
| 1 | Erreur generique (message sur `stderr`) |
| Autre | Erreur de l'environnement PHP ou MySQL |

Toujours verifier `returncode` dans les scripts : un `wp plugin install` peut se terminer proprement sur une erreur reseau.

## Variables d'environnement utiles

```bash
export WP_CLI_PHP_ARGS='-d memory_limit=512M'
export WP_CLI_CACHE_DIR=~/.wp-cli/cache
```

## Liens

- Commandes : <https://developer.wordpress.org/cli/commands/>
- Handbook : <https://make.wordpress.org/cli/handbook/>
- Installation : <https://make.wordpress.org/cli/handbook/guides/installing/>
