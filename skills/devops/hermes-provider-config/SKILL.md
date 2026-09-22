---
name: hermes-provider-config
description: "Use when configuring Hermes providers or fallbacks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, providers, fallback, config, custom-endpoint]
    created: "2026-09-21"
---

# Configurer les providers et la chaine de repli Hermes

Mecanique d'edition de la config Hermes (`config.yaml`, `.env`) et pieges qui
cassent une chaine de repli sans erreur visible. Pour la strategie de routage
(combos OmniRoute, couts, latences), voir la skill `fallback-intelligent`.

## Procedure

1. Lire l'etat reel avant d'ecrire : `hermes config get <cle>`,
   `hermes fallback list`, `hermes profile list`, `hermes auth status <provider>`.
2. Ecrire via `hermes config set` (voir ci-dessous). `hermes config get <cle>`
   relit la valeur ; `hermes doctor` valide la config apres coup.
3. Verifier la resolution des entrees de fallback **avant** de conclure (sonde
   `resolve_runtime_provider`, voir Pieges) puis `hermes fallback list`.
4. Rapporter la sortie brute : code HTTP + corps d'erreur exact, jamais une
   paraphrase. Si les sondes innocentent la config, le dire et ne rien corriger —
   ne pas appliquer une « correction » (setx, copie de `.env`, shim) que la
   mesure ne justifie pas.

## Editer la config : `hermes config set`, jamais patch/write_file

Le tool `patch` / `write_file` refuse `~/AppData/Local/hermes/config.yaml`
(et `~/.hermes/config.yaml`) : « Agent cannot modify security-sensitive
configuration ». Ne pas contourner par sed/echo. `hermes config set <cle>
'<litteral YAML ou JSON>'` accepte les valeurs structurees, donc un dict
imbrique ou une liste de dicts tient en une commande :

```bash
hermes config set providers.exemple '{base_url: "https://api.exemple.ai/v1", key_env: EXEMPLE_API_KEY, transport: chat_completions, default_model: m1, models: [m1, m2]}'
hermes config set fallback_providers '[{provider: omniroute, model: eco}, {provider: omniroute, model: nvidia-stack}]'
hermes config unset providers.exemple    # retire le provider
hermes config unset EXEMPLE_API_KEY      # retire la cle de .env (un commentaire "# --- EXEMPLE_API_KEY ---" reste comme trace)
```

Cles de provider custom reconnues : `api` / `base_url` / `url` (equivalentes),
`key_env` ou `api_key_env`, `transport` ou `api_mode` (`chat_completions`),
`default_model`, `models`. NE PAS ecrire `type: openai` (ignore) ni
`api_key: "${VAR}"` (substitution non faite -> cle introuvable).

## Model principal : il n'existe pas de `hermes model set`

`hermes model` est un selecteur interactif, sans sous-commande : toute forme de
`hermes model set ... --global` sort en erreur d'usage (`unrecognized arguments`,
exit 2). Pour persister la route du profil `default` (et lui seul), deux cles :

```bash
hermes config set model.provider google
hermes config set model.default gemini-3.6-flash
```

`model.base_url` n'est honore que si `model.provider` correspond au provider
resolu : changer de provider efface donc tout seul l'ancien `base_url` (le CLI
l'annonce). Ne pas le reecrire a la main — il ferait pointer le nouveau provider
vers l'endpoint de l'ancien. Verifier : `hermes fallback list` (`Primary: <modele>
(via <provider>)`), `hermes config get model`, `hermes profile list` (colonne
Model par profil).

## Secrets et .env

```bash
hermes config set EXEMPLE_API_KEY "<valeur>"   # route vers ~/AppData/Local/hermes/.env
hermes config set EXEMPLE_API_KEY ""           # placeholder a remplir a la main
```

- Ne JAMAIS lire `.env` avec `read_file` : les secrets entrent dans le contexte.
  Verifier par `grep -c '^NOM_API_KEY='` + un controle Python qui n'imprime que
  booleen / longueur.
