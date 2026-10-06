<!-- Extrait de hermes-operations/SKILL.md, lignes 816-913 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Cron d'un profil : créer, tester, vérifier

Un job appartient à **un profil** : `hermes -p <profil> cron …`. Le créer depuis le profil qui doit le
porter, jamais depuis `default` en supposant qu'il hériterait des deux.

```bash
hermes -p <profil> cron create "0 8 * * 1" "$(cat prompt.txt)" \
  --name <nom> --deliver telegram --skill <skill>
hermes -p <profil> cron status        # ✓ Gateway is running + Ticker heartbeat = le job partira
hermes -p <profil> cron run <job_id>  # test immédiat, part au tick suivant (< 1 min)
```

- Passer le prompt par un **fichier** (`--skill` ne remplace pas les consignes) : il part sans aucun
  contexte de session, donc il doit être auto-portant.
- `--deliver telegram` = canal home du profil (`TELEGRAM_HOME_CHANNEL`). Sans gateway vivant, pas de
  ticker : `cron status` le dit.
- **Attribuer l'echec d'un job : lire son `model`, `provider` et `last_error` dans `cron/jobs.json`.**
  Le champ `model` dit quel combo/alias le job fait tourner (un job pose sur `eco` herite de la
  fragilite du combo) et `last_error` porte l'erreur amont telle quelle — p. ex.
  `[openai/nvidia/nemotron-…] [503]: ResourceExhausted: Worker local total request limit reached
  (16/16)` est un plafond du fournisseur, pas une panne locale a reparer. Le job porte aussi
  `provider`, `base_url`, `script` (`no_agent: true` = pre-run script seul) et `repeat.completed`.
- **Changer le modele d'un job = editer ses deux champs `model` + `provider` dans `cron/jobs.json`**
  (l'override par job prime sur `model.default` du profil) puis revalider le JSON. C'est le geste juste
  pour sortir UN job d'une chaine fragile sans toucher au primaire de tout le parc. Verifier la cible
  avant de l'inscrire : le provider est-il natif (`plugins/model-providers/<nom>/`, alias compris —
  `gemini` a pour alias `google`, env `GOOGLE_API_KEY`) et le modele est-il servi par l'amont
  (`GET .../v1beta/models` cote Gemini, `GET /v1/models` cote routeur) ? Un modele absent de
  `providers.<p>.models` dans `config.yaml` reste utilisable, mais l'y ajouter evite de le croire
  indisponible. Montrer le diff avant d'appliquer, et NOMMER les autres jobs qui partagent le meme
  modele avant de n'en corriger qu'un seul.
- **`cron/jobs.json` est TOUJOURS modifié : le committer seulement si une DÉFINITION change.** Le
  planificateur y réécrit l'état de runtime à chaque tir (`completed`, `next_run_at`, `last_run_at`,
  `updated_at`, `scheduled_at`, `dispatched_at`, `lateness_seconds`) — 24 lignes de diff pour 2 jobs
  sur 14, dont **0** touchant une définition. Le garde-fou est `scripts/cron_jobs_gate.py` (sortie 0 =
  bruit de runtime seul, 1 = définition modifiée, avec les lignes fautives) : ne pas le retaper en
  one-liner — un filtre `^[+-]` sans exclusion des deux lignes d'en-tête du diff (`--- a/…`, `+++ b/…`)
  ne renvoie **jamais** « bruit » et valide tout. Corollaire de comptage : dans un relevé de porcelain,
  la ligne `M cron/jobs.json` **ne compte pas** comme une entrée de dérive.
- **`execute_code` est refusé dans un job cron** : « BLOCKED: execute_code runs arbitrary local Python
  … Cron jobs run without a user present to approve it ». Le job doit passer par `terminal` (+ `write_file`
  pour un payload), pas par Python — un run qui compte sur `execute_code` échoue une fois sur deux.
- **Un job relancé deux fois le même jour produit deux artefacts**, pas un remplacement : SiYuan accepte
  deux documents portant le même titre (ids distincts). Après un test manuel, vérifier et ranger le
  doublon, sinon la note « quotidienne » se dédouble en silence.
