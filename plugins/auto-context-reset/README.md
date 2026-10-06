# auto-context-reset

Plugin Hermes : detecter la saturation de contexte et agir sans intervention humaine.

## Ce qu'il fait

| Hook | Role |
|---|---|
| `post_auxiliary_call` | Un appel de compression qui sort en erreur, ne rend AUCUN texte, ou depasse `duree_suspecte_s` sans rien produire = incident. |
| `api_request_error` | Une erreur de fenetre cote fournisseur (`context length`, `maximum context`, `too long`...) = saturation dure. |
| `pre_llm_call` | Injectable une seule fois : un avis `<auto_context_reset>` dans le contexte du modele, avec le chemin du handoff et les 4 actions a faire. |

Effets de bord a chaque incident : une ligne JSONL dans
`<HERMES_HOME>/logs/auto-reset.log`, et au seuil `seuil_echecs` un **handoff
durable** `<HERMES_HOME>/handoffs/<session>_<horodatage>.md` (metadonnees de
session + etat de compression lus en lecture seule dans `state.db`, derniers
messages actifs, commandes de reprise).

## Ce qu'il ne peut pas faire

Forcer `/new` : aucun hook Hermes n'expose de directive de reinitialisation
(`VALID_HOOKS` dans `hermes_cli/plugins.py` — seuls `pre_tool_call` (blocage) et
`pre_llm_call` (injection) transforment quelque chose). Le plugin rend donc
l'action evidente (handoff + avis) au lieu de la declencher.

## Reglages (`plugins.entries.auto-context-reset.settings`)

    mode               bool   true = actif (defaut)
    seuil_echecs       int    1 = incident unique suffisant pour ecrire le handoff
    duree_suspecte_s   float  120 : au-dela, un appel de compression sans sortie est un etouffement
    notify_every_s     float  600 : delai minimal entre deux avis pour la meme session
    dernieres_messages int    12  : messages actifs recopies dans le handoff
    message_chars      int    400 : troncature de chaque message recopie
    ecrire_handoff     bool   true
    handoff_dir        str    vide = <HERMES_HOME>/handoffs
    log_path           str    vide = <HERMES_HOME>/logs/auto-reset.log

## Commandes

    hermes auto-context-reset status
    hermes auto-context-reset check
    hermes auto-context-reset simuler --n 2
    hermes auto-context-reset simuler --session <id> --n 3
    hermes auto-context-reset off | on

## Tests

    hermes-agent/venv/Scripts/python.exe tests/test_hook.py    # 33 assertions, aucun reseau

Le plugin est fail-open : toute erreur interne est avalee (`logger.debug`) et
retourne `None`, un tour ne casse jamais.
