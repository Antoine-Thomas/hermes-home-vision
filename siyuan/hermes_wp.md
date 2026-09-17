# hermes-wp

> **Statut** : préparé, à tester
> **Dernière mise à jour** : 15/09/2026

## Fait

`C:\wp-cli\hermes-wp.ps1` — enveloppe lisible autour de WP-CLI. Elle détecte le site depuis le
dossier courant et lance `wp.bat` depuis celui-ci.

| Raccourci | Effet |
|---|---|
| `hermes-wp info` | version de WordPress, URL, thème actif, extensions actives/total, taille de la base, version de PHP |
| `hermes-wp plugins` | extensions installées (nom, statut, version, mise à jour) puis mises à jour disponibles |
| `hermes-wp backup` | export SQL dans `<site>\hermes-backups\base-<horodatage>.sql` |
| `hermes-wp deploy` | vérifie les prérequis de déploiement (ssh, rsync, cibles déclarées) — **n'agit pas** |
| `hermes-wp <commande>` | toute commande WP-CLI : `hermes-wp plugin list --status=active` |
| `hermes-wp aide` | l'aide, plus le site détecté |

Options : `-NoColor` (sortie sans couleur) · `-Oui` (autoriser une action qui écrit).

**Détection du site** : le dossier courant, puis chaque dossier parent, jusqu'à trouver
`wp-config.php` (racine WordPress classique) ou `app\public\wp-config.php` (Local by Flywheel).

**Chemin absolu** : le script appelle `C:\wp-cli\wp.bat` et non `wp`. Un fichier vide nommé `wp`
dans `C:\Windows\System32` masque le `wp.bat` du PATH ; ce raccourci n'en dépend donc pas.

**Sécurité** : aucune action qui écrit n'est lancée sans `-Oui`. `deploy` ne fait que vérifier et
afficher la commande à employer ; le déploiement réel reste le domaine du skill
`wordpress-deployment`.

## Reste à faire

- **Aucun test sur un site vivant** : il n'existe aucun site Local sur cette machine au 15/09/2026.
  Ce qui a été vérifié est listé plus bas. À reprendre dès qu'un site est recréé, notamment
  `info` (lecture réelle de la base et de PHP) et `backup -Oui` (écriture de l'export).
- `rsync` n'est pas installé sur la machine (`ssh` oui) : le raccourci `deploy` le signale.
- Aucune cible de déploiement n'est déclarée. Format attendu dans
  `C:\wp-cli\hermes-wp-sites.json` :
  `{ "mon-site": { "hote": "user@srv", "chemin": "/var/www/site" } }`

### Ce qui a été testé le 15/09/2026 (sans site vivant)

| Test | Résultat |
|---|---|
| Analyse du script et `hermes-wp aide` | affiche les raccourcis et « aucun site détecté », code 0 |
| `hermes-wp info` hors d'un site | message clair, **code 2** |
| Détection depuis une arborescence Local (`mon-site\app\public\wp-config.php`) | site « mon-site » détecté, bon dossier |
| Détection depuis une racine classique (`wp-config.php` à la racine) | dossier détecté |
| `hermes-wp deploy -NoColor` | ssh présent, rsync absent, aucune cible déclarée, **code 3**, aucune action |
| Caractères non ASCII dans le script | aucun (PowerShell 5.1 sans BOM les affichait de travers) |

## Pièges

- **PowerShell 5.1 lit un `.ps1` UTF-8 sans BOM en ANSI** : les tirets longs et puces typographiques
  s'affichent de travers. Le script est volontairement sans accent ni caractère non ASCII.
- L'export `backup` ne couvre **que la base**. Les fichiers (`wp-content`) demandent
  `wordpress-backup-restore`.
- `wp-cli` a besoin d'un site : lancé hors d'une racine WordPress, il échoue. D'où le code 2 du
  raccourci `info` plutôt qu'un message d'erreur de WP-CLI.
- Le site détecté pour Local est `app\public`, pas la racine du site : c'est là que WP-CLI doit
  tourner, et les sauvegardes atterrissent donc dans `app\public\hermes-backups\`.

## Commandes

```
cd "chemin\du\site"

hermes-wp info
hermes-wp plugins
hermes-wp backup -Oui
hermes-wp deploy
hermes-wp plugin list --status=active
hermes-wp option get siteurl
hermes-wp aide
```

Le script vit dans `C:\wp-cli\` à côté de `wp.bat` : l'appeler par son chemin complet, ou ajouter
`C:\wp-cli` au PATH. Il n'est pas installé comme commande globale du système.
