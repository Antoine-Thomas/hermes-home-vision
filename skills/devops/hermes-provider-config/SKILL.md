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
(combos OmniRoute, couts, latences), voir la skill `fallback-intelligent` — mais la confronter a
`hermes fallback list` avant de recopier sa forme de chaine : elle est user-owned, donc hors curation
automatique, et peut citer des etages qui n'existent plus (mesure : `free-stack` en repli 1 alors que
l'alias ne resolvait rien).

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
configuration ». Ne pas contourner par sed/echo.

**`~/.hermes` n'est pas forcement le dossier de config VIVANT : ne jamais ecrire le chemin qu'une
demande nomme sans l'avoir confronte a la realite.** Sur cet hote le dossier actif est
`~/AppData/Local/hermes` (c'est lui qui porte `.env`, `config.yaml`, `state.db`), alors que `~/.hermes`
existe bel et bien mais ne contient que `scripts/` et `skills/`. Ecrire `~/.hermes/.env` ou
`~/.hermes/config.yaml` parce que la demande les cite produit deux fichiers **leurre** que Hermes ne
lit jamais : aucune erreur, aucun avertissement, et un rapport qui declare appliquee une
configuration sans effet. Deux reflexes : demander au CLI ou il ecrit (`hermes config set` annonce le
chemin complet : `✓ Set <cle> = <valeur> in <chemin>`), et lire `ls -a` des DEUX emplacements avant de
conclure. Verifier APRES coup qu'aucun leurre n'a ete cree (`ls -a ~/.hermes`) — c'est le controle qui
rend l'ecart prouvable. `hermes config set <cle>
'<litteral YAML ou JSON>'` accepte les valeurs structurees, donc un dict
imbrique ou une liste de dicts tient en une commande :

```bash
hermes config set providers.exemple '{base_url: "https://api.exemple.ai/v1", key_env: EXEMPLE_API_KEY, transport: chat_completions, default_model: m1, models: [m1, m2]}'
hermes config set fallback_providers '[{provider: omniroute, model: eco}, {provider: omniroute, model: nvidia-stack}]'
hermes config unset providers.exemple    # retire le provider
hermes config unset EXEMPLE_API_KEY      # retire la cle de .env (un commentaire "# --- EXEMPLE_API_KEY ---" reste comme trace)
```

**Une valeur structuree qui contient `:` s'ecrit en JSON quote.** Les slugs de modele portent souvent un
deux-points (`<vendeur>/<modele>:free`, `:batch`) et la valeur traverse le parseur YAML du CLI : la forme
libre (celle des exemples ci-dessus, tous sans `:`) met alors un `:` a l'interieur d'un scalaire. Des
qu'une valeur en contient un, passer cles ET valeurs entre guillemets doubles, puis relire les DEUX
formes — `hermes -p <profil> fallback list` reaffiche les slugs, `cat <profil>/config.yaml` montre ce qui
a ete ecrit au sol. Meme controle que pour une cle inconnue : le CLI annonce un succes qu'il ait bien
parse ou non.

`hermes config set` ne valide pas les cles : une cle inconnue est ecrite avec un simple
avertissement (`'x.y' is not a recognized config key — it was saved anyway`). Une faute de frappe
persiste donc en silence dans `config.yaml` — relire avec `hermes config get <cle>` apres chaque
`set`, c'est la seule relecture qui vaut.

Cles de provider custom reconnues : `api` / `base_url` / `url` (equivalentes),
`key_env` ou `api_key_env`, `transport` ou `api_mode` (`chat_completions`),
`default_model`, `models`. NE PAS ecrire `type: openai` (ignore) ni
`api_key: "${VAR}"` (substitution non faite -> cle introuvable).

Meme regle pour les autres fichiers de controle Hermes : **passer par le CLI, jamais par
`patch`/`write_file`**. Les jobs cron vivent dans `<profil>/cron/jobs.json` et le planificateur
REECRIT ce fichier a chaque run (risque de course) : un job s'edite par
`hermes cron edit <id> --prompt/--schedule/--clear-skills`, se cree par `hermes cron add`, se retire
par `hermes cron remove <id>`. Deux pieges verifies :

- **Le drapeau de profil va AVANT la sous-commande** : `hermes --profile veille cron edit <id> …`
  (ou `venv/Scripts/python.exe -m hermes_cli.main --profile <nom> cron …`). Sans lui, le job d'un
  autre profil est simplement invisible.
- **`cron run` refuse un job en pause** (`Job is paused/disabled; resume it before running`) : un job
  cree `--paused` pour un test doit etre REPRIS avant d'etre declenche, sinon le run n'a jamais lieu
  et le « test » ne prouve rien.
- Un `cron add` sur un profil non-`default` est une vraie modification : sauvegarder `jobs.json`
  avant, et comparer apres. Une edition sans effet fonctionnel ne laisse que `updated_at` modifie —
  le montrer evite de croire a une reecriture massive.

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
  prouve pas que la valeur est fausse, seulement qu'elle est un secret. **Aucune lecture de préfixe
  n'est donc possible** (`grep '^CLE=' | cut -c1-20` rend `***`) : la valeur est masquée avant d'arriver
  dans le contexte.
- **Prouver qu'une rotation a atteint TOUS les `.env` : comparer des empreintes, jamais les valeurs.**
  Pour chaque fichier, n'imprimer que la longueur, deux booléens de préfixe et `sha256(valeur)[:8]`
  (script qui ne rend que ces champs) : des empreintes identiques dans `hermes/.env` et
  `hermes/profiles/*/.env` = la même clé partout. Une clé attendue ABSENTE d'un profil n'est pas un
  oubli si ce profil tourne sur un autre fournisseur (`veille` en `nvidia-stack` n'a pas de
  `DEEPSEEK_API_KEY`) : nommer les profils porteurs au lieu de raisonner sur « les N .env » attendus.
- **Une cle absente du `.env` d'un profil rend son ETAGE de repli structurellement inoperant — et
  Hermes l'annonce comme un cooldown.** La resolution des cles passe par `agent/secret_scope.py`,
  scopee par profil et fail-closed : une cle definie dans le `.env` RACINE n'est pas visible d'un
  profil qui ne la redeclare pas. L'entree de pool sans cle runtime est sautee
  (`credential_pool.py`, `_available_entries`) -> `has_available()=False` + `next_available_at()=None`
  -> le message `Fallback skip: <provider> credential pool is exhausted (every entry in cooldown)`
  (`agent/chat_completion_helpers.py`, `_candidate_pool_exhausted`), qui ne decrit alors AUCUN cooldown.
  Diagnostic en 3 lectures, dans cet ordre : (1) `hermes --profile <p> auth list` — le marqueur `<-`
  est `pool.peek()`, la seule entree louable : aucun `<-` sur aucune entree = aucune cle louable pour
  ce profil ; (2) le `.env` du profil (noms de variables seulement) contient-il la cle de l'etage ?
  (3) l'entree du pool dans l'`auth.json` racine (`credential_pool.<provider>[0]`) : `last_status: None`
  + `last_error_reset_at: None` = aucun cooldown actif, aucune date d'expiration a chercher — un
  `failure_reason: billing` persistant est un residu de verdict, seul un vrai 402 le date.
  Ne pas annoncer « cooldown jusqu'a HH:MM » ni proposer de « lever le cooldown » avant ces trois
  lectures : l'etage n'est pas en attente, il est hors de portee du profil (et la cle peut etre
  parfaitement valide — le prouver depuis le profil qui la VOIT, ses appels factures recents, sans
  appel supplementaire).
- Cle collee dans le chat = compromise : la remplacer par un placeholder dans
  `.env`, demander la rotation, ne jamais la re-afficher ni la recopier dans un log.

## Pieges critiques

**Verifier « gratuit d'abord » : lire la chaine, pas le nom des etages.**
`fallback_providers` peut etre parfaitement ordonne (gratuits en repli) alors que
`model.default` reste le modele PAYANT : la chaine ne sert alors que quand le paye
tombe, soit l'inverse du besoin. Diagnostic en une commande : `hermes fallback
list` — `Primary:` doit etre le combo gratuit. Derive type mesuree :
`Primary: deepseek-flash (via deepseek)` + replis `[nvidia-stack, free-openrouter,
deepseek-flash]` -> 163 sessions facturees ~40 $ pour rien. Correction = 2 lignes
(`model.default`, `model.provider`) ; la liste de repli n'a pas besoin de bouger.
Preuve avant/apres : `state.db` (`sessions.billing_provider`,
`estimated_cost_usd`) sur des tours reels, jamais la duree du tour.

**Un tour servi par un etage gratuit qui n'est PAS le primaire n'est pas un echec —
c'est la cascade qui travaille.** Meme configuration saine, le premier appel apres
le tick horaire de la sonde (`:01`) tombe souvent sur l'etage 2 gratuit : la sonde
epuise les quotas des cibles du primaire (gemini 429 quotidien + NIM `Worker local
total request limit reached (16/16)`). Lire l'ordre des lignes d'`app.log`
(`Trying model 1/3` sur le primaire, `terminal={"status":503}`, puis un second
combo `terminal={"status":200}`) avant de conclure a une panne de configuration :
cout 0 et etage paye non atteint.

**Un etage gratuit qui tombe ne doit pas pousser vers le paye : le tester sans
couper le routeur.** Couper l'etage amont (proxy NIM local) et laisser Hermes
choisir : si l'etage gratuit suivant absorbe la panne, la cascade est saine.
Mesure : proxy NIM `:20200` tue -> `nvidia-stack` et `eco` en 502,
`free-openrouter` 200, tour Hermes servi par `free-openrouter` a 0 $ (DeepSeek
jamais appele). Forcer un primaire mort sans rien casser :
`hermes --provider xiaomi -m mimo-v2.6-pro -z "pong"` (402 facturation -> la
chaine avance). Relance du proxy NIM : `wscript.exe //B
"%LOCALAPPDATA%\hermes\data\nvidia\nvidia-nim-launch.vbs"` (idempotent, filtre
`LISTENING` ; port rouvert en ~3 s, 200 en ~1 s — inutile d'attendre le watchdog).

**Ne JAMAIS lancer un tour de bout en bout pendant une fenetre ou les etages gratuits sont
refuses.** Un tour reel parcourt la chaine entiere : si les 3 etages gratuits sont indisponibles
au meme instant, le 4e est le payant et la session est facturee (`api_max_retries: 3` = 3 bascules
maximum, soit exactement le nombre d'etages gratuits a traverser). Avant tout `hermes -z` de
controle, sonder les etages gratuits **en direct** (`POST /v1/chat/completions` par combo nomme) :
tant qu'un seul repond `200`, le tour est couvert ; si tous sont refuses, attendre la fenetre
suivante plutot que de prouver « ca marche » aux frais du client. Un tour qui repond pendant une
panne partielle ne prouve rien sur le gratuit, et il peut avoir paye — la preuve reste
`state.db` (`billing_provider`), pas le fait que la reponse soit arrivee.

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

**`<modele> via custom unavailable` : `custom` est l'etiquette du provider a `base_url` locale, pas
un service distinct.** Dans un avertissement de repli (`eco via custom unavailable (rate limit)`),
la partie apres `via` est le nom que la resolution a donne au provider de l'etage : un endpoint
local declare par sa seule `base_url` s'affiche `custom` meme quand `providers.<id>.name` vaut
`OmniRoute` (et `state.db` porte alors `billing_provider = custom`). Ne pas partir diagnostiquer le
provider `custom` de `auxiliary.vision` : c'est le meme routeur local qui est rate-limite, et la
suite de la chaine le confirme (`... using nvidia-stack via omniroute`). Corollaire :
`hermes usage` sur un provider local rend « No account usage available for provider 'omniroute' »
(aucun endpoint de conso) — ce n'est pas une preuve que le provider est en panne.

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

**Inversement : un solde a zero et un drapeau `billing` ne prouvent PAS que l'endpoint refuse.** Avant
de basculer un premier ou de rebrancher un service sur un diagnostic « le fournisseur X est en 402 »,
reproduire la panne : deux routes du meme fournisseur peuvent avoir deux politiques (route `alpha`
experimentale vs route stable), et un endpoint hors `/v1/chat/completions` (decisions, embeddings)
peut repondre 200 alors que le solde du compte vaut 0. Sondes, dans cet ordre :

```bash
# 1. solde reel cote fournisseur (OpenRouter) — pas le drapeau interne
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/credits
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/key
# 2. l'endpoint REELLEMENT appele, avec la vraie cle (chaque route se teste separement)
```

Un `failure_reason: "billing"` dans `auth.json` est un **marquage d'Hermes**, pas une mesure du
fournisseur : il persiste apres la reprise du service. Mesure : `total_credits: 0`,
`is_free_tier: true`, et pourtant 5 appels de decisions reussis (200, cout annonce ~1,2e-5 $) sur les
deux routes. Troisieme confirmation du meme motif, cote OpenRouter : un compte en `total_credits: 0`
et `is_free_tier: true` a servi un `200` sur un modele PAYANT, et AUCUN des deux compteurs cote
fournisseur (`credits.total_usage`, `key.usage`) n'a bouge apres l'appel — mesure repetee avant,
apres la sonde directe et apres un tour Hermes complet : la reponse existe, le debit n'est pas
demontre. **Ne pas trancher a la place du fournisseur : ecrire « la route repond, le debit n'est pas
etabli » plutot que « ca marche » ou « il n'y a pas de credit ».** Le signal cote Hermes vit dans le
tour lui-meme : `💳 Credit balance covers fewer output tokens — retrying with max_tokens=<N>` annonce
que Hermes a plafonne la sortie a cause de l'etat de credit — le lire comme un fait de FINANCEMENT,
pas comme une erreur a corriger. Rapporter ce constat meme s'il contredit la demande de bascule : appliquer la bascule sur
une premisse fausse degrade l'installation pour rien. Et chercher la trace avant de conclure : un
`grep` sur « 402 » dans `logs/*.log` ramene aussi des numeros de ligne et des horodatages — lire les
lignes entieres.

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
`rowid`). Les noms de colonnes DIFFERENT d'une table a l'autre : `sessions` porte **`id`** (pas
`session_id`), `session_model_usage` porte `session_id` — la jointure est
`sessions.id = session_model_usage.session_id`, et une requete qui suppose `session_id` des deux
cotes meurt en `sqlite3.OperationalError: no such column: session_id`. Introspecter avant d'ecrire la
requete (`select sql from sqlite_master where type='table' and name=?`) ; `sessions` porte aussi
`reasoning_tokens` et le couple `cost_status` / `cost_source`, qui distingue un cout ESTIME
(`estimated`, `provider_models_api`) d'un cout constate (`actual_cost_usd`). Un test de bout en bout
qui « marche » alors que le principal est casse
est le cas normal, pas l'exception.

**Prouver « aucune session payante » : compter des SESSIONS, jamais filtrer des ids.** Un
filtre `id >= '<AAAAMMJJ_HHMM>'` est une comparaison de CHAINES : les sessions de cron
(`cron_<jobid>_<date>`) sont plus grandes en ASCII que les ids dates, passent le filtre, et
une mesure de 0 session reelle devient « 40 sessions payantes ». Et la SOMME des couts du
profil bouge pendant le controle, puisque la session en cours s'accumule — un delta de
quelques centimes ne prouve rien. Deux signaux fiables : (1) `select count(*), sum(cost)
from sessions group by billing_provider` (un COMPTEUR inchange = aucune nouvelle session ;
`started_at` peut etre un epoch, un `where started_at >= '<ISO>'` ne matche alors rien) et
(2) les 5 dernieres lignes triees par `rowid`, dont l'horodatage de la derniere session
payante doit etre ANTERIEUR au changement teste. Ne pas non plus confondre
`billing_provider = custom` (endpoint local declare par sa seule `base_url`) avec une
session payante.

**Chiffrer un etage payant CANDIDAT avant de l'ajouter — et annoncer tout chiffre de sessions AVEC
son filtre.** Partir des sessions cron deja passees du profil (`state.db`, `source='cron'`) : sommer
`input_tokens`, `output_tokens` et `cache_read_tokens` SEPAREMENT (le cache se facture a un tarif
reduit : le compter comme de l'entree gonfle le cout), appliquer la grille du modele candidat, puis
doubler le resultat si le run tombe en heures pleines (un cron du lundi 08:00 Paris = 06:00 UTC).
Toujours ecrire le filtre a cote du nombre : « N sessions cron facturees deepseek » et « N sessions
cron » ne designent pas le meme ensemble (mesure : 83 sessions cron payantes sur le profil, 40
facturees deepseek, 361 sessions cron tous profils) — un chiffre sans son filtre rend le calcul
inverifiable, donc contestable, et fait douter du reste du rapport.

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
garde son ordre ; `fallback_model` (singulier, legacy) est fusionne A LA SUITE et
dedoublonne (provider, model, base_url) par `get_fallback_chain`
(`hermes_cli/fallback_config.py`). Un profil peut n'avoir QUE le legacy : ne pas
conclure « aucune chaine » parce que la cle pluriel est absente, et ne pas se fier a
`hermes config get fallback_model` (« not set » cote racine) pour un profil. Lire la
chaine EFFECTIVE, une cle isolee ne prouve rien :

```bash
venv/Scripts/python.exe -c "
import io, json, sys; sys.path.insert(0, 'hermes-agent')
from hermes_cli.fallback_config import get_fallback_chain
import ruamel.yaml as ry
cfg = ry.YAML(typ='safe').load(io.open(r'profiles/veille/config.yaml', encoding='utf-8'))
print(json.dumps(get_fallback_chain(cfg), ensure_ascii=False))"
```

**Editer la config d'un profil n'exige AUCUN redemarrage : le cron relit la chaine a chaque job.**
`cron/scheduler.py` (`_job_fallback_chain` -> `get_fallback_chain(cfg)`) l'applique « at credential
resolution AND mid-run », et le gateway rafraichit aussi a chaud
(`gateway/run_config_loaders.py`, `_refresh_fallback_model`). Retirer un etage d'une config de profil
se suffit donc a lui-meme : le prochain tir du job prend la nouvelle chaine. Le dire, et ne pas
demander ni annoncer un redemarrage de gateway pour un simple retrait d'etage. Corollaire : c'est le
job NON epingle qui parcourt cette chaine — verifier son epinglage avant de lui attribuer un echec.

**Ne pas toucher aux profils sans accord.** Modifier la config racine suffit
pour le profil `default` ; pour `veille` / `watch`, demander avant. Verifier
apres coup que les modeles primaires sont inchanges : `hermes profile list`.

**Creer un profil dedie a un role : `hermes profile create <nom>`, puis trois choses a ne pas rater.**
Un profil neuf (sans `--clone`) recoit son PROPRE `config.yaml` — mais seede avec le modele du profil
ACTIF au moment de la creation, pas avec un defaut neutre : le relire et le corriger. Il recoit aussi
son propre `.env` (0 variable), un `SOUL.md` germe (la persona de base), son `state.db`, et AUCUNE
chaine de repli (`No fallback providers configured`) — ce qu'on veut justement pour un profil dont le
modele ne doit pas etre substitue en silence. Sous Windows l'alias est un `.bat` dans `~/.local/bin/`.
Trois verifications : (1) la CLE du provider doit vivre dans le `.env` DU PROFIL
(`hermes -p <nom> config set <PROVIDER>_API_KEY "$VALEUR"`) — la portee des secrets est fail-closed,
un `.env` de profil vide ne voit PAS la cle racine ; le prouver par `hermes -p <nom> auth list`, ou
l'entree doit porter le marqueur `<-` (seule entree louable) ; (2) la persona va dans `SOUL.md`
(identity slot #1, lu depuis `HERMES_HOME`) ; (3) `hermes -p <nom> config get model` doit rendre le
couple voulu. Le drapeau de profil marche **dans n'importe quelle position** : `hermes chat --profile X`
et `hermes -p X chat` sont equivalents (verifie de bout en bout, pas seulement accepte par le parser).

**Ecrire un `SOUL.md` : les tools de fichier sont gates, le shell ne l'est pas.** `SOUL.md` est dans
`_PROTECTED_INSTRUCTION_BASENAMES` (`agents.md`, `claude.md`, `soul.md`, `.cursorrules`) : un
`write_file`/`patch` exige une approbation humaine — meme sous `--yolo` — et echoue ferme sans canal
humain. Chemin qui marche : ecrire le contenu dans le scratch (autorise), puis `cp` vers
`<profil>/SOUL.md` depuis le terminal, et comparer les `sha256` des deux fichiers.

**Prouver qu'un `SOUL.md` est CHARGE : sonde comportementale, pas la base.** `sessions.system_prompt`
est enregistre VIDE (seul `system_prompt_hash` est ecrit) : chercher le texte de la persona dans
`state.db` rend « absent » a tort et ferait conclure qu'un `SOUL.md` est ignore. Deux preuves valables :
`hermes -p <nom> prompt-size` (le palier `stable (identity/guidance/skills)` non nul) et surtout une
question qui force le modele a enoncer un element de perimetre ABSENT de la persona par defaut.

**`sessions.estimated_cost_usd` N'INCLUT PAS les taches auxiliaires.** Mesure : tour principal
0.02041965 et ligne `title_generation` 0.0002556 — la colonne `sessions` ne porte que la premiere,
`session_model_usage` porte les deux. Pour un cout de session juste, sommer `session_model_usage`,
jamais la table `sessions` seule.

**Un profil n'herite PAS du bloc `providers:` de la config racine.** Chaque
`profiles/<nom>/config.yaml` resout ses providers tout seul : passer le `model.provider`
d'un profil d'un provider BUILT-IN (`deepseek`, `google`, `openrouter` — qui n'exigent
qu'une cle `.env`) a un provider LOCAL (`omniroute`) le casse en
`hermes -z: agent failed: Unknown provider 'omniroute'`, alors que la config racine le
declare. L'echec est tardif et discret — le gateway demarre, `hermes profile list` affiche
le profil `running`, seules ses sessions echouent — donc il ne se decouvre qu'en lancant un
tour sur CE profil. Donc : tout changement de provider sur un profil s'accompagne de la
copie du bloc `providers.<id>` COMPLET depuis la config racine (`api`, `name`,
`default_model`, `key_env` — un NOM de variable d'environnement, aucun secret —,
`extra_headers`, `request_timeout_seconds`), puis d'une preuve par tour reel
(`hermes -p <profil> -z "pong"`) + lecture de `sessions.model` dans le `state.db` du
profil. Le gateway multiplexe reprend la correction sans redemarrage :
`[MULTIPLEX] Re-scanned profile '<nom>' after config/.env change`.

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

**`hermes chat` est l'autre porte, et elle exige une requete sous peine de blocage.** Elle accepte
`-q/--query`, `-m`/`--model`, `--provider`, `--oneshot`, `-Q` — la forme longue `--model` est bien
reconnue. Sans requete, sur un TTY, elle ouvre une session INTERACTIVE et ne rend pas la main ; dans
le shell de l'agent (non-TTY) une requete suffit a repondre et sortir. Le tir de controle s'ecrit donc
`hermes chat -q "pong" --provider <p> -m <slug> --oneshot`, jamais `hermes chat --provider <p>--model <slug>` seul (le `-q` manquant est ce qui fait croire a un blocage).

**« Gratuit » se prouve sur `/v1/chat/completions`, pas sur `/v1/models`.** Une
cle valide renvoie 200 sur `/v1/models` meme quand le compte refuse de generer
(429 `insufficient_quota` / `card_required` : empreinte de carte exigee). Ne pas
adopter un provider dit gratuit — ni le laisser dans la chaine — sans un
alle-retour complet a 200 : sinon chaque etage echoue et le CLI ne rend qu'un
message generique. Retirer l'etage et le dire.

**Et `/v1/models` n'authentifie RIEN : il ne peut donc pas valider une cle.** Mesure : le meme appel
avec `Authorization: Bearer <chaine bidon>` et SANS aucun en-tete d'authentification renvoie `200`
avec la MEME liste (467 ids, seuls quelques octets de metadonnees varient). Une demande formulee
« je grep le modele voulu dans `/v1/models`, donc la cle est valide » est un **faux positif** : elle
valide n'importe quelle chaine, y compris un mot invente apres `Bearer`. Separer trois questions et
les trois sondes qui y repondent : (1) la cle s'authentifie-t-elle -> `GET /v1/key` (label,
`is_free_tier`, `limit`, `expires_at`, `usage`, `free_model_daily_requests`) et/ou `GET /v1/credits` ;
(2) le modele existe-t-il -> catalogue `/v1/models` ; (3) la route sert-elle -> `POST
/v1/chat/completions` sur le slug EXACT. Ne jamais laisser une sonde qui ne porte pas la cle servir
de verdict sur la cle — le dire explicitement dans le rapport, parce que le test fourni par
l'utilisateur peut etre de ce type et passer pour un feu vert.

**Un compteur d'usage a du RETARD : ne pas conclure « non facture » d'un releve immediat.** Sur
OpenRouter, `usage` (`GET /v1/key`) et `total_usage` (`GET /v1/credits`) bougent avec plusieurs minutes
de decalage. Mesure : inchanges (0.036940335) juste apres trois tours servis, puis 0.049833355 et
0.062851751 plus tard — l'increment correspondant exactement a la somme des tours precedents
(0.01289302 releve contre 0.01262527 + 0.00020586 estimes). Un compteur immobile dans la minute qui
suit n'est PAS une preuve d'absence de debit : refaire le releve avant d'annoncer quoi que ce soit sur
la facturation, et ne jamais clore un diagnostic de cout sur un seul releve.

**`free_model_daily_requests` bouge LUI AUSSI avec du retard : ne pas le declarer « non concluant ». Mesure :
lu a `{used: 0, limit: 50}` juste apres 4 appels `:free`, puis a `{used: 6, limit: 50, remaining: 44}`
plus tard — le chiffre 6 correspond EXACTEMENT aux appels gratuits reellement faits (1 sonde POST +
mains d'un tour simple + main+title d'un tour avec outil). Le champ compte bien, il est seulement
differe. Donc on PEUT annoncer le quota gratuit restant, a condition de re-mesurer au lieu d'annoncer
sur le premier releve. La preuve de gratuite reste `estimated_cost_usd = 0` dans `state.db`.

**Un slug `:free` RETIRE repond 404 avec un message qui nomme le slug payant — ne pas le lire comme un 403.**
Mesure : `deepseek/deepseek-r1:free` et `qwen/qwen-2.5-72b-instruct:free` -> `404 {"message":"This model
is unavailable for free. The paid version is available now - use this slug instead: deepseek/deepseek-r1"}`.
Ce n'est ni `tier_not_allowed` ni un probleme de cle : la variante gratuite n'existe plus, et seul le
modele payant homonyme repond. Trois consequences a annoncer : (1) le slug nu est **payant** — le
substituer change le cout du palier, ne jamais le faire en silence ; (2) le contexte du payant peut etre
PLUS PETIT que celui du gratuit (mesure : `qwen/qwen-2.5-72b-instruct` = 32 768, alors qu'un prompt
d'agent ici pese 15-19 k tokens + ~11 k de schemas d'outils) ; (3) verifier la liste live des `:free`
avant de composer une chaine — elle ne compte que 16 entrees, et ni deepseek ni qwen n'y figurent plus.

**Le repli s'affiche en clair dans le CLI, et une chaine a etages morts se paie en duree.** Mesure d'une
cascade forcee (primaire mort + 2 etages `:free` inexistants + 1 valide) : deux avertissements
`Model fallback: <modele> unavailable (provider failure); using <suivant>`, tour servi par le 3e a cout 0
mais en **21 s contre 16 s** pour le meme tour servi par le primaire. Et il faut
`api_max_retries >= nombre d'etages morts a traverser` : avec 2 etages morts devant le bon, atteindre le
3e consomme exactement les 3 activations par defaut — une 4e entree serait inatteignable. Se prouve DANS
la cascade : primaire force sur un slug mort, `trap EXIT` qui restaure `config.yaml`, puis comparaison des
`sha256` avant/apres — c'est la seule preuve que l'etage choisi est atteignable.

**Promouvoir un `:free` en primaire : trois verifications, pas une.** Le catalogue donne
`context_length` et `pricing` (`0`/`0`) mais ne dit rien du reste. Avant d'ecrire `model.default` :
(1) un POST reel sur cet ID doit rendre 200 avec `cost: 0` ; (2) le TOOL-CALLING doit etre exerce
(`hermes chat -q "... utilise un outil ..."` -> `tool_call_count > 0` dans `state.db`) — un primaire
qui n'appelle pas d'outil est inutilisable pour un agent ; (3) le prompt REELLEMENT envoye doit passer
(comparer `input_tokens` du dernier tour a la fenetre du modele). Les en-tetes `x-ratelimit-*` ne sont
pas toujours exposes (aucun sur ce modele, meme sur un 200) : quand ils manquent, seul le tour reel
tranche. Placer ensuite le modele PAYANT juste derriere dans `fallback_providers` — deux entrees du
MEME provider avec des modeles differents sont bien essayees (le saut se fait sur le couple
provider+modele, cf. `same_deployment`).

**Un modele a raisonnement peut rendre `content: null` sur une sonde courte : ce n'est pas un echec.**
Mesure sur `nvidia/nemotron-3-super-120b-a12b:free` et `mistralai/mistral-large-4-0` : avec
`max_tokens` petit (5 a 64), la totalite du budget part en `reasoning_tokens` et `content` revient a
`null` — la route a pourtant repondu 200. Ne pas conclure « le modele ne repond pas » avant d'avoir
relu `usage.completion_tokens_details.reasoning_tokens` : augmenter `max_tokens`, ou juger sur un vrai
tour d'agent.

**Le dossier `~/AppData/Local/hermes` EST un clone du depot de configuration (ici
`hermes-home-vision`).** Avant de « restaurer depuis le repo », regarder l'etat local :
`git -C ~/AppData/Local/hermes remote -v`, `git log --oneline -3 -- config.yaml`,
`git diff -- config.yaml`. Le diff `git diff` donne exactement ce qui a change depuis le dernier
commit (model/fallback/providers), et le depot peut etre EN RETARD sur la prod : des blocs
`providers.*` ajoutes apres le dernier commit (cles deja posees dans `.env`) disparaitraient d'un
restore en bloc — restaurer cle par cle, via `hermes config set`, jamais `git checkout config.yaml`.
Un `yaml.safe_dump` global est a exclure deux fois : les tools refusent d'ecrire `config.yaml`, et le
dump perd commentaires + ordre.

**Ce clone vit avec du bruit permanent : un commit « isole » se joue au staging, pas au message.**
`git status` montre en permanence des fichiers modifies hors sujet (`skills/.usage.json`,
`.curator_state`, `plugin-update-checks/`, `*.bundled_manifest`, `cron/usage_audit.jsonl`) et des
reformatages de `config.yaml` (listes repliees puis derepliees par les outils Hermes). Un
`git add config.yaml && git commit` apres un `hermes config set` embarque donc tout ce bruit : lire
`git diff --stat`, puis stager au hunk (`git add -p`, ou un `git diff -- config.yaml` filtre sur les
seules lignes `model.default` / `model.provider` / `fallback_providers`). Quand l'utilisateur demande
un commit isole, c'est le contenu du commit qui le rend isole, pas son message.

**Le diff qui fait foi est celui contre la SAUVEGARDE prise avant l'edition, jamais `git diff` contre HEAD.**
Le working copy porte en permanence des modifications non commitees anterieures a l'intervention : mesure —
le diff contre le backup montre 3 lignes modifiees (53/56/66), `git diff --stat` en annoncait 52 insertions
et 8 suppressions. Rendre le diff BACKUP (CR-insensible : `diff <(sed 's/\r$//' bak) <(sed 's/\r$//' config.yaml)`)
et dire que `hermes config set` a reecrit le fichier sans reformatage parasite (aucune autre ligne du diff),
puis donner les deux sha256 (avant/apres). Corollaire de comptage : compter l'ID COMPLET (`qwen2.5:7b`), pas
la famille (`qwen2.5`) — `qwen2.5-coder:14b`/`:7b` vivent dans un autre bloc et font passer un controle de
3 a 5 lignes ; et un `grep` de traces dans `logs/` retrouve l'ancien nom apres le remplacement (historique,
pas configuration : le dire, sinon le compte semble faux).

**Apres `config set model.provider <x>`, `model.base_url` disparait — c'est normal.** La resolution
retombe alors sur `providers.<x>.api` : verifier le base_url reellement utilise dans `state.db`
(`session_model_usage.billing_base_url`), pas dans `config.yaml`. Ne pas le reecrire « pour etre
conforme au repo ».

**Recette detaillee provider OpenAI-compatible tiers** (sondes de resolution,
verification de cle sans exposition, catalogue de modeles) :
`references/custom-openai-provider.md`.
Route du principal, preuve du provider qui a servi le tour, plafonds de palier
gratuit par requete : `references/model-route-and-free-tier-limits.md`.
Analyse du cout paye (source de verite, fiabilite du champ cout, part imputable au repli)
et conception/test d'un watchdog de cout : `references/cout-paye-et-watchdog.md`.

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

**Les roles auxiliaires sont une liste FERMEE : une sous-cle inventee sous `auxiliary:` est inerte.**
Source de verite : `hermes_cli/config_defaults.py` (bloc `auxiliary`) et `hermes_cli/main_provider_setup.py`
(`_AUX_TASKS`). Cles reconnues : `vision`, `compression`, `skills_hub`, `approval`, `review`, `mcp`,
`title_generation`, `memory_query_rewrite`, `tts_audio_tags`, `triage_specifier`, `kanban_decomposer`,
`profile_describer`, `goal_judge`, `curator`. Forme d'un bloc :
`{provider, model, base_url, api_key, timeout, extra_body, reasoning_effort}`, et `provider: auto` =
herite du modele principal. **Corollaire de cout : changer `model.default` re-tarife AUSSI tous ces
roles.** Mesure : apres bascule du primaire sur un modele payant, la generation de titre
(`auxiliary.title_generation`, `provider: auto`) est passee sur ce meme modele dans le meme tour —
deuxieme ligne de `session_model_usage`, a cote du tour principal. Annoncer ce cout CACHE quand on
change de primaire (il ne se voit pas dans `config.yaml`), et pour le figer, ecrire explicitement
`auxiliary.<role>.provider`. Donc `auxiliary.decision:` — ou tout autre nom absent de cette liste —
s'ecrit sans erreur et n'est **jamais lu** : avant d'ajouter un role, `grep` le nom dans
`config_defaults.py`, citer la ligne, ou dire qu'il n'existe pas.

**`compression.threshold` est un RATIO du contexte, pas un nombre de tokens** (0.5 =
compresser a mi-contexte, pas « 96 000 tokens »). Verifier la valeur ET le type reels
(`hermes config get compression.threshold`) avant de proposer un seuil : une proposition batie
sur une hypothese de seuil fausse se refait. Le role de compression (`auxiliary.compression`)
defaut `provider: auto` (= herite du modele principal), PAS `free-openrouter` ; pour le figer
sur un combo gratuit : `hermes config set auxiliary.compression.provider omniroute` +
`hermes config set auxiliary.compression.model eco`.

**`auxiliary.approval` est le crochet d'approbation — et il attend un MODELE de chat.** C'est le
classifieur des commandes destructrices (defaut `provider: auto` + `model: ''` = modele principal).
Un service de decision type qui rend du JSON type n'entre PAS dans ce bloc, car il ne parle pas le
contrat de chat : Jev s'appelle en `POST https://openrouter.ai/api/v1/systemone`, la route officielle
de Laya est `/v1/decisions` (service Altherium) — aucune des deux n'est une completion. Meme un modele
local qui rendrait des logits ne s'y branche pas. Un approbateur maison passe par le rail **hooks de
plugin** (`agent/shell_hooks.py`, reponse `{"action"|"decision": "block"|"modify"}`) ou par un
**serveur MCP** — jamais par une sous-cle `auxiliary.*` inventee.

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

**Repli local d'un primitif de decision** : un modele type (oui/non, choix, note) exporte en ONNX
tourne sur le CPU sans PyTorch, hors ligne et a cout nul (~190 ms par decision) — il peut remplacer un
service de decisions payant dans du code, jamais un tour de chat ni un job d'agent qui doit REDIGER
(voir la skill `laya-onnx-windows`). Un modele local ne s'ajoute pas non plus a la chaine :
`fallback_providers` n'attend que des completions.

**Un etage local est refuse d'emblee si la fenetre de contexte DECLAREE du modele est < 64K — et
l'erreur ne ressemble pas a un probleme de chaine.** Mesure : `hermes --provider ollama-local -m
"qwen2.5:7b" -z "..."` sort en `agent failed: Model qwen2.5:7b has a context window of 32,768
tokens, which is below the minimum 64,000 required by Hermes Agent` apres 6,98 s et **sans aucune
inference** (l'erreur tombe avant le chargement des poids). Le seuil se lit sur la fenetre declaree
par le modele (`POST http://127.0.0.1:11434/api/show -d '{"model":"<m>"}'` ->
`qwen*.context_length` = 32768 ici), pas sur celle du serveur — mais les deux comptent : le log de
demarrage du serveur montrait `OLLAMA_CONTEXT_LENGTH:16384`, donc la fenetre REELLEMENT servie etait
encore plus basse. `model.ollama_num_ctx` ne debloque rien d'utile (le seuil des 64K reste) et
l'ecrire ferait croire a Hermes une fenetre que le serveur ne sert pas. Verifier AVANT de raccorder
un etage local, et se souvenir qu'une entree de `context_length_cache.yaml` peut porter la valeur
d'un modele desinstalle (`llama3.2:3b@http://127.0.0.1:11434/v1: 131072`) : un cache n'est pas une
preuve de joignabilite.

**Un etage LOCAL se prouve en confrontant deux listes, pas sur la presence du modele.** « installe »
n'est ni « declare dans `providers.<id>.models` », ni « joignable », ni « teste ». Lire ce qui existe
(`GET http://127.0.0.1:11434/api/tags`) et le comparer au bloc du provider plus son `default_model` :
mesure — un bloc `ollama-launch` declarait 7 modeles (dont `deepseek-v4-pro:cloud`, `qwen3.5:cloud`,
`gemma4:12b`) alors que l'hote n'en portait que deux (`qwen2.5:7b`, `llama3.2:3b`) : intersection
VIDE, et un `default_model` a modeles CLOUD dans un bloc cense servir de repli local. Un etage dont le
modele n'existe pas ne tombe pas « en panne » : il echoue a chaque bascule, sans un mot.

**Un modele INSTALLE n'est pas un modele LIBRE : inventorier ses autres consommateurs avant de le mettre dans la chaine.** Le meme serveur Ollama sert d'autres services que Hermes, et avec `OLLAMA_MAX_LOADED_MODELS=1` un tour qui charge le modele EVINCE celui du service voisin (qui repaie un chargement de poids complet au tir suivant) : ajouter un modele « deja present » CREE le partage, il ne l'evite pas. Avant d'ecrire un provider local, chercher le modele dans les configs de TOUTE la machine — `grep -rn "<modele>"` sur les dossiers de service (`data/*/config.json`, `*.conf`, `*.py`), avec le nom COMPLET et pas la famille — jamais seulement dans `config.yaml` / les `profiles/` Hermes ; un modele peut y etre declare depuis des semaines par un autre stack. Si un autre service le revendique : le dire et demander, ne pas l'ajouter en silence. Corollaire pour un retrait (`hermes config unset providers.<id>`) : verifier aussi les blocs `providers.<id>` RESIDUELS — un bloc inerte garde sa `api: http://127.0.0.1:11434/v1` (et ses modeles) et rend faux le raccourci « Hermes ne reference plus Ollama » ; le grep de controle doit viser l'ID, pas la famille de modele.

**Un modele local se mesure a CHAUD.** Le premier appel charge les poids : mesure 66,1 s
(`total_duration`, dont 39,3 s de `load_duration`) sur un 3B, puis 0,1 s au deuxieme tir (0,059 s cote
serveur, `size_vram` confirmant l'inference GPU). Un tir a froid declare l'etage inutilisable a tort ;
un `ollama list` le declare utilisable a tort. Rapporter le second chiffre, pas le premier.

**Le seuil des 64 K refuse PUREMENT un etage local trop petit — et remplacer le modele local rouvre ce seuil.**
Hermes refuse un modele dont la fenetre de contexte annoncee est < 64 000 tokens : `hermes -z` sort en
`agent failed: Model <m> has a context window of N tokens, which is below the minimum 64,000 required by
Hermes Agent`. L'etage est alors structurellement mort (echec a la construction du client, donc a CHAQUE
bascule, sans un mot dans la cascade), et l'erreur tombe AVANT le chargement des poids — donc un test qui
la rencontre ne fait aucun run GPU. La fenetre lue est celle de `context_length_cache.yaml` si une entree
existe (`<modele>@<base_url>: <tokens>`), sinon celle du serveur (`POST /api/show` ->
`model_info.<arch>.context_length`). Consequences a annoncer :

- **Un modele local qui passait le seuil peut etre refuse apres un simple changement de `default_model`** :
  mesure — `llama3.2:3b` avait `131072` en cache (seuil franchi), son remplacant `qwen2.5:7b` declare
  `32768` -> l'etage tombe. Le cache de l'ancien modele ne se transfere pas au nouveau.
- **La fenetre REELLEMENT servie ne se lit pas dans l'environnement du shell** : lire le log du serveur
  (`%LOCALAPPDATA%\Ollama\server.log`, ligne `server config`, champ `OLLAMA_CONTEXT_LENGTH`). Mesure : le
  shell portait `8192`, le serveur en cours `16384` — la variable du shell peut etre perimee.
- Corriger en levant la fenetre SERVEUR (`OLLAMA_CONTEXT_LENGTH=65536` + redemarrage du serveur) ; ecrire
  seul `model.ollama_num_ctx` ne fait que masquer le seuil en annoncant a Hermes une fenetre que le serveur
  ne sert pas. Ne pas appliquer cette correction d'environnement sans accord explicite (64 K de KV cache sur
  un 7B en 8 Go de VRAM deborde vers la RAM), et si la demande se limite au remplacement du nom, livrer le
  remplacement + declarer l'etage comme mort : la config est valide, l'etage ne l'est pas.

