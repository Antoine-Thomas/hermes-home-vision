# Reference - strategie de sauvegarde

## Ce qu'une sauvegarde complete doit contenir

| Element | Pourquoi | Sans lui |
|---------|----------|----------|
| `wp-config.php` | Connexion BDD, sels de securite, prefixes | WordPress ne demarre pas |
| `wp-content/plugins` | Code metier, extensions | Fonctionnalites perdues |
| `wp-content/themes` | Apparence, personnalisations | Site visuellement casse |
| `wp-content/uploads` | Medias (images, PDF) | Images manquantes |
| Base de donnees | Articles, pages, reglages, utilisateurs | Contenu perdu |
| `metadata.json` | Traçabilite (date, versions, URL) | Restauration a l'aveugle |

Ce qui ne sert a rien de sauvegarder : `wp-content/cache`, `wp-content/upgrade` (regenere automatiquement), les plugins de sauvegarde concurrents.

## Frequences conseillees

| Contexte | Frequence | Type |
|----------|-----------|------|
| Site en developpement actif | Quotidienne + avant chaque mise a jour | Complete compressee |
| Site stable, contenu rare | Hebdomadaire | Complete compressee |
| Avant une migration ou une mise a jour majeure | Ponctuelle, obligatoire | Complete + export BDD separe |
| Avant une manipulation risquee en BDD | Ponctuelle | Export BDD seul |

## Retention

Regle simple : conserver

- les 7 dernieres sauvegardes quotidiennes
- les 4 dernieres sauvegardes hebdomadaires
- la derniere sauvegarde avant chaque mise a jour majeure

Exemple de purge (Linux/macOS) :

```bash
# Supprimer les archives de plus de 30 jours
find ./backups -name "*_backup_*.tar.gz" -mtime +30 -delete

# Ne garder que les 10 archives les plus recentes
ls -1t ./backups/*_backup_*.tar.gz | tail -n +11 | xargs -r rm
```

## Restauration : ordre des operations

1. **Arreter** le site (fichiers verrouilles sinon).
2. **Sauvegarder** l'etat actuel, meme s'il est casse : il peut contenir des donnees recentes.
3. **Restaurer** les fichiers.
4. **Importer** la base.
5. **Redemarrer** le site.
6. **Verifier** : accueil, back-office, permaliens, medias, formulaires.
7. **Reecrire les URL** si l'environnement source differe (`search_replace.py`).

## Pieges classiques

- **Sauvegarde pendant que le site tourne** : la base peut etre incoherente. Arreter le site ou exporter BDD et fichiers dans la foulee.
- **Archiver `wp-content/uploads` en entier** : peut peser plusieurs gigaoctets. Pour une sauvegarde de code, utiliser `--exclude-uploads` et sauvegarder les medias separement (rsync vers un NAS, par exemple).
- **Restaurer une base d'un autre environnement sans reecrire les URL** : le back-office redirige vers l'ancien domaine, les images cassent.
- **Oublier les sels de securite** : restaurer `wp-config.php` d'un autre site invalide les sessions.
- **Penser que Local suffit** : Local ne fait pas de versioning. Une suppression de site est definitive.

## Verifier une archive avant restauration

```bash
# Lister le contenu
tar -tzf mon-site_backup_20260101_030000.tar.gz | head -30

# Verifier l'integrite
gzip -t mon-site_backup_20260101_030000.tar.gz

# Extraire les metadonnees seulement
tar -xzf mon-site_backup_20260101_030000.tar.gz --wildcards "*/metadata.json" -O
```

## Liens

- <https://wordpress.org/documentation/article/wordpress-backups/>
- <https://developer.wordpress.org/cli/commands/db/>
