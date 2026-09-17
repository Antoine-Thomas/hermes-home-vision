<!-- Source: security-audit/SKILL.md -->
---
name: security-audit
description: "Auditer deps, ports, logs web et secrets exposes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [securite, audit, npm, vulnerabilites, ports, logs, wordpress, telegram, cron]
    related_skills: [wordpress-security, requesting-code-review]
prerequisites:
  commands: [python, npm]
---

# Audit de securite a la demande

Lance un audit local en 6 modules, produit un rapport priorise, et le pousse
sur Telegram. Concu pour tourner en 10 secondes et etre relance chaque semaine
sans generer de bruit.

Modules : `deps` (npm/pip), `perms` (ACL Windows / bits POSIX), `ports`
(ecoutes publiques), `logs` (motifs d'attaque web), `secrets` (fichiers
sensibles exposes), `wp-integrity` (checksums du core WordPress).

## When to Use — quand l'utiliser

- L'utilisateur demande un audit / scan de securite, "verifie mes vulnerabilites",
  "est-ce que mes sites sont exposes", "j'ai des dependances a jour ?"
- L'utilisateur demande si un site WordPress a ete modifie / pirate / infecte,
  "verifie l'integrite de mon WordPress" -> `--modules wp-integrity`
- Avant une mise en production ou une livraison client
- Apres l'installation d'un plugin/theme/paquet d'origine incertaine
- Declenchement automatique hebdomadaire (voir section Cron)

## Fichiers

| Chemin | Role |
|---|---|
| `~/AppData/Local/hermes/data/hermes-optim/bin/security_scan.py` | le scanner (stdlib uniquement) |
| `~/AppData/Local/hermes/data/hermes-optim/targets.json` | perimetre : projets, racines web, listes blanches |
| `~/AppData/Local/hermes/data/hermes-optim/reports/security/` | rapports `audit_<stamp>.json` + `.md` |
| `~/AppData/Local/hermes/scripts/security_weekly.py` | wrapper appele par le cron |

Sur Linux/macOS remplacer `~/AppData/Local/hermes` par `~/.hermes`.

## Procedure

### 1. Lancer le scan

```bash
cd ~/AppData/Local/hermes/data/hermes-optim
./.venv/Scripts/python.exe bin/security_scan.py --config targets.json
```

`python bin/security_scan.py` marche aussi : le script n'utilise que la stdlib.
Le venv n'est requis que pour les autres outils du dossier.

Modules a la carte :

```bash
# uniquement les dependances et les ports
python bin/security_scan.py --config targets.json --modules deps,ports

# integrite du core WordPress seule (SEUL module qui sort sur le reseau)
python bin/security_scan.py --config targets.json --modules wp-integrity

# perimetre ad hoc sans toucher au fichier de config
python bin/security_scan.py --projects C:/dev/monapp --webroots "C:/inetpub/wwwroot" --out ./rap
```

Codes de sortie : `0` = rien de grave, `1` = findings ELEVE, `2` = findings CRITIQUE.

### 2. Lire le rapport et trier

Le stdout est une synthese courte. Le vrai contenu est dans le `.md`.
Toujours ouvrir le `.md` avec `read_file` avant de commenter, et **lire la
section "Limites du scan"** : elle dit ce qui n'a PAS pu etre verifie.

Regles de triage a appliquer :

- **CRITIQUE** = action aujourd'hui (secret expose, webshell, dump SQL servi par le web).
- **ELEVE** = action cette semaine.
- **MOYEN** = a planifier. Beaucoup de MOYEN "ports" sont normaux en dev.
- **INFO** = documentation, aucune action.

Ne jamais presenter un finding comme une compromission confirmee. Le scanner
detecte des *signatures*, pas des intrusions. Formuler : "signature de X, a verifier".

### 3. Envoyer sur Telegram

```bash
python bin/security_scan.py --config targets.json | hermes send --to telegram --subject "Audit securite"
```

Ou en deux temps si on veut le rapport complet :

```bash
hermes send --to telegram --file reports/security/audit_<stamp>.md --subject "Audit securite detaille"
```

`hermes send` reutilise les identifiants du gateway, aucun agent n'est demarre.
Verifier les cibles disponibles avec `hermes send --list`.

### 4. Corriger

Chaque finding porte un champ `remediation` avec la commande exacte. Pour npm,
toujours proposer `npm audit fix` d'abord, et prevenir que `--force` peut casser
le build (montees de version majeures). Ne jamais lancer `--force` sans accord.

## Cron hebdomadaire

Job deja cree (le verifier avec `hermes cron list`). Pour le recreer :

```
cronjob(action='create',
        name='Audit securite hebdomadaire',
        schedule='0 8 * * 1',
        script='security_weekly.py',
        deliver='telegram',
        prompt="Le script d'audit vient de tourner, sa sortie est ci-dessus. "
               "Redige un point securite court en francais : ce qui a change depuis "
               "la semaine derniere, les 3 actions prioritaires, et dis explicitement "
               "si rien de nouveau. Ne repete pas la liste brute.",
        continuity=True,
        enabled_toolsets=['file', 'terminal'])
```

Deux variantes selon le besoin :

- **Avec agent** (ci-dessus, `continuity=True`) : l'agent compare a la semaine
  precedente et priorise. Coute quelques milliers de tokens par semaine.