- **`Ran now: succeeded` est le résultat du déclenchement, pas la preuve que le travail a abouti.**
  Vérifier l'artefact réel (fichier, note, message), plus la ligne
  `cron.scheduler: Job '<id>': delivered to telegram:<chat_id>` dans `logs/agent.log`, plus le dernier
  message assistant de la session `cron_<job_id>_<stamp>` dans `state.db`.

### Diagnostiquer un run en échec (lecture seule)

- **`cron/output/<job_id>/<AAAAMMJJ_HH-MM-SS>.md`** : écrit même pour un run en échec, avec l'en-tête
  `FAILED`, le prompt COMPLET et la trace exacte — la source la plus directe, à citer de préférence au
  log applicatif.
- `cron/executions.db` (`executions` : `status`, `error`, `delivery_outcome`, `scheduled_instant` ;
  `cron_incidents` : `state`, `error`, `alerted_at`) donne l'historique des tirs que `jobs.json`
  n'a pas. Lire en `mode=ro` : le gateway écrit pendant la lecture.
- **`status=failed` + `delivery_outcome=delivered` coexistent** : l'échec est celui du TRAVAIL, pas de
  l'envoi. Ne pas rapporter « rien n'est parti » sur cette base.
- **Le `RuntimeError: …` d'un job vient de `cron/scheduler.py::_final_response_from_result`**, qui lève
  quand l'agent n'a produit AUCUN message final : le run est classé `cron_incomplete_no_output`. Ce
  n'est ni une panne du modèle ni une panne de livraison — remonter la chaîne d'appels du run.
- **`model: null` dans `jobs.json` = défaut du PROFIL, pas le `model_snapshot`.** Le snapshot est figé à
  la création/dernière édition du job : il décrit l'intention, pas le run. Le modèle réel se lit dans
  `state.db` du profil (`sessions.model` de la session `cron_<job_id>_<horodatage>`) et dans
  `cron/usage_audit.jsonl` (une ligne par tir : `model`, jetons, `error`, `duration_ms`).
- **Un job est un run d'AGENT : sa surface d'outils est `_get_platform_tools(cfg, "cron")`** —
  `from hermes_cli.tools_config import _get_platform_tools`, à exécuter avec le python du venv Hermes.
  `platform_toolsets` ne contient que des RESTRICTIONS par plateforme : l'absence d'une clé `cron` ne
  signifie pas « pas d'outil », et une restriction écrite pour `telegram` ne borne pas les runs cron.
  C'est ce contrôle qui tranche « le job peut-il appeler un script ? ».
- **Le tick se fait dans le processus gateway qui sert le profil** : la ligne
  `Cron scheduler will tick N profile(s): [...]` du `logs/gateway.log` (racine) nomme les profils
  servis, et l'outil terminal d'un run cron hérite de cet environnement (seuls les secrets/credentials
  providers sont retirés du sous-processus). Le lanceur (`gateway-service/Hermes_Gateway.vbs` →
  `wscript` → `tools/python-* -m hermes_cli.main gateway run`) pose `HERMES_HOME` sur la RACINE du home,
  jamais sur le dossier du profil — donc ce qui résout `%LOCALAPPDATA%\hermes` tombe juste depuis un run
  cron d'un autre profil.
- Le CLI n'a **pas** d'équivalent au `StartWhenAvailable` du Task Scheduler : le rattrapage d'un
  déclenchement manqué est le fait du ticker (`catch_up_occurrences`), donc conditionné au gateway
  vivant à cette heure-là. Le dire, ne pas promettre le rattrapage.

### Relire le `state.db` d'un profil (lecture seule)

Le gateway écrit pendant qu'on lit : ouvrir en **read-only**, ne jamais copier ni verrouiller le
fichier live.

```python
sqlite3.connect("file:C:/Users/<user>/AppData/Local/hermes/profiles/<profil>/state.db?mode=ro", uri=True)
```

Schéma utile : `sessions` est indexée par **`id`** (pas `session_id`) et porte `source`, `title`,
`chat_id` ; `messages` porte `session_id`, `role`, `content`, `timestamp` ; `delivery_obligations`
porte `platform`, `chat_id`, `state`, `attempts`, `last_error`. **`delivery_obligations` est vidée
après une livraison réussie** : une table vide ne signifie pas « rien livré » — la preuve d'envoi est
la ligne du scheduler dans `agent.log`.

