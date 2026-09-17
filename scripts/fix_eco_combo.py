import json, subprocess, os, datetime, sys

KEY = open(os.path.expanduser("~/.omniroute/.env")).read().split("OMNIROUTE_API_KEY=",1)[1].splitlines()[0].strip().strip('"').strip("'")
BASE = "http://127.0.0.1:20128"

def curl(args):
    return subprocess.run(["curl","-s"]+args, capture_output=True, text=True, timeout=60).stdout

# 1. fetch current combos
raw = curl(["-H","Authorization: Bearer "+KEY, BASE+"/api/combos"])
combos = json.loads(raw)["combos"]
eco = next(c for c in combos if c["name"] == "eco")

# backup
bak = os.path.expanduser("~/.omniroute/combos_bak_%s.json" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
json.dump({"combos": combos}, open(bak,"w",encoding="utf-8"), indent=2)
print("backup:", bak)
print("eco id:", eco["id"])
print("eco OLD models:", [m["model"] for m in eco["models"]])

# 2. build new body (preserve name/strategy/config/id, replace models)
body = {k:v for k,v in eco.items() if k not in ("createdAt","updatedAt","version","computed_context_length","repairNote")}
body["strategy"] = "priority"
# verified working RIGHT NOW (probe 200 + non-empty content)
WORKING = [
    ("oc/muse-spark-1.2-contributor-free", "oc"),
    ("oc/big-pickle", "oc"),
    ("opencode/big-pickle", "opencode"),
]
body["models"] = [
    {"id": f"eco-{i:02d}-{m.replace('/','-')}", "kind":"model", "model":m, "providerId":p, "weight":0}
    for i,(m,p) in enumerate(WORKING,1)
]

tmp = os.path.expanduser("~/.omniroute/_eco_put.json")
json.dump(body, open(tmp,"w",encoding="utf-8"))
out = curl(["-X","PUT", BASE+"/api/combos/"+eco["id"],
            "-H","Content-Type: application/json",
            "-H","Authorization: Bearer "+KEY,
            "--data-binary","@"+tmp,
            "-w","\n__HTTP=%{http_code}"])
os.remove(tmp)
print("PUT result tail:", out.strip().splitlines()[-1][:200])

# 3. verify eco now
ver = subprocess.run(["curl","-s","-X","POST",BASE+"/v1/chat/completions",
    "-H","Content-Type: application/json","-H","Authorization: Bearer "+KEY,
    "-d",json.dumps({"model":"eco","messages":[{"role":"user","content":"dis bonjour en trois mots"}],"max_tokens":20,"stream":False}),
    "-w","\n__HTTP=%{http_code}","--max-time","45"], capture_output=True, text=True, timeout=60).stdout
code = ver.split("__HTTP=")[-1].strip()
b = ver.split("\n__HTTP=")[0]
try:
    d = json.loads(b)
    if "error" in d:
        print("VERIFY eco:", code, "ERR", str(d["error"])[:80])
    else:
        c = d.get("choices",[{}])[0].get("message",{}).get("content","")
        print("VERIFY eco:", code, "->", d.get("model"), "|", repr(c[:40]))
except Exception:
    print("VERIFY eco:", code, "RAW", b[:120])
