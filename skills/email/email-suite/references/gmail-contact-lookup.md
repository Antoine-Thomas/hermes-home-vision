# Gmail Search as Contact Email Lookup

When the People API is not enabled (returns `403: People API has not been used in project`),
use Gmail search to find contact email addresses in sent mail and inbox.

## Command

```bash
GAPI="python $HOME/AppData/Local/hermes/skills/productivity/google-workspace/scripts/google_api.py"

# Search for a contact by name
$GAPI gmail search "Cendre Delort" --max 5
$GAPI gmail search "Guylaine" --max 5
```

## How to extract emails from results

The JSON output contains `from`, `to`, and `snippet` fields. Parse with `jq` or Python:

```python
import json, subprocess

result = subprocess.run(
    [sys.executable, GAPI, "gmail", "search", "Name Surname", "--max", "10"],
    capture_output=True, text=True
)
messages = json.loads(result.stdout)
for msg in messages:
    # Check 'to' field for sent mail (contains recipient)
    # Check 'from' field for received mail (contains sender)
    if 'to' in msg:
        print(f"Found in 'to': {msg['to']}")
    if 'from' in msg:
        print(f"Found in 'from': {msg['from']}")
```

## When this works best

- Searching for unique names (full name or uncommon first name)
- The contact has been emailed before (sent mail) or has emailed the user (inbox)
- People API is not enabled or not configured

## Pitfalls

- Common names return too many results — use the full name
- Draft messages may have incomplete `to` fields
- Bandcamp/notification emails may show the contact in the `snippet` but not the `to`/`from` fields
- The search is Gmail's full-text search, not a contact directory — it searches email bodies too
