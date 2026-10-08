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

**Corollaire mesure (piege de diagnostic) : le manager ne journalise PAS ce rejet.** Un agent refuse
pour cause de version (ou qui boucle sur l'enrolement) ne laisse cote manager **aucune** ligne a son nom
et **aucune** ligne `Agent version must be lower or equal to manager version` : un `grep <nom>` dans
`/var/ossec/logs/ossec.log` rend `0` alors que l'agent est en train d'echouer en boucle. Un `0` cote
manager ne prouve donc jamais que l'agent va bien — descendre dans l'`ossec.log` de l'AGENT, ou l'on
trouve et le refus de version et la demande de cle associee. Et ces demandes repetees (une toutes les
~50 s) sont la source du `wazuh-authd: ERROR: Invalid password provided by <passerelle Docker>` quand
`authd` tourne sans `authd.pass` : le message accuse l'adresse de la passerelle, c'est l'agent de la
machine locale qui s'enrolle. Nommer l'auteur avant de chercher une attaque.

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

1. Pre-vols AVANT de desinstaller : (a) **verifier que le MSI de RETOUR est telechargeable** sur le
   depot officiel (`curl -sI https://packages.wazuh.com/4.x/windows/wazuh-agent-<v>-1.msi`) — un build
   non publie rend la retrogradation irreversible, et aucun MSI Wazuh n'existe en local (les `.msi` du
   cache `C:\Windows\Installer` ne sont pas identifiables par nom) ; (b) sauvegarder `client.keys.save`
   aussi — ecrit par l'installeur, il porte la cle de l'agent au moment ou l'on desinstalle (cf. 4) ;
   (c) lire `VERSION.json` : il porte un `stage` (`"stage":"rc2"` sur cet hote, invisible au registre) ;
   (d) **prouver que l'identite est synchrone des deux cotes** avant de casser quoi que ce soit :
   comparer non pas la LONGUEUR de la cle mais l'**empreinte sha256 du champ cle** cote agent et cote
   manager (`grep '^00N ' /var/ossec/etc/client.keys`) — deux empreintes egales prouvent la
   synchronisation sans jamais afficher le secret ; une longueur egale ne prouve rien.
2. Instantane + md5 de `client.keys` et `ossec.conf`, **hors** de Program Files. `client.keys` porte
   l'ID et la cle que le manager connait deja : le perdre, c'est re-enroller.
3. Desinstaller par **ProductCode** lu dans `...\Uninstall` - jamais `Win32_Product | Uninstall()`
   (lent, et il reconfigure tous les produits MSI). Effets MESURES de `msiexec /x {code} /qn` : exit 0,
   `WazuhSvc` retire du SCM, cle `Uninstall` supprimee, **tous** les sous-dossiers du dossier agent
   retires (`rids\ logs\ active-response\ …`) et **les deux fichiers a preserver supprimes**
   (`client.keys`, `ossec.conf`) : la restauration n'est pas optionnelle. Rien n'est journalise par
   defaut — ajouter `/l*v <journal>` (journal MSI en **UTF-16LE** : un `grep` ASCII y rend 0 ligne et
   fait croire a un journal vide, decoder avant de filtrer) pour obtenir `Removal completed
   successfully` et le nom du paquet effectivement retire.
