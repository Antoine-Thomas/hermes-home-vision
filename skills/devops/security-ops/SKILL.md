---
name: security-ops
description: "Audit securite, CVE et troubleshooting Wazuh (SIEM)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [security, audit, wazuh, siem]
    category: devops
    created: "2026-09-10"
    umbrella_of: [security-audit, wazuh-troubleshooting]
---

# Security Ops — Audit & Wazuh

Audit de securite systeme et depannage de la stack Wazuh. Les skills proteges `security-monitoring` et `supply-chain-hardening` restent independants.

## When to Use

- Auditer deps, ports ouverts, logs web, secrets exposes (`security-audit`)
- Wazuh ne repond plus / 403 dashboard / Docker Desktop eteint (`wazuh-troubleshooting`)
- Wazuh : audit de version, verdicts CVE et hygiene de configuration (`wazuh-security-audit`)
- Ne pas utiliser pour monitoring Telegram spam (`security-monitoring`, protege)

## Security Audit — resume

- Fichiers cibles, procedure de scan, cron hebdomadaire.
- Limites du scanner et pieges rencontres.
- **Un hit de scanner se qualifie AVANT tout verdict, et le verdict n'est pas binaire.** Ordre qui marche :
  1. caracteriser la valeur SANS jamais l'afficher (longueur exacte, alphabet : minuscules / majuscules /
     chiffres / tirets, prefixe de 8 caracteres au plus). Un `sk-*` majoritairement minuscule, a tirets et
     sans un seul chiffre ni majuscule n'est pas une cle mais un fragment de mot : le motif `sk-` nu mord
     dans `delegate-task-concurrency-...`. Corriger la CAUSE au niveau du scanner (frontiere de mot, ou
     exiger un chiffre / une majuscule), pas le fichier signale.
  2. compter les occurrences (fichier courant ET historique complet) et dire si la chaine est versionnee.
  3. etablir l'ATTEIGNABILITE distante avant de parler d'urgence : un blob ne s'interroge pas par
     `git branch -r --contains <blob>` (la commande veut un COMMIT) — passer par
     `git log --all --format=%H --find-object=<blob>`, puis `git branch -r --contains <commit>` et
     `git tag --contains <commit>`. Completer par la visibilite du depot
     (`gh repo view <owner>/<repo> --json visibility`) : elle change la SEVERITE, pas la methode.
  4. rendre le verdict nomme (placeholder / chaine reelle jamais poussee / chaine reelle deja sur le
     distant) et proposer la correction sans l'executer. Le sha tronque affiche par le scanner peut etre
     celui du BLOB du fichier et non celui de la valeur : le dire avant de conclure.
- **Un durcissement d'ACL ne se propage PAS au profil cree ensuite.** Le pass precedent avait ramene les
  `.env` existants a 3 ACE non heritees ; le `.env` du profil cree apres portait **4 ACE toutes
  heritees**, dont le groupe applicatif (`CodexSandboxUsers:(I)(RX)`) que ce pass avait justement retire
  des autres. Apres toute creation de profil, remesurer chaque fichier de secrets :
  `icacls "<profil>\.env"` doit rendre 3 ACE non heritees (`Systeme(F)`, `Administrateurs(F)`,
  `<utilisateur>(F)`) et 0 `(I)` ; correction = `icacls "<f>" /inheritance:r /grant:r ...`. Enumerer les
  fichiers par le DISQUE (`profiles/*/.env` plus la racine), jamais par le README ni par un document de
  version : ils ne citent que les profils qui existaient a leur redaction, et c'est exactement par la
  qu'un nouveau profil passe entre les mailles.
- **Compter les ACE sur la sortie BRUTE d'`icacls`, jamais par un filtre indirect.** Un comptage filtre
  (`Select-String` sur `(F)|(I)`) a rendu une ACE la ou il y en a trois : `icacls` imprime la premiere ACE
  sur la MEME ligne que le chemin, et l'indirection de quoting mange le motif. Une sonde qui rend un
  compte plus petit que la sortie brute est une sonde cassee, pas une ACL correcte — relire les lignes
  brutes avant de conclure.