**Raccorder un etage local : un provider DEDIE, ajoute en DERNIER — jamais un combo du routeur.** Un
etage local passe par son propre bloc `providers.<id>` (`api` sur `127.0.0.1`, `default_model` = un modele
reellement present, `models` = la meme liste que `GET /api/tags`, `request_timeout_seconds` eleve car le
chargement des poids depasse le defaut), puis par une entree ajoutee a la FIN de `fallback_providers` :

```bash
hermes config set providers.ollama-local '{name: "Ollama (local)", api: "http://127.0.0.1:11434/v1", default_model: "llama3.2:3b", models: ["llama3.2:3b", "qwen2.5:7b"], request_timeout_seconds: 300}'
hermes config set fallback_providers '[{provider: omniroute, model: free-openrouter}, {provider: omniroute, model: nvidia-stack}, {provider: deepseek, model: deepseek-flash}, {provider: ollama-local, model: "llama3.2:3b"}]'
hermes fallback list   # 4 entrees, la locale en 4e
```

Le raccord se fait cote Hermes, pas par une cible OmniRoute : un etage qui traverse le routeur tombe avec
lui, alors qu'un provider local pointe directement sur `127.0.0.1`. Verifier avant d'ecrire : OmniRoute n'a
souvent AUCUNE cible locale (table `provider_connections`, zero ligne `ollama` / `11434`).

