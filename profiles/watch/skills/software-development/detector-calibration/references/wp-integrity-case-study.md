# Cas reel : calibrage du module wp-integrity

Contexte : ajout d'un module de verification d'integrite du core WordPress a un
scanner de securite local (checksums officiels `api.wordpress.org`, comparaison
md5 fichier par fichier). Perimetre : 5 sites WordPress locaux
(Local by Flywheel), versions 7.0 a 7.0.3, locales `fr_FR` et `en_US`.

## Resultat brut du premier run — a ne pas croire

```
CRITIQUE 0 | ELEVE 5 | MOYEN 0 | FAIBLE 0
- [ELEVE] searching-murphy : 7 fichier(s) inconnu(s) dans le core
- [ELEVE] sm               : 9 fichier(s) inconnu(s) dans le core
- [ELEVE] the-one          : 1 fichier(s) inconnu(s) dans le core
- [ELEVE] oldstyle         : 1 fichier(s) inconnu(s) dans le core
- [ELEVE] reold            : 2 fichier(s) inconnu(s) dans le core
```

20 fichiers signales, 5 alertes ELEVE. **Zero etait une vraie compromission.**

L'inspection de la preuve de chaque finding a montre le motif decisif :
aucun de ces fichiers n'etait dans `wp-admin/` ou `wp-includes/` — tous etaient
a la racine. Et `local-xdebuginfo.php` apparaissait sur **5 sites sur 5**.

```
.htaccess.bk, AI-SKILLS.md, llms.txt, local-xdebuginfo.php,
superpwa-manifest-nginx.json, superpwa-sw-nginx.js, sw.js
manifest.json, pre-flight-check.php, pre-production-audit.php,
seo-path-validator.php, setup-customizer.php, verify-seo-files.php
wp-config.php.backup
```

## Les trois regles appliquees

1. **Artefact du generateur** — `local-xdebuginfo.php` est ecrit par
   Local by Flywheel a la racine de chaque site. Filtre par une liste nommee
   (`WP_DEV_ARTIFACTS`), avec le motif de la regle en commentaire.
   Sans elle : 1 faux positif par site, a chaque scan, pour toujours.

2. **Capacite de nuire plutot qu'inconnu** — `sw.js`, `manifest.json`,
   `superpwa-*`, `llms.txt`, `AI-SKILLS.md` sont deposes par des plugins et sont
   **inertes** : le serveur ne les execute pas. Ignores via une liste
   d'extensions reellement executables (`WP_EXEC_EXT`), et **comptes** dans le
   rapport (`racine_fichiers_inertes_ignores`) pour rester auditable.

3. **Zone utilisateur exclue du decompte, pas du controle** — les fichiers
   `wp-content/` figurent dans les checksums officiels (themes et plugins par
   defaut) mais leur suppression par l'utilisateur est legitime. Le decompte
   « manquant » exclut donc `wp-content/`, sans desactiver le reste du controle.
   Preuve que la regle agit : sur le controle positif, 3503 manquants remontes
   pour 3950 checksums au total — l'ecart correspond exactement a la zone exclue.

## Resultat apres calibrage — tout est reel

```
ELEVE 3 | MOYEN 1 | INFO 2
[ELEVE]  searching-murphy : .htaccess.bk servi en clair
[ELEVE]  sm               : .htaccess.bk servi en clair
[ELEVE]  reold            : wp-config.php.backup (identifiants BDD lisibles)
[MOYEN]  sm               : 5 scripts PHP non-core a la racine (a confirmer)
[INFO]   the-one, oldstyle : core conforme
```

Les 5 scripts PHP de `sm` sont vraisemblablement ceux de l'utilisateur. Ils sont
**degrades en MOYEN « a confirmer un par un »**, jamais whitelistes par nom : un
`setup-customizer.php` legitime aujourd'hui peut etre un fichier hostile portant
le meme nom demain.

## Deux details techniques qui ont compte

- **`wp-config.php` et `.htaccess` ne sont pas dans l'API de checksums** (leur
  contenu est propre a chaque installation). Impossible de les comparer a un md5.
  Substitut retenu : rechercher une signature d'execution de code dans leur
  contenu (`eval`, `base64_decode`, `gzinflate`, `auto_prepend_file`,
  `AddType application/x-httpd-php .jpg`).
- **Une copie de fichier de configuration est un vrai risque**, pas un artefact :
  `.bk`, `.bak`, `.backup`, `.old` ne sont pas interpretes par PHP, donc servis
  en clair par le serveur. Detectees par prefixe de stem (`wp-config`,
  `.htaccess`, `.htpasswd`, `.user.ini`) en excluant les noms exacts legitimes.

## Cout mesure

| Mesure | Valeur |
|---|---|
| 5 sites, 19 874 fichiers haches | ~12 s |
| Requetes reseau | 1 par couple (version, locale), mises en cache |
| Import `urllib` au demarrage | 76 ms — rendu paresseux pour ne pas penaliser les passes ciblees |

## Lecon transferable

Le premier run d'un detecteur mesure surtout **l'environnement**, pas la cible.
Un fichier present sur 5 cibles sur 5 est une propriete de la plateforme de dev ;
c'est le premier motif a chercher avant d'ecrire la moindre regle de filtre.
