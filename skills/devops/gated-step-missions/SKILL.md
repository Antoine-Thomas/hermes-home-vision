---
name: gated-step-missions
description: "Use when a multi-step mission needs a GO between steps."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [mission, chantier, go-gate, lecture-seule, journal, rapport, etats-normalises]
    related_skills: [hermes-stack-audit, windows-path-handling, planning-workflow]
    category: devops
---

# Missions par etapes avec GO (chantiers)

Un « chantier » / « mission » annonce par l'utilisateur : des etapes numerotees, une seule a la
fois, un GO entre chaque, un journal, et souvent des contraintes de lecture seule. Cette skill
porte le PROTOCOLE (cadence, preuves, format de rapport, journal) ; pour la liste des sondes a
lancer sur tel sous-systeme, voir `hermes-stack-audit` et `windows-path-handling`.

## When to use

- La demande porte « MISSION », « CHANTIER », « ETAPE 1 / 2 / 3 », « un GO entre chaque etape »,
  « lecture seule », « aucune modification », « log dans… », « backup avant toute modification ».
- Toute demande d'inventaire et d'etat d'un parc de services avec un verdict a rendre avant d'agir.
- Une demande d'audit dont la sortie attendue est un rapport que l'utilisateur valide avant la suite.

## Regles durables

