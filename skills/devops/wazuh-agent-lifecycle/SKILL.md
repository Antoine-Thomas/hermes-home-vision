---
name: wazuh-agent-lifecycle
description: "Use when a Wazuh agent won't start or register."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [wazuh, agent, siem, msiexec, service]
    category: devops
---

# Wazuh Agent Lifecycle

Installer, aligner, reparer et verifier un agent Wazuh face a un manager (le plus souvent un stack
Docker single-node sur l'hote). Complementaire de `security-ops`, qui couvre la stack elle-meme
(dashboard 403, roles_mapping, regles custom, audit) : ici, c'est le cycle de vie de l'AGENT.

## When to use

- L'agent (Windows ou Linux) ne demarre pas, ou le manager ne le voit jamais.
- `ERROR: (1226): Error reading XML file 'ossec.conf'` sur une configuration pourtant valide.
- `Agent version must be lower or equal to manager version`.
- Reinstaller ou retrograder l'agent sans perdre son ID ni sa configuration.
- Verifier de bout en bout que les alertes remontent vraiment jusqu'au manager.

## Regle 1 — lire le journal de l'AGENT avant de croire le manager

Vu du manager, « l'agent ne se connecte jamais » recouvre au moins deux pannes independantes, qui
peuvent coexister. Le seul juge est le journal de l'agent :
`C:\Program Files (x86)\ossec-agent\ossec.log`. Ne pas conclure depuis `agent_control` ni depuis
l'absence d'alertes : un agent peut etre `Disconnected` pour incompatibilite de version ET avoir un
fichier de configuration illisible - deux causes, deux corrections, dans cet ordre.

## Regle 2 — erreur 1226 sur un `ossec.conf` VALIDE = probleme d'OBJET fichier

Symptome : le fichier valide en XML (`ElementTree`, `XmlDocument`) et identique octet pour octet a sa
sauvegarde, mais l'agent sort au demarrage. C'est un echec d'**ouverture**, ce qui explique que la
validation de syntaxe passe sans rien voir.

Le confirmer avant d'agir : les binaires natifs sont refuses sur ce fichier alors que MSYS le lit, et
`icacls` affiche le chemin **sans aucune ACE**.

```bash
python -c "open(r'C:\Program Files (x86)\ossec-agent\ossec.conf','rb').read(16)"   # PermissionError
head -c 16 "/c/Program Files (x86)/ossec-agent/ossec.conf"                          # fonctionne
```

Correction : **remplacer** le fichier pour que le nouvel objet herite d'une DACL saine. Ne jamais
ecrire dans le descripteur existant (`>`, `tee`, editeur en place) : cela conserve l'objet fautif.

```bash
cp "<ossec.conf>" "<ossec.conf>.new" && mv -f "<ossec.conf>.new" "<ossec.conf>"
```

Sauvegarder d'abord et comparer les md5 avant/apres (le contenu doit etre identique), verifier que le
nouvel ACL est normal (SYSTEM + Administrateurs) et que `python` ouvre le fichier, puis
`Start-Service WazuhSvc` en surveillant `ossec.log` : la ligne 1226 doit disparaitre et
`INFO: (4102): Connected to the server` apparaitre.

**Un service qui demarre n'est pas un service qui TIENT.** L'agent qui echoue au parsing sort
**proprement** : `ExitCode 0`, PID 0, aucune erreur remontee par `Start-Service`. Un service vu
`Running` juste apres le demarrage ne prouve donc rien, et enchainer sur le diagnostic suivant sur la
foi d'un seul releve fait rapporter une reparation qui n'a pas eu lieu. Controle a faire AVANT de lire
le journal : `Get-Service WazuhSvc` **trois fois** (+5 s, +35 s, +2 min) doit rendre `Running` avec un
PID stable. C'est la meme discipline que pour toute la pile : chaque couche peut etre verte localement
alors que la chaine est cassee, donc `docker ps` -> port 55000 -> `Get-Service` -> `agent_control -l`
-> `alerts.json` qui grossit, une couche a la fois, en nommant celle qui casse.

## Regle 3 — agent ≤ manager, sans exception

Wazuh refuse tout agent **plus recent** que le manager. Lire les deux versions, jamais les supposer.

```powershell
(Get-Item 'C:\Program Files (x86)\ossec-agent\wazuh-agent.exe').VersionInfo.FileVersion
Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' |
  Where-Object DisplayName -match Wazuh | Select-Object DisplayName,DisplayVersion
```
```bash
docker exec single-node-wazuh.manager-1 /var/ossec/bin/wazuh-control info
```

Le compose **epingle un tag d'image** : `WAZUH_VERSION` dans `~/wazuh-docker/single-node/.env` peut etre
perime et inutilise. Comparer avec `docker ps --format '{{.Image}}'`, pas avec le .env - sinon on
annonce une version que le manager n'a pas.

Deux issues : monter manager + indexer + dashboard **ensemble**, ou retrograder l'agent (option
contenue).

