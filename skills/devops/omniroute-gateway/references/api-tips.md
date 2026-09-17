## API Tips

- **Combo Management**: Access via `GET /api/combos` and `PUT /api/combos/<id>`. Requires `Authorization: Bearer <TOKEN>` (token from `$OMNIROUTE_API_KEY` env var or `~/.omniroute/.env`).
- **Combos are keyed by UUID, not name**: `GET /api/combos/eco` returns `COMBO_007 Combo not found`. Fetch `GET /api/combos`, find the entry with `"name":"eco"`, and use its `id` (a UUID) for `GET`/`PUT /api/combos/<id>`. The name is only a display field.
- **Combo model entry shape**: each `models[]` item is `{"id": <unique-slug>, "kind":"model", "model":"<provider>/<model>", "providerId":"<provider-type>", "weight":0}`. Order of the array IS the priority order under `"strategy":"priority"`; `weight` is ignored (always 0).
- **Provider registration**: `POST /api/providers` with body `{"name":..., "provider":<type>, "authType":"apikey", "apiKey":..., "isActive":true, "providerSpecificData":{"baseUrl":...}}`. `GET /api/providers` returns `{connections:[...]}` with status/testStatus/lastError per provider.
- **Model Discovery**: `GET /v1/models` lists all available. Probing them individually via `v1/chat/completions` is necessary to check if they are truly free, but limit probing to avoid quota saturation (only check known free prefixes/suffixes like `-free`).
- **No `jq` on this host**: parse JSON with `grep`/`python -c` or pipe to a file and read it; the `/v1/models` payload is ~500KB and floods the terminal.
- **Routing test**: `POST /v1/chat/completions` with `"model":"combo/eco"` exercises the combo; the error payload's `diagnostics.attemptOrder` shows which providers were tried in order and why each failed.
