# Wazuh — audit de version, CVE et configuration (lecture seule)

Posture : **lecture seule**. Aucune modification sans accord explicite. Si Wazuh n'est pas sur la
machine, le dire et s'arreter. Chaque affirmation du rapport se justifie par une sortie de commande.

## 1. Localiser et mesurer les versions — par composant

Une stack Wazuh combine souvent un deploiement Docker (manager / indexer / dashboard) et un agent natif.
Les quatre versions se lisent a quatre endroits differents.

```bash
# inventaire : nom, image (=> version), ports publies
docker ps -a --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}'

# version telle que le produit la declare
docker exec <manager>   /var/ossec/bin/wazuh-control info    # WAZUH_VERSION / WAZUH_REVISION / WAZUH_TYPE
docker exec <indexer>   sh -c 'cat /usr/share/wazuh-indexer/VERSION'
docker exec <dashboard> sh -c 'cat /usr/share/wazuh-dashboard/VERSION'
```

Agent Windows : `VERSION.json`, `ossec.conf` et `client.keys` sont souvent **proteges en lecture**.
Passer par le registre et par la version des binaires, qui sont lisibles :

```powershell
Get-ChildItem 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall' |
  Where-Object { $_.GetValue('DisplayName') -like '*Wazuh*' } |
  ForEach-Object { $_.GetValue('DisplayName'); $_.GetValue('DisplayVersion') }
# puis la version des DLL du dossier de l'agent
# (Get-Item -LiteralPath '<dir>\<dll>').VersionInfo.FileVersion
```

Complement utile : `<dir>\ossec-agent\.agent_info` (lisible) porte le nom et l'identifiant d'agent, et
le fait que l'agent parle au manager se lit au `netstat` (`ESTABLISHED` vers le port agent).

**Comparer les quatre versions avant tout verdict CVE** : un agent plus recent que son manager est un cas
courant, et il rend les verdicts differents d'un composant a l'autre.

## 2. Ports et interfaces

Le port publie par Docker n'est pas forcement le port du conteneur.

```bash
docker ps --format '{{.Names}} {{.Ports}}'          # ex. 127.0.0.1:55085->55000/tcp
netstat -ano | tr -d '\0' | grep -aE ":(1514|1515|55000|55085|9200)\b"
```

- Un `netstat` muet sur le port attendu, alors qu'un service repond sur cet endpoint, signe un
  **remappage** — pas un arret. Autre exemple : API publiee sur `<port different>->55000/tcp`.
- Dans le conteneur, l'API peut declarer `Listening on 0.0.0.0:55000`
  (`/var/ossec/logs/api.log`) : c'est l'interieur du conteneur. L'interface qui compte est celle de la
  publication.
- Conclure par interface : `127.0.0.1` = boucle locale seule ; `0.0.0.0` = exposition reseau.

## 3. Verdicts CVE

Trois sources, trois questions differentes :

1. **NVD** — `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=<ID>` : donne les plages de versions
   dans `configurations[].nodes[].cpeMatch[]` (`versionStartIncluding`, `versionEndExcluding`) et la
   severite CVSS. **C'est la source qui tranche un numero de version.** Sans cle d'API, compter ~7 s
   entre deux appels.
2. **OSV** — `https://api.osv.dev/v1/vulns/<ID>` : confirme l'existence et fournit les alias GHSA, mais
   pour un projet hors gestionnaire de paquets, `affected.ranges` est de type **GIT** : des hashes de
   commit, inutilisables pour un verdict sur un numero de version.
3. **API des avis GitHub** — `https://api.github.com/advisories/<GHSA>` (en-tete `User-Agent` requis) :
   `vulnerabilities[].first_patched_version` quand l'avis est publie. Un 404 signifie « aucun avis
   publie », pas « aucune vulnerabilite ».

**Regle de calcul : AFFECTE si `borne_basse <= version_installee < borne_haute`.** Ne comparer qu'a la
version corrigee rate la borne basse : une plage qui commence au-dessus de la version installee donne un
NON AFFECTE, meme si la version est inferieure au correctif annonce.

Avant de rendre un verdict, **lire la description** : une entree peut concerner un tout autre produit, et
la version « corrigee » annoncee n'a alors aucun objet.

## 4. Hygiene de configuration

| Point | Sonde |
|---|---|
| Identifiants par defaut | `curl -s -k -o /dev/null -w '%{http_code}' -u '<user>:<pass>' https://127.0.0.1:9200/_cluster/health`, puis `/_plugins/_security/authinfo` pour les roles obtenus |
| Certificat API | `docker exec <manager> sh -c 'openssl x509 -in /var/ossec/api/configuration/ssl/server.crt -noout -subject -issuer -dates'` — `subject == issuer` signifie **auto-signe** |
| Enrolement distant | `docker exec <manager> sh -c 'grep -aE "<auth>|<disabled>|<use_password>|<port>" /var/ossec/etc/ossec.conf'`, puis existence de `authd.pass` |
| Format des logs d'audit API | `docker exec <manager> head -c 300 /var/ossec/logs/api.log` — texte brut ou JSON se voit a la premiere ligne |
| Permissions Linux | `docker exec <manager> ls -la /var/ossec/api/configuration/security/ /var/ossec/api/configuration/ssl/` |
| Permissions Windows | `icacls '<chemin>'` — s'il rend « Acces refuse », declarer le point **NON MESURE** |

Sonder les identifiants par defaut est une action d'audit normale quand elle est demandee : uniquement
en **boucle locale**, uniquement en **lecture** (une requete d'authentification). 
**Ne jamais reproduire dans le rapport la valeur d'un secret** : `authd.pass` se caracterise par
« present / absent / taille », jamais par son contenu, et la correction s'exprime comme une commande de
rotation.

## 5. Forme du rapport

- Un verdict par point : **OK**, **A CORRIGER** ou **CRITIQUE**, chacun appuye sur la sortie de commande
  qui le fonde.
- Pour chaque point non-OK : la commande exacte de correction.
- Une section **NON MESURE** distincte pour ce qui n'a pas pu etre observe (ACL illisible, endpoint de
  login inexistant, source d'une boucle non identifiee). Ne pas combler par inference ; si une
  conclusion repose sur l'architecture plutot que sur une mesure, l'ecrire comme telle.
- Quand les deux bornes d'un verdict de version changent la reponse, le dire explicitement plutot que de
  rendre un « affecte / non affecte » nu.
