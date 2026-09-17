import io, sys, shutil, datetime

CFG = r"C:\Users\searc\AppData\Local\hermes\config.yaml"

# 1. Backup
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = CFG + ".bak.eco_fix_" + ts
shutil.copy2(CFG, bak)
print("backup ->", bak)

# 2. Read raw, normalize newlines for matching (keep original endings)
with io.open(CFG, "r", encoding="utf-8") as f:
    raw = f.read()

crlf = "\r\n" in raw
NL = "\r\n" if crlf else "\n"

old_block = (
    "model:" + NL +
    "  base_url: https://text.pollinations.ai/openai" + NL +
    "  default: eco" + NL +
    "  provider: omniroute" + NL +
    "  api_key: dummy" + NL +
    "  model: openai" + NL
)
new_block = (
    "model:" + NL +
    "  base_url: https://api.deepseek.com/v1" + NL +
    "  default: deepseek-v4-pro" + NL +
    "  provider: deepseek" + NL
)

if old_block not in raw:
    print("ERROR: model block not found verbatim; line endings?", repr(NL))
    sys.exit(1)

raw = raw.replace(old_block, new_block, 1)

with io.open(CFG, "w", encoding="utf-8", newline="") as f:
    f.write(raw)

print("edited model block")

# 3. Validate
import yaml
with io.open(CFG, "r", encoding="utf-8") as f:
    c = yaml.safe_load(f)
m = c["model"]
print("model.default   =", m.get("default"))
print("model.provider  =", m.get("provider"))
print("model.base_url  =", m.get("base_url"))
print("model.api_key   =", m.get("api_key"))
print("model.model     =", m.get("model"))
print("fallback_providers =", c.get("fallback_providers"))
print("total lines =", raw.count(NL) + 1)