- **Le durcissement d'un `.env` est une ACL de FICHIER : le dossier parent n'est pas couvert, et une
  operation d'ACL ulterieure sur l'arbre peut l'ANNULER.** Un `/reset` (ou un `/inheritance:e`) ramene
  l'heritage : le `.env` repasse a 4 ACE heritees et le groupe applicatif qu'on venait de retirer
  redevient lecteur du secret. Tout fichier NOUVEAU cree dans le dossier (`config.yaml`, sauvegarde de
  `.env`, copie de secours) re-herite la ACE du parent. Consequence : re-mesurer les `.env` APRES toute
  ecriture d'ACL portant sur les profils, et traiter le DOSSIER — pas seulement ses fichiers — quand
  c'est la re-heritage qu'on veut fermer.

Voir `references/security-audit.md` (214l, decoupee en refs par H2).

## Wazuh Troubleshooting — resume

- OMATHS Security Monitoring Stack, activation / cold start, Docker Desktop.
- Quand utiliser, core concepts, erreurs 403, indexation, agents.

Voir `references/wazuh-troubleshooting.md` (812l, decoupee en refs par H2).

## Wazuh — audit de version, CVE et configuration

Audit en LECTURE SEULE d'une stack deja en place (une installation absente se declare et on s'arrete) :
versions par composant, verdicts CVE, hygiene de configuration, verdicts OK / A CORRIGER / CRITIQUE
avec la commande de correction. Releves exacts, sondes et forme du rapport :
`references/wazuh-security-audit.md`.

- **Une stack Wazuh n'a pas UNE version.** Le manager, l'indexer, le dashboard et l'agent se mesurent a
  quatre endroits differents, et un agent peut etre en avance de plusieurs branches sur son manager.
  Rendre un verdict **par composant** : un « non affecte » global sur une stack a versions melangees
  peut etre faux pour l'un des quatre.
- **Un verdict CVE se calcule sur les DEUX bornes de la plage**, jamais sur « version installee < version
  corrigee » : une plage qui commence au-dessus de la version installee donne NON AFFECTE, meme quand la
  version est inferieure au correctif annonce. Prendre les plages aux CPE NVD, pas dans un resume.
- **Une entree listee peut ne pas concerner le produit du tout.** Lire la description avant de rendre un
  verdict : une CVE d'un autre composant (noyau, systeme) mise dans une liste Wazuh se declare NON
  APPLICABLE, et la version « corrigee » annoncee n'a alors aucun objet.