- **Zero token** : `no_agent=True` + `script='security_weekly.py'`, la sortie du
  script est livree verbatim. Ajouter `--quiet-if-clean` dans le wrapper pour
  ne rien envoyer quand tout va bien (motif watchdog).

`deliver='telegram'` est obligatoire pour etre notifie : un job cree depuis une
session CLI avec `deliver='origin'` n'a **aucun** canal de livraison.

## Ce que le scanner ne fait pas

A dire a l'utilisateur, sinon l'audit donne une fausse assurance :

- Aucune analyse de code (pas de detection de faille dans *ton* PHP/JS) —
  utiliser le skill `code-review` pour ca.
- Aucun scan reseau externe : il regarde ce qui ecoute sur la machine, pas ce
  qui est joignable depuis Internet.
- Aucune verification d'integrite des coeurs WordPress (checksums) ni des
  plugins — utiliser le skill `wordpress-security`.
- Pas de detection d'intrusion : les logs d'ACCES sont necessaires, et Local by
  Flywheel n'en produit pas par defaut (le scan le signale dans "Limites").
- Les dependances Python ne sont auditees que si `pip-audit` est installe
  (`uv tool install pip-audit`).

## Pieges rencontres

1. **Ne jamais appliquer les motifs d'attaque a la ligne entiere d'un
   `php/error.log`.** Un chemin Composer `vendor/composer/../../src` declenche
   la regle "traversee de repertoire" et une stack trace citant `wp-config.php`
   declenche "acces fichier sensible" : 650 faux positifs constates. Le scanner
   n'analyse desormais que la cible HTTP extraite (`REQUEST_RE`) pour les motifs
   web, et un jeu de motifs distinct (`ERROR_LOG_PATTERNS`) pour les logs d'erreur.
2. **Ports 49152-65535 tenus par `lsass.exe`/`svchost.exe`/`services.exe`** :
   c'est le RPC dynamique Windows, normal. Filtre par `BENIGN_SYSTEM_PROCS`.
   Steam, Hyper-V, Logitech => `BENIGN_APP_PROCS`, remontes en `info`.
3. **`wp-config.php` a la racine d'un site WordPress est normal**, ce n'est pas
   un finding. Seules les variantes de sauvegarde (`.bak`, `.save`, `.txt`) sont
   critiques.
4. **Regrouper les findings de masse.** Un dossier `backup-migration/tmp/db_tables`
   contient 23 dumps : c'est UN finding, pas 23. Le titre doit inclure le nom de
   la racine scannee, sinon 3 sites produisent 3 lignes identiques.
5. **Les regex ne doivent pas matcher un timestamp comme une IP.** `01:52:42`
   ressemble a de l'IPv6 : utiliser un `IPV4_RE` strict + `client:` pour nginx.
6. **`icacls` est lent sur une arborescence profonde** : le scan echantillonne
   les dossiers de premier niveau sous Windows au lieu de tout parcourir.
7. **`--modules` en ligne de commande est prioritaire sur `targets.json`.**
   La cle `modules` du fichier de config ne s'applique que si `--modules` est
   absent. Sans cette precedence, `audit --modules ports` relancait les 5
   modules et prenait 10 s au lieu de 0,3 s.
8. **`wp-integrity` : ne jamais traiter "absent des checksums" comme
   "backdoor".** Sur les 5 sites de la machine, la version naive remontait 20
   alertes ELEVE dont 0 reelle. Trois regles indispensables :
   - `local-xdebuginfo.php` est genere par Local by Flywheel a la racine de
     CHAQUE site (liste `WP_DEV_ARTIFACTS`) ;
   - un fichier racine **inerte** (`.md`, `.txt`, `.js`, `.json` : `sw.js`,
     `manifest.json`, `superpwa-*`, `llms.txt`) est deposé par des plugins et
     ne peut pas s'executer : il est ignore (`WP_EXEC_EXT` filtre l'inverse) ;
   - les fichiers `wp-content/` figurent dans les checksums (themes et plugins
     par defaut) mais leur suppression est legitime : `manquant` n'est compte
     que hors `wp-content/`.
   Ce qui reste ELEVE est reel : fichier inconnu dans `wp-admin/`/`wp-includes/`,
   md5 de core different, copie de configuration servie (`wp-config.php.backup`,
   `.htaccess.bk`), code injecte dans `wp-config.php`/`.htaccess`.
9. **`wp-config.php` et `.htaccess` ne sont PAS dans l'API de checksums** (leur
   contenu est propre a chaque installation). Impossible de les comparer a un
   md5 : le module cherche a la place une signature d'execution de code
   (`eval`, `base64_decode`, `auto_prepend_file`, `AddType ... .jpg`).
10. **`tasklist` est le vrai cout du module `ports`** (0,1 a 0,8 s selon la
    charge), pas le script. Il n'est appele que s'il reste un port a qualifier
    apres la liste blanche : ne pas le rendre inconditionnel a nouveau.

## Verification

Apres modification du scanner, verifier qu'il n'a pas regresse :

```bash
python bin/security_scan.py --config targets.json --modules logs
# attendu : aucun finding "Traversee de repertoire" si les logs sont des error.log
python bin/security_scan.py --config targets.json --modules ports
# attendu : aucun finding pour les ports 49664+ de svchost/lsass
python bin/security_scan.py --config targets.json --modules wp-integrity
# attendu : 0 "fichier inconnu dans wp-admin/ ou wp-includes/" sur un site sain,
#           et aucune alerte pour local-xdebuginfo.php
```
