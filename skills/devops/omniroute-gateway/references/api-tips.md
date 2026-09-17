## API Tips

- **Combo Management**: Access via `GET /api/combos` and `PUT /api/combos/<id>`. Requires `Authorization: Bearer <TOKEN>` (token from `$OMNIROUTE_API_KEY` env var or `~/.omniroute/.env`).
- **Combos are keyed by UUID, not name**: `GET /api/combos/eco` returns `COMBO_007 Combo not found`. Fetch `GET /api/combos`, find the entry with `"name":"eco"`, and use its `id` (a UUID) for `GET`/`PUT /api/combos/<id>`. The name is only a display field.
- **Combo model entry shape**: each `models[]` item is `{"id": <unique-slug>, "kind":"model", "model":"<provider>/<model>", "providerId":"<provider-type>", "weight":0}`. Order of the array IS the priority order under `"strategy":"priority"`; `weight` is ignored (always 0).
- **Provider registration**: `POST /api/providers` with body `{"name":..., "provider":<type>, "authType":"apikey", "apiKey":..., "isActive":true, "providerSpecificData":{"baseUrl":...}}`. `GET /api/providers` returns `{connections:[...]}` with status/testStatus/lastError per provider.
- **Model Discovery**: `GET /v1/models` lists all available. Probing them individually via `v1/chat/completions` is necessary to check if they are truly free, but limit probing to avoid quota saturation (only check known free prefixes/suffixes like `-free`).
- **No `jq` on this host**: parse JSON with `grep`/`python -c` or pipe to a file and read it; the `/v1/models` payload is ~500KB and floods the terminal.
- **Routing test**: `POST /v1/chat/completions` with `"model":"combo/eco"` exercises the combo; the error payload's `diagnostics.attemptOrder` shows which providers were tried in order and why each failed.

### Ecrire sur une ressource existante (les trois gestes verifies)

- **Desactiver une connexion sans la supprimer** : `PATCH /api/providers/<id>` avec `{"isActive": false}`
  -> `200`. L'objet rendu par le PATCH **n'est pas la preuve** : relire `GET /api/providers` et
  verifier `isActive`. C'est le bon geste pour une connexion en erreur qu'on veut garder en trace
  (cle expiree) : elle disparait du routage sans perdre sa configuration.
- **Elaguer un combo** : relire le combo (`GET /api/combos`, retrouver par `name`), filtrer son
  `models[]`, puis `PUT /api/combos/<uuid>` avec l'**objet complet** (tous les autres champs
  conserves). Verifier par relecture du nombre de cibles restantes. Un combo n'est pas casse par une
  cible morte en plus : nettoyer sert a arreter le bruit et les tentatives perdues, pas a reparer un
  502.
- **Le perimetre d'un modele se lit en trois endroits** et peut differer : la liste stockee du combo,
  la liste autorisee de la cle (`allowedModels`), et ce que le routeur tente reellement au dispatch
  (log `Trying model i/N`, ou N peut etre bien plus grand que la liste stockee — un alias resout sa
  cible a la volee). Ne jamais conclure d'un seul des trois.

### Cle restreinte : verifier l'isolation avant de s'en servir

Sur `/api/*`, une cle dont `allowedModels` n'est pas vide repond
`403 {"error":{"code":"AUTH_001","message":"Invalid management token"}}` : elle peut inferer, pas
administrer. C'est une verification utile (une cle de consommateur ne peut ni lire ni modifier les
autres cles) — l'administration se fait avec la cle du poste. Corollaire : quand une automatisation
qui ne parle qu'a `/v1` fonctionne, elle ne prouve rien sur l'etat de `/api`.