4. **L'installeur RECOPIE dans le `.save` le fichier qu'il supprime.** Apres la desinstallation,
   `client.keys.save` porte la cle de l'agent (et le mtime du fichier vivant, plus celui de la version
   precedente) et `ossec.conf.save` est byte-identique a `ossec.conf`. Ne pas les lire comme des
   reliques perimees ni les supprimer sans regle — ne supprimer un `.save` que si (a) la sauvegarde de
   reference est **verifiee** et (b) ce `.save` est un **doublon exact d'un fichier encore vivant**.
   Apres une desinstallation, (b) est le plus souvent indécidable puisque le vivant a disparu :
   conserver et signaler, en donnant la commande de suppression plutot qu'en la lancant d'office. Ces
   `.save` n'empechent pas l'installation de la version cible, que la restauration ecrasera de toute
   facon. Ne supprimer `upgrade\` (dossier vide ou ne contenant que des `.msi`/`.exe`/`.cab`) qu'apres
   l'avoir liste : le nom reel est `upgrade\`, pas `upgrades\`.
5. Installer le MSI cible **sans enrolement** :
   `msiexec /i <msi> /qn WAZUH_MANAGER=<ip> WAZUH_MANAGER_PORT=1514 WAZUH_PROTOCOL=tcp`.
   `WAZUH_MANAGER` est obligatoire pour que `/qn` aboutisse, et il faut **omettre** les proprietes
   `WAZUH_REGISTRATION_SERVER|_PASSWORD|_PORT` : ce sont elles, pas la config, qui declenchent une
   tentative d'enrolement. Verifier la version du paquet AVANT : un MSI n'a pas de `VersionInfo`
   exploitable - lire sa table `Property` via l'objet COM `WindowsInstaller.Installer`, et sa signature
   Authenticode quand l'editeur ne publie pas de checksum (le certificat de signature peut etre
   **expire** avec un statut `Valid` : horodatage Authenticode ; le dire au lieu de conclure a un paquet
   douteux). **Arreter le service dans la MEME fenetre elevee que l'installation**
   (`Stop-Service -Name WazuhSvc -Force`) puis le passer en `StartupType Manual` : tant que la config
   n'est pas restauree, un demarrage automatique ferait tourner l'agent avec le `client.keys` vide du
   MSI. Ne pas supposer que l'installation demarre le service (mesure 4.7.3 : installe deja `Stopped`).
   Preuves que l'agent n'a jamais tourne, plus fortes qu'un `Start-Sleep` : `ossec.log` **absent** +
   `logs\` **vide** + `Get-NetTCPConnection -RemotePort 1514,1515` sans aucune ligne.
   `VERSION.json` **n'existe pas** en 4.7.3 : la version se lit au registre (`DisplayVersion`) et dans
   `wazuh-agent.exe` (`FileVersion`) - **deux** sources, pas trois. Le **ProductCode change a chaque
   version** (`{8DD4A697-...}` en 4.7.3, `{840F372A-...}` en 4.14.8) : le relire au registre apres
   chaque installation, ne jamais le reutiliser d'une version a l'autre.
6. L'installation fraiche ecrit un **`client.keys` vide** (0 o, sha256 `E3B0C442…` - l'empreinte du
   fichier vide : c'est a cela qu'on reconnait un "vide" et non un fichier illisible) et un
   `ossec.conf` par defaut. Avant de restaurer, differ la config sauvee et la fraiche : chaque bloc que
   l'ancienne ajoute (`localfile`, `syscheck`, `sca`, `rootcheck`, `client`, `logging`,
   `active-response`) doit etre compris par la version cible, sinon l'agent rejette le fichier entier.
   Le differ sert aussi de decision : la config 4.14.8 portait **9 `<localfile>`** contre **4** pour la
   4.7.3 - la sauvegarde contient donc la vraie config de surveillance, mais ses directives 4.14
   inconnues de 4.7.3 feront des avertissements au demarrage. Et mesurer les blocs d'enrolement plutot
   que les supposer : la config fraiche 4.7.3 n'en a **aucun**, alors que la 4.14.8 porte
   `<enrollment><enabled>yes</enabled>` - restaurer la sauvegarde telle quelle **re-arme la boucle
d'enrolement** (cf. pas 8). Ne pas confondre les `<enabled>yes</enabled>` legitimes (`<sca>`,
   `<synchronization>`) avec un bloc d'enrolement : citer le parent, pas la ligne.
7. Restaurer les deux fichiers (md5 conforme aux instantanes), puis `Start-Service WazuhSvc`.
8. Piege dormant a signaler : un `<manager_address>MANAGER_IP</manager_address>` non substitue (config
   generee par template) est inoffensif tant que `client.keys` est valide, mais l'agent tentera de
   s'enroller aupres d'un hote litteralement nomme `MANAGER_IP` si ce fichier est vide un jour. Le
   desactiver (`<enrollment><enabled>no</enabled></enrollment>`) des que `authd` est desactive cote
   manager : sinon l'agent redemande une cle toutes les ~50 s pour rien (cf. Regle 1).

**Mecanique d'execution de `msiexec` depuis un enfant eleve (piege mesure, coute une UAC)**

- Lancer `msiexec` par son **chemin complet** `C:\Windows\System32\msiexec.exe`. Avec le nom nu
  (`Start-Process -FilePath 'msiexec.exe'`), l'enfant eleve **ne lance rien** : `$p` reste vide, le code
  de sortie aussi, duree 0 s, aucun journal MSI, **aucun effet de bord** - et l'erreur part dans une
  console detachee invisible. Refaire l'operation au lieu de conclure au succes.
- Quand l'appel est de toute facon porte depuis la console Hermes (deja non elevee), `-Verb RunAs`
  interdit `-RedirectStandardOutput`/`-RedirectStandardError` : mettre un `Start-Transcript` dans
  l'enfant, sinon toute erreur est perdue.
- **Discriminant avant toute conclusion** : le journal MSI doit exister et etre non vide (`/l*v`), et
  `Get-WinEvent -ProviderName MsiInstaller` doit porter un evenement de transaction. Journal absent +
  aucun evenement = `msiexec` n'a jamais traite la ligne de commande, quel qu'ait ete le code de sortie.
- Code de sortie : `-Wait -PassThru` peut le rendre vide ; repli fiable = `& $exe @args` puis
  `$LASTEXITCODE`.
- Codes de sortie **a interpreter, pas a supposer** : 0 = succes, 3010 = succes + redemarrage requis,
  1605 = produit non installe (c'est le code a attendre pour un `/x` sur un ProductCode perime).
  Le journal MSI porte la phrase exploitable : `Product: Wazuh Agent -- Installation completed
  successfully` / `Removal completed successfully`.

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

## Regle 9 — retrogradation d'agent : sequence validee et pieges mesures (2026-10-08, 4.14.8 -> 4.7.3)

Sequence qui a fonctionne, dans cet ordre : sauvegarde (Regle 8) -> `Stop-Service WazuhSvc -Force` ->
`msiexec /x "{ProductCode}" /qn` (ancien code) -> telecharger le MSI cible et VERIFIER (taille exacte
attendue + `Get-AuthenticodeSignature`) -> `msiexec /i <msi> /qn WAZUH_MANAGER=<ip> WAZUH_MANAGER_PORT=1514
WAZUH_PROTOCOL=tcp` **sans aucune propriete `WAZUH_REGISTRATION_*`** -> `Stop-Service` immediatement ->
restaurer `client.keys` -> reinjecter les blocs de surveillance dans la config FRAICHE -> `Set-Service
-StartupType Automatic` -> `Start-Service` -> prouver par la regle **503** + `agent_control -i`.

Pieges mesures (chacun a coute un aller-retour) :
1. **`Start-Process -FilePath 'msiexec.exe'` (nom nu) dans un enfant eleve ne lance RIEN** : ni objet, ni
   code de sortie, 0 s, aucun journal MSI. Utiliser `C:\Windows\System32\msiexec.exe` et `Start-Transcript`
   dans l'enfant. Discriminant fiable avant de conclure : **le journal MSI existe et n'est pas vide**.
2. **Reinjecter la config ancienne ENTIERE duplique les blocs** : compter les doublons par
   `(location, log_format, query)` normalises AVANT d'inserer, n'injecter que les nouveaux. Ici 9 blocs ->
   4 doublons exacts des blocs deja presents dans la config fraiche, 5 reellement nouveaux (surveiller
   deux fois le meme canal = alertes doublees).
3. Verifier la compatibilite des directives dans la **doc officielle de la version CIBLE**, jamais par
   recherche de chaines dans le binaire : `strings`-like rend « present » pour tout, y compris `macos`.
4. Fins de ligne : la config d'origine peut etre en **LF pur** et celle ecrite par le MSI en **CRLF** ->
   une insertion textuelle produit un fichier mixte ; normaliser en CRLF (l'XML normalise de toute façon).
5. Le **desinstalleur MSI recopie dans `.save` les fichiers qu'il retire** : apres un `/x`, `client.keys.save`
   peut contenir **la cle de l'agent** avec un mtime neuf (ici l'identite s'est retrouvee conservee sur place,
   en plus de la sauvegarde). Ne jamais traiter un `.save` comme un dechet sans lire son sha256.
6. **4.7.3 ne livre pas `VERSION.json`** (apparu plus tard) : attendre 2 sources de version (registre +
   `FileVersion` de l'exe), pas 3. Le `ProductCode` change a chaque version : `{840F372A-…}` en 4.14.8,
   `{8DD4A697-…}` en 4.7.3.
7. Ne PAS appeler `wazuh-agent.exe control status` sous Windows (pas d'equivalent de `wazuh-control`) :
   risque de seconde instance. Verifier par `Get-Service` / `Get-Process`.
8. Preuves de connexion : `agent_control -l` (Active), `agent_control -i` (**Client version**, Last keep
   alive), alerte **503** dans `alerts.json`. Le `ossec.log` du manager **ne cite jamais le nom de
   l'agent** : y chercher l'agent renvoie 0 ligne et fait croire a un echec.
9. Apres un changement de version, un `ERROR: Could not move (shared/…)` cote agent (violation de partage
   sur un residu de synchro) + l'alerte manager **222** sont benins : verifier que l'agent est Active et
   que la politique SCA se charge, puis classer en benin plutot qu'en panne.

## Regle 8 — sauvegarder/restaurer un agent aux fichiers ILLISIBLES (elevation UAC)

Etat mesure le 2026-10-08 : `client.keys`, `ossec.conf`, `ossec.log`, `VERSION.json` et `rids\` rendent
**« Acces refuse »** a une session Hermes non elevee (`net session` refuse, `IsInRole(Administrator)`
= False), tandis que l'**inventaire** du dossier fonctionne (`ls -l` liste tout) et que
`local_internal_options.conf` / `internal_options.conf` restent en `(RX)` pour Utilisateurs. Un `icacls`
sur ces fichiers rend « Acces refuse » — l'ACL est restrictive, ce n'est PAS le cas de la Regle 2
(chemin sans aucune ACE). Ne pas confondre les deux, ne pas « reparer » une DACL saine.

L'elevation est disponible **a la demande** depuis le terminal (l'utilisateur clique Oui sur l'invite) :

```powershell
Start-Process -FilePath 'powershell' -Verb RunAs -Wait -PassThru -ArgumentList `
  @('-NoProfile','-ExecutionPolicy','Bypass','-File','<scratch>\backup_agent.ps1')
```