- **Une etape par tour, puis STOP explicite.** Terminer le rapport par une ligne d'arret nette
  (ex. « STOP. J'attends ton GO »). Un GO ne se deduit jamais : ni parce que l'etape suivante est
  triviale, ni parce qu'elle est deja en lecture seule, ni parce qu'une etape precedente a ete
  validee. Un GO vaut pour l'etape suivante et rien d'autre. Le perimetre reel d'un GO est ce qu'il NOMME
  plus ce que ses DECISIONS decrivent : quand un GO « ETAPE 1 + 2 » enonce ensuite des decisions qui
  portent sur une etape ulterieure (le script d'envoi doit charger des fichiers d'exclusion, backup du
  script avant modif = le contenu de l'etape 3), cette etape est autorisee par sa decision — la
  traiter et l'annoncer au rapport (« etape 3 traitee au titre de la decision 3 »). Ce qui n'est ni
  nomme dans le GO ni decrit par une decision reste gele : un GO « 1 + 2 » ne couvre pas une etape 4
  simplement ecrite plus bas dans le plan.
- **Une cible non identifiee se DEMANDE, elle ne se cherche pas.** Quand un GO porte sur un artefact
  precis (un commit a reecrire, un job, une entree de registre) sans en donner l'identifiant — chemin
  du depot, branche, hash —, l'etape 0 est UNE question a l'utilisateur, puis STOP : pas de `git grep`,
  pas de `find`, pas de recherche recursive pour « retrouver » la cible. Un inventaire large coute des
  minutes, ramene des faux positifs, et expose a reecrire l'objet VOISIN (« le commit qui parle du meme
  sujet ») : ne jamais substituer une cible approchante a celle qui est demandee. Si l'artefact annonce
  n'existe pas (aucun depot ne porte ce commit), le rapport dit l'ECART entre la premisse et la mesure
  et rend la question de localisation — il ne « repare » rien et ne touche a rien.
  Quand une verification bornee est indispensable pour pouvoir poser la question, deux formes
  suffisent : `find <racine> -maxdepth 4 -path '*/.git/logs/HEAD' -newermt '<N> hours ago'` donne les
  depots qui ont recu un commit recemment (un commit APPEND toujours `logs/HEAD`), et l'interrogation
  d'un depot PRECIS (`git -C <depot> grep -n <motif>`) remplace tout balayage de disque.
  **L'horodatage de `.git/index` ne prouve aucune activite** : tout `git status`, y compris une sonde
  en lecture seule de l'agent lui-meme, le rafraichit — une « activite recente » deduite de cet index
  peut etre la sienne. Et verifier qu'un volume porte bien quelque chose avant de conclure « aucun
  depot » : un `find` qui rend en une seconde sur un disque de plusieurs To a parcouru un point de
  montage vide, ce qui ne prouve pas l'absence de depot.
- **Un GO qui pre-enregistre une REGLE DE DECISION autorise d'avance sa branche non-creative.** Quand
  le plan dit « si <critere mesure> alors produire <livrable> ; sinon garder <l'existant>, STOP, et
  documenter dans <skill> », appliquer le critere est de la MESURE, pas une decision autonome : si le
  critere n'est pas rempli, la branche « garder + documenter » s'execute parce que le GO l'ecrit, et le
  rapport dit le verdict et la mesure qui le fonde. La branche qui PRODUIT un nouveau livrable reste
  soumise au GO : un critere rempli se RAPPORTE, il ne se fabrique pas tout seul.
- **Un plan remplace par un plan plus recent se traite comme tel.** Quand une demande qui arrive en
  cours de route redefinit les etapes (nouvelle liste, nouvel ordre, ou un plan complet a la place d'un
  autre), basculer sur la PLUS RECENTE et l'annoncer en une ligne ; les mesures deja prises restent
  valables et se reutilisent — un chiffre mesure ne perime pas parce que le plan a change — mais les
  etapes du plan abandonne ne se poursuivent pas. Ne pas mener les deux de front, et ne pas rejouer ce
  que le nouveau plan ne demande plus.
- **Etiqueter chaque affirmation** : `etabli` (mesure), `hypothese`, `inconnu`. La conformite
  demandee est litterale : un ecart entre une premisse de la demande et la mesure se signale dans
  le rapport, jamais ne se corrige en silence.
- **Ne pas se fier a un resume** — ni a celui d'une session precedente, ni a son propre brouillon.
  Re-deriver les faits des sources primaires a chaque etape (fichier, base en lecture seule, trace,
  sortie de commande fraichement executee).
- **Un GO qui annonce un payload (« les sections du document X, que je te donne ci-dessous ») peut
  arriver SANS lui.** Des placeholders du type `[ICI : coller …]` a la place du contenu ne rendent pas
  l'etape « a deviner » : elle est infalsifiable. Etablir l'absence par des sondes bornees et NOMMEES
  — les chemins cites par le mandat, `Desktop`/`Documents`, l'historique des sessions, la base de
  connaissances — puis rendre un rapport `BLOCKED` avec l'etat livrable par livrable (`OK`/`ABSENT`)
  et la question. Ne JAMAIS rediger le contenu manquant depuis un artefact voisin, un journal ou de
  memoire : le rapport dit ce qui est fait et ce qui reste gele. Les etapes independantes du payload
  (revert, archivage, nettoyage) s'executent quand meme et se declarent faites — un GO partiel ne
  justifie pas de geler ce qu'il ne touche pas.
- **Une liste de fichiers d'un plan porte des chemins faux : verifier chaque source avant de copier
  ou de supprimer.** Un fichier annonce « depuis `<dossier>` » peut vivre dans le dossier voisin — le
  localiser (`find`), dire l'ECART dans le rapport, et executer l'item depuis son chemin REEL plutot
  que de l'abandonner ; le compte declare par le plan (nombre de fichiers attendus) sert de controle
  d'acceptation. Inversement, un motif de suppression sans objet (fichier inexistant dans tout l'arbre)
  se signale comme tel : ce n'est pas un echec d'execution. Avant tout `rm` par motifs, lister les
  correspondances et les croiser avec la liste « conserver » du mandat, puis RE-verifier cette liste
  apres la suppression — un motif large emporte des fichiers que le plan veut garder.
- **Backup horodate + retour possible** avant toute ecriture : copie a cote de la cible
  (`<f>.bak.<AAAAMMJJ_HHMMSS>`), nom citee dans le rapport, diff montre avant application.
  Un correctif qui touche PLUSIEURS fichiers se sauvegarde dans un dossier horodate
  (`backups/<CHANTIER>_<ETAPE>_<AAAAMMJJ_HHMMSS>/`) accompagne d'un manifeste : SHA256 avant, SHA256
  des copies (comparaison a l'original exigee identique), SHA256 apres, verdict « INCHANGE / MODIFIE »
  fichier par fichier, et un `diff -u` complet. C'est ce manifeste qui rend le rollback verifiable et
  le rapport chiffrable (`+ajoutees/-retirees` par fichier).
  **La liste de backup du plan est un plancher, pas un perimetre** : tout fichier qu'on TOUCHE y entre,
  y compris une documentation que le plan avait oubliee. S'apercevoir APRES coup qu'un fichier modifie
  n'a pas de copie interdit de pretendre a une restauration : consigner son hash et dire que le
  rollback est l'annulation des N passages decrits.
  Ne jamais editer a la main un fichier qu'un service reecrit (jobs du planificateur, config geree
  par le CLI) : passer par l'outil ou la CLI dediee.