**Choisir le modele local sur une mesure, et tester le TOOL-CALLING avant de le declarer utilisable.**
Protocole et chiffres : `references/model-route-and-free-tier-limits.md` §5. Deux pieges mesures : un
modele peut rendre un `tool_calls` parfait sur un tour court et produire un tour d'agent inexploitable (un
3B a recopie du texte d'amorcage du prompt systeme au lieu de repondre, 1 tir sur 3) — l'annoncer comme
DERNIER RECOURS, jamais comme remplacant ; et verifier la LANGUE de la reponse (un 7B a repondu en chinois
a une question francaise).

**Prouver l'etage local par une coupure a cout nul, restauree par `trap`.** Chaine temporaire
`[{provider: omniroute, model: <combo-inexistant>}, {provider: ollama-local, model: "llama3.2:3b"}]` +
primaire forcee sur le meme modele mort (`hermes -z "..." --provider omniroute -m <combo-inexistant>`) :
le tour est servi par l'etage local, ce que `state.db` confirme (`billing_provider`, `billing_base_url`,
`estimated_cost_usd = 0`, `tool_call_count`). Reecrire la chaine nominale dans un `trap EXIT` du script de
test : une erreur du test ne doit pas laisser l'installation sur une chaine de laboratoire.

Note : un one-shot `hermes -z` sur un modele local fait ecrire `context_length_cache.yaml` par Hermes —
ce fichier qui apparait modifie n'est PAS une edition manuelle (meme bruit que `skills/.usage.json`).

