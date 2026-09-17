# Reference - Local by Flywheel

## Ce que Local installe

Local embarque l'ensemble de la pile necessaire, sans installation separee :

| Composant | Role |
|-----------|------|
| PHP | Execution de WordPress (versions 7.4 a 8.3 selon Local) |
| MySQL / MariaDB | Base de donnees par site |
| nginx ou Apache | Serveur web par site |
| MailHog | Capture des emails sortants (test) |
| WP-CLI | Gestion de WordPress en ligne de commande |
| Adminer | Interface web pour la base de donnees |

## Arborescence d'un site

```
~/Local Sites/<site>/
├── app/
│   └── public/          # Racine WordPress (wp-config.php, wp-content, ...)
├── conf/                # Configurations serveur (nginx, php.ini, my.cnf)
├── logs/                # Logs PHP, nginx, MySQL
└── site.json            # Metadonnees (cree par le skill create_site.py)
```

## Versions et environnement

- **Preferred** : versions recommandees par Local, bon choix par defaut.
- **Custom** : permet de choisir PHP/MySQL/nginx. Pertinent pour reproduire un hebergement.
- Changer la version PHP se fait dans l'onglet du site, sans reinstaller WordPress.

## SSL local

Local genere un certificat auto-signe par site. Pour l'approuver :

1. Onglet du site > **Trust** (ou Tools > Trust SSL)
2. Redemarrer le site

Sans cette etape, le navigateur affiche un avertissement de securite sur `https://<site>.local`.

## Emails sortants

MailHog intercepte tous les emails (`wp_mail`). Consultation : bouton **MailHog** dans l'onglet du site. Utile pour tester les formulaires de contact et les emails de reinitialisation.

## Base de donnees

- Acces via **Adminer** depuis l'interface Local.
- Identifiants affiches dans l'onglet **Database** du site.
- Export/import en ligne de commande : voir le skill `wp-cli-automation`.

## Commandes utiles dans le conteneur

Local permet d'ouvrir un shell dans le site : clic droit sur le site > **Open Site Shell**.

```bash
wp --info
wp core version
wp plugin list
php -v
```

## Pieges connus

- Les chemins avec espaces (`Local Sites`) doivent etre entre guillemets en ligne de commande.
- `wp` est disponible dans le shell du site, pas forcement dans un terminal classique.
- Sur Windows, lancer les scripts depuis Git Bash avec des chemins `C:/...` (pas `/c/...`) pour les outils natifs.
- Un site arrete ne repond pas : verifier l'etat avant de diagnostiquer un probleme WordPress.

## Liens

- Documentation : <https://localwp.com/help-docs/>
- Local CLI : <https://localwp.com/help-docs/advanced/local-cli/>
- Forum : <https://community.localwp.com/>