- **Journal de chantier en AJOUT SEUL** (`data/route_ia_fix/chantier_<NOM>.log`) : une entree
  horodatee par etape, aucune ligne existante modifiee.
  **L'emplacement du journal obeit au mandat, pas a cette convention.** Quand le mandat exclut les dossiers
  du projet (data\rag, profiles\.env, jobs) ou annonce un emplacement final pas encore cree
  (`D:\Backup_...`), ouvrir le journal dans un dossier de MISSION neutre et durable hors du projet
  (`C:\Users\<user>\<mission>_<AAAAMMJJ>\`), y poser aussi le script d'append et les blocs de texte, et
  le copier vers l'emplacement final a la derniere etape — en l'annoncant. Jamais `cache/scratch` : il est
  elague apres 24 h d'inactivite, alors qu'une mission gatee attend un GO humain, donc des jours, et
  l'historique des etapes disparait avant la fin. Prouver l'ajout (comptage de lignes + SHA
  avant/apres) et sauvegarder le journal avant l'ajout s'il existe deja.
  **Un journal NEUF s'aligne sur l'encodage des journaux voisins** (les journaux de `data/rag/` sont en
  CRLF) : l'outil d'ecriture cree en LF, donc normaliser UNE fois avant la premiere entree (remplacement
  des octets `\n` -> `\r\n`, puis comptage `CRLF` / `LF` en Python) — un journal a fins de ligne
  melangees fait ensuite deviner l'encodage a l'outil d'append. Les fins de ligne se comptent sur les
  OCTETS (`io.open(p, 'rb')`), jamais a l'ecran : un CRLF affiche peut se lire `\r\r\n` et faire croire a
  un fichier corrompu. Un outil de dry-run/append existe deja
  (`release-documentation/scripts/dryrun_edit.py --fichier <f> --mode append --text-file <txt> --write`) ;
  a defaut, un script qui ouvre la cible en `"a"` (cf. Pieges).
  Les journaux de chantier d'un meme dossier portent la MEME forme d'entree (`====` de separation,
  `[horodatage] CODE — TITRE`, texte sans accents) : s'y conformer, y compris pour l'entree d'ouverture
  d'un chantier neuf, qui annonce le perimetre et les regles (lecture seule, aucun secret, journal en
  ajout seul) avant la premiere mesure.
- **Secrets : noms de variables uniquement.** Aucune valeur dans le rapport, le journal ou le
  scratch. Aucun identifiant en argument de commande (une sonde de service protege se valide par le
  code ATTENDU `401`/`403`) ; un secret repere = `[REDACTED]` + presence notee.
- **Une etape de diagnostic garde la main legere sur ce qu'elle mesure.** Quand le GO interdit de
  consommer du quota (ou toute autre ressource comptee), une question d'etat (« est-ce toujours en
  panne ? ») se repond d'abord par une trace FRAICHE deja ecrite (`call_logs` d'un routeur,
  `executions.db`), et seulement si elle manque par le minimum de sondes : une par cible, jamais en
  rafale. Le rapport ANNONCE leur nombre (« 3 sondes, 1 par combo ») : c'est ce qui rend le cout
  auditable. Un fichier d'ETAT (`*_state.json`) ne repond jamais a une question d'HISTORIQUE — le dire,
  et lui substituer la source mesuree equivalente en signalant l'ecart.
- **L'en-tete d'etape prime sur ses items.** Une etape annoncee « DIAGNOSTIC (lecture seule) » reste
  sans ecriture meme si l'un de ses items demande de produire un fichier (« extraire la liste des N
  adresses dans un CSV ») : livrer la donnee dans le rapport, laisser la creation du fichier a l'etape
  gatee qui la prevoit, et SIGNALER la contradiction de consigne — ecrire le fichier « puisqu'il est
  demande » rompt le mandat, et ne rien dire laisse croire a un oubli.
- **Une cause presumee dans la demande se confirme ou se refute a l'etape 0, pieces en main.** Quand le
  mandat ouvre sur une hypothese (« cause probable : X mal configure ») et enchaine un plan de
  correction « selon le diagnostic », l'etape de diagnostic teste l'hypothese et rend le verdict
  `confirme` ou `refute` avec la mesure qui le fonde. Une premisse refutee ne se corrige pas en
  silence et ne s'execute pas « quand meme » : le rapport dit ce qui a ete refute, nomme la cause
  REELLEMENT mesuree, et propose la suite sur cette base.
- **Verdicts normalises** : `READY` / `DEGRADED` / `FAILED` / `BLOCKED`, et une ligne
  `MODIFICATIONS: 0` quand l'etape etait en lecture seule.
- **Ne rien supprimer** : une fonction obsolete se documente et se propose en retrait de perimetre,
  jamais ne se supprime en cours de chantier. Un retrait se fait par DESACTIVATION reversible
  (tache `Disable-ScheduledTask`, entree d'allowlist retiree, doc corrigee) : recette complete dans
  `references/retrait-composant.md`.
- **Un GO deja execute qui revient ne se rejoue pas.** Si le meme GO est renvoye apres le rapport
  (copier-coller, relance), ne pas refaire les modifications : mesurer l'etat courant en lecture seule,
  confirmer qu'il est inchange, et ajouter au journal une courte entree de re-verification (« aucun
  changement depuis le rapport »). Le dire dans la reponse : ce tour est une confirmation, pas une
  execution. Rejouer une modification deja appliquee (2e desactivation, 2e retrait) est un ecart de
  conformite, pas une precaution.
- **Le rapport reprend LES EN-TETES demandes dans le GO, mot pour mot.** La plupart des GO enumerent
  la structure attendue (« 2.1 / 2.2 / 2.3 », « Tache / Allowlist / Documentation / Listeners /
  Consommateurs / Backups / SHA256 avant-apres / Tests / Rollback / Regressions », « ETAT : READY /
  DEGRADED / BLOCKED ») : produire exactement ces sections, dans cet ordre, puis regrouper tout bloc
  supplementaire (MODIFICATIONS TOTALES, BACKUPS, ERREURS, RISQUES RESTANTS) en UN seul bloc final.
  Un rapport bien fait mais range dans un autre ordre se lit comme un rapport incomplet.
- **Un GO qui porte son propre STOP est DEUX tours.** Quand la demande enchaine « PHASE 1 … RAPPORT
  PHASE 1 (obligatoire) … STOP … PHASE 2 … », s'arreter au rapport de la premiere phase et attendre :
  la suite est ecrite d'avance mais elle n'est pas autorisee avant que le rapport ait ete lu. Ne pas
  enchainer sur la phase 2 parce que les instructions sont deja la.
- **Une etape de DECISION (A reparer / B remplacer / C retirer) a sa propre forme.** Chaque option
  porte Avantages / Inconvenients / Effort (temps, argent) / Risques ; puis UNE recommandation
  motivee, avec le plan numerote exact (backup, correctif, preuve, tests, re-verification) et le
  risque de re-panne chiffre separement sur la DEPENDANCE et sur l'IMPACT. Ne pas appliquer l'option
  recommandee : elle reste soumise au GO et le rapport finit par le STOP. Avant de recommander un
  REMPLACEMENT, citer l'ecart mesure entre le composant et son remplacant (`N/M cas contre N'/M'`) et
  son accord avec les decisions reellement prises ; avant de recommander un RETRAIT, exiger la mesure
  qui compare le composant a son repli — sinon la capacite est jetee a l'aveugle, et le dire ainsi.
- **Quand un composant est juge « en panne », nommer le point exact du code qui le condamne.** Un
  rapport d'etape qui conclut « composant BLOCKED » sans dire QUI a pose l'etat, ni si un critere est
  ecrit en dur, laisse l'etape suivante reparer un service sain.

## Procedure

1. **Cadrer l'etape avant de mesurer** : ecrire la liste des mesures (une ligne = une commande ou une
   lecture), puis les executer. Une mesure non prevue mais decouverte en route s'ajoute et se dit.
2. **Mesurer par lots, et ecrire chaque lot dans un fichier du scratch**
   (`cache/scratch/<sujet>/lotN.txt`) avant de le relire. Une sortie longue tronquee n'est pas une
   sortie vide ; la relecture du fichier est la seule preuve et survit a un appel qui expire.
3. **Un composant = une ligne de tableau** : nom, role, port, processus, dependances, etat, health
   check disponible, DERNIER SUCCES, DERNIER ECHEC. Les deux derniers se lisent dans un artefact
   reel — `call_logs` d'un routeur, traceur de decision `*.jsonl`, `executions.db` du planificateur,
   `last_alert`/`last_run` d'un heartbeat, horodatage de tache. Sans trace : `inconnu`, jamais un vert.
4. **Deduire l'etat du ROLE, pas du port ouvert.** Un service qui repond mais dont le dernier passage
   s'est solde par un repli n'est pas `READY` : il est `BLOCKED` tant qu'un appel reel n'a pas
   demontre son role. Un composant non surveille ne recoit jamais `READY` par defaut.
5. **Rapport calibre sur `templates/rapport-etape.md`** : bloc `READY / DEGRADED / FAILED / BLOCKED /
   RISQUES / MODIFICATIONS`, puis preuve de non-modification, puis proposition de l'etape suivante
   soumise au GO. **STOP.**
6. **Apres le GO, une correction a la fois**, chacune avec son backup, sa preuve par mesure (pas par
   code de sortie) et sa re-verification de non-regression. Cinq temps a ne pas sauter :
   1. **Completer le backup avant d'ecrire** (cf. « Backup horodate + retour possible ») : tout fichier
      touche, meme absent de la liste du plan, entre dans le lot ou se declare en rollback documentaire.
   2. **Valider une constante par REPLAY avant de la changer** : rejouer les decisions deja consignees
      sous l'ancienne et la nouvelle regle donne la distribution avant/apres (acceptees, abstentions,
      accords avec la decision de reference) sans un seul appel paye ; consigner aussi ce que la
      constante achete en DESACCORDS et nommer le cas gagne. Detail de la recette :
      `references/diagnostic-composant-distant.md`, section 4.
   3. **Verifier le RESULTAT ATTENDU du plan par mesure et rapporter l'ECART.** Un correctif applique sur
      une premisse fausse ne produit pas l'effet promis : le rapport dit ce qui a ete applique, ce qui a
      ete mesure, et ce que la mesure contredit — jamais « etape reussie » sur la foi du plan. Meme regle
      pour un chiffre annonce par le plan (cout, quota consomme, duree) : le mesurer avant/apres, ne pas
      le recopier.
   4. **Relancer le producteur REEL de l'etat** — la tache planifiee, pas seulement le module en direct —
      et citer l'horodatage du run qui porte le nouvel etat.
   5. **Verifier ce qui ne devait pas bouger** : taches hors perimetre (etat, dernier resultat, prochain
      declenchement, journal applicatif intact), chemins d'alerte, et lecteurs historiques du fichier
      touche. Un correctif qui franchit son perimetre se declare, il ne se decouvre pas a l'etape d'apres.

## Pieges

- **Attribution des horodatages.** Un `jobs.json`, un `health.json` ou un `state.db` reecrit pendant
  la fenetre de mesure l'est par le planificateur ou la tache de sante, pas par l'agent en lecture
  seule. Relever les horodatages et attribuer explicitement, sinon « MODIFICATIONS: 0 » est
  indemonstrable et l'agent semble avoir touche ce qu'il devait seulement lire.
- **Une tache planifiee `Enabled` sans declencheur ne demarre jamais**, et son `LastTaskResult` vaut
  `0` quand le lanceur est `wscript.exe` — meme si le programme lance meurt aussitot. Statuer sur un
  service avec deux faits seulement : aucun listener sur son port, et la commande lancee qui n'existe
  plus. Un `LastTaskResult` de `267009` sur une tache longue est une instance en cours, pas un echec.
- **Un service decrit dans le README n'est pas un service vivant.** Verifier que la sous-commande ou
  le binaire lance existe encore (aide du CLI, `--help`) avant de conclure « attendu mais absent ».
- **Un masquage trop large detruit la preuve** : un motif `sk-…` matche a l'interieur d'un nom de
  dossier et remplace un chemin reel par `[REDACTED]`. Ancrer le motif, exiger une longueur realiste,
  et masquer par NOM DE CLE plutot que par contenu — relire le journal avant de le publier.
- **Inventaire de ports** : `netstat` localise ne rend pas ce qu'on attend ;
  `Get-NetTCPConnection -State Listen` donne adresse, port et PID sans parsing, et les binds publies
  par Docker se lisent dans la colonne `PORTS` de `docker ps`.
- **Ne pas conclure d'un etat « actif »** : un plugin liste dans la config, une tache `Ready`, un
  drapeau `enabled` ne disent rien de l'execution. Chercher la trace d'execution avant d'ecrire
  « actif », et un `inconnu` assume vaut mieux qu'un vert non prouve.
- **Un balayage de motif sur la racine Hermes noie le resultat dans les caches.** Un `grep` d'un nom de
  port ou de composant y ramasse des dizaines de milliers de faux positifs : tables de tokens des caches
  de modeles (`data/**/hf_cache/**/vocab.json`, `tokenizer.json`), runtimes embarques
  (`hermes-agent/.hermes-runtime/`, `.venv.retired-*`, `installs/`), journaux d'appels d'un routeur
  (`~/.omniroute/call_logs/**`). Mesure : 650 Ko de sortie, tronquee, et le vrai resultat perdu. Borner
  le parcours en Python avec une liste `SKIP_DIRS` + extensions utiles, et ne rapporter que les fichiers
  qui portent une decision (code, lanceur, job, config, doc).
- **Un composant se classe en CONSOMMATEUR, PRODUCTEUR ou RESIDU — les trois ne se valent pas.**
  Aucun appel sortant vers le service (aucun client, script, job, plugin) = aucun consommateur : c'est
  la seule preuve qui autorise « obsolete ». Un script d'installation ou de restauration qui recree la
  tache, un lanceur, un `.vbs` = des PRODUCTEURS : ils ne consomment rien, mais ils ressuscitent le
  composant au prochain bootstrap — les nommer et proposer leur correction, sans y toucher. Une entree
  ecrite par le composant lui-meme dans un registre d'execution (ledger de spawn, table de session,
  ligne d'historique) avec un PID MORT = un RESIDU, pas une dependance ; le verifier par une mesure
  (`Get-Process -Id <pid>`), jamais par la lecture du registre seul.
- **Un nom de tache planifiee ACCENTUE ne se sonde pas par egalite stricte.** Un `.ps1` ecrit en UTF-8
  sans BOM est relu en ANSI par Windows PowerShell : `Get-ScheduledTask -TaskName 'Laya - serveur
  décision local'` rend `$null` et la tache est rapportee ABSENTE alors qu'elle tourne — faux negatif
  qui declare en panne un composant sain. Confirmer par un filtre ASCII
  (`Get-ScheduledTask | Where-Object { $_.TaskName -like '*Laya*' }`) ou par
  `schtasks /query /fo csv /nh | grep -a -i laya` : la sortie de `schtasks` n'est pas forcement de
  l'UTF-8 (UTF-16LE ou cp1252 selon le FORMAT demande, cf. skill `windows-path-handling` Regle 6), donc sans
  `-a` le terminal repond « Binary file (standard input) matches » au lieu des lignes.
- **Un repli enregistre n'est PAS forcement une panne.** Le champ de verdict d'une trace
  (`source: "regex"`, `state: "fallback"`) est ecrit par le code APPELANT, qui confond couramment
  « le decideur a repondu mais sous le seuil » avec « le decideur n'a pas repondu ». Trancher par la
  FORME de l'entree, pas par son libelle : presence des champs qui n'existent que sur le chemin
  succes (probabilites detaillees, confiance, latence du service) et ABSENCE de la cle d'erreur
  (`raison: "<service>_down"`, `erreur`). Puis derouler les causes et les ELIMINER une a une : seuil
  local (lire la constante dans le consommateur) -> quota distant (sonde de lecture du fournisseur,
  cf. `references/diagnostic-composant-distant.md`) -> timeout (latence mesuree contre le timeout
  configure) -> erreur de payload (code HTTP). Une confiance de 0,37 pour un seuil de 0,65 est une
  ABSTENTION du modele, pas une panne d'infrastructure : le rapport doit dire laquelle des deux,
  sinon l'etape suivante repare ce qui n'est pas casse.
- **L'etat d'un health check se lit dans SON code avant de se lire dans ses mesures.** Un critere
  ecrit en dur (drapeau `... = False`) ou calcule sur la SEULE derniere ligne de trace explique un
  `BLOCKED` definitif mieux que n'importe quel releve : aucune mesure ne peut alors en faire sortir le
  composant. Le rapport expose le critere, l'attribue a la conception (et non au service), et propose
  l'ARBITRAGE du critere ; il ne propose pas de « reparer » le service.
- **Ajouter un bloc a un journal en AJOUT SEUL ne se fait pas avec l'outil d'ecriture de fichiers**
  (il remplace tout le fichier). Ecrire un petit script qui ouvre la cible en `"a"` avec
  `encoding="utf-8"` et le lancer : c'est la seule forme qui garantit les lignes precedentes intactes.
  Preuve = couple taille + SHA256 avant/apres, plus la relecture de la queue du fichier. Piege du
  script : le texte ajoute porte des accolades (exemples JSON, dictionnaires de probabilites) et
  `str.format()` leve alors `KeyError` sur la premiere d'entre elles — utiliser
  `.replace("<jeton>", valeur)`, ou une concatenation.

- **Un filtre de processus par mot-cle fabrique des faux positifs, et sa sortie porte des secrets.**
  `CommandLine` contient des jetons passes en argument : ne jamais l'imprimer. Le filtrer par sous-chaine
  est pire : « rag » matche `storage`/`fragment`, un motif de 6 caracteres remonte 150 lignes parasites sur
  12 utiles et noie les vraies cibles. Filtrer sur `ExecutablePath` ou sur un motif ancre (`\b`), et
  n'imprimer que nom + PID + memoire + mot-cle matche. Un pool nomme par un chemin d'outillage
  (navigateur du runtime en cours de mission, venv d'un service surveille) n'est pas un candidat a la
  fermeture : le nommer comme tel, avec sa somme.
- **Une ressource annoncee « a liberer » doit etre mesuree, pas supposee gaspillee.** Le cache standby
  (`StandbyCache*Bytes`) est compte DANS la memoire disponible : le vider ne libere rien de mesurable, ne
  reduit aucun backup, et RAMMap / EmptyStandbyList sont des outils tiers a ne pas installer sans GO
  explicite. Meme regle pour la VRAM : un GPU a 0 % d'utilisation n'a rien a rendre, et la memoire par
  processus sort en `[N/A]` sur les pilotes grand public en WDDM — seul le total `--query-gpu` est
  chiffrable. Le rapport dit lequel des deux cas il a mesure, et chiffre la memoire disponible avant/apres
  au lieu d'affirmer une liberation.
- **Classer les processus par working set ET par memoire privee.** Un service qui mappe plusieurs Go hors
  du working set affiche ~66 Mo en WS pour ~4 Go de prive : un classement par WS seul rate le plus gros
  consommateur et presente une machine tranquille. Les deux colonnes, et la somme par famille plutot que le
  top 10, sont ce qui rend la liste de cibles utilisable.

## Files

- `templates/rapport-etape.md` — squelette du rapport de fin d'etape (blocs d'etats, preuve de
  non-modification, proposition d'etape suivante).
- `references/retrait-composant.md` — recette d'un retrait formel sans suppression : preuve d'absence
  de consommateur, desactivation reversible (tache planifiee + backup XML), retrait d'allowlist en
  dernier, mise a jour de la documentation, validation, rollback et classement des references restantes.
- `references/diagnostic-composant-distant.md` — diagnostiquer un composant qui depend d'un service
  distant (decideur LLM, API a quota) : niveaux de preuve sans appel payant, forme des entrees de trace
  (succes contre echec), sondes de quota en lecture seule, seuils cote consommateur, plugin active
  contre handler inactif, et comment compter l'usage reel avant de conclure que le composant sert.
- `references/reecriture-message-commit.md` — mission « changer UNIQUEMENT le message d'un commit
  deja fait » : localisation de la cible, amend par `-F` (message en fichier hors depot),
  `--cleanup=verbatim`, preuve de non-changement par egalite des hash d'arbre, porte de push /
  `--force-with-lease`, point de rollback et pieges (index stage, commit non-HEAD).
