---
name: windows-file-forensics
description: "Use when a file vanished and the cause must be proven."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [forensics, windows, usn, incident, preuves, lecture-seule]
    related_skills: [windows-path-handling, windows-ops, hermes-stack-audit]
---

# Forensique fichier Windows — instruire un incident passe

Reconstituer ce qui est arrive a un fichier, un dossier ou un arbre : deplace ou supprime, quand, par
quel type de processus — et le rapporter avec des preuves citables. Mission type : « des fichiers ont
disparu entre 13:58:19 et 13:58:56, cause inconnue ».

## When to Use

- Un fichier ou un dossier a « disparu », change de contenu ou d'emplacement sans explication.
- Une mission lecture seule qui exige « cause identifiee ou hypotheses classees par probabilite, avec
  les preuves (fichier, ligne, log) ».
- Un rapport anterieur affirme quelque chose sur un incident et il faut le verifier, pas le croire.
- Un fichier suivi disparait du disque et apparait en ` D` dans `git status` (arbre de profil, `skills/`) :
  prouver l'archivage avant de parler de perte.
- Pour un audit de sante Hermes/Windows sans incident : `hermes-stack-audit`, `windows-ops`.

## Regles durables

- **Deplace n'est pas supprime.** Un `mv` et un `rm -rf` laissent la meme impression : listing vide,
  fichiers introuvables, aucune erreur. Ne jamais ecrire « supprime », « perdu » ou « vide » sans un
  enregistrement de suppression au journal USN ET l'absence de l'arbre a sa destination.
- **Le deplacement est l'hypothese par defaut tant qu'elle n'est pas ecartee** : chercher l'arbre
  ailleurs (dossier parent receveur, `%TEMP%`, stash maison) avant de parler de perte.
- **Une preuve = un artefact citable** : enregistrement USN horodate, `queryfileid`, CreationTime, id
  d'evenement, ligne de log, ligne du `state.db`. Un raisonnement n'est pas une preuve.
- **Encadrer l'auteur, ne pas l'inventer.** Si 4104/4688/4663 ne sont pas journalises sur l'hote,
  l'acteur reste « type de processus + heure » et ca se dit tel quel. Une attribution inventee coute
  plus cher que l'aveu d'incertitude.
- **Lecture seule = aucune ecriture d'agent**, mais le runtime Hermes ecrit ses propres caches dans
  `cache/` a chaque demarrage de process (tampon `.last_prune`, `banner_snapshot.json`,
  `mcp_schema_cache.json`). Le declarer dans l'en-tete du rapport : « aucune ecriture » sans cette
  nuance est faux au premier `ls` de l'utilisateur.
- **Rapport avant correctif.** La mission se termine par le rapport et un STOP : aucun correctif,
  aucun git, meme quand la cause est identifiee et la reparation evidente. Les risques residuels se
  listent, ils ne se traitent pas.
- **Un chiffre annonce par un rapport anterieur se re-mesure contre la source, pas contre le rapport.**
  Un fichier d'etat annexe (jobs cron, index, caches) ne fait que grossir et garde ses entrees
  desactivees : deux comptes contradictoires peuvent etre tous deux vrais a leur date. Trancher par le
  contenu (ensembles de noms, horodatages) et par les copies horodatees, jamais par le chiffre. Le
  **perimetre** se re-mesure aussi : « skills/ hors index = 3 » peut etre exact ET laisser 81 suppressions
  ailleurs dans l'arbre. Compter `git status --porcelain` par categorie (` M` / ` D` / `??`) avant
  d'accepter un etat de depot annonce — un chiffre porte sur un sous-arbre, pas sur le depot.

## Procedure

1. **Photographier l'etat actuel** avant tout : contenu et nature du dossier (entrees de premier
   niveau, recursif, tailles, modes), et son statut git (`git check-ignore -v`, `git ls-files`) — un
   arbre non versionne ne se restaure pas par git, et ca change la conclusion.
2. **Chercher la trace retroactive** au journal USN (NTFS) : renommages (deplacements), creations,
   suppressions de la fenetre. Codes de raison et bornes : `references/recettes-preuves.md`.
