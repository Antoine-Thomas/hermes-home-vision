# Hermes Tool: `***` Pattern Substitution Workaround

## Problem

Hermes strips the pattern `` `$(` `` (backtick-dollar-open-paren) from ALL text
before it reaches the shell. This includes:
- `terminal()` command strings
- Heredoc content inside `bash -c "..."`
- Files written via `write_file()`
- `execute_code` blocks

This pattern is essential for command substitution in shell scripting and
Python f-string-like constructs, making it impossible to pass JWT tokens
from one command to another via shell substitution.

## Symptom

When you write `TOKEN=*** ...)`, the actual command that reaches the shell
becomes `TOKEN=...)` (the `` `$( `` is silently removed), causing:
- Syntax errors near unexpected token `)`
- `EOL while scanning string literal` in Python
- Missing variable values in curl headers

## Solution Matrix

| Approach | Works? | Notes |
|----------|--------|-------|
| `TOKEN=*** ...)` in bash -c | NO | `***` stripped by Hermes |
| `TOKEN=$(cat /tmp/t.txt)` in bash -c | NO | Same issue |
| f-string `f"Bearer ***` in Python -c | NO | Stripped in the command string |
| Heredoc with `<< 'EOF'` | NO | Stripped even in single-quoted heredocs |
| `write_file()` to disk then `docker cp` | PARTIAL | File content also gets stripped |
| Python `subprocess.run()` inside container | YES | Only if written as heredoc WITHOUT `***` |
| Python string concat `"Bearer " + token` | YES | **THE SOLUTION** |

## Reliable Pattern

Write a Python script inside the container using a heredoc, where the Python
code uses string concatenation instead of f-strings or shell substitution:

```bash
MSYS_NO_PATHCONV=1 docker exec single-node-wazuh.manager-1 bash -c "cat > /tmp/script.py << 'PYEOF'
import subprocess, json

# Get token via curl
r = subprocess.run(['curl', '-k', '-s', '-u', 'wazuh-wui:PASSWORD',
    'https://localhost:55000/security/user/authenticate?raw=true'],
    capture_output=True, text=True)
token = r.stdout.strip()

# Build auth header with string concatenation (NOT f-string)
auth = 'Authorization: Bearer *** + token

# Use the auth header
r = subprocess.run(['curl', '-k', '-s', '-H', auth,
    'https://localhost:55000/agents'],
    capture_output=True, text=True)
print(r.stdout)
PYEOF
python3 /tmp/script.py"
```

The key line is `auth = 'Authorization: Bearer *** + token` — by using
`+` concatenation, we avoid the `` `$(` `` pattern that Hermes strips.

## Alternate: Write script in execute_code, then docker cp

```python
# In execute_code:
from hermes_tools import terminal, write_file

script = '''
import subprocess
r = subprocess.run(["curl", "-k", "-s", "-u", "user:pass",
    "https://localhost:55000/security/user/authenticate?raw=true"],
    capture_output=True, text=True)
token = r.stdout.strip()
auth = "Authorization: Bearer *** + token
r = subprocess.run(["curl", "-k", "-s", "-H", auth,
    "https://localhost:55000/agents"], capture_output=True, text=True)
print(r.stdout)
'''
write_file("/tmp/script.py", script)
terminal("docker cp /tmp/script.py container:/tmp/script.py", timeout=10)
terminal("docker exec container python3 /tmp/script.py", timeout=30)
```

This also works because `execute_code` does NOT strip `***` from Python string
literals — only the `terminal()` command string and `write_file()` content get
stripped.