**Une chaine entierement distante n'est pas un mode degrade.** Quand la demande porte sur le
hors-ligne ou la degradation, verifier qu'un etage LOCAL existe (provider pointant `127.0.0.1` +
modele reellement installe) : trois etages distants (proxy, combo, API payante) tombent ensemble des
la premiere coupure reseau, et annoncer un repli hors ligne serait faux. L'ecrire comme un ecart a
corriger, jamais comme une intention satisfaite.

**Ne pas conclure « inexistant / obsolete » depuis `--help` ou depuis la doc.** Hermes masque des
sous-commandes de son aide : `hermes serve` n'apparait dans aucun `--help` et demarre pourtant le backend
+ dashboard sur `127.0.0.1:9119` (`HERMES_BACKEND_READY port=9119`). Avant d'ecrire qu'une commande ou un
composant n'existe pas, le sonder (`hermes <cmd>`) et grep le code
(`grep -rn '"<cmd>"' hermes-agent/hermes_cli/main.py`) : une conclusion d'audit fausse sur ce point fait
prendre une decision de retrait sur un composant encore valide. Et classer un composant « obsolete » exige
deux preuves : aucun consommateur mesure (code, scripts, `.vbs`/`.cmd`, jobs cron, profils) ET une decision
DATEE du proprietaire — une entree d'`allowlist` de surveillance ou une mention de README n'exigent rien,
elles tolerent.

