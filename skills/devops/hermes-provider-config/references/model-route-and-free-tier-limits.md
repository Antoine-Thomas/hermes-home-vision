# Route du modele principal, preuve du routage, plafonds de palier gratuit

Recettes de verification pour `hermes-provider-config`. Deux questions : quel
provider sert REELLEMENT les tours, et un provider peut-il tenir le role de
principal ?

## 1. Persister / basculer la route du profil `default`

```bash
hermes config set model.provider <provider>   # google, groq, omniroute, ...
hermes config set model.default  <model>      # gemini-3.6-flash, eco, openai/gpt-oss-120b
hermes fallback list                          # "Primary: <model> (via <provider>)"
hermes config get model
hermes profile list                           # colonne Model, par profil
```

- `hermes model` = picker interactif, sans sous-commande ; `hermes model set` est
  une erreur d'usage (exit 2).
- Bascules ponctuelles sans ecrire la config : `hermes --provider <p> -m <m> -z "..."`
  (les deux flags vont ensemble ; en session : `/model`).
- Un tour avec `--provider` force ne beneficie pas de la chaine de repli : l'echec
  est rendu directement (« grown too large to send to ... », exit 2) au lieu de
  basculer — utile pour prouver un etage, trompeur pour tester un principal.
- La config racine ne concerne que `default` ; `veille` / `watch` ont la leur.
  Controler `hermes profile list` apres toute ecriture.
- Un ID de modele contenant un `/` (ex. `openai/gpt-oss-120b` chez Groq) reste
  intact : `normalize_model_for_provider` ne le decompose pas en provider/modele.

## 2. Prouver quel provider a servi le tour

`hermes -z` n'imprime que la reponse du modele ; les one-shots n'apparaissent pas
non plus dans `logs/agent.log`. Lire la base d'etat en lecture seule :

```python
import sqlite3, os
home = os.path.expandvars(r"%LOCALAPPDATA%\hermes")   # POSIX : ~/AppData/Local/hermes
c = sqlite3.connect(f"file:{os.path.join(home, 'state.db')}?mode=ro", uri=True)
for row in c.execute("""select s.id, s.title, s.model, s.billing_provider, s.billing_base_url,
                               u.input_tokens, u.output_tokens
                        from sessions s
                        left join session_model_usage u on u.session_id = s.id and u.task = ''
                        order by s.started_at desc limit 5"""):
    print(row)
```

`billing_provider` / `billing_base_url` = route qui a servi le tour
(generativelanguage.googleapis.com = Google, api.groq.com = Groq,
127.0.0.1:20128 = OmniRoute) ; `input_tokens` = taille du prompt envoye, a
comparer aux plafonds de la section 3. `source='oneshot'` = `hermes -z`.

Attention aux faux positifs : le meme provider apparait en `custom` ou sous son
nom selon le chemin de resolution — c'est la `billing_base_url` qui tranche.

## 3. Plafond par requete d'un palier gratuit

Les paliers gratuits comptent `input + max_tokens` dans le TPM et refusent la
requete ENTIERE, pas seulement le surplus :

- lire le plafond dans les en-tetes, presents aussi sur les 4xx :
  `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens`, `x-ratelimit-reset-tokens` ;
- messages typiques : 413 `Request too large for model ... service tier on_demand
  on tokens per minute (TPM): Limit N, Requested M` ; 429 `Rate limit reached for
  model ... on tokens per minute (TPM)` des que `max_tokens` n'est plus minuscule ;
- ordre de grandeur illustratif (compte Groq free) : chat 8 000 TPM ;
  `groq/compound` 70 000 TPM mais relais interne vers des sous-modeles a
  8 000 TPM — un 429 qui nomme un AUTRE modele que celui demande signale le
  routage interne du modele compose, pas une erreur de config.

Mesure du seuil reel (cle lue depuis `.env`, jamais imprimee) : poster plusieurs
fois le meme prompt en ne faisant varier que `max_tokens` (50, 1024, 4096, 8192)
et relever statut + `x-ratelimit-limit-tokens`. Exemple de resultat : 200 a
`max_tokens: 50` sur un input de ~6 000 tokens, 429 des 1024 -> le seuil est
`input + max_tokens`, pas l'input seul.

Decision : plafond < `input_tokens` du tour courant -> le provider ne peut PAS
etre principal (chaque tour sera refuse, avec bascule silencieuse). Le garder en
repli pour les tours courts, mesurer la taille du prompt de l'agent
(`input_tokens` : ~5,9 k avec toolsets reduits, ~9,3 k en config par defaut), et
n'annoncer les vraies options que sur cette base : montee de palier payant, ou
reduction du prompt (moins de toolsets / skills charges, `max_tokens` bas).

## 4. Sondes HTTP depuis un script

- Poser un `User-Agent` explicite (`curl/8.x`, `OpenAI/Python 1.x`) sur toute
  sonde : un endpoint derriere Cloudflare renvoie `403 error code: 1010` a l'UA
  par defaut d'urllib — faux negatif qui ressemble a une cle invalide.
- Lister le catalogue reellement accessible avant de figer un modele :
  `GET <base_url>/models` avec `Authorization: Bearer <cle>` (le catalogue local
  peut proposer un modele retire : un ID mort donne un 404 `model_not_found`
  non retryable, mais la chaine avance quand meme et le tour est servi par
  l'etage suivant, sans signal visible).
- Tester le tool-calling, pas seulement le texte : un appel
  `chat/completions` avec `tools` + `tool_choice: auto` doit rendre un
  `tool_calls` non vide.
