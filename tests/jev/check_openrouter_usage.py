import sys
import json
import urllib.request
sys.path.insert(0, 'skills/typesafe-ai/scripts')
from jev_helper import _key

key = _key()
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/auth/key",
    headers={"Authorization": "Bearer " + key},
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)