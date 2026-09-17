# Reference - guide de deploiement

## Choisir la methode de transfert

| Methode | Avantages | Inconvenients | Quand l'utiliser |
|---------|-----------|---------------|------------------|
| FTP/FTPS | Disponible partout, aucun acces shell | Lent, pas de differentiel, fragile sur de nombreux fichiers | Hebergement mutualise sans SSH |
| SSH/rsync | Rapide, differentiel, reprise possible, exclusions fines | Necessite un acces SSH | VPS, serveur dedie, hebergement avec SSH |
| scp | Simple, universel avec SSH | Reecrit tout, pas d'exclusion, pas de reprise | Transfert ponctuel d'un fichier ou d'une archive |
| Git + CI | Versionne, reproductible, rollback | Demande une chaine de deploiement | Projet a plusieurs, deploiements frequents |

Regle pratique : **rsync des que SSH est disponible**, FTP uniquement en dernier recours.

## Ce qui appartient a l'environnement local et ne doit pas partir en production

- `wp-config.php` (identifiants BDD, sels, prefixe)
- `.env` et tout fichier de secrets
- `wp-content/cache`, `wp-content/upgrade`, logs
- la base de donnees locale telle quelle : elle contient les URL `.local`

## Ordre de deploiement correct

```
1. Sauvegarde locale
2. Sauvegarde distante (avant ecrasement)
3. Verification des differences (--dry-run)
4. Transfert des fichiers
5. Transfert de la base (si necessaire)
6. Remplacement des URL dans la base
7. Vider les caches (wp cache flush, wp rewrite flush)
8. Verification fonctionnelle
```

## Verification apres deploiement

```bash
# Cote serveur
wp option get siteurl --path=/var/www/html
wp option get home --path=/var/www/html
wp core version --path=/var/www/html
wp plugin list --status=active --field=name --path=/var/www/html
wp rewrite flush --path=/var/www/html

# Depuis un poste
curl -sI https://exemple.com | head -5
```

Controles fonctionnels a faire a la main :

- page d'accueil et une page interne
- back-office (`/wp-admin`) : connexion
- images et medias
- formulaires de contact
- HTTPS valide (pas d'avertissement navigateur)

## Rollback

```bash
# Fichiers (rsync inverse depuis une sauvegarde locale)
rsync -avz --delete ./backups/mon-site_backup_<date>/files/ bob@serveur:/var/www/html/

# Base distante
ssh bob@serveur "wp db import ~/backup_before_sync_<date>.sql --path=/var/www/html"
```

Conserver systematiquement la sauvegarde distante avant import : c'est le seul moyen de revenir en arriere si la base envoyee est mauvaise.

## Pieges specifiques a WordPress

- **URL en dur** : WordPress stocke l'URL dans les options `siteurl` et `home`, mais aussi dans les tables `wp_posts` (contenu, blocs Gutenberg) et `wp_postmeta`. `wp search-replace` traite tout cela ; modifier seulement les options ne suffit pas.
- **Serialisation PHP** : un simple `UPDATE` SQL sur `wp_options` casse les valeurs serialisees. Utiliser `wp search-replace` qui gere la serialisation.
- **Prefixe de tables** : si le local et la production utilisent des prefixes differents, reecrire les URL avec les bonnes tables (`--all-tables`).
- **Versions PHP differentes** : verifier la version PHP de l'hebergeur avant de deployer un theme ou un plugin recent.
- **Sels de securite** : ne jamais ecraser `wp-config.php` en production, meme pour "corriger" une erreur : cela deconnecte tous les utilisateurs.

## Depot distant : quelques commandes utiles

```bash
# Verifier l'espace disque
ssh bob@serveur "df -h"

# Droits des fichiers (typique hebergement mutualise)
ssh bob@serveur "find /var/www/html -type d -exec chmod 755 {} \; -o -type f -exec chmod 644 {} \;"

# Proprietaire correct
ssh bob@serveur "sudo chown -R www-data:www-data /var/www/html"
```

## Liens

- <https://wordpress.org/documentation/article/moving-wordpress/>
- <https://developer.wordpress.org/cli/commands/search-replace/>
- <https://rsync.samba.org/>
