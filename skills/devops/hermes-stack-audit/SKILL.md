---
name: hermes-stack-audit
description: "Use when auditing the Hermes stack end to end."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [audit, hermes, stack, wazuh, omniroute, gateway, securite, lecture-seule]
    related_skills: [security-monitoring, windows-ops, hermes-operations]
---

# Audit complet de la stack Hermes

Revue de plusieurs sous-systemes d'un coup (primitives de decision locales, routeur LLM,
surveillance continue, gateway, securite Windows) avec un rapport par section et une liste
d'actions priorisees. Une demande sur UN seul sous-systeme ne releve pas de cette skill :
prendre la skill dediee (`security-monitoring`, `omniroute-*`, `windows-ops`).

## When to Use

- « revue complete », « audit de la stack », « etat des lieux + optimisations » portant sur
  plusieurs sous-systemes a la fois.
- Verification periodique de sante : gateway, routeur LLM, surveillance, securite Windows.
- Controle d'espace disque et inventaire des gros fichiers, quand la demande melange plusieurs
  sous-systemes (pour l'espace seul : `disk-space-reclamation`).

## Regles durables (valables a chaque audit)

- **Lecture seule d'abord.** Aucune modification, aucune suppression, aucun redemarrage tant que
  le rapport n'est pas rendu et valide. Les corrections viennent apres, une par une.
- **Toute ecriture est precedee du diff exact** montre a l'utilisateur (fichier de config,
  `icacls`, patch de skill). Ne jamais appliquer une correction « evidente » en cours d'audit.
- **Aucune suppression sans feu vert explicite**, meme reversible, meme petite ; toute
  suppression > 1 Go est une question a poser, jamais une action.
- **Ne rien redemarrer** : ni Windows, ni le gateway, ni les conteneurs, ni le routeur. Un
  service arrete est un CONSTAT a rapporter, pas un probleme a reparer sur-le-champ.
- **Zones interdites** : `pelerinage alternate/`, `token.txt.pending_review`, `pending/`,
  `memories/`. L'utilisateur traite ces dossiers lui-meme.
- **Mesure, ne deduis pas.** Chaque chiffre du rapport vient d'une commande reellement executee.
  Tout ecart avec une premisse de la demande (une valeur « de reference », un service suppose
  up, un modele suppose en pause, un conteneur suppose lance) est signale dans le rapport et
  jamais corrige en silence.
- **Sortie attendue** : un verdict par section (conforme / non conforme, avec les chiffres),
  puis une liste d'actions triee `[critique]` / `[important]` / `[optimisation]`, toutes NON
  executees, chacune avec la commande ou le diff qu'elle impliquerait.

## Procedure

1. **Reconnaissance en lot.** Regrouper dans un meme tour les lectures independantes (contenu
   du skill concerne, etat des fichiers, etat des services). Une tour par sous-systeme gaspille
   la session ; les appels independants doivent partir ensemble.
2. **Un sous-systeme = un lot de sondes**, dans l'ordre du rapport demande. Voir
   `references/sondes-par-sous-systeme.md` pour les commandes et les emplacements d'etat
   verifies (Laya/JEV, OmniRoute, Wazuh, gateway, Windows).