3. **Relier les FRN du journal aux chemins** avec `fsutil file queryfileid "<chemin>"`. Sans cette
   etape le journal ne dit rien d'exploitable.
4. **Trancher suppression / recreation / deplacement** par les heures de creation du dossier et de ses
   enfants : un enfant qui garde sa CreationTime ancienne prouve que le parent n'a pas ete supprime
   recursivement (une suppression emporte les enfants).
5. **Localiser la destination** par les mtime des dossiers parents sur la fenetre de l'evenement.
6. **Compter l'arbre a sa nouvelle place** et le rapprocher du listing d'origine : « deplace, pas
   perdu » ne se dit qu'apres cette mesure.
7. **Encadrer l'auteur** : instant de lancement d'un processus via les journaux d'evenements, apres
   avoir etabli la cadence habituelle des scripts planifies ; verifier quels journaux d'attribution
   sont actifs avant de promettre un nom.
8. **Rejouer ce qu'une session precedente a observe** quand un rapport anterieur est en cause
   (`state.db` en `mode=ro`) plutot que d'en discuter la formulation.
9. **Rendre le rapport et s'arreter** : etabli / ecarte / hypotheses par probabilite decroissante,
   plus les risques residuels (durabilite de l'emplacement ou l'arbre a ete deplace). Redater l'etat
   de l'arbre AU MOMENT du rapport : un releve du debut de mission est un instantane, pas un constat.

## Un ` D` dans git n'est pas une suppression : prouver l'archivage du curateur

Un fichier suivi qui disparait du disque se lit ` D` dans `git status`. Dans un arbre de profil Hermes, la
cause la plus frequente n'est PAS une suppression : le curateur d'arriere-plan ARCHIVE un skill en le
DEPLACANT vers `<skills>/.archive/<skill>/`. Rien n'est detruit, mais git ne voit que la disparition.
Preuve, dans cet ordre, avant toute restauration :

1. **Le dossier d'arrivee existe-t-il ?** Lister `<skills>/.archive/` et ses dossiers dates (mtime du
   jour des vagues d'archivage), compter ses fichiers.
2. **Le ledger documente-t-il le deplacement ?** `.curator_ledger.jsonl` porte des entrees
   `action:"archive"`, `actor:"curator"`, avec une paire `before[]`/`after[]` de `{path, sha256}`. Un
   deplacement authentique a le MEME sha256 avant et apres, et le chemin d'arrivee existe sur disque
   avec ce sha.
3. **Croiser programmatiquement** les chemins ` D` avec le ledger : couverts / fichier d'arrivee
   present / sha identique. Attendre N/N et nommer tout ecart. `scripts/prouver-archivage-curateur.py`
   fait ce croisement (code de sortie 3 au premier ecart).
4. **Corroborer par le resume du run** dans `<skills>/.curator_state` : `last_run_summary` annonce le
   nombre d'archivages (« auto: N marked stale, M archived »), `run_count` et `last_run_at` donnent
   l'historique.

- **Ne jamais conclure par comparaison a HEAD.** La copie archivee differe presque toujours de
  `git show HEAD:<chemin>`, et ca ne prouve RIEN : le contenu deplace est de la derive runtime non
  committée, donc plus RECENTE que HEAD (mtime des sources anterieurs, contenu enrichi apres le dernier
  commit du chemin). La reference qui prouve un deplacement est le couple `before`/`after` du ledger,
  pas HEAD. Annoncer « N ecarts vs HEAD » sans le qualifier fait passer une derive pour une perte.
- **Un arbre `profiles/*/skills/` peut etre a MOITIE dans git.** Une regle `.gitignore` sur
  `profiles/*/skills/` n'arrete pas le suivi des fichiers deja indexes : les suppressions apparaissent en
  ` D` alors que les copies `.archive/` (non suivies ET ignorees) ne produisent AUCUN `??`. Un
  `git status -uall` sans fichier non suivi, alors que le disque en compte plus que l'index, est donc
  normal : recompter par `find` + `git ls-files`, pas par `git status`.
- **Le nom du skill n'est pas toujours a la position N du chemin.** Un skill a la racine de l'arbre (pas
  de dossier de categorie) decale tout decoupage positionnel (`awk -F/`, `$4"/"$5`) et fabrique un faux
  skill nomme d'apres le fichier. Extraire le nom en le comparant au dossier connu, jamais par index de
  champ.