Le script eleve ecrit son propre rapport (`BACKUP_REPORT.txt` : sha256 + taille de chaque copie) dans le
dossier de sauvegarde ; la session non elevee **relit et re-verifie** ces sha256 — c'est ce couple qui
rend la sauvegarde opposable (un simple « COPIE OK » auto-declare ne prouve rien). Contraintes : script
`.ps1` en **ASCII pur** (PowerShell 5.1 relit l'UTF-8 sans BOM en ANSI) et `-Wait` pour que l'appelant
sache quand le travail est fini. La copie n'herite PAS de l'ACL restrictive de la source : `client.keys`
devient lisible par la session non elevee — necessaire pour restaurer, mais c'est un secret a ne pas
deplacer. Corollaire : **toute restauration dans `Program Files (x86)` demandera la meme elevation**.
Chaque `RunAs` coute une validation UAC : regrouper dans la MEME fenetre elevee l'inventaire (lecture
seule) **puis** l'action, le script enfant ecrivant un rapport horodate par etape ; pour `msiexec`,
enchainer la desinstallation et l'inventaire post-operation dans le meme appel (le `/qn` est
silencieux et ne represente pas d'UAC). Un seul clic, deux preuves.

**Ecrire un enfant eleve sans se tirer une balle dans le pied** (template pret a copier :
`templates/elevated_child.ps1`) :

