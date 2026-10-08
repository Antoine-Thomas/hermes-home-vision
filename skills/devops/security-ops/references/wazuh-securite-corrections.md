# Wazuh Docker — appliquer des corrections de securite (chemins reels, sauvegarde, rollback)

Suite de `wazuh-security-audit.md` : la phase de CORRECTION apres l'audit. Toutes les commandes
ci-dessous ont ete verifiees sur une stack `wazuh-docker` 4.7.3 single-node (Windows + Docker Desktop).

## 1. Cartographier AVANT de toucher : bind-mount ou volume nomme ?

C'est la mesure qui decide de tout le reste — ou vit la source de verite, ce qu'il faut sauvegarder, et
si une correction faite dans le conteneur survivra a un redemarrage.

```bash
docker inspect <conteneur> --format '{{range .Mounts}}{{.Type}} {{.Name}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

- **BIND-MOUNT** : la source de verite est un fichier de l'HOTE. Editer dans le conteneur ne survit pas
  (l'entrypoint recopie la version hote). Corriger l'hote, en gardant une copie `.bak` a cote.
- **VOLUME NOMME** : pas de copie hote. Copier/replacer par `docker cp` ou `docker exec`, et la
  sauvegarde passe par l'archive du volume.

Cartographie mesuree (compose `wazuh-docker/single-node`) :

| Fichier | Nature | Chemin de verite |
|---|---|---|
| `internal_users.yml` | **bind-mount** | `<compose>/single-node/config/wazuh_indexer/internal_users.yml` |
| `roles.yml`, `roles_mapping.yml` | fichier d'image | `/usr/share/wazuh-indexer/opensearch-security/` |
| `ossec.conf` | **bind-mount** | `<compose>/single-node/config/wazuh_cluster/wazuh_manager.conf` -> `/wazuh-config-mount/etc/ossec.conf` |
| `api.yaml` | volume nomme | `wazuh_api_configuration` -> `/var/ossec/api/configuration/api.yaml` |
| `internal_options.conf` | volume nomme | `wazuh_etc` -> `/var/ossec/etc/internal_options.conf` |
| certs API | volume nomme | `/var/ossec/api/configuration/ssl/server.{crt,key}` |
| RBAC de l'API **manager** | volume nomme | `/var/ossec/api/configuration/security/rbac.db` |

**Le chemin documente `plugins/opensearch-security/securityconfig/` n'existe PAS dans ce deploiement** :
le repertoire reel des configs de securite est `/usr/share/wazuh-indexer/opensearch-security/`. Une
consigne qui cite `securityconfig/` se signale comme ECART (premisse fausse) avant d'agir, jamais ne se
« repare » en silence. Ne pas confondre non plus la RBAC de l'INDEXER (`opensearch-security/*.yml`) avec
la RBAC de l'API MANAGER (`/var/ossec/api/configuration/security/rbac.db`) : deux bases distinctes.

## 2. Sauvegarder la stack avant toute correction

Destination : un dossier de mission DURABLE (`C:\Users\<user>\<mission>_<AAAAMMJJ>\`), jamais
`cache/scratch` (elague apres 24 h, alors qu'une mission gatee attend un GO des jours).

1. **Manifeste des montages** (section 1) pour lister ce qu'il faut sauver.
2. **Volumes nommes, un par un** — mesurer d'abord leur poids (`docker system df -v`) :

```bash
for v in $(docker volume ls -q | grep -a '^<prefixe>_'); do
  docker run --rm -v "$v":/data:ro -v "<DEST>/volumes":/backup \
     busybox tar czf "/backup/$v.tar.gz" -C /data .
done
```

   Puis relire chaque archive (`tar tzf <f> | wc -l`) : une archive qu'on n'a pas relue n'est pas une
   sauvegarde. Un `tar: ./sockets/... socket ignored` sur `wazuh_queue` est normal (sockets Unix).
3. **Fichiers de config** : `docker cp <conteneur>:<chemin> <DEST>/` pour les volumes nommes, `cp` du
   fichier hote pour les bind-mounts.
4. **Prouver l'identite des copies** — triple verification : SHA256 du fichier DANS le conteneur ==
   SHA256 de la copie exportee == SHA256 du bind-mount hote. C'est cette egalite (pas l'`exit 0` de
   `docker cp`) qui rend la restauration verifiable.
5. **Manifeste** : `MANIFEST_SHA256.txt` (configs, archives, sources hotes, sources vivantes,
   identifiants d'images) + un `ROLLBACK.md` executoire par cible.

Creer un dossier de secours vide ne suffit pas a prouver une sauvegarde « complete » quand un volume
fait 48 Mo et que `du` en annonce 11 Mo compresses : dire le couple (taille brute mesuree, taille de
l'archive) et le nombre d'entrees.

### La sauvegarde d'une stack contient des secrets en clair

`docker-compose.yml`, les `.env` et `api.yaml` portent `INDEXER_PASSWORD`, `API_PASSWORD`, les
identifiants par defaut. Le dossier de sauvegarde se declare SENSIBLE dans le rapport et ne se deplace
pas sur un support partage ; les valeurs ne se reproduisent jamais (seulement « present »).

### Copie « a chaud » d'un volume de donnees

Un volume de donnees (index Lucene) archive pendant que le service tourne n'est pas un instantane
coherent a 100 %. Utilisable pour revenir sur de la CONFIGURATION, a declarer tel quel si la correction
prevue ne touche pas ces donnees. Un instantane coherent demande un arret (`docker compose stop`, pas
`docker kill`) — a decider, pas a supposer.

### Preuve de non-modification (lecture seule)

```bash
docker exec <conteneur> sh -c 'find /var/ossec/etc /var/ossec/api/configuration -newermt "<debut>" -type f'
```

Aucune ligne = aucune ecriture depuis l'heure du debut. A joindre au rapport a cote de
`MODIFICATIONS: 0`.

## 3. Faire appliquer une config de securite a l'indexer (hash puis securityadmin)

**Prendre l'invocation reelle dans l'image, ne pas l'inventer** :

```bash
docker exec <indexer> sh -c 'cat /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh'
docker exec <indexer> sh -c 'grep -an "securityadmin\|hash.sh\|cacert" \
   /usr/share/wazuh-indexer/plugins/opensearch-security/tools/wazuh-passwords-tool.sh'
```

Forme verifiee en 4.7.3 (extraite de `wazuh-passwords-tool.sh`) : application **par fichier** et non par
repertoire, car `securityconfig/` n'existe pas ; HTTPS REST sur `-p 9200`, PEM `-cacert/-cert/-key`,
`-icl` (ignore l'index de securite deja pose) et `-nhnv` (ne verifie pas le nom d'hote) :

```bash
docker exec <indexer> bash -c \
 'OPENSEARCH_JAVA_HOME=/usr/share/wazuh-indexer/jdk OPENSEARCH_CONF_DIR=/etc/wazuh-indexer \
  /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh \
  -f /usr/share/wazuh-indexer/opensearch-security/internal_users.yml -t internalusers \
  -p 9200 -icl -nhnv \
  -cacert /usr/share/wazuh-indexer/certs/root-ca.pem \
  -cert  /usr/share/wazuh-indexer/certs/admin.pem \
  -key   /usr/share/wazuh-indexer/certs/admin-key.pem'
```

- `-t` : `internalusers`, `roles`, `rolesmapping`, `actiongroups`, `config`, `audit`, `tenants`.
- `JAVA_HOME` est **vide** dans le conteneur par defaut : l'exporter, sinon `hash.sh` et
  `securityadmin.sh` echouent. `hash.sh` lit `OPENSEARCH_JAVA_HOME` puis `JAVA_HOME`.
- Verifier DANS le conteneur lequel des deux repertoires de certs existe
  (`/usr/share/wazuh-indexer/certs/` monte par le compose vs `/etc/wazuh-indexer/certs/` cite par le
  script officiel) : un `-cacert` sur un chemin absent rend une erreur de confiance TLS qui ressemble a
  un mot de passe refuse.

Hachage d'un mot de passe et remplacement du hash dans `internal_users.yml` :

```bash
docker exec <indexer> bash -c 'OPENSEARCH_JAVA_HOME=/usr/share/wazuh-indexer/jdk \
   bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/hash.sh -p "<mdp>" | grep -A 2 issues | tail -n 1'
```

Le hash bcrypt se substitue a la ligne `hash:` de l'utilisateur vise, puis on reaffiche (section 3).
Le mot de passe n'entre **jamais** dans le fichier de sauvegarde ni dans le manifeste : il est affiche
une fois dans la reponse et note par l'utilisateur.

### Verification d'un changement d'identifiants (jamais par code de sortie)

```bash
curl -s -k -o /dev/null -w 'ancien=%{http_code}\n' -u 'admin:admin' https://127.0.0.1:9200/_cluster/health
curl -s -k -o /dev/null -w 'nouveau=%{http_code}\n' -u 'admin:<nouveau>' https://127.0.0.1:9200/_cluster/health
curl -s -k -u 'admin:<nouveau>' https://127.0.0.1:9200/_plugins/_security/authinfo
```

Attendu : `401` sur l'ancien, `200` sur le nouveau, et le role `all_access` toujours porte par le compte.
Une reponse `401` sur le NOUVEAU mot de passe ne prouve pas un mauvais hash : verifier d'abord la casse
et l'echappement shell du mot de passe, puis les certs, avant de restaurer.

## 4. Rollback : ce qu'un ROLLBACK.md doit porter

Par cible (fichier, volume, dossier compose) : chemin de la copie, chemin de destination REEL, SHA256
attendu, commande de restauration exacte, et la commande qui reapplique la config au service (un
`internal_users.yml` restaure sur l'hote ne change rien tant que `securityadmin.sh` n'a pas rejoue).

- Config type 4.7.3 : les 3 images sont presentes localement, un retour arriere ne demande aucun
  telechargement ; citer les identifiants d'images (`docker image inspect <image> --format '{{.Id}}'`)
  rend le retour verifiable.
- Restauration d'un volume : `docker compose stop` (JAMAIS `docker kill`) -> extraction par un conteneur
  jetable -> `docker compose up -d` -> controle par `docker ps` et les hashs.
- Un depot git de reference n'est PAS un rollback suffisant : un `git status` qui montre des fichiers
  deja modifies avant le chantier interdit de compter dessus — l'archive du dossier est le filet.

## 5. Pieges

- **Le nouveau mot de passe ne se met pas dans un fichier.** Le mandat le fait afficher une fois ; toute
  autre trace (manifeste, journal, scratch) est une fuite.
- **Un mot de passe d'enrolement absent (`authd.pass`) avec `use_password=yes` produit une boucle de
  rejets** (« Invalid password provided » toutes les ~50 s) qui se lit comme une tentative d'enrolement
  repetee. Signaler si la source (ex. `172.18.0.1`, la passerelle du reseau Docker) est identifiee ou
  reste NON IDENTIFIEE — ne pas la nommer par inference.
- **Une directive de configuration annoncee pour une version donnee se verifie DANS l'image**
  (`grep` du fichier de config par defaut, aide du binaire) avant d'etre ecrite : si elle n'existe pas
  dans la version installee, le dire et passer, jamais inventer un nom de directive.
- **Un tar natif Windows lit `C:` comme un hote distant** (`Cannot connect to C: resolve failed`) :
  ecrire l'archive par redirection (`tar czf - ... > "C:/..."`, cf. `windows-path-handling` Regle 3).