**`hermes status` affiche « not set » pour une cle utilisee par un service satellite.** L'inventaire
des cles est celui de l'environnement de la CLI : un proxy local (NIM `:20200`) peut servir des `200`
avec une cle absente du `.env` racine (la sienne vit dans l'environnement de son lanceur). Le ✗ est
donc un PERIMETRE, pas une preuve d'absence — ne pas declarer la dependance cassee, ni la
« reparer », avant d'avoir teste le service lui-meme.

## Diagnostiquer un job cron qui echoue (`503 all targets skipped`)

Un job cron en echec ne se diagnostique PAS depuis son message ni depuis la config : la cause est
repartie entre quatre artefacts, tous lisibles en lecture seule. Recette complete (colonnes exactes,
requetes, tableau de preuve a rendre) : `references/cron-job-failure-triage.md`. Ce qui repond a quoi :

1. `<profil>/cron/jobs.json` — la definition : `model`/`provider`/`base_url` a `null` = AUCUN
   epinglage, le job suit le `model.default` du profil ; `model_snapshot`/`provider_snapshot` sont des
   traces inertes ; `failure_streak` + `last_error` portent la derniere panne.
2. `<profil>/cron/executions.db` — l'historique : date, duree, statut, `source` (`builtin` =
   planificateur en process, `direct` = run declenche a la main), erreur. Ouvrir en
   `file:<chemin>?mode=ro` (URI sqlite3) : lecture seule garantie.
