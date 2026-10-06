---
name: hermes-plugin-authoring
description: "Use when building a Hermes plugin with hooks."
version: 1.0.0
author: hermes-agent
license: mit
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, plugins, hooks, authoring, devops]
    category: devops
    related_skills: [hermes-provider-config, windows-path-handling, omniroute-gateway]
---

# Hermes plugin with hooks — authoring

Quand l'utilisateur veut que **Hermes lui-meme** reagisse a un evenement interne
(echec de compression, erreur d'appel API, appel d'outil, debut de session) au lieu
d'etre informe apres coup. Un plugin avec hooks est la bonne reponse ; un skill n'est
qu'un document.

## When to Use

- « Je veux que Hermes detecte <evenement> et fasse <action> tout seul. »
- Un besoin d'automatisation interne qui touche `config.yaml`, l'etat de session, ou
  les evenements du cycle de vie d'un tour.
- Un plugin existant doit etre etendu, corrige, ou son detecteur mis au point.

Le detail des charges utiles et le squelette de test sont dans
`references/hook-payloads.md`.

## 1. Ce qu'un hook peut — et ne peut pas — faire

- `ctx.register_hook(nom, fn)` ; `fn(**kwargs)` ; le nom doit figurer dans
  `VALID_HOOKS` (`hermes_cli/plugins.py`) — un nom invente est silencieusement inerte.
- **Seuls deux hooks transforment un tour** : `pre_tool_call` (peut bloquer) et
  `pre_llm_call` (retourne `{"context": "..."}`, injecte dans le contexte du modele).
  Tous les autres sont de l'observation.
- **Il n'existe AUCUN hook de reinitialisation de session.** Ne jamais promettre un
  `/new` automatique : c'est impossible. Le livrable realiste est « detecter +
  preserver le travail + rendre l'action evidente » (avis injecte + fichier de
  reprise ecrit), et le dire dans le rapport au lieu de le laisser croire.
- `pre_llm_call` se declenche au DEBUT d'un tour : un incident en milieu de tour
  produit son avis au tour SUIVANT. Le dire aussi.

## 2. Structure, et fail-open obligatoire

    plugins/<nom>/{plugin.yaml, __init__.py, README.md, tests/test_hook.py}

`plugin.yaml` : `name`, `version`, `description`, `author`, `license`,
`requires_hermes`, `kind: standalone`, `tags`, les listes
`provides_tools`/`provides_hooks`/`provides_middleware` — elles doivent
**correspondre exactement** a ce que fait `register()` — et `config_schema`.

- **Fail-open** : chaque handler dans un `try/except` qui journalise en
  `logger.debug` et retourne `None`. Un hook qui leve ne doit jamais casser un tour.
