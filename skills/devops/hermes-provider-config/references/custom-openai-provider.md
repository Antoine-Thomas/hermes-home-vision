# Provider OpenAI-compatible tiers (custom)

Brancher une API tierce compatible OpenAI (ex. Experiential Labs,
`https://api.experientiallabs.ai/v1`) comme provider Hermes, puis l'utiliser
dans la chaine de repli. Les commandes supposent Windows ; sous POSIX,
remplacer `venv/Scripts/python.exe` par `venv/bin/python` et
`~/AppData/Local/hermes` par `~/.hermes` si c'est le chemin actif.

## Forme de config qui marche

```bash
hermes config set providers.<id> '{base_url: "https://api.exemple.ai/v1", name: "Nom lisible", key_env: EXEMPLE_API_KEY, transport: chat_completions, default_model: modele-1, models: [modele-1, modele-2]}'
hermes config get providers.<id>
```

NE PAS ecrire `type: openai` (ignore) ni `api_key: "${VAR}"` (substitution non
faite). Pour la cle, `key_env: NOM_VARIABLE` + la variable dans `.env`.

## Cle API : passer par config set

```bash
hermes config set EXEMPLE_API_KEY "<valeur>"   # ecrit dans .env
hermes config set EXEMPLE_API_KEY ""           # placeholder vide, a remplir a la main
```

Verifier sans exposer la valeur :

```bash
grep -c '^EXEMPLE_API_KEY=' "$LOCALAPPDATA/hermes/.env"
python -c "p=r'C:\Users\<user>\AppData\Local\hermes\.env'; v=[l.split('=',1)[1].strip() for l in open(p,encoding='utf-8',errors='ignore') if l.startswith('EXEMPLE_API_KEY=')][0]; print('placeholder ok=', v=='A_REMPLIR', '| length=', len(v))"
```

Le terminal masque les variables `*API_KEY` en `***` : confirmer par un controle
Python (booleen / longueur), pas par l'affichage brut.

## Sonder la resolution avant tout appel reseau

```bash
cd ~/AppData/Local/hermes/hermes-agent && venv/Scripts/python.exe -c "
from hermes_cli.runtime_provider import _get_named_custom_provider, resolve_provider_client
print(_get_named_custom_provider('exemple'))
c,m = resolve_provider_client('exemple', model='modele-1', raw_codex=True)
print(bool(c), m, getattr(c,'base_url',None))"
```

- `_get_named_custom_provider` doit renvoyer `base_url`, `key_env`, `api_mode`.
- `resolve_provider_client` avertit `no resolvable api_key ... will 401` quand
  la variable d'environnement est absente / vide : la config est bonne, la cle
  manque. Avec une cle presente, le client se construit et `base_url` remonte.

Un provider custom nomme se resout par son ID dans la chaine (`provider:
exemple`), sans repeter `base_url` / `key_env` dans chaque entree de fallback.

## Choisir les IDs de modele (le nom marketing n'est pas l'ID)

```bash
KEY=$(grep '^EXEMPLE_API_KEY=' "$LOCALAPPDATA/hermes/.env" | cut -d= -f2- | tr -d '\r\n')
curl -s -m 30 "https://api.exemple.ai/v1/models" -H "Authorization: Bearer $KEY" |
  python -c "import sys,json; ids=[m['id'] for m in json.load(sys.stdin)['data']]; print(len(ids)); [print(i) for i in ids if 'luna' in i.lower() or 'nemotron' in i.lower()]"
```

Exemple mesure : la plateforme affiche « Nemotron 3 Ultra », l'ID API reel est
`nemotron-3-ultra-550b-a55b`. Mettre l'ID affiche produit un 404 qui ne declenche
PAS la chaine de repli.

## Test final et entree de fallback

```bash
hermes --provider exemple -m modele-1 -z "ping"
hermes config set fallback_providers '[{provider: exemple, model: modele-1}, {provider: omniroute, model: eco}]'
hermes fallback list   # "via exemple" / "via omniroute" = resolu
```

Si `-z` rend « every provider in the fallback chain kept failing », l'erreur
sous-jacente n'est pas visible : reproduire avec `curl` sur
`/v1/chat/completions` pour voir le code HTTP et le corps exact avant de
conclure au mauvais modele ou a la mauvaise cle.

## Triage : « la cle .env n'est pas chargee » (souvent faux)

Symptome typique : la meme commande `-z` reussit parfois et echoue d'autres fois,
et forcer `$env:NOM_API_KEY` avant l'appel semble la faire marcher — d'ou la
conclusion erronee que le CLI ne lit pas `.env`. Trois sondes, dans cet ordre,
avant toute correction.

1. Prouver que le CLI charge bien `.env` (aucune valeur affichee) :

```bash
cd ~/AppData/Local/hermes/hermes-agent && venv/Scripts/python.exe -c "
import os
from hermes_cli.env_loader import load_hermes_dotenv
print(load_hermes_dotenv())
v = os.environ.get('EXEMPLE_API_KEY') or ''
print('set=', bool(v), 'len=', len(v), 'prefix=', v[:4])"
```

Relancer la meme sonde en prefixant `env -u HERMES_HOME -u HERMES_REAL_HOME -u
EXEMPLE_API_KEY` pour simuler un shell propre. Si le `.env` du home est charge et
la variable posee dans les deux cas, le chargement n'est pas le probleme. Observe :
`get_process_hermes_home()` resout `%LOCALAPPDATA%\hermes` meme sans
`HERMES_HOME`, et les cles `.env` sont chargees avec `override=True` — un export
shell vide ou perime ne peut donc pas masquer la cle.

2. Separer « cle invalide » de « compte a sec » avec deux `curl` sur la meme cle :

```bash
KEY=$(grep '^EXEMPLE_API_KEY=' "$LOCALAPPDATA/hermes/.env" | cut -d= -f2- | tr -d '\r\n')
curl -s -o /dev/null -m 20 -w "models HTTP:%{http_code}\n" \
  https://api.exemple.ai/v1/models -H "Authorization: Bearer $KEY"
curl -s -m 30 -w "\nHTTP:%{http_code}\n" \
  https://api.exemple.ai/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"modele-1","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' | head -c 700
```

`/v1/models` 200 + `/v1/chat/completions` 429 = la cle est bien lue et valide,
c'est le compte qui refuse (quota, verification de facturation). Le corps d'erreur
nomme la cause et souvent l'action attendue (`insufficient_quota`, `card_required`,
URL de verification...) : le citer tel quel au lieu de supposer une erreur de
configuration. A l'inverse, `models` 401 = cle absente ou fausse.

3. Reproduire hors de l'UI Hermes, depuis deux dossiers differents (`$HOME` puis
`C:\WINDOWS\System32`) et deux fois de suite. Un resultat qui change selon le
dossier ou le tirage confirme l'origine cote provider, pas cote chemin.

Ne pas appliquer les corrections reflexe quand les sondes innocentent la config :
`setx NOM_API_KEY` persistent la cle en clair dans le registre Windows, copier le
`.env` racine dans `profiles/<profil>/.env` cree une divergence silencieuse, et un
shim n'ajoute qu'une couche. `profiles/default/.env` n'est pas lu par le profil
`default` (il lit le `.env` de la racine du home) — le verifier avec
`ls profiles/default/.env` avant d'inventer une priorite de chargement.