3. **Tester la capacite, pas la configuration.** Pour chaque capacite auditee (primitive de
   decision, routeur, chaine d'alertes), lancer le test reel : self-test du modele, appel direct
   sur le combo, requete SQL sur la base d'usage. Lire une config ne prouve rien.
4. **Se mefier des indicateurs indirects** avant de declarer « arrete / en pause / epuise » :
   solde de credits d'un fournisseur, drapeau `is_active` en base, presence d'une tache
   planifiee, presence d'un `enabled: true`. Le seul verdict fiable est un appel reel qui
   repond.
5. **Chiffrer l'espace** : espace libre d'abord, puis gros fichiers (> 50 Mo) par sous-systeme,
   puis distinguer ce qui est supprimable (fichiers, sauvegardes, logs) de ce qui exige un
   compactage (VHDX Docker/WSL).
6. **Rendre le rapport et s'arreter la.** Lister les actions, demander par laquelle commencer.

## Phase 2 — appliquer les corrections validees (apres le feu vert)

Le rapport valide, les corrections s'appliquent une par une, chacune avec sa preuve.

1. **Backup de l'objet avant toute ecriture**, nom horodate a cote du fichier
   (`cp <f> <f>.bak_$(date +%Y%m%d_%H%M%S)`). Citer dans le rapport le chemin du backup ET la commande
   de retour REELLEMENT utilisable.
   Pour une ACL il n'y a pas de fichier a copier : le dump
   `icacls <f> > cache/scratch/<f>_acl_backup_<horodatage>.txt` est un CONSTAT (format d'affichage, non
   reimportable), pas un artefact de restauration. La commande de retour se construit autrement — `/reset`
   (recale la DACL sur l'heritage du parent intact) ou la paire `icacls /save` + `/restore` — et elle ne
   fonctionne que la ou l'appelant peut ecrire la DACL : relever donc AUSSI le PROPRIETAIRE de chaque objet
   (`Get-Acl -LiteralPath <objet>` -> `Owner`) et compter les objets accessibles AVANT
   (`scripts/verifier-acces-dacl.py`, skill `devops/hermes-install-troubleshooting`). Sans ces deux
   mesures, une propagation qui vide des DACL sur des objets dont l'utilisateur n'est pas proprietaire
   n'est ni detectable ni reparable sans elevation.
   Voir aussi la PROPAGATION des ACE heritables sur tout un sous-arbre : `devops/hermes-install-troubleshooting/SKILL.md`, section ACL (source unique).
2. **Construire le diff SUR UNE COPIE, jamais sur la cible.** Ecrire la version proposee dans
   `cache/scratch/`, puis `diff -u <original> <copie>` ; l'original reste intact tant que le diff
   n'est pas valide. Avant d'annoncer le diff, **compter l'occurrence du bloc a remplacer** et exiger
   exactement 1 : 0 ou 2+ doit arreter la proposition, jamais etre « rattrape » au feeling.
3. **Faire le remplacement sur les OCTETS**, pas via `read_text`/`write_text` : les fins de ligne
   universelles reecrivent tout le fichier en LF et le diff passe de 1 ligne a 108 — illisible et
   suspect. `read_bytes()`/`write_bytes()`, puis verifier que le `diff` d'apres ecriture ne montre
   QUE les lignes voulues (et que le CRLF d'origine est conserve).
4. **Prouver par mesure, pas par code de sortie.** Un `docker compose up` a 0 pendant qu'un conteneur
   reste `Created` ne prouve rien. Chaque correction a sa lecture : la chaine exacte dans `docker ps`,
   l'adresse LOCALE en `LISTENING`, un code HTTP avec `%{time_total}`, la taille et le prefixe d'un
   jeton (jamais sa valeur), l'etat relu d'un service, la taille du fichier reecrit.
5. **`netstat` : ne pas tester `0.0.0.0` a l'aveugle.** Les lignes `LISTENING` portent `0.0.0.0:0`
   comme adresse DISTANTE : un `grep -c 0.0.0.0` compte toutes les lignes et fait croire a un bind
   public. Filtrer l'etat puis la colonne locale (`awk '$4=="LISTENING"{print $2}'`).
6. **Une correction par couche, puis re-verifier la couche du dessous.** Un port publie n'est pas un
   client reconnecte : enchainer host up -> port en LISTENING -> connexion etablie -> client `Active`
   -> flux qui grossit, et ne declarer resolu que la couche reellement observee.
7. **Si une etape validee degrade l'etat, le dire au present.** Un correctif qui echoue (conteneur
   recree non demarre, service arrete, ACL posee sur le mauvais objet) doit apparaitre comme
   regression assumee : ce qui a change, l'impact reel, la commande de retour — jamais presente comme
   neutre, jamais enterre dans un paragraphe de succes.

## Pieges (ils ont coute du temps)

- **Jamais de `curl` sur un chemin non verifie d'un service local.** Un dashboard Next.js
  (OmniRoute) renvoie, sur un chemin inconnu, la page 404 COMPLETE : des centaines de Ko de HTML
  dans le contexte en un seul appel, qui chassent le reste du travail de la fenetre. Prober par
  `curl -s -o /dev/null -w "%{http_code} %{time_total}"`, jamais par le corps, tant que
  l'endpoint n'est pas prouve.
- **Le terminal est bash/MSYS sur cet hote, pas PowerShell.** Les cmdlets doivent passer par
  `powershell -NoProfile -Command "..."` ; `Get-Service`/`Get-LocalUser`/`Get-MpComputerStatus`
  tapes directement echouent. Dans une chaine a quotes simples, `$_` reste litteral.
- **Les logs applicatifs JSON ne se filtrent pas par niveau texte.** Chercher `'"level":"warn"'`
  ou `'"level":"error"'` : un `grep -E "\[error\]"` renvoie 0 et fait croire a zero erreur.
- **Une base SQLite d'un service en cours d'execution se lit en `mode=ro`** :
  `sqlite3.connect("file:<chemin>?mode=ro", uri=True)`. Jamais en ecriture.
- **Un hebergement arrete transforme une chaine de surveillance en mensonge silencieux.**
  Demon Docker coupe ⇒ conteneurs down ; le moniteur qui lit les alertes par `docker exec`
  renvoie « 0 alerte » sans lever d'erreur. Un compteur vide n'est pas une preuve de calme :
  verifier l'hebergement (`docker ps`, `netstat`) AVANT de conclure.
- **Un chemin absolu dans une config se verifie sur le disque** (`search_files` en mode `files`,
  ou un test d'existence direct). Un venv renomme ou deplace rend le
  chemin faux sans que la tache echoue visiblement (repli silencieux sur un binaire du PATH) :
  chercher les chemins d'executables dans les config JSON des sous-systemes et les tester un par un.
- **Ne pas lire une statistique de combo comme une statistique de fournisseur.** Dans la base
  d'usage d'OmniRoute, le champ provider porte le premier segment du modele DEMANDE : quand un
  combo echoue, la ligne porte le nom du combo, d'ou des « 100 % d'erreur » qui designent une
  cible visee. Voir `references/sondes-par-sous-systeme.md`.
- **Les sondes de sante polluent les moyennes d'usage** (`connection-test` des boutons « Test
  connection ») : les exclure avant tout classement par modele.
- **Distinguer le bruit du signal dans les logs d'un gateway** : timeouts de classements distants,
  synchronisations de stats, `REDIS_URL is not set` et flots d'auth « invalid bearer » sont
  permanents. Les signaux reels : cle invalide, binaire absent (`spawn ... ENOENT`), quota epuise
  (`402`), modele introuvable (`404`), pool vide, `429` subis.
- **Ne pas regler un seuil sur un flux mort.** Monter `min_level`, reduire les timeouts ou elargir
  les fenetres d'un moniteur n'a aucun sens tant que la source en amont est coupee : le constat
  est « chaine cassee », pas « seuil mal regle ».
- **Ne pas conclure a l'activite d'un plugin/skill sur sa presence dans `config.yaml`** : un
  plugin active peut etre en `mode: off`, une tache planifiee peut etre `Disabled`, une skill
  peut n'avoir aucun log d'usage. Chercher la trace d'execution (fichier de log, `last_run`,
  compteur d'usage) avant d'ecrire « actif ».

- **Une premisse chiffree de la demande peut etre fausse : la remesurer dans l'unite de la limite.**
  Un « 2343 o / limite 2200 » annonce un depassement qui peut n'exister qu'en OCTETS alors que
  l'unite de la limite est le CARACTERE : le fichier peut etre conforme. Remesurer avant de reprendre
  le chiffre, et rapporter l'ecart avec la premisse. Meme regle quand la demande suppose la meme
  erreur dans « 2 fichiers » et que `search_files` n'en trouve qu'un : corriger le seul porteur reel, et
  dire explicitement que le second a ete enrichi (re-verification datee) plutot que « corrige » — ne
  pas fabriquer une seconde modification pour honorer la premisse.
- **Un fichier de config peut vivre dans un clone d'un depot AMONT, pas dans le depot du projet.**
  Avant d'annoncer un commit, verifier `git ls-files`, `git check-ignore -v` (le fichier peut etre
  gitignore, donc jamais sauvegarde) et `git remote -v` : un compose d'infrastructure vit souvent
  dans un clone tiers en HEAD detache, avec des modifications locales preexistantes. Dans ce cas on
  ne committe rien et on le signale — et on previent que le prochain `git checkout`/`pull` du clone
  effacera la correction.

- **Une ecriture d'ACL de masse ne se verifie pas par le bilan d'`icacls`.** Un `/T` dont le grant porte
  des drapeaux d'heritage (`(OI)(CI)`) les applique aussi aux FICHIERS, ou ils n'ont pas de sens : vue
  sur ce parc, DACL videe sur la majorite d'un arbre de 3188 objets, bilan annonce « echec du traitement
  de 0 fichiers » — et les objets dont l'utilisateur n'est pas proprietaire ne sont plus reparables que
  par un shell eleve (`takeown` + `icacls /reset`). Controle par l'ACCES avant/apres, jamais par le
  bilan : `scripts/verifier-acces-dacl.py` dans `devops/hermes-install-troubleshooting`.

## Files

- `references/sondes-par-sous-systeme.md` — emplacements d'etat et commandes de sonde verifies,
  sous-systeme par sous-systeme (decisions locales, OmniRoute, Wazuh, gateway, Windows).