- Lecture d'etat par le plugin : `sqlite3.connect("file:<chemin>?mode=ro", uri=True)`
  (le gateway ecrit pendant qu'on lit) avec un `timeout` court.
- Ecrire le fichier produit par le plugin par un chemin ABSOLU, jamais relatif au
  repertoire courant du processus (cf. `windows-path-handling`).

## 3. Les noms de champs ne sont PAS documentes — lire le constructeur

`post_auxiliary_call` : `agent/auxiliary_hooks.py` ; `api_request_error` :
`agent/api_request_hooks.py` ; `pre_llm_call` : le payload du tour.
Tables de champs completes dans `references/hook-payloads.md`.

**Piege qui rend un detecteur faux** : en erreur ET en flux, le constructeur pose
`assistant_content_chars=0` et `finish_reason=None` **par conception** (une reponse
streamee est rendue non consommee). Un detecteur « pas de texte == echec » qui ignore
`streaming=True` se declenche sur chaque appel streame correct. Lire `streaming` avant
d'interpreter un contenu vide.

## 4. Reglages du plugin et `config.yaml`

- Lus/ecrits sous `plugins.entries.<nom>.settings.<cle>` via
  `ctx.get_config(cle, defaut)` / `ctx.set_config(cle, valeur)`.
- **YAML 1.1 convertit `on`/`off`/`yes`/`no` en booleens** :
  `hermes config set ... mode on` ecrit `true`. Declarer la cle en `type: bool` dans
  `config_schema` et normaliser dans le code (`on/true/1/yes` -> actif).
  `hermes config set <cle> '"on"'` ecrit la chaine `'"on"'` guillemets compris — a ne
  jamais faire.
- Le type declare dans `config_schema` est verifie au demarrage : un desaccord
  imprime un avertissement a CHAQUE lancement (« should be str (got bool) »).
- `hermes config set` est le SEUL chemin d'edition de `config.yaml` depuis une session
  d'agent : le tool `patch` refuse (garde-fou de securite). Sauvegarder avant
  (`cp config.yaml config.yaml.bak.<motif>_<date>`).
- Une cle imbriquee reelle mais inconnue du schema est ecrite avec l'avertissement
  « not a recognized config key » : verifier dans le code qu'elle est bien LUE avant de
  s'y fier.

## 5. Valider, activer, tester

    hermes plugins validate <dossier>   # manifeste, import, hooks declares == enregistres, scan securite
    hermes plugins doctor <nom>         # contrats du runtime ; « registrations: N hook(s) »
    hermes plugins enable <nom> [--no-allow-tool-override]
    hermes plugins show <nom>

- `enable` ajoute `plugins.enabled` + `entries.<nom>` ; la reponse
  « Gateway reloaded plugins » prouve qu'un gateway en cours l'a pris.
- Avec `plugins.isolation: host`, `ctx.register_cli_command` est cable dans le CLI
  local : `hermes <nom> status` fonctionne. Donner au plugin un jeu de sous-commandes
  `status | check | simuler | on | off`, dont un **`simuler`** qui fabrique N incidents
  et ecrit un VRAI fichier : c'est le test qui prouve toute la chaine sans attendre
  l'incident reel.
- Test hors ligne : charger `__init__.py` par `importlib`, piloter les handlers avec un
  faux `ctx` (get_config/set_config/register_hook). Assertions utiles : regles de
  detection, fail-open sur un ctx casse, fichier ecrit, lignes de journal, avis injecte
  UNE fois, aucune injection sur une commande `/…`.
- Test d'integration sans session vivante : `discover_plugins()` puis
  `hermes_cli.lifecycle.invoke_hook("post_auxiliary_call", **payload_reel)` — vrai
  chargeur + vrai dispatcher, seule la charge utile est fabriquee. Recette et noms de
  champs : `references/hook-payloads.md`.
- Interpreteur pour ces tests : le `python.exe` du venv Hermes rejoue le script avant
  `site-packages` et fait croire a des dependances manquantes — voir
  `windows-path-handling` (Regle 3).

## 6. `state.db`, lecture seule : un signal de premiere main

Avant de parser des logs, regarder l'etat que Hermes persiste deja : la table
`sessions` porte les colonnes de compression (`compression_failure_error`,
`compression_failure_cooldown_until`, `compression_fallback_streak`,
`compression_ineffective_count`, `compression_overload_streak`,
`compression_recovery_deadline`), et `messages` est filtrable par `session_id` avec
`active=1`. Details dans `references/hook-payloads.md`.

## Pitfalls

- Un plugin qui _journalise seulement_ ne resout rien : detecter sans ecrire de quoi
  reprendre le travail laisse l'utilisateur au meme point. Ecrire un fichier (chemins
  ABSOLUS, restes a faire, commande de reprise) et injecter un avis.
- Ne pas compter sur `plugins show` pour verifier une commande CLI : il affiche
  `Listens: (none)` et le chemin d'execution, pas la sous-commande. La preuve est
  `hermes <nom> status` qui s'execute.
- Un seuil de declenchement trop haut rend le plugin inutile : sur un incident qui a
  deja coute des minutes, l'avis doit partir au PREMIER incident, avec un anti-spam par
  session (re-injection au plus toutes les N minutes), pas un compteur eleve.
- Ne pas confondre « le hook ne se declenche pas » et « le nom est mauvais » : verifier
  d'abord que le nom figure dans `VALID_HOOKS`, puis que `validate` voit le hook declare.

## Voir aussi

- `windows-path-handling` — chemins, shell, et l'interpreteur des tests.
- `omniroute-gateway` — quand l'evenement a detecter est un echec de route/provider.
- `hermes-provider-config` — quand la correction est une route de modele.
- `devops/auto-context-reset` — un plugin complet de cette famille, livrable de reference.
