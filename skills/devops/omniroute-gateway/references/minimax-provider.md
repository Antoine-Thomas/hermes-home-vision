# Minimax provider in OmniRoute (integration notes)

Minimax (MiniMax International) is an OpenAI-compatible chat API. Adding it
as a new upstream provider so its models can sit in a combo.

**Correct base URL is `https://api.minimax.io`** (no `/v1` suffix, no `/v1`
in `providerSpecificData.baseUrl`). `https://api.minimaxi.com` and
`https://api.minimax.chat` are alternate hosts; a key issued for one portal
is rejected by the others. Docs now live at `platform.minimax.io` (the
`.minimaxi.com` domain redirects here).

## Register the provider

```bash
curl -X POST http://127.0.0.1:20128/api/providers \
  -H "Authorization: Bearer $OMNIROUTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "minimax",
    "provider": "minimax",
    "authType": "apikey",
    "apiKey": "<FULL KEY>",
    "isActive": true,
    "providerSpecificData": { "baseUrl": "https://api.minimax.io" }
  }'
```

Returns `{connection:{id, provider:"minimax", ...}}` on success. The new
connection appears in `GET /api/providers`.

## Add Minimax models to a combo

Add `models[]` entries in priority order (first = highest priority):

```json
{ "id": "minimax-m3", "kind": "model", "model": "minimax/MiniMax-M3", "providerId": "minimax", "weight": 0 },
{ "id": "minimax-m27", "kind": "model", "model": "minimax/MiniMax-M2.7", "providerId": "minimax", "weight": 0 }
```

Real chat model names are `MiniMax-M3` and `MiniMax-M2.7` (NOT `h3-1.0`/
`h3-2.0` — those were guessed names and 401/404 on the real API).
`providerId` must be the provider type string (`"minimax"`), NOT the connection UUID.

## Pitfall: Minimax API keys are long JWT-style tokens

Minimax issues API keys as a single very long token (~350+ chars, JWT-like,
starting `eyJ`). A key that arrives truncated mid-string will be REGISTERED
fine but rejected at inference time with `invalid api key (2049)` / HTTP 401.
Before debugging "provider auth broken", re-confirm the full key from the
portal — a pasted key cut off at the message boundary is the most common cause.

**`Sk-api-` prefix is a red flag.** Official platform.minimax.io keys start
with `eyJ...` (JWT). A key beginning `Sk-api-` is NOT a valid MiniMax key for
any host — it fails with `login fail: Please carry the API secret key in the
'Authorization' field of the request header (1004)` on api.minimax.io,
api.minimaxi.com AND api.minimax.chat. Stop and get the real `eyJ...` key
rather than re-trying the same one against more endpoints.

Key format differs by portal: `platform.minimaxi.com` vs `platform.minimax.chat`
issue different key shapes; a key from one portal is not valid against the
other's endpoint. Match the `baseUrl` to the portal the key came from.

## Video API (talking portrait / image-to-video)

Minimax H3 also does video generation — used for a `/portrait`-style talking
avatar (image + text → animated lips). Async task pattern:

- Endpoint: `POST https://api.minimax.io/v2/video_generation` (NOT `/v1/...`,
  NOT `video_generation` under `/v1`).
- Model: `MiniMax-H3` (NOT `MiniMax-Video-01`).
- Auth: `Authorization: Bearer <full eyJ... key>` — same key as chat, but an
  invalid/`Sk-api-` key fails here too (1004).
- Image-to-video payload: `content[]` array with one `{type:"text", text:"<what
  they say>"}` item + one `{type:"image_url", image_url:{url:...}, role:"first_frame"}`
  item; plus `duration` (seconds) and optional `resolution`/`ratio`.
- Returns `task_id`; poll `GET https://api.minimax.io/v2/query/video_generation?task_id=...`
  for the result URL. Generation is asynchronous — never expect a video URL in
  the create response.

## Test the combo routing

```bash
curl -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Authorization: Bearer $OMNIROUTE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"combo/eco","messages":[{"role":"user","content":"ping"}]}'
```

On failure, read `diagnostics.attemptOrder` to confirm Minimax was tried first
and then fell back to the `oc`/`opencode` entries as expected.
