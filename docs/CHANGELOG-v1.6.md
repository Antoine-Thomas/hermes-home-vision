# Changelog — Version 1.6 « Hermes Aegis-Sec+ »

> **Statut : publiée.** Tag annoté `v1.6` sur `main` (posé dans le même commit que ce changelog).
> La version **publiée** antérieure reste la **1.5 « Aegis-Sec »** (tag annoté `v1.5`, objet `3be8041` → commit `8f15b6c`).
> Toutes les valeurs ci-dessous sont **mesurées le 08/10/2026** sur la machine d'origine
> (`%LOCALAPPDATA%\hermes`, Windows 11 natif), avec Hermes Agent **v0.21.6+131.g38880bd (2026.9.24)**,
> upstream `38880bd2`, Python **3.11.16**. Dépôt `hermes-home-vision` (public), branche `main`,
> commit `7e459eb` (parent de ce commit) au moment de la rédaction.

Thème de la 1.6 : **Aegis-Sec+**, la suite directe d'Aegis-Sec — clôture des liens cassés publiés avec
la 1.5, première version versionnée du plugin `anima-memoire-router`, et capitalisation des mesures de
la couche sécurité (ACL, Wazuh, sondes) dans les skills.

Convention : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) · versionnage
[SemVer](https://semver.org/lang/fr/).

---

## [1.6] — 2026-10-08

### Added

**Références de la couche sécurité — les 4 liens cassés signalés en 1.5 sont clôturés**

Les quatre fichiers ci-dessous sont **absents de tout l'historique versionné** (`git cat-file -e
HEAD:<chemin>` et `git cat-file -e v1.5:<chemin>` échouent pour les quatre) alors que les `SKILL.md`
correspondants les citent : ce sont donc bien des **liens morts publiés avec la 1.5**. Ils entrent dans
le dépôt avec cette version.

- `skills/devops/security-ops/references/wazuh-security-audit.md` — **6 089 o / 102 l** — audit Wazuh
  (version, CVE, configuration) en posture **lecture seule** : aucune modification sans accord
  explicite, chaque affirmation justifiée par une sortie de commande.
- `skills/devops/security-ops/references/wazuh-securite-corrections.md` — **10 200 o / 171 l** — phase
  de **correction** après l'audit (chemins réels, sauvegarde, rollback) ; commandes vérifiées sur une
  stack `wazuh-docker` **4.7.3 single-node** (Windows + Docker Desktop).
- `skills/devops/security-ops/references/certificat-api-wazuh.md` — **3 590 o / 61 l** — échéance et
  renouvellement du **certificat auto-signé de l'API** : il vit dans le VOLUME
  `single-node_wazuh_api_configuration` (`/var/ossec/api/configuration/ssl/`), pas dans un bind-mount
  hôte — la copie du dossier compose ne le contient pas.
- `skills/autonomous-ai-agents/hermes-agent/references/verifier-un-plugin-tiers.md` — **3 618 o /
  55 l** — checklist à ouvrir avant d'installer ou d'activer un plugin/paquet tiers annoncé pour
  Hermes.

**Plugin `anima-memoire-router` — première version versionnée**

`plugins/anima-memoire-router/` — **3 fichiers source, 22 426 o** (`__init__.py` 12 265 o,
`plugin.yaml` 1 614 o, `tests/test_hook.py` 8 547 o), plus un `.gitignore` de dossier. Le dossier **ne
contient pas de README** : la description ci-dessous vient de `plugin.yaml` et de la docstring de
`__init__.py`.

- Déclaration : `name: anima-memoire-router`, `version: 0.2.0`, `license: MIT`,
  `requires_hermes: ">=0.21"`, `kind: standalone`, aucun `provides_tools`, un hook
  `provides_hooks: [pre_llm_call]`.
- Fonction : route la question utilisateur vers la couche **mémoire** (JEV, repli regex) **avant**
  l'appel LLM, puis classe sa **complexité** — simple → aucune recherche, modérée → RAG top-5,
  complexe → RAG top-20 puis sélection locale de 5 — et injecte les extraits sous `<rag_context>`.
- Réglages par défaut : `mode: off` (**opt-in** : le plugin ne fait rien tant qu'il n'est pas activé),
  `rag_url: http://127.0.0.1:8200`, `rag_k: 5`, `rag_k_complexe: 20`, `routeur: on`, `timeout_s: 4.0`,
  `max_chars: 4000` ; journal `<HERMES_HOME>/logs/anima-memoire-router.log`, une ligne JSON par décision.
- Contraintes annoncées et vérifiées à l'exécution : **fail-open sur chaque chemin d'erreur** (un
  routeur cassé ne casse jamais un tour), **stdlib uniquement**, aucun reranker externe.
- Tests : `tests/test_hook.py` → **29 assertions OK / 0 échec, exit 0** (Python 3.11.16, hors ligne) —
  groupes T2 (JEV en échec → repli regex, sans injection RAG), T3 (RAG en échec → non-injection),
  bornage/troncature du bloc injecté, T4 (routeur de complexité : 0 / 5 / 20 fragments), T5 (décision
  du routeur **avant** le `POST /search`, journalisation des décisions et des abstentions).
- `plugins/anima-memoire-router/.gitignore` — `__pycache__/` et `*.pyc` : les deux `.pyc` présents sur
  disque (`__init__.cpython-311.pyc`, `__init__.cpython-314.pyc`, 42 118 o au total) **restent hors du
  dépôt**.

**Deux fichiers cités par les `SKILL.md` de cette version (versés pour ne pas créer de lien mort)**

- `skills/devops/hermes-install-troubleshooting/scripts/verifier-acces-dacl.py` — **4 045 o / 95 l** —
  sonde d'**ACCÈS** à lancer avant/après toute écriture d'ACL de masse.
- `skills/devops/wazuh-agent-lifecycle/templates/elevated_child.ps1` — **3 756 o / 58 l** — gabarit
  d'enfant élevé (transcript, nommage explicite des variables).

### Changed

- `skills/devops/security-ops/SKILL.md` (**+36/-1**) — ordre de qualification d'un hit de scanner
  (caractériser la valeur sans l'afficher, compter les occurrences, établir l'atteignabilité distante
  par `git log --all --find-object` puis `git branch -r --contains`, rendre un verdict nommé) ; un
  `.env` de profil créé **après** le durcissement n'hérite pas des 3 ACE non héritées ; compter les ACE
  sur la sortie **brute** d'`icacls`, jamais par un filtre indirect.
- `skills/devops/wazuh-agent-lifecycle/SKILL.md` (**+171/-16**) — pré-vols de rétrogradation (MSI de
  retour téléchargeable, **empreinte `sha256` du champ clé** des deux côtés plutôt que la longueur),
  effets mesurés de `msiexec /x` (service retiré, dossiers supprimés, `.save` recopiés par
  l'installeur), séquence validée **4.14.8 → 4.7.3** (nouvelle Règle 9), sauvegarde/restauration d'un
  agent aux fichiers illisibles sous UAC (Règle 8), `Start-Process` « nom nu » dans un enfant élevé qui
  ne lance **rien**.
- `skills/devops/hermes-install-troubleshooting/SKILL.md` (**+16/-0**) — un chemin MSYS remis à un
  **Python natif** rend `FileNotFoundError` et masque l'erreur réelle (convertir par `cygpath -w`) ;
  **dossier témoin** avant l'arbre réel ; un `icacls /T > dump` est un **constat**, pas un artefact de
  restauration.
- `skills/devops/security-monitoring/SKILL.md` (**+10/-1**) — un composant qui reste `DEGRADED` (ou
  `READY`) en continu est un **faux positif structurel** : clé jamais remplie par le parseur, ou
  critère vrai par construction ; rappel du redémarrage automatique de la pile Wazuh (`restart: always`,
  identifiants `INDEXER_*` vs `API_*`).
- `skills/devops/hermes-stack-audit/SKILL.md` (**+18/-3**) — une écriture d'ACL de masse **ne se
  vérifie pas par le bilan d'`icacls`** (la propagation `(OI)(CI)` vide les DACL des fichiers) : leçon
  de l'incident du 08/10, avec relève du **propriétaire** de chaque objet et contrôle par l'**accès**.
- `README.md` — bloc de version en tête (1.6 publiée / 1.5 publiée / 1.4 préparée non publiée),
  tableau des versions (ligne 1.6), §2 **Supervision** remise sur les mesures réelles du gateway, §8
  (**cinq** fichiers de secrets au lieu de quatre, et bullet « plus aucun lien cassé »), §9
  Documentation (`CHANGELOG-v1.6.md`).

### Fixed

- **Les 4 liens cassés signalés en 1.5 sont clôturés.** `skills/devops/security-ops/SKILL.md` (3
  références) et `skills/autonomous-ai-agents/hermes-agent/SKILL.md` (1 référence) pointaient vers des
  fichiers **absents du dépôt** ; vérifié **objet par objet** — `HEAD:<chemin>` et `v1.5:<chemin>` en
  échec pour les quatre, alors que le dossier `security-ops/references/` ne contenait au tag `v1.5` que
  `security-audit.md` et `wazuh-troubleshooting.md`. Les quatre fichiers sont désormais versionnés.
- **Aucune référence morte dans le périmètre publié.** Contrôle des fichiers cités (`references/`,
  `templates/`, `scripts/`, `assets/`) par les 10 fichiers texte du périmètre : les **deux seules
  cibles absentes du disque** (`scripts/verifier-acces-dacl.py`, `templates/elevated_child.ps1`) sont
  versées avec cette version — il n'en reste **aucune**.
- **0 secret réel dans le périmètre.** Les 17 fichiers entrant dans la 1.6 ont été passés au scanner
  « forme de clé » (`sk-`, `ghp_`, `hf_`, `AIza`, bloc `PRIVATE KEY`, `token[:=]`), **valeurs jamais
  affichées** (sortie masquée : longueur, alphabet, préfixe). 11 hits bruts, **tous classés faux
  positif / placeholder** : 3 `sk-` dans `security-ops/SKILL.md` (le fragment
  `delegate-task-concurrency-…` que le texte cite lui-même comme faux positif), 1 dans
  `hermes-stack-audit/SKILL.md` (mot `disk-…`), 7 dans `README.md` (6 compteurs documentaires
  `token: …` du contrôle d'historique, et le fragment de nom de fichier
  `delegate-task-concurrency-diagnosis.md` — 24 car, 100 % minuscules, 0 chiffre, entropie 3,559
  bit/car — déjà documenté comme faux positif en 1.5). Conclusion : **0 valeur réelle**.

### Notes

- **Commit intermédiaire, déjà publié** : `7e459eb docs(skills): consigne le piège ACL (OI)(CI) sur
  fichier` — **+52/-1** sur `skills/devops/hermes-install-troubleshooting/SKILL.md`, poussé sur
  `origin/main` **après** le tag `v1.5`. Le tag annoté `v1.5` (objet `3be8041`) pointe le commit
  `8f15b6c` — même schéma que `v1.6` (objet `08c96712` → commit `93acef7`). La 1.6 s'appuie sur cet
  état : **aucun commit n'est réécrit**.
- **Durcissement des dossiers `profiles/` : reporté, hors périmètre 1.6.** Une opération d'ACL de masse
  sur l'arbre peut ré-ouvrir l'héritage des `.env`, et tout fichier **créé** ensuite dans un dossier
  ré-hérite la ACE du parent : fermer l'héritage au niveau des **dossiers** exige le **gateway arrêté**
  et une validation par étapes — ce n'est pas une opération « à chaud » pendant une publication.
- **Hors périmètre : `skills/devops/hermes-provider-config/SKILL.md`** (**+144/-4**, modification en
  attente dans l'arbre de travail, non committée) — plomberie fournisseurs/coûts : chemins de config
  réels vs leurres `~/.hermes`, quoting JSON des slugs à `:` en fin de valeur, portée *fail-closed* des
  secrets de profil, schéma de `state.db`, retard des compteurs OpenRouter, profondeur de repli
  (`api_max_retries`), re-tarification des rôles `auxiliary`. Réservé à un lot ultérieur
  « providers/coûts » : le thème Aegis-Sec+ ne le couvre pas.
- **Incident ACL du 08/10 — contexte, aucune ACL touchée pour cette version.** Propagation d'un
  `/grant:r "X:(OI)(CI)(F)"` aux **fichiers** d'un arbre (vue sur 3 188 objets dans le rapport de
  diagnostic), `takeown /r /d O` rejoué et **635 objets réparés** (relevé opérateur) ; les `.env` sont
  restés protégés (3 ACE non héritées, `Protected=True`). Ce qui sort de ce chantier est de la
  **connaissance** (les cinq `SKILL.md` de cette version) — pas une modification de droits.
- **Fins de ligne.** Les 10 fichiers texte du périmètre sont en **CRLF sur le disque** (effet de la
  réécriture des objets de l'incident) alors que la 1.5 n'avait versionné que du LF. `.gitattributes`
  (`* text=auto eol=lf`) + `core.autocrlf=true` normalisent à l'index : contrôle `git ls-files --eol`
  → **`i/lf`** pour les 9 fichiers texte de ce périmètre, **aucun `i/crlf`** — et `i/lf` pour les
  **17 fichiers indexés** au total. Le gabarit `templates/elevated_child.ps1` est en `i/lf` avec
  l'attribut `eol=crlf` (`*.ps1 text eol=crlf`) : c'est la forme attendue — blob normalisé en LF dans le
  dépôt, copie de travail en CRLF. Aucune normalisation disque n'a été faite.
- **Mesure de supervision (08/10/2026, gateway non redémarré, PID 11700 non touché).**
  `hermes gateway status` → tâche `Hermes_Gateway` enregistrée + `Gateway process running
  (PID: 11700)` ; `hermes profile list` → **5 profils servis** (`default`, `docs-writer`, `security`,
  `veille`, `watch`, tous `running`) ; `hermes -p {watch,veille,security,docs-writer} gateway status`
  → « Gateway is running via the default-profile multiplexer » + « ✓ default — PID 11700 » ; un seul
  processus `python.exe` de gateway sur la machine ; `config.yaml` → `gateway.multiplex_profiles: true`,
  `scale_to_zero.idle_timeout_minutes: 5` ; tâche `Hermes_Gateway_HealthCheck` en `Ready` (dernier
  passage 08/10 17:55, suivant 18:00).
- **Secrets hors dépôt.** Aucun `.env`, `state.db`, `auth.json` ni clé privée n'entre dans cette
  version (périmètre = 17 fichiers, listés au message de commit). Les `.env` restent hors de l'index.
- **Bloqueurs B1** (MP4 manquant) et **B2** (watchdog en pause) de la 1.4 « Aegis » restent reportés en
  « issues connues » : la **1.4 reste préparée et non publiée** (aucun tag), et aucune version
  antérieure n'est réécrite.
