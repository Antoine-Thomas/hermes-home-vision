#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inventaire IMAP en LECTURE SEULE (aucune modification du serveur).

Usage:
    python gmail_imap_label_inventory.py [fichier_env] [sortie.json]

Defaut env : %LOCALAPPDATA%/hermes/.env  (EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_IMAP_HOST)

Sortie : dossiers visibles en IMAP, etiquettes reellement portees + comptages,
sondes de categories Gmail, top expediteurs, volumetrie par annee, comptage des
messages sans label utilisateur, JSON complet (uid/flags/labels/expediteur/objet/date)
reutilisable pour construire un plan de classement.
Aucun STORE, aucun COPY, BODY.PEEK partout.
"""
import base64
import imaplib
import json
import os
import pathlib
import re
import sys
from collections import Counter
from email.header import decode_header
from email.utils import parsedate_to_datetime

DEFAULT_ENV = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "hermes" / ".env"
ALL_NAMES = ("[Gmail]/Tous les messages", "[Gmail]/All Mail")


def load_env(path):
    d = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def utf7_decode(s):
    """Modified UTF-7 -> str (imaplib.utf7_decode n'existe pas en 3.11)."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "&":
            j = s.find("-", i)
            if j == -1:
                out.append(c); i += 1
            elif j == i + 1:
                out.append("&"); i = j + 1
            else:
                b64 = s[i + 1:j] + "=" * ((4 - (j - i - 1) % 4) % 4)
                try:
                    out.append(base64.b64decode(b64).decode("utf-16-be"))
                except Exception:
                    out.append(s[i:j + 1])
                i = j + 1
        else:
            out.append(c); i += 1
    return "".join(out)


def dec(s):
    if not s:
        return ""
    r = ""
    for part, cs in decode_header(s):
        r += part.decode(cs or "utf-8", errors="replace") if isinstance(part, bytes) else part
    return r.replace("\r", " ").replace("\n", " ").strip()


def balanced(meta, key):
    pos = meta.find(key)
    if pos == -1:
        return None
    start, depth, i = pos + len(key), 1, pos + len(key)
    while i < len(meta) and depth:
        if meta[i:i + 1] == b"(":
            depth += 1
        elif meta[i:i + 1] == b")":
            depth -= 1
        i += 1
    return meta[start:i - 1].decode("utf-8", "replace")


def parse_labels(blob):
    """Tokens de X-GM-LABELS (...), guillemets et echappements respectes."""
    toks, i, cur, quoted = [], 0, "", False
    while i < len(blob):
        c = blob[i]
        if quoted:
            if c == "\\":
                cur += blob[i + 1]; i += 2; continue
            if c == '"':
                quoted = False; toks.append(cur); cur = ""; i += 1; continue
            cur += c
        else:
            if c == '"':
                quoted, cur = True, ""
            elif c.isspace():
                if cur:
                    toks.append(cur); cur = ""
            else:
                cur += c
        i += 1
    if cur:
        toks.append(cur)
    return [utf7_decode(t) for t in toks if t]


def main():
    env_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ENV
    out_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("gmail_inventory.json")
    env = load_env(env_path)

    M = imaplib.IMAP4_SSL(env.get("EMAIL_IMAP_HOST", "imap.gmail.com"), 993, timeout=180)
    M.login(env["EMAIL_ADDRESS"], env["EMAIL_PASSWORD"])
    print("X-GM-EXT-1 :", "X-GM-EXT-1" in M.capabilities)

    folders = []
    for raw in M.list()[1]:
        t = raw.decode("utf-8", "replace")
        m = re.match(r'\((?P<flags>[^)]*)\)\s+"(?P<delim>[^"]*)"\s+(?P<name>.*)$', t)
        if not m:
            continue
        nm = re.search(r'"([^"]*)"\s*$', m.group("name").strip())
        raw_name = nm.group(1) if nm else m.group("name").strip('"')
        folders.append({"flags": m.group("flags"), "raw": raw_name,
                        "name": utf7_decode(raw_name)})
    print("\n=== DOSSIERS VISIBLES EN IMAP (%d) ===" % len(folders))
    for f in sorted(folders, key=lambda x: x["name"]):
        print("  %-50s %s" % (f["name"], f["flags"]))

    allbox = next((f for f in folders if "\\All" in f["flags"]), None) or \
        next((f for f in folders if f["name"] in ALL_NAMES), None)
    if not allbox:
        print("ABORT : dossier 'Tous les messages / All Mail' introuvable")
        return 1

    typ, d = M.select('"%s"' % allbox["raw"], readonly=True)
    total_exists = int(d[0])
    uids = [u.decode() for u in M.uid("search", None, "ALL")[1][0].split()]
    print("\n%s : EXISTS=%d, UID SEARCH ALL=%d" % (allbox["name"], total_exists, len(uids)))

    probes = {}
    for q in ("category:promotions", "category:social", "category:updates",
              "category:forums", "category:personal", "in:inbox", "is:unread"):
        typ, dat = M.uid("search", None, "X-GM-RAW", '"%s"' % q)
        probes[q] = len(dat[0].split()) if typ == "OK" else "ERR"
    print("\n=== SONDES X-GM-RAW ===")
    for k, v in probes.items():
        print("  %-24s %s" % (k, v))

    msgs, label_counter = [], Counter()
    CHUNK = 250
    for i in range(0, len(uids), CHUNK):
        chunk = uids[i:i + CHUNK]
        typ, res = M.uid("fetch", ",".join(chunk).encode(),
                         "(UID FLAGS X-GM-LABELS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if typ != "OK":
            print("  lot %d : %s" % (i, typ)); continue
        for item in res:
            meta, payload = (item[0], item[1].decode("utf-8", "replace")) \
                if isinstance(item, tuple) else (item, "")
            mu = re.search(rb"UID (\d+)", meta)
            if not mu:
                continue
            labs = parse_labels(balanced(meta, b"X-GM-LABELS (") or "")
            fl = balanced(meta, b"FLAGS (") or ""
            frm = subj = date = ""
            for line in payload.splitlines():
                low = line.lower()
                if low.startswith("from:"):
                    frm = dec(line[5:])
                elif low.startswith("subject:"):
                    subj = dec(line[8:])
                elif low.startswith("date:"):
                    date = line[5:].strip()
            ma = re.search(r"<([^>]+)>", frm)
            addr = ((ma.group(1) if ma else frm).strip().strip('"') or frm.strip('"')).lower()
            for l in labs:
                label_counter[l] += 1
            try:
                dt = parsedate_to_datetime(date).strftime("%Y-%m-%d")
            except Exception:
                dt = ""
            msgs.append({"uid": mu.group(1).decode(), "from": frm, "addr": addr,
                         "dom": addr.split("@")[-1] if "@" in addr else "",
                         "subj": subj, "date": dt, "labels": labs, "flags": fl})
        print("  %d/%d" % (min(i + CHUNK, len(uids)), len(uids)), end="\r")
    print()
    assert len(set(m["uid"] for m in msgs)) == len(msgs), "UID dupliques : revoir le FETCH"

    print("\n=== ETIQUETTES REELLEMENT PORTEES ===")
    for l, c in label_counter.most_common():
        print("  %-44s %6d" % (l, c))

    sysl = re.compile(r"^\\\\?[A-Za-z]|^\[Imap\]/")
    user_labels = [l for l in label_counter if not sysl.match(l)]
    unclass = [m for m in msgs if not any(l in user_labels for l in m["labels"])]
    print("\nlabels utilisateur : %s" % user_labels)
    print("messages sans label utilisateur : %d / %d" % (len(unclass), len(msgs)))
    print("  dont en INBOX : %d | deja archives : %d | non lus : %d" % (
        sum(1 for m in unclass if "\\Inbox" in m["labels"]),
        sum(1 for m in unclass if "\\Inbox" not in m["labels"]),
        sum(1 for m in unclass if "\\Seen" not in (m["flags"] or ""))))

    print("\n=== TOP 30 EXPEDITEURS (non classes) ===")
    for a, c in Counter(m["addr"] for m in unclass).most_common(30):
        print("  %-46s %6d" % (a[:46], c))
    print("\n=== REPARTITION PAR ANNEE (non classes) ===")
    for y, c in sorted(Counter(m["date"][:4] for m in unclass).items()):
        print("  %-6s %6d" % (y or "?", c))

    json.dump({"folders": folders, "label_usage": dict(label_counter),
               "user_labels": user_labels, "probes": probes,
               "exists": total_exists, "msgs": msgs},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    print("\nJSON -> %s" % out_path.resolve())
    M.logout()
    return 0


if __name__ == "__main__":
    sys.exit(main())
