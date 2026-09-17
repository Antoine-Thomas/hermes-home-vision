# API Tips

- **Combo Management**: Access via `GET /api/combos` and `PUT /api/combos/<id>`. Requires `Authorization: Bearer <TOKEN>` (token from `~/.omniroute/.env`).
- **Model Discovery**: `GET /v1/models` lists all available. Probing them individually via `v1/chat/completions` is necessary to check if they are truly free, but limit probing to avoid quota saturation (only check known free prefixes/suffixes like `-free`).