- **Les fiches OSV ne donnent pas de numero de version pour un projet hors gestionnaire de paquets** :
  `affected.ranges` y est de type GIT et les correctifs sont des hashes de commit. L'API des avis GitHub
  (`api.github.com/advisories/<GHSA>`, l'alias GHSA etant dans la fiche OSV) rend
  `first_patched_version` quand l'avis est publie — sinon croiser NVD.
- **Un port publie par Docker peut differer du port du conteneur.** Un `netstat` muet sur le port attendu
  ne prouve pas que le service est arrete : croiser `docker ps` (colonne Ports) avant de conclure « pas en
  ecoute », et dire sur quelle interface la publication ecoute reellement.
- **Ne jamais reproduire la valeur d'un secret dans le rapport** (`authd.pass`, cles, jetons) :
  caracteriser — present / absent / taille — et exprimer la correction comme une commande de rotation. Un
  `authd.pass` absent avec `use_password=yes` ne casse pas silencieusement : il produit une boucle de
  rejets dans le journal, qui se lit comme une tentative d'enrolement repetee.
- **Declarer NON MESURE ce qui n'a pas pu etre mesure.** Un `icacls` qui rend « Acces refuse » sur un
  fichier protege ne prouve pas que l'ACL est correcte, et un endpoint de login qui rend 404 ne prouve
  pas qu'un identifiant est inactif. Un rapport qui comble ces trous par inference est faux.

## Wazuh — appliquer les corrections (hors audit)

La suite de l'audit (rotation d'identifiants de l'indexer, sauvegarde et rollback d'une stack Docker,
hachage + `securityadmin.sh`, verification des identifiants, forme d'un `ROLLBACK.md`) est dans
`references/wazuh-securite-corrections.md`. Trois regles qui valent AVANT d'y toucher :

- **Determiner bind-mount contre volume nomme avant d'editer** :
  `docker inspect <conteneur> --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'`.
  Un fichier bind-monte depuis l'hote se corrige sur l'HOTE (l'entrypoint recopie la version hote au
  redemarrage, ce qui efface une correction faite dans le conteneur), et c'est le fichier HOTE qui entre
  dans la sauvegarde. `ossec.conf` et `internal_users.yml` sont dans ce cas ; `api.yaml` et
  `internal_options.conf` vivent dans des volumes nommes.
- **Le repertoire de securite de l'indexer est `/usr/share/wazuh-indexer/opensearch-security/`** dans ce
  deploiement. Un chemin `plugins/opensearch-security/securityconfig/` (celui de la documentation)
  n'existe pas : le signaler comme ECART avant d'agir, jamais le « reparer » en silence. Ne pas confondre
  la RBAC de l'INDEXER (`*.yml`) avec celle de l'API MANAGER
  (`/var/ossec/api/configuration/security/rbac.db`).
- **L'invocation de `securityadmin.sh` se prend dans l'image**, jamais inventee : lire
  `plugins/opensearch-security/tools/wazuh-passwords-tool.sh` (invocation reelle : application PAR
  FICHIER, `-f <f> -t internalusers -p 9200 -icl -nhnv -cacert/-cert/-key`), et exporter `JAVA_HOME`
  explicitement (`OPENSEARCH_JAVA_HOME=/usr/share/wazuh-indexer/jdk`) — il est vide par defaut dans le
  conteneur, et `hash.sh` comme `securityadmin.sh` en depend. Verifier lequel des deux repertoires de
  certs existe avant de le citer : un `-cacert` sur un chemin absent rend une erreur TLS qui se lit
  comme un mot de passe refuse.

- **Modifier un fichier hote d'une stack Wazuh Docker suppose d'abord de verifier qu'on peut y ECRIRE.** Un
  arbre detenu par `BUILTIN\Administrateurs` avec `BUILTIN\Utilisateurs:(RX)` est hors d'atteinte d'un shell
  non eleve (`net session` refuse = token filtre), et le bind-mount ne rattrape rien : le fichier y reste en
  0555 pour l'uid du conteneur ET pour root (Docker Desktop applique l'ACL hote). Sonder l'ecriture
  (`touch` dans le dossier, `>>` sur le fichier) AVANT de fabriquer un secret a usage unique — un mot de
  passe genere puis jamais applique est un secret mort, et l'affichage « une seule fois » est consomme pour
  rien. Les fichiers vivant dans un VOLUME nomme (`api.yaml` de l'API sous `/var/ossec/api/configuration`,
  `/var/ossec/etc`) restent, eux, modifiables par `docker cp`/`docker exec`.
- **Un fichier hote bind-monte doit etre modifie EN PLACE** : ecrire un nouveau fichier (editeur, `sed -i`,
  remplacement par renommage) change l'inode et le conteneur continue de voir l'ancien contenu. Ouvrir en
  `r+b` et ecrire a l'offset du hash (longueurs egales) preserve le montage — puis prouver par comparaison
  des SHA256 hote / conteneur, pas par le code de sortie de l'editeur.