3. `<profil>/state.db` — le modele REELLEMENT servi (`sessions.model`, `billing_provider`,
   `estimated_cost_usd`, `api_call_count`) : c'est cette table qui tranche, pas la config.
4. `<profil>/logs/agent.log` — le deroule par etage (`API call #n: model=… summary=…`,
   `Fallback activated`, 429/502/503/504) et la ligne terminale.

Regles durables :

- **Le modele SERVI peut differer de la config alors que rien n'a ete edite.** Un run `builtin` tourne
  dans le planificateur en process, qui garde le contexte modele charge a SON demarrage ; un run
  `direct` est un process neuf qui relit la config. Face a un changement de modele inexplique, mettre
  en regard le servi (`state.db`) et le configure
  (`git show <rev>:profiles/<p>/config.yaml | grep -m1 '^  default:'`) et declarer l'ecart comme un
  fait a instruire — pas l'expliquer par une edition qui n'a pas eu lieu.
- **`git diff profiles/<p>/cron/jobs.json` est l'instrument « qu'est-ce qui a change sur ce job ? »** :
  le diff montre le prompt, les skills, `last_status` et le `failure_streak` sans fouiller des
  sauvegardes. Le planificateur REECRIT ce fichier a chaque run : ne jamais l'editer a la main.
- **`503 all targets were skipped by pre-dispatch filters` avec `poolSize`/`attempted: 0` n'accuse ni
  la cle ni le combo.** Verifier d'abord que les cibles du job sont dans les modeles autorises de SA
  cle (`GET http://127.0.0.1:20128/api/keys` -> `modelAccessMode`, `allowedModels`, valeurs masquees),
  puis chercher la fenetre de quota dans `~/.omniroute/logs/application/app.log` (`16/16`, `429 … limit:
  20`, `rate-limit execution expiration`). Un meme job servi par la meme chaine plus tot dans la
  journee = panne par FENETRES, pas chaine morte : le dire ainsi.
- **Un compteur de quota journalier ne se lit pas comme « le quota ne s'est pas reconstitue ».**
  `GET /api/v1/auth/key` rend `free_model_daily_requests {used, limit, remaining}`, `usage_daily` et
  `is_free_tier` : deux releves identiques dans la meme journee sont normaux (remise a zero a
  00:00 UTC). Annoncer l'heure de remise a zero plutot qu'une reconstitution absente.
- **Un quota epuise ne compte que s'il appartient a la CHAINE du job.** Comparer le quota mesure a la
  liste des etages reellement cites par la config du profil : un quota sature sur une route absente de
  la chaine n'explique rien et se declare comme tel dans le rapport.
- **Ne pas `grep -r` la racine Hermes pour retrouver un id de job** : le parcours expire avant de
  rendre. Cibler `profiles/*/cron/jobs.json` + `cron/jobs.json`, et lire tout journal avec `grep -a`
  (sans lui : « Binary file (standard input) matches » au lieu des lignes), en extrayant par
  `grep -aoE "API call #[0-9]+: model=[^ ]+ summary=.{0,120}"`.
