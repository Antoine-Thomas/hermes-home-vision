#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inventaire YouTube + classification (LECTURE SEULE).

Usage :
    python youtube_channel_inventory.py [handle] [dossier_de_sortie]

Ecrit a cote de lui-meme (ou dans le dossier passe) :
    youtube_inventory.csv / youtube_inventory.json
    youtube_classification.csv / youtube_classification.json

Aucune valeur de cle n'est affichee. Aucune modification cote YouTube.
Dependances : bibliotheque standard uniquement.
"""
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HANDLE = sys.argv[1] if len(sys.argv) > 1 else "searchingmurphy"
SCRATCH = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", ".env")
API = "https://www.googleapis.com/youtube/v3/"

CALLS = {"playlistItems": 0, "videos": 0, "channels": 0}


def load_key():
    with open(ENV, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("YOUTUBE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("FATAL: YOUTUBE_API_KEY absente du .env")


KEY = load_key()
print("cle: longueur=%d prefixe=%s" % (len(KEY), KEY[:4]))


def api_get(endpoint, params):
    """Un appel HTTP. Retry sur 429/5xx, STOP net avec corps brut sur les autres erreurs."""
    params = dict(params)
    params["key"] = KEY
    url = API + endpoint + "?" + urllib.parse.urlencode(params, safe=",")
    safe_url = url.replace(KEY, "<REDACTED>")
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                CALLS[endpoint] += 1
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            CALLS[endpoint] += 1
            if e.code in (429, 500, 503) and attempt < 3:
                print("  HTTP %d sur %s -> retry %d" % (e.code, safe_url, attempt + 1))
                time.sleep(2 * (attempt + 1))
                last = (e.code, body)
                continue
            print("HTTP_ERREUR code=%d url=%s" % (e.code, safe_url))
            print("CORPS_BRUT=" + body)
            sys.exit(2)
        except urllib.error.URLError as e:
            print("ERREUR_RESEAU url=%s : %s" % (safe_url, e))
            sys.exit(3)
    print("HTTP_ERREUR code=%d url=%s" % last)
    print("CORPS_BRUT=" + last[1])
    sys.exit(2)


# ------------------------------------------------------------------ la chaine
ch = api_get("channels", {"part": "id,snippet,statistics,contentDetails",
                          "forHandle": HANDLE.lstrip("@")})
item = ch["items"][0]
CH_ID = item["id"]
CH_TITLE = item["snippet"]["title"]
UPLOADS = item["contentDetails"]["relatedPlaylists"]["uploads"]
ST = item.get("statistics", {})
print("canal=%s id=%s uploads=%s videoCount=%s"
      % (CH_TITLE, CH_ID, UPLOADS, ST.get("videoCount")))

# ------------------------------------------------------------------ uploads
video_ids = []
token = None
pages = 0
while True:
    p = {"part": "contentDetails", "playlistId": UPLOADS, "maxResults": 50}
    if token:
        p["pageToken"] = token
    d = api_get("playlistItems", p)
    pages += 1
    for it in d.get("items", []):
        vid = it.get("contentDetails", {}).get("videoId")
        if vid and vid not in video_ids:
            video_ids.append(vid)
    token = d.get("nextPageToken")
    print("  page %d -> %d ids cumules" % (pages, len(video_ids)))
    if not token:
        break
    time.sleep(0.15)

print("TOTAL_IDS_PLAYLIST=%d" % len(video_ids))

# ------------------------------------------------------------------ metadonnees
videos = {}
for i in range(0, len(video_ids), 50):
    batch = video_ids[i:i + 50]
    d = api_get("videos", {"part": "snippet,statistics,contentDetails,status",
                           "id": ",".join(batch), "maxResults": 50})
    for it in d.get("items", []):
        videos[it["id"]] = it
    print("  lot %d/%d -> %d recus (cumul %d)"
          % (i // 50 + 1, (len(video_ids) + 49) // 50,
             len(d.get("items", [])), len(videos)))
    time.sleep(0.15)

missing = [v for v in video_ids if v not in videos]
print("VIDEOS_NON_RETOURNEES=%d" % len(missing))
print("QUOTA_APPELS=%s total=%d" % (json.dumps(CALLS), sum(CALLS.values())))


# ------------------------------------------------------------------ helpers
def dur_s(iso):
    """ISO 8601 (PT1H2M3S) -> secondes."""
    if not iso:
        return 0
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def norm_title(t):
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def lev_ratio(a, b):
    """Distance de Levenshtein normalisee par la longueur max."""
    if a == b:
        return 0.0
    if not a or not b:
        return 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1] / max(len(a), len(b))


NOW = datetime.now(timezone.utc)
rows = []
for vid in video_ids:
    it = videos.get(vid)
    if not it:
        continue
    sn = it["snippet"]
    stt = it.get("statistics", {})
    cd = it.get("contentDetails", {})
    sta = it.get("status", {})
    pub = sn.get("publishedAt", "")
    try:
        dt = datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = (NOW - dt).days
        date_s = dt.strftime("%Y-%m-%d")
    except Exception:
        age, date_s = -1, (pub or "")[:10]
    desc = (sn.get("description") or "").replace("\r", " ").replace("\n", " | ")
    rows.append({
        "video_id": vid, "titre": sn.get("title", ""),
        "date_pub": pub, "date_court": date_s, "age_jours": age,
        "duree_s": dur_s(cd.get("duration")),
        "vues": int(stt["viewCount"]) if "viewCount" in stt else None,
        "likes": int(stt["likeCount"]) if "likeCount" in stt else None,
        "commentaires": int(stt["commentCount"]) if "commentCount" in stt else None,
        "visibilite": sta.get("privacyStatus", "?"),
        "nb_tags": len(sn.get("tags", []) or []),
        "desc_200c": desc[:200],
        "norm": norm_title(sn.get("title", "")),
    })

print("LIGNES_INVENTAIRE=%d" % len(rows))

# ------------------------------------------------------------------ inventaire
inv_csv = os.path.join(SCRATCH, "youtube_inventory.csv")
with open(inv_csv, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["video_id", "titre", "date_pub", "duree_s", "vues", "likes",
                "commentaires", "visibilite", "nb_tags", "desc_200c"])
    for r in rows:
        w.writerow([r["video_id"], r["titre"], r["date_pub"], r["duree_s"],
                    "" if r["vues"] is None else r["vues"],
                    "" if r["likes"] is None else r["likes"],
                    "" if r["commentaires"] is None else r["commentaires"],
                    r["visibilite"], r["nb_tags"], r["desc_200c"]])

views = [r["vues"] for r in rows if r["vues"] is not None]


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


tot = len(rows)
by_priv = {}
for r in rows:
    by_priv[r["visibilite"]] = by_priv.get(r["visibilite"], 0) + 1
top10 = sorted(rows, key=lambda r: (r["vues"] is None, -(r["vues"] or 0)))[:10]
flop10 = sorted(rows, key=lambda r: (r["vues"] is None, (r["vues"] or 0)))[:10]
by_date = sorted(rows, key=lambda r: r["date_pub"])

summary = {
    "channel": {"id": CH_ID, "titre": CH_TITLE, "handle": "@" + HANDLE.lstrip("@"),
                "uploads_playlist": UPLOADS,
                "videoCount_api": int(ST.get("videoCount", 0)),
                "subscriberCount": int(ST.get("subscriberCount", 0)),
                "viewCount": int(ST.get("viewCount", 0))},
    "genere_le": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "appels_api": dict(CALLS, total=sum(CALLS.values())),
    "nb_ids_playlist": len(video_ids), "nb_videos_non_retournees": len(missing),
    "videos_non_retournees": missing, "nb_total": tot,
    "nb_public": by_priv.get("public", 0), "nb_unlisted": by_priv.get("unlisted", 0),
    "nb_private": by_priv.get("private", 0),
    "vues_totales": sum(views), "vues_medianes": median(views),
    "nb_0_vue": sum(1 for v in views if v == 0),
    "nb_lt_10_vues": sum(1 for v in views if v < 10),
    "nb_lt_100_vues": sum(1 for v in views if v < 100),
    "nb_lt_1000_vues": sum(1 for v in views if v < 1000),
    "duree_moyenne_s": round(sum(r["duree_s"] for r in rows) / tot, 1) if tot else 0,
    "top10_vues": [{"id": r["video_id"], "titre": r["titre"], "vues": r["vues"]} for r in top10],
    "top10_moins_vues": [{"id": r["video_id"], "titre": r["titre"], "vues": r["vues"]} for r in flop10],
    "plus_ancienne": {"id": by_date[0]["video_id"], "date": by_date[0]["date_pub"]} if by_date else None,
    "plus_recente": {"id": by_date[-1]["video_id"], "date": by_date[-1]["date_pub"]} if by_date else None,
}
inv_json = os.path.join(SCRATCH, "youtube_inventory.json")
with open(inv_json, "w", encoding="utf-8") as fh:
    json.dump({"resume": summary, "videos": rows}, fh, ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ doublons
DUP_THRESH = 0.2
parent = list(range(tot))


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


for i in range(tot):
    if not rows[i]["norm"]:
        continue
    for j in range(i + 1, tot):
        if not rows[j]["norm"]:
            continue
        la, lb = len(rows[i]["norm"]), len(rows[j]["norm"])
        if abs(la - lb) / max(la, lb) >= DUP_THRESH:
            continue
        if lev_ratio(rows[i]["norm"], rows[j]["norm"]) < DUP_THRESH:
            union(i, j)

groups = {}
for i in range(tot):
    groups.setdefault(find(i), []).append(i)
dup_groups, dup_member = [], set()
for root, idxs in groups.items():
    if len(idxs) < 2:
        continue
    titres = {}
    for i in idxs:
        titres[rows[i]["titre"]] = titres.get(rows[i]["titre"], 0) + 1
    rep = sorted(titres.items(), key=lambda kv: (-kv[1], len(kv[0])))[0][0]
    dup_groups.append({"titre_commun": rep,
                       "ids": [rows[i]["video_id"] for i in idxs], "nb": len(idxs)})
    dup_member.update(idxs)
dup_groups.sort(key=lambda g: -g["nb"])

# ------------------------------------------------------------------ verdicts
MARKERS = ["test", "essai", "brouillon", "draft", "wip", "todo",
           "a finir", "v1", "v2", "temp"]


def has_marker(title):
    pad = " " + norm_title(title) + " "
    for m in MARKERS:
        if " " + m + " " in pad:
            return m
    return None


for i, r in enumerate(rows):
    v = r["vues"] if r["vues"] is not None else 0
    a = r["age_jours"]
    mk = has_marker(r["titre"])
    if v == 0 and a > 30:
        r["verdict"], r["raison"] = "rouge", "0 vue et publiee il y a %d jours (>30)" % a
    elif v < 10 and a > 182:
        r["verdict"], r["raison"] = "rouge", "%d vues et publiee il y a %d jours (>6 mois)" % (v, a)
    elif r["visibilite"] == "unlisted" and a > 30:
        r["verdict"], r["raison"] = "rouge", "unlisted depuis %d jours (>30)" % a
    elif v < 100 and a > 365:
        r["verdict"], r["raison"] = "jaune", "%d vues et %d jours (>12 mois)" % (v, a)
    elif r["duree_s"] < 60 and a > 182:
        r["verdict"], r["raison"] = "jaune", "duree %ds (<60s) et %d jours (>6 mois)" % (r["duree_s"], a)
    elif mk:
        r["verdict"], r["raison"] = "jaune", "marqueur de brouillon dans le titre : '%s'" % mk
    elif i in dup_member:
        r["verdict"], r["raison"] = "jaune", "titre quasi identique a un autre clip (doublon probable)"
    else:
        r["verdict"], r["raison"] = "vert", "%d vues, %d jours, %s" % (v, a, r["visibilite"])

ORDER = {"rouge": 0, "jaune": 1, "vert": 2}
rows.sort(key=lambda r: (ORDER[r["verdict"]], r["vues"] if r["vues"] is not None else 0))

cls_csv = os.path.join(SCRATCH, "youtube_classification.csv")
with open(cls_csv, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["video_id", "titre", "date", "vues", "duree_s", "verdict", "raison"])
    for r in rows:
        w.writerow([r["video_id"], r["titre"], r["date_court"],
                    "" if r["vues"] is None else r["vues"],
                    r["duree_s"], r["verdict"], r["raison"]])

counts = {"rouge": 0, "jaune": 0, "vert": 0}
for r in rows:
    counts[r["verdict"]] += 1

cls_json = os.path.join(SCRATCH, "youtube_classification.json")
with open(cls_json, "w", encoding="utf-8") as fh:
    json.dump({
        "genere_le": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "criteres": {
            "rouge": ["vues=0 et age>30j", "vues<10 et age>6 mois", "unlisted depuis >30j"],
            "jaune": ["vues<100 et age>12 mois", "duree<60s et age>6 mois",
                      "marqueur brouillon dans le titre",
                      "doublon titre (Levenshtein normalise < 0.2)"],
        },
        "par_verdict": counts,
        "groupes_doublons": dup_groups,
        "liste_rouge": [{"id": r["video_id"], "titre": r["titre"], "vues": r["vues"],
                         "date": r["date_court"], "duree_s": r["duree_s"],
                         "raison": r["raison"]} for r in rows if r["verdict"] == "rouge"],
        "liste_jaune": [{"id": r["video_id"], "titre": r["titre"], "vues": r["vues"],
                         "date": r["date_court"], "duree_s": r["duree_s"],
                         "raison": r["raison"]} for r in rows if r["verdict"] == "jaune"],
    }, fh, ensure_ascii=False, indent=1)

print("VERDICTS=" + json.dumps(counts))
print("GROUPES_DOUBLONS=%d" % len(dup_groups))
print("FICHIERS=" + " ; ".join([inv_csv, inv_json, cls_csv, cls_json]))