- **Prouve ne veut pas dire committe.** Une fois le deplacement etabli, l'action proposee est un commit
  unique qui nomme le ledger et les vagues (git cesse de porter des fichiers fantomes) ; la restauration
  (`git checkout --`, qui remet la version de HEAD et recree l'ecart avec `.archive/`) est l'action
  INVERSE, a proposer et non a decider.

## Pitfalls

- **`grep` sans `-a` sur un flux binaire** (journal USN, sorties d'outils Windows) repond
  `Binary file (standard input) matches` : ce n'est pas « motif absent », c'est un flux non textuel.
  Refaire avec `grep -a` avant de conclure.
- **Le journal USN est une fenetre glissante** (bornes par `fsutil usn queryjournal C:`) : au-dela,
  l'evenement est sorti du journal. Le dire, au lieu de conclure « rien ne s'est passe ».
- **Le journal ne porte ni chemin ni PID.** Toute conclusion nominative exige FRN ↔ `queryfileid`,
  et l'attribution d'un processus passe par un autre journal.
- **Un dossier dont la CreationTime est recente n'est pas forcement neuf** : c'est aussi le point
  d'atterrissage d'un deplacement. Discriminer par les enfants.
- **Chercher un dossier par son nom sur tout le disque est le dernier recours** : les mtime des
  parents donnent la destination en une commande, sans bruit.
- **Ne pas prendre le bruit interne de Windows pour l'auteur** (taches `OneSettings RefreshCache`,
  `taskhostw`, nettoyeurs du systeme) : filtrer sur la seconde concernee.
- **`%TEMP%` n'est pas durable** : les nettoyeurs (SilentCleanup / Storage Sense, FluentCleaner)
  purgent ce dossier. Un arbre « mis de cote » la est a risque — constat a rapporter.
- **Un arbre restaure un cran trop bas dans `cache/scratch` devient une ENTREE UNIQUE**, supprimee
  en bloc par l'elagage Hermes apres 24 h sans ecriture (`hermes_constants.py` →
  `hermes_constants_scratch.prune_idle_entries`, `SCRATCH_MAX_IDLE_HOURS`).
- **Ne pas choisir un chiffre quand deux comptes s'opposent** : comparer les ENSEMBLES (noms, ids) a
  la copie horodatee la plus ancienne disponible et rapporter « 0 retire / N ajoute » plutot qu'une
  valeur unique. Pour les jobs cron : `cron/jobs.json` (champ `jobs`, `updated_at`), copies dans
  `cron.bak.*/jobs.json`, `state-snapshots/<ts>-pre-update/cron/jobs.json` et
  `data/*/backups/*/jobs.json` ; `enabled` + `state` sont la verite d'execution (`next_run_at`
  reste pointe sur l'heure suivante quand le job est en pause), et chaque profil a son propre
  `profiles/<p>/cron/jobs.json` — un « total » doit dire de quel home il parle.

- **L'arbre peut repartir apres le rapport.** Une remise en place hors bande peut elle-meme etre
defaite : un arbre restaure un cran trop bas dans `cache/scratch` a ete remonte a sa place quelques
minutes plus tard, sans trace dans les sessions. Recompter avant chaque conclusion et ne jamais
presenter le placement comme definitif.
- **L'heure du premier echec d'une commande est un releve de disparition.** Le shell garde le
repertoire courant de la session : si le dossier a ete deplace pendant la session, la commande
suivante echoue sur son `cd` avant d'avoir tourne. C'est une preuve horodatee gratuite (cf.
`windows-path-handling`, remede `workdir=`).

## Files

- `references/recettes-preuves.md` — commandes verifiees : journal USN (codes de raison, bornes),
  heures de creation, fenetres de mtime, ids d'evenements d'attribution, relecture de `state.db`.
- `scripts/prouver-archivage-curateur.py` — croise les suppressions ` D` d'un arbre de profil avec
  `.curator_ledger.jsonl` : couverture, existence de la destination, sha256 identique, et le contraste
  explicite « vs HEAD » (derive, pas perte). Sortie 0 = deplacement prouve, 3 = ecart a nommer.
