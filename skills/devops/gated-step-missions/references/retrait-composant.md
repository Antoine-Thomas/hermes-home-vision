# Retrait formel d'un composant, sans suppression

Le retrait est une operation de PERIMETRE, pas de menage : on retire un composant du perimetre
surveille/decrit, on ne supprime ni fichier, ni tache, ni lanceur, ni historique. Repond a
« retire X de l'architecture » / « X ne fait plus partie du perimetre » en gardant tout reversible.

## 1. Prouver l'absence de consommateur AVANT d'ecrire

Deux bouts a verifier, sinon le retrait est un pari :

- **Aucun appel sortant** : balayer le code, les scripts (`.ps1` / `.vbs` / `.cmd`), les jobs cron, les
  configs de profils, les plugins, les `.env` (noms de variables seulement). Borner le parcours
  (cf. SKILL.md, piege du balayage qui noie le resultat dans les caches de modeles).
- **Aucun PRODUCTEUR oublie** : un script de bootstrap/restauration qui recree la tache, un lanceur,
  un `Register-ScheduledTask` — ils ne consomment pas, mais ils ressusciteront le composant. Les
  nommer dans le rapport comme « producteurs restants », sans les modifier.
- **Residus** : un registre d'execution (ledger de spawn, `state.db`, table de session) peut contenir
  une ligne portant le port/PID. La verifier : PID mort = residu, pas dependance.
- L'entree d'`allowlist` d'un moniteur de ports ne prouve RIEN : elle tolere, elle n'exige pas.
  Idem une mention de README ou un ancien rapport d'audit.

Le composant ne se declare obsolete que sur la conjonction : aucun consommateur mesure ET une decision
DATEE du proprietaire (la sienne, citee avec sa source). Sinon : `BLOCKED` + question.

## 2. Desactiver plutot que supprimer (tache planifiee Windows)

```bash
# backup : exporter la definition de la tache ALORS qu'elle est encore fonctionnelle
BKDIR="$LOCALAPPDATA/hermes/backups/<NOM>_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BKDIR"
schtasks /query /tn "<Nom de la tache>" /xml > "$BKDIR/tache_<nom>.xml"   # chemin natif, hors guillemets simples de bash
powershell -NoProfile -ExecutionPolicy Bypass -File <script>.ps1           # Disable-ScheduledTask ne passe pas en inline
```

```powershell
# dans le .ps1 : desactiver, puis relire l'etat REEL
Disable-ScheduledTask -TaskName '<Nom de la tache>' | Out-Null
$t = Get-ScheduledTask -TaskName '<Nom de la tache>'; $i = $t | Get-ScheduledTaskInfo
'State={0} Enabled={1} declencheur={2} dernier={3} rc={4}' -f $t.State, $t.Settings.Enabled,
  ($t.Triggers | ForEach-Object { $_.CimClass.CimClassName }), $i.LastRunTime, $i.LastTaskResult
```

- Attendu apres : `State=Disabled`, `Enabled=False`, **declencheur conserve**, **historique conserve**
  (`LastRunTime` / `LastTaskResult` non remis a zero). Un `State=Disabled` avec historique vide est le
  signe qu'on a supprime puis recree, pas desactive.
- Rollback : `Enable-ScheduledTask -TaskName '<Nom>'` (ou reimport du XML exporte).
- Les fichiers du lanceur restent en place : les citer dans le rapport (chemin + taille) comme preuve de
  non-suppression.

## 3. Retirer l'entree d'allowlist EN DERNIER

Ordre impose : desactiver d'abord, retirer l'entree ensuite. Fait dans l'autre sens, la surveillance
crie sur un port qui est encore ouvert par le service — un faux positif avant meme que le retrait soit
applique.

- Editions chirurgicales d'un JSON : retirer la ligne exacte (`"    9119,\n"`) et **revalider**
  (`json.loads`) avant d'ecrire. Un `json.dump` complet reformate tout le fichier et rend le diff
  inverifiable.
- Relever avant/apres : nombre d'entrees (30 -> 29), SHA256, et l'absence de modification des AUTRES
  cles (`process_allowlist`, `ephemeral_min/max`, cles racine).
- Dire l'EFFET DE BORD voulu : la surveillance compare desormais les ports en ecoute a cette liste, donc
  une reapparition du port declenchera une alerte au lieu d'etre toleree. Citer le fichier et la ligne
  qui lit la liste (`<moniteur>.py` L<n>, `cfg["ports"]["allowlist"]`).

## 4. Documentation : corriger, puis affirmer le retrait

- **Schemas ASCII a largeur fixe** : remplacer le contenu de la case en CONSERVANT sa largeur (compter
  les caracteres du gabarit, ex. 15 entre les `│`) ; re-titrer la case sur ce qui reste (CLI, dashboard)
  et y ecrire la mention du retrait. Un remplacement direct decale tout le cadre.
- Citer les emplacements par nature : schema d'architecture, prose « les N couches », liste « services
  communs », **ordre de demarrage**, procedure de mise a jour (`docs/*VENVS*`, scripts de bootstrap).
- Une procedure d'update qui portait « arreter/relancer le composant » devient « sans objet » : la
  reecrire, pas la laisser avec un renvoi.
- Porter la phrase explicite : « <composant> n'appartient plus a l'architecture <NOM> ».
- Le document de proposition de retrait recoit une section « APPLIQUE » (date, tableau action/etat/preuve,
  backups, avant/apres SHA256, rollback) : la proposition et l'etat reel ne doivent pas diverger.
- **Distinguer les mentions HISTORIQUES** (rapport d'audit ancien, constats dates, libelles de videos) :
  elles ne se reecrivent pas — les lister dans le rapport comme « references restantes » et laisser le
  proprietaire decider. Reecrire l'histoire d'un document date est une falsification de trace.

## 5. Valider, puis journaliser

Validation minimale, chaque point mesure et jamais deduit :

- `Get-NetTCPConnection -State Listen` (ou `netstat`) : plus aucun listener sur le port.
- `Get-ScheduledTask` : tache PRESENTE + `Disabled` ; `Get-ScheduledTaskInfo` : historique conserve.
- Balayage du motif sur jobs cron, configs, config du moniteur, README, docs : classer chaque occurrence
  restante (producteur / doc stale / historique) et affirmer « aucun consommateur actif ».
- Non-regression des services voisins : une sonde par service (code attendu, `401` pour un service
  protege) + les taches interdites relues (`State`, `rc`, `NextRunTime`).
- Journal (ajout seul) : verifications prealables, action par action, dossier de backup, SHA256
  avant -> apres, validation, references restantes, rollback, et le verdict d'etape.
