# Provisionner un 2ᵉ profil Hermes (isolé, avec son propre fournisseur)

## État d'un profil fraîchement créé

Un profil neuf hérite de la structure mais pas de la configuration : `.env` **vide** (en-tête de
commentaires seul), pas de section `providers:`, SOUL.md au texte par défaut, et **tous les skills
bundled actifs**. Il ne produit donc aucune inférence tant qu'on ne l'a pas équipé — et il échoue de
façon trompeuse (voir plus bas).

Ordre de travail : fournisseur → clé → modèle → repli → skills → SOUL → **preuve d'inférence**.

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

## 8. Le gateway du profil reste arrêté jusqu'à décision

Provisionner un profil ne l'allume pas. Ne pas démarrer son gateway « pour voir » : ce sont deux
décisions distinctes, et un profil équipé mais éteint est un état voulu.