- Le terminal masque les variables `*API_KEY` en `***` : une sortie `***` ne
  prouve pas que la valeur est fausse, seulement qu'elle est un secret.
- Cle collee dans le chat = compromise : la remplacer par un placeholder dans
  `.env`, demander la rotation, ne jamais la re-afficher ni la recopier dans un log.

## Pieges critiques

**Un fallback s'adresse a un PROVIDER, pas a un modele.** `eco` et
`nvidia-stack` sont des modeles servis par OmniRoute ; ecrire `provider: eco`
leve `AuthError: Unknown provider 'eco'` a la resolution, l'entree est ignoree
avec un simple log debug (`Fallback entry eco/eco failed`) et la chaine perd des
etages sans erreur visible. Ecrire `provider: omniroute` + `model: eco`.
Prouver la resolution avant d'ecrire :

```bash
cd ~/AppData/Local/hermes/hermes-agent && venv/Scripts/python.exe -c "
from hermes_cli.runtime_provider import resolve_runtime_provider as r
for p,m in [('eco','eco'),('omniroute','eco')]:
    try:
        d=r(requested=p, target_model=m); print(p,'->',d.get('provider'),d.get('base_url'))
    except Exception as e:
        print(p,'ERR',type(e).__name__,e)"
```
(Windows : `venv/Scripts/python.exe` ; POSIX : `venv/bin/python`.)

**Declenchement du fallback.** Rate-limit (429), 5xx, erreur reseau et
epuisement de credits (402) font avancer la chaine. Un modele inexistant
(`404 model_not_found`) est classe « non retryable » — aucune reprise sur le meme
provider — mais fait lui aussi avancer la chaine : le tour est servi par l'etage
suivant sans aucun signe visible. A la resolution (avant tout appel reseau), seule
une `AuthError` fait avancer la chaine ; une entree dont la resolution leve autre
chose est loggee puis ignoree.

**Le message CLI ne dit pas la cause.** « every provider in the fallback chain
kept failing over » est generique : il masque le code HTTP et l'etage reellement
en echec. Ne jamais diagnostiquer depuis ce message, et ne pas conclure a un
probleme de chargement `.env` parce que forcer la variable d'environnement semble
corriger le tirage : une commande qui reussit puis echoue au coup suivant, ou
d'un dossier a l'autre, signe un probleme provider, pas de chemin. Obtenir
l'erreur brute du provider avant toute correction (triage en 3 sondes :
`references/custom-openai-provider.md`).

**Entrees gatees par OAuth.** Une entree vers un provider OAuth non connecte
(`nous`, `minimax-oauth`) ne resout pas : controler
`hermes auth status <provider>` (`logged out` = entree inutile).
`hermes fallback list` n'affiche PAS l'etat de connexion, seulement la
resolution des entrees — ne pas en deduire que l'etage fonctionne.

**Le catalogue statique d'Hermes vieillit plus vite que l'API.** Des IDs encore
listes par `models_catalog_static.py` peuvent etre refuses par le provider : Xiaomi
`mimo-v2-pro` -> `400 Unsupported model`, alors que la liste live du compte ne
sert plus que `mimo-v2.5*` / `mimo-v2.6*`. Un ID mort en tete d'une chaine fait
sauter l'etage en silence (l'API repond, juste pas ce modele). Toujours confronter
`/v1/models` live apres avoir pose la cle, jamais se fier au catalogue.

**Une cle valide n'est pas un compte approvisionne.** Xiaomi : `/v1/models` -> 200
(9 modeles), mais tout `/v1/chat/completions` -> `402 Insufficient account
balance` sur chacun des 9 modeles. L'etage reste alors inutile en repli : il coute
un appel perdu a chaque bascule. Le dire, et proposer soit de recharger le compte,
soit de retirer l'etage (un 402 est classe facturation, donc la chaine avance —
mais elle avance moins vite).