- **`securityadmin.sh` rend `SUCC: ... created or updated` meme quand la valeur ne change pas** (re-application
  d'un fichier identique) : le succes de l'outil ne prouve rien. La preuve d'une rotation est le couple
  `401` sur l'ancien secret / `200` sur le nouveau, plus `/_plugins/_security/authinfo` pour les roles.
- **En 4.7.3 le bon endpoint est `/_plugins/_security/authinfo`** : `/_security/authinfo` rend
  `400 no handler found for uri`. Dans l'image `wazuh-indexer`, `OPENSEARCH_CONF_DIR` est vide et
  `/etc/wazuh-indexer` n'existe pas — les outils officiels fonctionnent avec
  `OPENSEARCH_CONF_DIR=/usr/share/wazuh-indexer` et `OPENSEARCH_JAVA_HOME=/usr/share/wazuh-indexer/jdk`,
  certs sous `/usr/share/wazuh-indexer/certs/`. `hash.sh -p "$P"` accepte le mot de passe par stdin
  (`printf '%s' "$P" | docker exec -i ... bash -c 'IFS= read -r P; ... hash.sh -p "$P"'`), ce qui evite de
  le laisser dans une ligne de commande.
- **Un compte d'administration est souvent aussi une identite de SERVICE.** Avant de faire tourner le mot de
  passe du user `admin` de l'indexer, chercher ses consommateurs : dans `wazuh-docker` le filebeat du
  manager s'y authentifie avec `username: 'admin'` code en dur dans `/etc/filebeat/filebeat.yml` (issu de
  `INDEXER_USERNAME`/`INDEXER_PASSWORD` du service `wazuh.manager`) — sa rotation SEULE coupe l'ingestion
  des alertes. Le dashboard, lui, utilise `kibanaserver`, et l'API Wazuh `wazuh-wui` : a verifier au cas par
  cas (`docker inspect` des env, plus le yaml effectif de chaque conteneur).

- **`docker restart` ne peut pas appliquer un changement de `docker-compose.yml` ni de `.env`.**
  L'environnement d'un conteneur est fige a sa creation : un redemarrage rejoue le cont-init avec les
  MEMES variables. Ici `/etc/cont-init.d/1-config-filebeat` regenere `/etc/filebeat/filebeat.yml` a
  chaque demarrage a partir de `$INDEXER_PASSWORD` — donc tourner le mot de passe de l'indexer sans
  recreer le manager laisse filebeat avec l'ancien secret (401, ingestion coupee). La seule forme qui
  applique le changement est `docker compose up -d <service>` (recree parce que la definition a change),
  avec `docker compose up -d --dry-run` avant pour voir ce qui serait recree.
  **Corollaire mesure : si seul un fichier MONTE a change (ossec.conf, api.yaml...), `up -d` est un NO-OP**
  — il repond `Container <nom> Running` et le service garde l'ancienne configuration (authd reste actif).
  `docker compose` ne compare que la DEFINITION du service. La forme qui rejoue l'init est
  `docker compose up -d --force-recreate <service>`. Ne jamais conclure a l'application d'un changement de
  fichier monte depuis un `up -d` muet : verifier l'EFFET dans le conteneur (valeur du fichier, etat du
  service) — `wazuh-control status` doit passer de `wazuh-authd is running` a `wazuh-authd not running`.
- **Un service peut consommer un compte que le compose declare en clair dans DEUX services.** Dans
  `wazuh-docker/single-node`, `INDEXER_USERNAME`/`INDEXER_PASSWORD` sont des valeurs EN DUR (aucune `${VAR}`
  dans le fichier, le `.env` ne sert donc a rien pour elles) et sont ecrites dans le service `wazuh.manager`
  (filebeat, consomme) ET dans `wazuh.dashboard` (inerte : son entrypoint utilise `DASHBOARD_USERNAME`, il
  s'authentifie aupres de l'indexer via le keystore avec `kibanaserver`). Avant une rotation, classer les
  occurrences par service et par consommateur REEL, pas par presence du nom de variable.
- **Sur cet hote, `curl` est celui de MSYS (`/mingw64/bin/curl`)** : un `-o /dev/null` echoue (exit 23) et,
  en processus d'arriere-plan promu, un `-o <chemin>` peut rendre 0 octet SANS message ni fichier. Une
  sonde qui ne rend NI code HTTP NI fichier n'est pas une mesure : rejouer la verification en avant-plan
  sous la forme sans fichier (`curl -sk -u ... -w '\n%{http_code}' <url> | tail -1`).