## Regle 4 — retrograder sans perdre l'ID ni la configuration

1. Instantane + md5 de `client.keys` et `ossec.conf`, **hors** de Program Files. `client.keys` porte
   l'ID et la cle que le manager connait deja : le perdre, c'est re-enroller.
2. Desinstaller par **ProductCode** lu dans `...\Uninstall` - jamais `Win32_Product | Uninstall()`
   (lent, et il reconfigure tous les produits MSI). La desinstallation laisse `ossec.conf.save`,
   `client.keys.save`, `local_internal_options.conf.save`, vide le dossier sans le supprimer, et
   supprime le service `WazuhSvc`.
3. Installer le MSI cible : `msiexec /i <msi> /qn /norestart WAZUH_MANAGER=<ip>`. Verifier la version
   du paquet AVANT : un MSI n'a pas de `VersionInfo` exploitable - lire sa table `Property` via l'objet
   COM `WindowsInstaller.Installer`, et sa signature Authenticode quand l'editeur ne publie pas de
   checksum.
4. L'installation fraiche ecrit un **`client.keys` vide** et un `ossec.conf` par defaut. Avant de
   restaurer, differ la config sauvee et la fraiche : chaque bloc que l'ancienne ajoute (`localfile`,
   `syscheck`, `sca`, `rootcheck`, `client`, `logging`, `active-response`) doit etre compris par la
   version cible, sinon l'agent rejette le fichier entier.
5. Restaurer les deux fichiers (md5 conforme aux instantanes), puis `Start-Service WazuhSvc`.
6. Piege dormant a signaler : un `<manager_address>MANAGER_IP</manager_address>` non substitue (config
   generee par template) est inoffensif tant que `client.keys` est valide, mais l'agent tentera de
   s'enroller aupres d'un hote litteralement nomme `MANAGER_IP` si ce fichier est vide un jour.

## Regle 5 — prouver la remise en route par trois lectures independantes

Aucune ne suffit seule :

```bash
tail -5 "/c/Program Files (x86)/ossec-agent/ossec.log"                    # (4102) Connected to the server
docker exec single-node-wazuh.manager-1 /var/ossec/bin/agent_control -l  # ID <n> <nom> Active
curl -k -H "Authorization: Bearer $TOK" \
  "https://localhost:55000/agents?agents_list=<id>&select=status,version,lastKeepAlive"
```

Puis : `alerts.json` doit **grossir** et contenir `"agent":{"id":"<n>"}`. La regle
**503 "Wazuh agent started"** prouve la poignee de main ; de vraies alertes Windows
(`Windows logon success`) prouvent la voie eventchannel. Ne voir que des 50x = l'agent se connecte mais
ses evenements ne matchent aucune regle - c'est un autre probleme, ne pas le rapporter comme un echec
de connexion.

## Regle 6 — tester la chaine d'alertes SANS appel modele

`ai/analyze_alerts.py` n'a **pas** de `--dry-run` (ses flags sont `--minutes/--level/--limit/--deep/--telegram`)
et refuse de tourner sans `WAZUH_API_PASSWORD`. Pour exercer le chemin de lecture sans aucun appel IA,
importer le collecteur - `common.py` est dans `data/security-monitoring/`, il n'y a **pas** de
sous-dossier `scripts/` :

```bash
python -c "import sys; sys.path.insert(0,'<...>/data/security-monitoring'); import common; print(len(common.get_recent_alerts()))"
```

Attention au seuil : la chaine filtre `min_level` (10 par defaut), donc une stack saine rend
legitimement **0** quand le manager ne contient que des alertes de cycle de vie de niveau 3. Ne pas
lire ce 0 comme une panne, et le dire explicitement dans le rapport.

## Regle 7 — « connexion refusee » sur 1514 : c'est le MANAGER qui ne publie pas

