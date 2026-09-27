# Provisionner un 2ᵉ profil Hermes (isolé, avec son propre fournisseur)

## État d'un profil fraîchement créé

Un profil neuf hérite de la structure mais pas de la configuration : `.env` **vide** (en-tête de
commentaires seul), pas de section `providers:`, SOUL.md au texte par défaut, et **tous les skills
bundled actifs**. Il ne produit donc aucune inférence tant qu'on ne l'a pas équipé — et il échoue de
façon trompeuse (voir plus bas).

Ordre de travail : fournisseur → clé → modèle → repli → skills → SOUL → **preuve d'inférence**.

`hermes profile create <nom>` (sans `--clone`) suffit pour partir d'un profil nu, et **ne touche pas au
`config.yaml` principal** — le prouver par `sha256sum config.yaml` avant/après (empreinte identique),
c'est le contrôle qu'attend un opérateur qui a interdit d'y toucher. Ce que la commande produit :
`profiles/<nom>/` avec un `config.yaml` minimal (`model: {default, provider}` + `_config_version`),
un `.env` sans clé, SOUL.md, **les skills bundled synchronisées** (« N bundled skills synced » —
compter et le dire, l'opérateur croit souvent qu'on lui copie ses skills), et un lanceur
`~/.local/bin/<nom>.bat`. `state.db` n'apparaît qu'au premier `hermes -p <nom> …`. Un nom avec tiret
est accepté (`docs-writer`), et `--no-skills` évite même les bundled si le profil doit rester vide.
Le modèle du profil neuf est recopié du profil principal (`deepseek-flash` ici) : les clés manquent,
donc `hermes -p <nom> setup` (ou héritage des clés du shell) avant toute inférence.

## 1. La section `providers:` est obligatoire

`model.provider` ne suffit pas. Un profil dont le `config.yaml` ne contient que
`model: {default, provider, base_url}` échoue à l'inférence avec :

```
Unknown provider '<nom>'. Check 'hermes model' for available providers, or run 'hermes doctor'
```

Recopier la déclaration du profil principal (le fournisseur OpenAI-compatible se décrit ainsi) :

```yaml
providers:
  <nom>:
    api: http://127.0.0.1:<port>/v1
    name: <libellé>
    default_model: <modèle>
    key_env: <VARIABLE_DU_.env>
    extra_headers:
      <En-tête>: <valeur>
    request_timeout_seconds: 120
```

`key_env` est ce qui relie le profil à **sa** clé : le profil lit la variable dans son propre `.env`,
donc deux profils peuvent viser le même endpoint avec deux clés différentes.

## 2. Clé dédiée, jamais celle du poste