**Le nom marketing n'est pas l'ID API.** Interroger `/v1/models` du provider
avant de figer la config (ex. « Nemotron 3 Ultra » ->
`nemotron-3-ultra-550b-a55b`). Un ID inexistant donne un 404 `model_not_found`
que le CLI n'affiche pas : le tour part sur l'etage suivant, donc un modele
principal mort peut ne jamais servir sans que rien ne le signale.

**Sonder depuis un script : poser un User-Agent explicite.** Un endpoint derriere
Cloudflare (api.groq.com) renvoie `403 error code: 1010` a l'UA par defaut
d'urllib — faux negatif qui ressemble a une cle morte ou a une IP bloquee ; le
meme appel avec `User-Agent: curl/8.x` (ou `OpenAI/Python 1.x`) + la cle renvoie
200. Ne jamais conclure « cle invalide » depuis un 403 sans corps JSON structure.

**Un plafond gratuit par requete peut exclure un provider du role de principal.**
Les paliers gratuits comptent `input + max_tokens` dans le TPM, par requete (ex.
compte Groq free : `x-ratelimit-limit-tokens: 8000`). Un prompt d'agent de 6 a
9 k tokens plus un budget de sortie depasse le plafond : toutes les requetes sont
refusees (413 `Request too large ... TPM: Limit 8000, Requested 9128`, ou 429 des
que `max_tokens` n'est plus minuscule) et le CLI bascule en silence vers l'etage
suivant — le provider reste « configure » mais ne sert jamais. Mesurer avant de
nommer un principal : lire `x-ratelimit-limit-tokens` et le comparer a
`input_tokens` du dernier tour (`session_model_usage`). Plafond < taille du
prompt -> provider utilisable en repli (tours courts) seulement, et le dire.

**`agent.api_max_retries` borne le NOMBRE D'ETAGES essayes par tour — c'est le vrai
verrou d'une chaine.** `agent/conversation_loop.py` fait `s.max_retries =
agent._api_max_retries`, et le walk s'arrete des que `restart_count > max_retries`
(`agent/turn_iteration_prep.py`, jetons `rebuilt_restart_limit_exceeded`). Avec la valeur 1,
un seul etage est activable : une chaine de 5 entrees vaut 1 entree, et le premier etage
mort suffit a produire « every provider in the fallback chain kept failing over ». Regle a
appliquer : `api_max_retries` >= nombre d'etages morts a traverser. Mesure : primaire
force en `402`, chaine `[omniroute/eco-fast(mort 502), omniroute/nvidia-stack]` -> echec
avec `api_max_retries=1`, etage 2 reellement atteint (504 du proxy) avec `api_max_retries=2`.
Ne jamais diagnostiquer une chaine epuisee depuis le message CLI : c'est un compte
d'activations, pas une panne de configuration.

**Deux MODELES du meme provider sont bien essayes (l'ancienne regle « un etage par
provider/base_url » etait fausse).** `agent/backend_identity.py` definit le saut par
`same_deployment` (comparaison provider **et** modele, `FailureScope.MODEL` par defaut) :
seul le couple provider+modele identique est saute. Mesure : chaine `[omniroute/eco-fast,
omniroute/nvidia-stack]` + primaire en `402` -> l'etage 2 est atteint sous charge. Les
echecs jadis attribues au partage d'un `base_url` etaient en realite causes par
`api_max_retries: 1`. Corollaire : un 429 quota reste temporaire (`429 ... exceeded your
current quota`, quotas Google par modele) et se reveille au reset — mais tout provider
dont l'etage en tete est limite reste indisponible tant que le budget d'activations est
depense : mettre en tete le modele du provider le plus disponible, pas le plus recent.

**Un etage qui ne peut pas porter le prompt casse toute la cascade.** Une entree
dont la route refuse la taille de la requete (preflight local, plafond TPM, cap
de requete) ne se contente pas d'etre sautee : le tour s'arrete sur
« This conversation ... has grown too large to send to <modele> » (exit 2), les
etages suivants ne sont jamais essayes. Mesure : chaine
`[groq/openai-gpt-oss-120b, google/gemini-3.8-flash, ...]` + primaire force en
402 -> exit 2 (arret sur l'etage groq) ; meme chaine sans l'etage groq -> le tour
est servi par `gemini-3.8-flash`. Ne placer en tete de chaine que des routes
capables de porter le prompt plein (verifier `input_tokens` du dernier tour contre
le plafond de la route) ; un provider « rapide mais petit » se force a la main
(`hermes --provider groq -m ... -z`), il ne se met pas en chaine.

**Un etage peut etre sature sans etre casse.** Un proxy local (OmniRoute) renvoie
`503 ResourceExhausted: Worker local total request limit reached (16/16)` : la
route existe, elle est juste pleine. Variante mesuree : `RATE_LIMIT_EXECUTION_TIMEOUT` —
« Request exceeded OmniRoute's local rate-limit execution expiration (legacy
resilienceSettings.requestQueue.maxWaitMs=15000ms) » : la file d'attente du proxy abandonne au bout
de 15 s, ce que Hermes voit comme un 503 de l'etage et fait avancer la chaine vers le paye. Preuve :
5 tirs avec primaire force en echec (402 Xiaomi) -> 4 servis par l'etage gratuit `nvidia-stack`, 1
par `deepseek-flash`. Le log par appel est dans `~/.omniroute/call_logs/<date>/*.json`
(`error` du dernier fichier = cause exacte cote proxy). Consequence pratique : une cascade peut
echouer de facon intermittente, un coup servie par l'etage 1, un coup
« every provider in the fallback chain kept failing over » alors que les sondes
directes des etages repondent 200. Rejouer le tir avant de conclure, et sonder
chaque etage separement (surtout le dernier, souvent un proxy local).

**Prouver qui a servi le tour, ne pas le deduire.** `hermes -z` n'imprime que le
texte du modele, et les one-shots n'ecrivent pas dans `logs/agent.log` : une
bascule invisible est indistinguable d'un succes du principal. La preuve est dans
`state.db` (`sessions.billing_provider` / `billing_base_url`,
`session_model_usage(model, billing_provider, session_id, input_tokens,
output_tokens)` — la table n'a pas de colonne `provider` ni `created_at`, trier par
`rowid`). Un test de bout en bout qui « marche » alors que le principal est casse
est le cas normal, pas l'exception.

**Un etage se prouve DANS la cascade, pas force a la main.** `hermes --provider X
-m Y -z` valide le couple cle/modele, pas l'entree de repli : la resolution peut
sauter une entree (backend identique, credential manquant, `unavailable` pour la
session). Pour prouver qu'un etage ajoute est reellement atteignable, mettre une
chaine temporaire reduite a cet etage en tete (`[{provider: X, model: Y},
{provider: omniroute, model: eco}]`) et forcer un primaire en echec propre (un
`402` : `hermes --provider xiaomi -m mimo-v2.6-pro -z "..."`), puis relire la
ligne `billing_provider` du tour. C'est cette sonde, pas le ping force, qui a
valide l'etage OpenRouter gratuit. Restaurer la chaine complete ensuite.

**Providers built-in : la cle `.env` suffit, aucun bloc `providers.<id>`.**
`openrouter` resout depuis `OPENROUTER_API_KEY` (`source: env:OPENROUTER_API_KEY`,
`base_url: https://openrouter.ai/api/v1`) sans entree dans `config.yaml` — comme
`xiaomi`. Un bloc custom du meme nom serait ignore (voir « nom canonique »
ci-dessous) : ne pas en ecrire, se contenter de la cle.

**Options de repli inexistantes.** Il n'y a PAS de `skip_on_missing_key`,
`max_retries_per_provider` ni `fail_fast` : ne pas les chercher, ne pas les
inventer. Ce qui existe : `agent.api_max_retries` (tentatives par provider avant
de passer au suivant ; defaut 3 ; 1 = bascule rapide, mais alors un 5xx
transitoire du gratuit saute vers le provider paye) et
`fallback.min_switch_reset_seconds` (seule cle de la section `fallback` ; 0 =
bascule immediate). Le saut des providers sans credential est implicite : a la
resolution une `AuthError` fait avancer la chaine, et un client non
constructible marque l'entree `unavailable` pour la session.

**Pluriel vs legacy.** `fallback_providers` (pluriel) est la source de verite et
garde son ordre ; `fallback_model` (singulier, legacy) est fusionne a la suite.
Confirmer l'absence du legacy : `hermes config get fallback_model` ->
« Config key not set ».

**Ne pas toucher aux profils sans accord.** Modifier la config racine suffit
pour le profil `default` ; pour `veille` / `watch`, demander avant. Verifier
apres coup que les modeles primaires sont inchanges : `hermes profile list`.

**Un provider custom nomme est ignore quand son nom est canonique.** La
resolution n'utilise l'entree `providers.<id>` que si le nom demande n'est pas
deja le nom canonique d'un built-in (`_shadowed_by_builtin` : le built-in gagne
uniquement quand `resolve_provider(<id>)` renvoie exactement `<id>`). Un nom
canonique (`nous`) est donc ignore au profit du built-in, mais un simple alias
ne l'est pas : `google` resout en built-in `gemini`, `gemini` != `google`, donc
l'entree custom gagne. Verifier avant d'ecrire :

```bash
venv/Scripts/python.exe -c "from hermes_cli.auth import resolve_provider; print(resolve_provider('google'))"
```

Canonique different du nom demande -> le custom passe ; canonique identique ->
renommer l'entree (ex. `google-openai`) ou assumer le built-in.

**`-z` : `--provider` et `--model` vont ensemble.** `hermes --provider eco -z
"ping"` echoue avec « --provider requires --model (or HERMES_INFERENCE_MODEL) ».
Ecrire `hermes --provider omniroute -m eco -z "ping"`, ou simplement
`hermes -m eco -z "ping"` pour le provider configure par defaut : un
`--provider` sans `--model` n'est pas un raccourci, c'est une erreur d'usage.

**« Gratuit » se prouve sur `/v1/chat/completions`, pas sur `/v1/models`.** Une
cle valide renvoie 200 sur `/v1/models` meme quand le compte refuse de generer
(429 `insufficient_quota` / `card_required` : empreinte de carte exigee). Ne pas
adopter un provider dit gratuit — ni le laisser dans la chaine — sans un
alle-retour complet a 200 : sinon chaque etage echoue et le CLI ne rend qu'un
message generique. Retirer l'etage et le dire.

**Le dossier `~/AppData/Local/hermes` EST un clone du depot de configuration (ici
`hermes-home-vision`).** Avant de « restaurer depuis le repo », regarder l'etat local :
`git -C ~/AppData/Local/hermes remote -v`, `git log --oneline -3 -- config.yaml`,
`git diff -- config.yaml`. Le diff `git diff` donne exactement ce qui a change depuis le dernier
commit (model/fallback/providers), et le depot peut etre EN RETARD sur la prod : des blocs
`providers.*` ajoutes apres le dernier commit (cles deja posees dans `.env`) disparaitraient d'un
restore en bloc — restaurer cle par cle, via `hermes config set`, jamais `git checkout config.yaml`.
Un `yaml.safe_dump` global est a exclure deux fois : les tools refusent d'ecrire `config.yaml`, et le
dump perd commentaires + ordre.

**Apres `config set model.provider <x>`, `model.base_url` disparait — c'est normal.** La resolution
retombe alors sur `providers.<x>.api` : verifier le base_url reellement utilise dans `state.db`
(`session_model_usage.billing_base_url`), pas dans `config.yaml`. Ne pas le reecrire « pour etre
conforme au repo ».

**Recette detaillee provider OpenAI-compatible tiers** (sondes de resolution,
verification de cle sans exposition, catalogue de modeles) :
`references/custom-openai-provider.md`.
Route du principal, preuve du provider qui a servi le tour, plafonds de palier
gratuit par requete : `references/model-route-and-free-tier-limits.md`.

**Verifier une mise a jour Hermes : `hermes --version` peut mentir.** Il affiche
« Up to date » a partir de la ref locale `origin/main`, jamais rafraichie depuis
l'install (method `git`). Comparer avec le distant en lecture seule, sans fetch :

```bash
cd "$LOCALAPPDATA/hermes/hermes-agent"
git rev-parse HEAD          # ex. c7c2df1a...
git ls-remote origin HEAD   # ex. e2f8a073...  <- divergence = commits a recuperer
```

Des SHA differents signifient qu'il y a bien une mise a jour malgre « Up to date ».
Ne pas lancer `hermes update` a l'aveugle : la commande est sensible (approbation
utilisateur requise) et un lancement bloque ou expire ne se retente pas — demander
l'accord. Rollback d'une install git : `git reset --hard <ancien SHA>` dans
`hermes-agent`, apres `git status -sb` (arbre propre).

**`hermes doctor` : deux faux positifs a ne pas suivre.** (1) `model.default
'<valeur>' is vendor-prefixed but model.provider is 'omniroute'` se declenche des
que la valeur contient un `/` qui n'est pas un vendeur — alias de routeur
(`auto/best-reasoning`), jamais un probleme : suivre la suggestion (passer
`model.provider` a `openrouter`) sortirait la chaine d'OmniRoute. (2) « Run `hermes
setup` to configure missing API keys » est generique : verifier la presence reelle
(`grep -c '^<CLE>=.' .env`) avant de croire le diagnostic.

**Un tour lent n'est pas une bascule de chaine — lire `state.db` avant de conclure.**
Le meme primaire `auto/best-reasoning` a servi une fois en 13,6 s puis une fois en
46,9 s, avec `api_call_count = 1` les deux fois : c'est la variance de l'amont. Seul
`session_model_usage` (`model` + `billing_provider` + `api_call_count`) prouve quel
etage a servi ; la duree du tour ne prouve rien.

**Supprimer un doublon dans la chaine, verifier les 5 etages par `state.db`.** Apres
`hermes config set fallback_providers`, `hermes fallback list` relu doit montrer
`Primary` distinct des 4 entrees. Un combo OmniRoute peut etre mis en etage :
`--provider omniroute -m free-openrouter -z "ping"` -> `pong` et
`session_model_usage.model = free-openrouter` prouve que le combo a repondu par son nom.

**Un modele de DECISION n'est pas un etage de chaine — et ne se teste pas sur `/v1/chat/completions`.**
Un modele qui rend une reponse structuree (classification, choix, score) n'accepte pas le contrat de
chat : `fallback_providers` n'attend que des completions, donc il ne peut pas y entrer. Il s'appelle
en direct a cote de la chaine, et il est facture. Recette verifiee chez OpenRouter (cle
`OPENROUTER_API_KEY`, endpoint hors `/v1/` standard) :

```python
# POST https://openrouter.ai/api/v1/systemone
{"model": "typesafe/jev-1.13",      # resolu cote serveur en typesafe/jev-1.13-<date>
 "state": "<texte a classer>",
 "questions": {"<nom>": {"type": "noul",           # ou "choice" + criteria{...}
                         "instructions": "..."}}}
# -> {"model","answers":{"<nom>":{"noul":0.98} | {"choice":"billing",
#     "probabilities":{...},"confidence":1}},
#     "usage":{"input_tokens","output_tokens","cost"},"provider":"TypeSafe"}
```

Mesure : 0,36 s, 337 tokens in / 47 out, `usage.cost` 0,000014154 $ la question (~0,014 $ / 1 000
appels, ~1,4 $ / 100 000) — negligeable devant un tour de chat paye, mais pas nul : ne l'appeler
qu'aux points de decision. Proposer un tel modele pour un role auxiliaire (pre-filtre, routage)
reste une decision de l'utilisateur : l'annoncer comme tel, ne rien installer sans son accord.
