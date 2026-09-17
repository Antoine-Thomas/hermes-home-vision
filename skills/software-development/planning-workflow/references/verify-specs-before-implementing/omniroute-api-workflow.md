# OmniRoute API workflow: managing providers and combos

**Date**: 2026-08-26  
**Context**: Session on updating OmniRoute "eco" combo with specific provider order

## Key discoveries from this session

### 1. Correct API endpoints for managing OmniRoute

**Wrong assumption from brief**:  
`POST /api/providers/{provider}/keys` (returns 404)

**Correct endpoint**:  
`POST /api/keys` with JSON payload:
```json
{
  "provider": "provider-name",
  "name": "Account Name",
  "key": "api-key-here"
}
```

**Example for FreeAIAPIKey**:
```bash
curl -X POST http://127.0.0.1:20128/api/keys \
  -H "Content-Type: application/json" \
  -d '{"provider":"freeaiapikey","name":"FreeAIAPIKey Account","key":"sk-EXAMPLE-cle-real-masquee-avant-commit"}'
```

### 2. Provider initialization delay

**Discovery**: After adding API keys via `/api/keys`, providers may not immediately appear in `/api/providers` or have their models visible in `/api/models`.

**Implication**: Need to allow time for provider initialization or check via web interface.

### 3. Combo management workflow

**Retrieve current combos**:  
`GET /api/combos`

**Update a combo**:  
`PUT /api/combos/{combo_id}` with full combo definition

**Critical**: Must include ALL fields from the GET response, not just models. OmniRoute validates the entire object.

### 4. Finding specific models in OmniRoute

**Challenges encountered**:
- Provider IDs in `/api/providers` are often UUIDs, not human-readable names
- Model names in `/api/models` may not match expected patterns
- Some providers (Gemini, Pollinations, HuggingChat) may not be available even after adding keys

**Verification steps**:
1. Check `/api/providers` for provider connections
2. Check `/api/models` for available models
3. Use case-insensitive pattern matching (e.g., "gemini" in provider_id or model_name)

### 5. Testing combo functionality

**Direct API test**:
```bash
curl -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"eco","messages":[{"role":"user","content":"Test"}],"max_tokens":10}'
```

**Hermes CLI test**:
```bash
hermes -z "Bonjour" --model eco
```

## Common pitfalls

1. **Assumption that all providers are immediately available** after adding keys
2. **Expecting human-readable provider IDs** when OmniRoute uses UUIDs
3. **Not preserving all combo fields** when updating via PUT
4. **Case-sensitive matching** for provider/model names

## Verification checklist for OmniRoute tasks

- [ ] Verify `/api/keys` endpoint for adding API keys
- [ ] Check `/api/providers` for existing connections
- [ ] Search `/api/models` with case-insensitive patterns
- [ ] Allow time for provider initialization (5+ seconds)
- [ ] Preserve all fields when updating combos via PUT
- [ ] Test combo functionality with both API and CLI