Créer une clé par consommateur (voir `omniroute-gateway` pour l'API des clés et la sémantique des
listes d'autorisation) : elle borne les dégâts, rend l'usage attribuable et se révoque seule. Poser
la valeur dans le `.env` **du profil**, jamais recopier celui du poste.

Si l'écriture se fait à l'aveugle — parce que le secret ne doit pas transiter par le contexte de
l'agent — faire créer, poser et relire par **un seul script** qui n'affiche que le préfixe et la
longueur. C'est la seule forme qui ne laisse pas le secret dans l'historique de conversation.

## 3. Modèle et chaîne de repli

`model.default` et `fallback_model.*` sont des **scalaires** : `hermes -p <profil> config set` convient.

`fallback_model` accepte **deux formes** : un dict `{provider, model}`, ou une **chaîne ordonnée** :

```yaml
fallback_model:
  - provider: <nom>
    model: <modèle-1>
  - provider: <nom>
    model: <modèle-2>
```

La chaîne est bien supportée de bout en bout — validée par `hermes_cli/config.py`
(`_validate_fallback_model`: « single dict OR list of dicts (chain) », `provider` + `model` requis par
entrée) et **consommée** par `hermes_cli/fallback_config.py` (`_iter_fallback_entries` itère dict *ou*
liste, `get_fallback_chain` préserve l'ordre). L'avertissement du CLI
(« Did you mean: fallback_providers.provider ») est une **fausse alerte** pour la forme dict : les deux
clés coexistent, `fallback_providers` étant la moderne.

Vérifier après écriture : `hermes -p <profil> config check` (« Config version: N ✓ ») **et** un
`config get fallback_model` qui relit les entrées dans l'ordre.

### Ordre réel du repli, et comment le prouver

`get_fallback_chain` (`hermes_cli/fallback_config.py`) **fusionne deux sources** : `fallback_providers`
d'abord, puis l'ancienne clé `fallback_model`, chaque entrée dédupliquée sur `(provider, model,
base_url)`. Trois conséquences pratiques :

- Écrire la chaîne dans **une seule** des deux clés. Avec les deux, l'ordre effectif n'est pas l'ordre
du fichier mais « toutes les entrées de `fallback_providers`, puis celles de `fallback_model` ».
- **Un repli gratuit avant le repli payant.** Un profil dont le seul repli est payant bascule sur
  la facturation à la première défaillance du primaire — et rien ne le signale dans la réponse. Un
target local/gratuit (`nvidia-stack` via le proxy NIM, par exemple) passe avant le payant.
- **Chaque entrée de repli doit être un modèle CONCRET, jamais un alias `auto/*`.** Un alias résout sa
  cible à chaque appel dans un pool qui peut être entièrement mort : mesuré `502` sur un alias présenté
  comme « gratuit », là où un `provider/modèle` concret répondait en ~3 s. Écrire l'entrée en
  `provider: <nom>` / `model: <provider>/<modèle>` ; si l'alias reste utile, le placer APRÈS le concret.
- **Une clé restreinte au consommateur impose un modèle déterministe de bout en bout.** Dès que
  `allowedModels` n'est pas vide, la clé passe en `modelAccessMode: restricted` et le filtre s'applique
  aux cibles **résolues** : un `model.default` qui est un alias dynamique (`eco`) échoue en `503`
  (`all targets were skipped by pre-dispatch filters`) dès que la rotation sort de la liste. Aligner les
  trois — `model.default` concret, entrées de repli concrètes, et toutes présentes dans `allowedModels`
  — puis prouver par un vrai tour `hermes -p <profil> -z "…"` **et** par la défaillance forcée du
  primaire (voir plus bas) : une clé restreinte posée sans cet alignement casse le profil en silence.
- **La preuve se fait par défaillance forcée, pas par lecture du YAML** : forcer un primaire inexistant
  et regarder qui a réellement servi, options **avant** `-z`.

```bash
hermes -m <modele-inexistant> -z "Réponds exactement : OK FALLBACK"
```

Puis lire la session (read-only) : `SELECT id, model, billing_provider FROM sessions ORDER BY rowid
DESC LIMIT 1` — `model` nomme l'entrée qui a servi, `billing_provider` sépare gratuit et payant.
Piège d'argument : `hermes -z -m <modele> …` échoue (`-z/--oneshot: expected one argument`) parce que
`-z` consomme le token suivant. Le repli déclenché est silencieux dans le chat : sans cette lecture,
une bascule payante passe inaperçue.

## 4. Skills : la clé `disabled` est une LISTE

`skills.disabled` se modifie par **insertion textuelle ciblée** dans `config.yaml` (backup d'abord),
jamais `hermes config set` qui remplace la liste par un scalaire. Le profil peut partir **sans**
section `skills:` : l'insérer proprement (en-tête `skills:` + `  disabled:` + entrées `    - <nom>`).

Après écriture, la seule vérification qui compte est le recomptage **par `find`** (voir la règle des
trois niveaux dans le SKILL.md) : le CLI **tronque les noms longs** et **filtre par plateforme**, donc
un appariement par égalité stricte sur sa sortie déclare à tort « non appliqué » des noms qui le sont.

## 5. SOUL.md : nommer les interdits, pas les évoquer

Un SOUL de rôle doit porter une section « périmètre interdit » **explicite**, avec les chemins réels :
le `.env` du profil principal (attention, il vit à la **racine** de l'installation — le profil
`default` n'a pas de `.env` à lui, écrire `profiles/default/.env` désigne un fichier inexistant) et
`auth.json`, partagé à la racine.

## 6. L'isolation est partielle : le dire

Le `.env` par profil isole les **clés**, pas tout : `auth.json` reste à la racine et est partagé entre
profils — c'est lui qui fournit la recherche web. Un profil « isolé » a donc accès à des credentials
qu'on n'a pas mis dans son `.env`. Le documenter dans le SOUL **et** dans le rapport, plutôt que de
laisser croire à une isolation totale.

**L'isolation ne couvre pas l'arbre de travail git.** Le profil a ses propres `skills/`, `memories/`,
`config.yaml` et `state.db` — c'est ce qui empêche ses passes de doc de salir les fichiers du profil
principal — mais un `terminal.cwd` pointé sur le dépôt canonique
(`hermes -p <nom> config set terminal.cwd <chemin>`, clé **scalaire** réelle, section `terminal:`,
relue par `config get terminal.cwd`) fait écrire la session dans le **même working tree**. Un profil
« dédié » ne protège donc pas l'arbre git de la dérive : le dire, et pour séparer vraiment pointer le
cwd sur un second clone ou un worktree — décision distincte, à demander.

### 6 bis. Séparer vraiment : worktree dédié + profil non versionné (recette vérifiée)

```bash
git worktree add C:/Users/<user>/<nom-projet-doc> -b <branche-doc>
hermes -p <nom> config set terminal.cwd C:/Users/<user>/<nom-projet-doc>
```

- **`git worktree add <chemin> main` échoue** si `main` est déjà cochée ailleurs :
  `fatal: 'main' is already used by worktree at '<chemin du canonique>'`. L'échec est propre (aucun
  résidu) ; l'option qui marche sans toucher au canonique est `-b <branche-doc>` — branche **neuve et
  locale**, non poussée, à laisser telle quelle.
- Vérifier les trois côtés, dans cet ordre : `git worktree list` (deux entrées : canonique sur `main`,
  worktree sur `<branche-doc>`), `git -C <chemin> status` (propre, sur la branche attendue), et le
  `git status` du dépôt canonique (toujours sur `main`, inchangé).
- **Un worktree ne contient que les fichiers suivis** : c'est exactement ce qui empêche une session
  documentaire d'écrire dans les dossiers de runtime du home (`cache/`, `logs/`, `sessions/`,
  `pending/`) — l'argument à donner, au-delà du simple rangement.
- Le worktree **ne se met pas à jour tout seul** : il voit les nouveaux commits quand on y travaille.
  Ne pas le fast-forwarder « pour aligner » si l'opérateur ne l'a pas demandé.
- **Le profil de travail ne se versionne pas** : une seule ligne `/profiles/<nom>/` dans
  `.git/info/exclude`, avec un commentaire au-dessus — `.gitignore` couvre déjà `state.db*`,
  `sessions/`, `cache/`, `logs/`, `workspace/` et `.env` d'un profil. Vérifier par
  `git check-ignore -v <chemin>` **avant** d'écrire la moindre ligne, préférer une ligne de dossier à N
  lignes de fichiers, et prouver par `git status --porcelain profiles/<nom>/` vide +
  absence du profil dans le porcelain global.
- **`hermes -p <nom> setup --non-interactive` ne configure RIEN** : le CLI répond « Running in a
  non-interactive environment (no TTY detected)… » et sort sans écrire de clé — un agent ne peut donc
  pas provisionner les credentials. Livrer à l'opérateur la commande exacte à lancer dans SON
  terminal (`<nom> setup`, via le lanceur de `~/.local/bin`) et le dire comme tel.
- **Piège de lecture après le setup** : `hermes -p <nom> auth list` affiche des fournisseurs (déduits
  des variables d'environnement) alors que `hermes -p <nom> config get providers` rend `{}` — ce sont
  des clés **héritées du shell**, pas celles du profil. Ne pas en conclure que le profil est
  provisionné ; la preuve d'inférence reste le tour réel (§7).

## 7. Preuve d'inférence : au niveau du profil, pas du endpoint

Un `200` obtenu par `curl` sur le fournisseur ne prouve rien du profil : config, section `providers:`,
`key_env`, chaîne de repli et streaming ne sont exercés que par un tour réel.

```bash
hermes -p <profil> -z "Réponds exactement et uniquement : OK <PROFIL>"
```

Attendu : la réponse littérale. `Unknown provider` ⇒ section `providers:` manquante ;
`provider didn't answer after N attempts` ⇒ lire le message imbriqué (`Provider said: …`) : il porte le
modèle réellement demandé et l'erreur amont, ce qui distingue une clé refusée, un modèle hors liste
d'autorisation et un relais qui ne sait pas streamer.

**Vérifier la RÉPONSE du profil contre ta propre mesure.** Un tour `-z` juste sur la question posée
peut sur-affirmer un détail qu'il ajoute de lui-même (comptage annoncé « identique en sensible et
insensible à la casse », faux : 9 vs 14). Recouper chaque chiffre avec ta propre commande avant de le
reprendre dans un rapport — sinon le chiffre inventé devient un fait.

## 8. Le gateway du profil reste arrêté jusqu'à décision

Provisionner un profil ne l'allume pas. Ne pas démarrer son gateway « pour voir » : ce sont deux
décisions distinctes, et un profil équipé mais éteint est un état voulu.

## 9. Le profil tel qu'un wizard `setup` peut le laisser : toolsets et environnements de dépendances

Un wizard peut écrire son INTENTION de désactiver un toolset sous `tools.<plateforme>.<toolset>.enabled`
— un chemin que Hermes ne lit pas. La mesure qui tranche est `hermes -p <nom> tools list` (ou
`--summary`), jamais le `config.yaml` : une intention sans effet laisse le toolset **actif**, et un
toolset actif **provisionne son environnement de dépendances** dans le profil.

```
profiles/<nom>/environments/<toolset>/
  active.json          # {"generation": "gen-<hash>", "requirements": ["<pkg>==<ver>"]}
  gen-<hash>/          # pyproject.toml + uv.lock + venv/   <- le poids est ici
```

Mesurer avant de juger : `du -sh profiles/<nom>` puis `du -sh profiles/<nom>/environments/*`. Ici le
seul toolset `browser` actif a provisionné `browser-use==0.13.10` : 299 Mo de `venv` pour un profil de
310 Mo. **Ce poids n'est PAS celui du navigateur** : les Chromium/Playwright vivent dans le cache
PARTAGÉ `%LOCALAPPDATA%\ms-playwright` (1,4 Go, un dossier par version) — l'inspecter avant
d'attribuer un poids navigateur au profil, et ne pas y toucher pour alléger un profil.

Assainir, dans cet ordre (chemin supporté, réversible) :

```bash
cp profiles/<nom>/config.yaml profiles/<nom>/config.yaml.bak_<horodatage>_pre-clean
hermes -p <nom> tools disable browser image_gen   # écrit platform_toolsets.<plateforme>, la clé autoritative
# puis retirer le bloc mort tools.<plateforme>.* du config.yaml (édition textuelle ciblée)
mv profiles/<nom>/environments/browser-use "$LOCALAPPDATA/hermes/backups/<nom>-browser-use_$(date +%Y%m%d_%H%M%S)"
```

- **Mettre l'environnement en QUARANTAINE, jamais le supprimer** : c'est un venv régénérable (le
  `pyproject.toml`/`uv.lock` du `gen-*` est sa recette) mais le supprimer ne se défait pas — déplacé
  dans `backups/`, il se restaure ; réactiver le toolset le reprovisionne de toute façon.
- **Avant de retirer une clé de config, prouver que rien ne la lit** : `rg '<nom-de-la-clé>'` dans
  `hermes-agent` → 0 occurrence = clé morte. Une clé morte n'est pas neutre : elle laisse l'opérateur
  croire à un réglage appliqué.
- **`hermes profile create` n'a PAS de `--no-setup`** (options réelles : `--clone`, `--clone-all`,
  `--clone-from`, `--clone-channels`, `--sync-imports`, `--no-alias`, `--no-skills`, `--description`) :
  **recréer un profil pour effacer une pollution le repollue**, en détruisant un profil qui répondait.
  Un profil fonctionnel mais lourd s'assainit sur place ; la recréation ne se décide que pour un profil
  cassé, et à part.
- Vérifier après coup que le profil répond toujours (§7) et que le poids a bougé
  (`du -sh profiles/<nom>`) — pas depuis la seule édition de config.