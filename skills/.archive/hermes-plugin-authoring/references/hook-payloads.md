# Charges utiles des hooks Hermes — noms de champs et recettes de test

Les noms de champs ne sont PAS documentes dans l'aide : les lire dans le
constructeur, a cote du `invoke_hook`.

## `post_auxiliary_call` — `agent/auxiliary_hooks.py`

Emis une fois par TENTATIVE FOURNISSEUR d'une tache auxiliaire (compression,
generation de titre, vision...). Filtrer sur `aux_task`.

| Champ | Sens |
|---|---|
| `aux_task` | tache logique : `compression`, `title_generation`, ... |
| `session_id`, `task_id`, `turn_id`, `api_request_id` | identite |
| `retry_count`, `api_call_count` | relances de cette tentative |
| `model`, `provider`, `base_url`, `api_mode` | cible reellement appelee |
| `streaming` | bool — voir le piege |
| `started_at`, `ended_at`, `api_duration` | `api_duration` en secondes (float) |
| `error`, `error_type` | chaine `"Type: message"` (tronquee a ~2000) ou `None` |
| `finish_reason`, `response_model`, `usage` | `None` si erreur ou flux |
| `assistant_content_chars`, `assistant_tool_call_count` | taille de la reponse |
| `response` | choix + message, assaini |

`pre_auxiliary_call` (meme fichier) porte en plus : `request_messages`,
`system_prompt`, `tool_count`, `approx_input_tokens`, `request_char_count`,
`max_tokens`, `request` (corps assaini).

**Piege** : en erreur ET en flux, le constructeur pose
`assistant_content_chars=0` et `finish_reason=None` **par conception** — une reponse
streamee est rendue NON consommee (README du module : le reassemblage appartient a
l'appelant). Un detecteur « aucun texte == echec » qui ignore `streaming=True`
se declenche sur chaque appel streame reussi. Lire `streaming` AVANT d'interpreter
un contenu vide.

## `api_request_error` — `agent/api_request_hooks.py`

Emis quand un appel du modele PRINCIPAL echoue. Champs : `task_id`, `turn_id`,
`api_request_id`, `session_id`, `platform`, `model`, `provider`, `error_type`,
`error_message`, `status_code`, `retry_count`, `max_retries`, `retryable`, `reason`,
`api_start_time`/`ended_at`/duree.

C'est le hook pour une **saturation dure** (fenetre depassee) : chercher dans
`error_message` les signatures `context length`, `maximum context`,
`context_length_exceeded`, `context window`, `too many tokens`, `reduce the length`,
`prompt is too long`, `input is too long`. Un `429 rate limit` n'est PAS une
saturation — ne pas le classer comme tel.

## `pre_llm_call`

`session_id`, `user_message`, `conversation_history`, `is_first_turn`, `model`,
`platform`. Retour attendu pour injecter : `{"context": "<texte>"}`. Ignorer les
messages commencant par `/` (commandes de session) : y injecter un avis n'a aucun
sens et brouille l'affichage.

## Recette : simuler un evenement par le VRAI dispatcher

Teste le plugin charge par le vrai loader, seule la charge utile est fabriquee.
Interpreteur : voir `windows-path-handling` (Regle 3) — le `python.exe` du venv
Hermes rejoue le script avant `site-packages` et fait croire a des dependances
manquantes.

    for _p in (r"...\hermes-agent\venv\Lib\site-packages", r"...\hermes-agent"):
        sys.path.insert(0, _p)
    from hermes_cli.plugins import discover_plugins
    discover_plugins()
    from hermes_cli import lifecycle
    lifecycle.invoke_hook("post_auxiliary_call", aux_task="compression", session_id=SID,
                          model="<modele>", provider="<provider>", streaming=False,
                          api_duration=300.0, error=None, error_type=None,
                          finish_reason=None, assistant_content_chars=0,
                          assistant_tool_call_count=0)
    r = lifecycle.invoke_hook("pre_llm_call", session_id=SID, user_message="...",
                              conversation_history=[], is_first_turn=False)

Controles qui ont de la valeur : le fichier produit apparait, le journal gagne une
ligne par incident (+ une par fichier), l'avis est injecte UNE fois, pas reinjecte
au tour suivant, pas injecte sur `/new`, et un evenement hors sujet (autre
`aux_task`) ne produit AUCUN bruit.

## `state.db` en lecture seule

    sqlite3.connect("file:<HERMES_HOME>/state.db?mode=ro", uri=True)

- `sessions` : `id`, `title`, `model`, `cwd`, `started_at`, `ended_at`, `end_reason`,
  `message_count`, `tool_call_count`, `billing_provider`, `estimated_cost_usd`, et
  l'etat de compression deja calcule par Hermes : `compression_failure_error`
  (ex. `backoff:stall_interrupted:strategy=lean:...:model=<modele>`),
  `compression_failure_cooldown_until`, `compression_fallback_streak`,
  `compression_ineffective_count`, `compression_overload_streak`,
  `compression_recovery_deadline`.
- `messages` : `session_id`, `role`, `content`, `timestamp`, `active` —
  `WHERE session_id=? AND active=1 ORDER BY id DESC LIMIT n`.
- Un fichier de reprise bati sur ces deux tables est reellement exploitable apres un
  `/new` (metadonnees de session + derniers messages + commande de reprise). Le plugin
  l'amorce, l'AGENT le complete : chemins absolus, restes a faire, mesures a ne pas
  refaire, commandes exactes.
- `hermes -c` et `session_search(session_id=...)` sont les deux portes de reprise a
  citer dans le fichier.