- **Ecrire dans un fichier structure (YAML de compose) se valide par le parseur de l'outil, pas par un diff.**
  Un remplacement d'octets qui perd l'indentation d'une ligne casse le fichier sans changer le nombre de
  lignes : enchainer l'ecriture avec `docker compose config -q` (muet = valide) AVANT l'action suivante, et
  conserver le `.bak` pour reparer depuis la ligne d'origine plutot que de reconstruire a la main.

- **En 4.7.3, `logs.format: json` dans `api.yaml` ecrit dans un AUTRE fichier.** `wazuh-apid.py` teste
  `'plain' in format` -> `<API_LOG_PATH>.log` et `'json' in format` -> `<API_LOG_PATH>.json` : passer en
  `json` **gele `api.log`** (qui conserve ses anciennes lignes en clair) et fait vivre les entrees dans
  `api.json`, structure `{"timestamp", "levelname", "data": {"type", "payload"}}`. Verifier le BON
  fichier avant de conclure a un echec, et chercher les consommateurs de `api.log` (harvester filebeat,
  `localfile` d'`ossec.conf`, rules/decoders) : la bascule les casse silencieusement. La valeur `both`
  (`plain,json` selon la doc) garde les deux sorties, donc le vecteur texte qu'on voulait fermer.
  Valider le `api.yaml` edite avec l'interpreteur de l'API avant de l'installer :
  `/var/ossec/framework/python/bin/python3 -c "import yaml; print(yaml.safe_load(open('<tmp>')))"` —
  le code fait `sys.exit(1)` si la configuration est invalide, donc un YAML casse prive la stack d'API.
- **L'API Wazuh n'utilise PAS les comptes de l'indexer.** Elle a ses propres utilisateurs (`wazuh`,
  `wazuh-wui`) dans `api/configuration/security/rbac.db` : `admin:<mot de passe indexer>` rend
  `401 Invalid credentials`, `wazuh-wui:<API_PASSWORD>` rend `200` + un JWT (~404 o). Toute sonde de
  l'API (port `55085` sur cet hote) se fait avec les identifiants du service `wazuh.manager` du compose.

- **Quand un composant est juge « en panne », nommer le point exact du code qui le condamne** : un rapport
  d'etape qui conclut « BLOCKED » sans dire QUI a pose l'etat laisse l'etape suivante reparer un service
  sain.
- **L'echeance d'un certificat se mesure a chaque audit, jamais de memoire.** Le certificat de l'API Wazuh
  est auto-signe, vit dans un VOLUME (donc absent de la copie du dossier compose) et porte `SAN:
  DNS:localhost` : exporter `server.crt` separement, comparer l'empreinte **X509** (pas le sha256 du
  fichier) entre le fichier servi, le certificat presente par le serveur et la copie archivee, puis calculer
  les jours restants. Detail, sondes et procedure de renouvellement : `references/certificat-api-wazuh.md`.

## Proteges — non inclus

- `security-monitoring` (protege, 96l, 2026-09-09) — silencing alertes Telegram
- `supply-chain-hardening` (protege, 347l, 2026-09-10) — hardening npm/pnpm

## References

- `references/security-audit.md` — audit complet
- `references/wazuh-troubleshooting.md` — Wazuh complet
- `references/wazuh-security-audit.md` — audit de version / CVE / configuration d'une stack Wazuh
- `references/certificat-api-wazuh.md` — rappel d'echeance et renouvellement du certificat de l'API Wazuh
  (mesure de reference 2027-07-19, sondes, pieges de mesure)
- `references/wazuh-securite-corrections.md` — appliquer les corrections : cartographie bind-mount /
  volume nomme, sauvegarde et rollback d'une stack Docker, hash + `securityadmin.sh`, verification d'un
  changement d'identifiants, contenu attendu d'un `ROLLBACK.md`