- **Les variables PowerShell sont insensibles a la casse** : `$l` et `$L` sont la MEME variable. Un
  `foreach ($l in ...)` qui alimente un tableau de rapport `$L` l'**ecrase** en silence (l'appel
  `.Add()` sur une chaine echoue sans bruit si l'erreur n'est pas fatale) : le rapport sort avec une
  seule ligne, et l'inventaire est perdu, a rejouer. Nommer explicitement (`$ligne`, `$item`, `$out`).
- **`$args` est une variable automatique** : ne pas s'en servir pour construire une ligne de commande
  (`msiexec` recevrait une liste vide, donc pas de `/qn`, donc une interface qui attend). `$msiArgs`.
- L'ACL **varie selon la version installee** : l'installation 4.14.8 rendait `client.keys`/`ossec.conf`
  totalement illisibles, la 4.7.3 les laisse en `(RX)` pour l'utilisateur (lecture possible sans
  elevation, ecriture toujours interdite). Re-mesurer (`icacls`) apres chaque installation au lieu de
  presupposer ; dans tous les cas la restauration ecrit dans `Program Files (x86)` et exige l'elevation.

## Voir aussi

- `security-ops` - stack Wazuh Docker, dashboard 403, roles_mapping, regles custom, audit de securite.
- `windows-path-handling` - piege `msiexec //x` en bash (echec silencieux, exit 103).