Un agent qui boucle sur `ERROR (1216): Unable to connect to '[127.0.0.1]:1514/tcp'` (connexion
refusee), accompagne de `ERROR (1208): Unable to connect to enrollment service at
'[127.0.0.1]:1515'`, n'a presque jamais un probleme d'agent : ni `client.keys`, ni l'enrolement, ni
`ossec.conf`. La seule question a trancher est « le manager publie-t-il 1514 sur l'HOTE ? ». Quand
l'agent et le manager tournent sur la meme machine, l'agent vise deja `127.0.0.1:1514` : aucune
action cote agent ne reparera un port que le manager ne publie pas.

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"   # 1514->1514 visible sur le manager ?
docker port single-node-wazuh.manager-1                          # vide = rien de publie
netstat -ano | grep -E ":(1514|1515)\s"                          # rien en LISTENING = rien n'ecoute
```

**Le piege de diagnostic** : `HostConfig.PortBindings` peut declarer les quatre mappings
correctement alors que `NetworkSettings.Ports` est **vide** et que le conteneur tourne quand meme
(« Up », ports muets). Ne jamais conclure depuis le compose ni depuis `HostConfig` : lire
`NetworkSettings.Ports` ou `docker port`. Un `docker restart` ne change rien — l'obstacle est au
niveau de l'hote, pas du conteneur.

**Cause la plus frequente sur Windows : une plage de ports RESERVEE** (Hyper-V / HNS / winnat).
Docker ne peut pas binder le port hote, et il ne publie alors AUCUN port du conteneur. Le meme
mecanisme frappe n'importe quel `ports:` d'un compose, pas seulement Wazuh.

```bash
powershell -NoProfile -Command "netsh int ipv4 show excludedportrange protocol=tcp"
docker inspect single-node-wazuh.manager-1 --format '{{json .NetworkSettings.Ports}}'   # {} = rien
```

`docker compose up -d --force-recreate` ne contourne pas l'exclusion : il echoue franchement
(`bind: An attempt was made to access a socket in a way forbidden by its access permissions`) et
laisse le manager en etat **Created** — donc une pile plus degradee qu'avant. Le correctif est un
**remap du port hote** juste au-dessus de la plage exclue, port interne inchange, bind sur localhost :

```yaml
    ports:
      - "127.0.0.1:1514:1514"
      - "127.0.0.1:1515:1515"
      - "127.0.0.1:514:514/udp"
      - "127.0.0.1:55085:55000"
```

Reflexes d'execution lies : `docker compose config -q` pour valider le compose edite avant de
l'appliquer (puis `docker compose config` pour relire les `host_ip`/`published` resolus) ; et
`docker compose up -d` etant refuse en avant-plan par le terminal, le lancer en `background=true` +
`notify=true` puis lire la sortie avec `process_manage(action='poll')` — c'est elle qui porte
l'erreur de bind.

Suites specifiquement Wazuh (une seule ligne oubliee suffit a casser la suite) :

- `data/security-monitoring/config.json` : corriger `wazuh.api_url` **ET** l'entree correspondante de
  `ports.allowlist`. Sans l'allowlist, le nouveau port publie est vu comme un « port ouvert non
  attendu » et la surveillance s'alarme de sa propre correction.
- Le dashboard joint l'API par le reseau Docker (`https://wazuh.manager:55000`,
  `config/wazuh_dashboard/wazuh.yml`) : le remap du port hote ne le touche pas, ne pas y toucher.
- Preuve de la nouvelle API : `curl -sk -m 15 -u "<user>:<motdepasse>" -X POST
  "https://localhost:<port>/security/user/authenticate?raw=true"` doit rendre **200** + un JWT
  (~400 car., prefixe `ey`). Verifier le code HTTP et la nature de la reponse, ne jamais imprimer le
  jeton.

Verification de la remise en route, dans cet ordre : `INFO: (4102) Connected to the server` dans
`ossec.log`, socket `ESTABLISHED` sur 1514, `agent_control -l` -> `Active`, puis alertes. Une erreur
`SSL error (5). Connection refused by the manager` quelques secondes AVANT la ligne
`Started (pid: ...)` de l'agent est le dernier soubresaut du redemarrage, pas un echec restant —
verifier l'horodatage avant de la compter.

**Decalage horaire a ne pas lire comme une incoherence** : `ossec.log` est horodate en heure LOCALE,
`alerts.json` en UTC. Une alerte qui semble preceder l'evenement de deux heures est le meme instant
dans deux fuseaux.

## Voir aussi

- `security-ops` - stack Wazuh Docker, dashboard 403, roles_mapping, regles custom, audit de securite.
- `windows-path-handling` - piege `msiexec //x` en bash (echec silencieux, exit 103).
