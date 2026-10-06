#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Application par lots d'etiquettes EXISTANTES via UID STORE +X-GM-LABELS.

Usage:
    python gmail_imap_label_apply.py plan.json "TECH=Professionnel;ADMIN=plus important" --confirm
    python gmail_imap_label_apply.py plan.json "TECH=Professionnel" --dry-run

plan.json attendu (produit par l'etape d'inventaire + la classification) :
    {"themes": {"TECH": ["uid", ...], ...},
     "msgs":   [{"uid": "...", "labels": ["\\Inbox"], "flags": "\\Seen"}, ...]}

Garde-fous : refuse de tourner sans --confirm ou --dry-run, abandonne si un mail
cible porte deja un label utilisateur, n'ecrit QUE +X-GM-LABELS (jamais COPY,
jamais d'archivage, jamais de STORE \\Seen), et compare avant/apres le total de la
boite et le comptage de chaque label.
"""
import base64
import imaplib
import json
import os
import pathlib
import sys
import time

DEFAULT_ENV = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "hermes" / ".env"
LOT = 250


def load_env(path):
    d = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def utf7_encode(s):
    """str -> modified UTF-7, pour les noms de labels non-ASCII."""
    out, buf = [], ""
    def flush():
        nonlocal buf
        if buf:
            b64 = base64.b64encode(buf.encode("utf-16-be")).decode().rstrip("=")
            out.append("&" + b64 + "-")
            buf = ""
    for ch in s:
        if ch == "&":
            flush(); out.append("&-")
        elif 0x20 <= ord(ch) <= 0x7E:
            flush(); out.append(ch)
        else:
            buf += ch
    flush()
    return "".join(out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    if "--confirm" not in sys.argv and "--dry-run" not in sys.argv:
        print("REFUS : ajouter --confirm (ou --dry-run) apres validation utilisateur du plan.")
        return 2
    dry = "--dry-run" in sys.argv
    plan_path = pathlib.Path(sys.argv[1])
    mapping = []
    for pair in sys.argv[2].split(";"):
        theme, _, label = pair.partition("=")
        mapping.append((theme.strip(), label.strip(), utf7_encode(label.strip())))

    plan = json.load(open(plan_path, encoding="utf-8"))
    msgs = {m["uid"]: m for m in plan.get("msgs", [])}
    user_labels = [lab for _, lab, _ in mapping]
    env = load_env(os.environ.get("IMAP_ENV", str(DEFAULT_ENV)))

    M = imaplib.IMAP4_SSL(env.get("EMAIL_IMAP_HOST", "imap.gmail.com"), 993, timeout=300)
    M.login(env["EMAIL_ADDRESS"], env["EMAIL_PASSWORD"])
    ALL = '"[Gmail]/Tous les messages"'

    typ, d = M.select(ALL, readonly=True)
    total_avant = int(d[0])
    baseline = {}
    for _, lab, raw in mapping:
        typ, d = M.select('"%s"' % raw, readonly=True)
        baseline[lab] = int(d[0])
    print("AVANT  total=%d  %s" % (total_avant, baseline))

    for theme, lab, raw in mapping:
        for u in plan["themes"].get(theme, []):
            if any(l in user_labels for l in msgs.get(u, {}).get("labels", [])):
                print("ABORT : UID %s porte deja %s" % (u, msgs[u]["labels"]))
                return 1

    rapport = {"dry_run": dry, "total_avant": total_avant, "labels_avant": baseline,
               "applique": {}, "erreurs": []}
    M.select(ALL, readonly=False)
    for theme, lab, raw in mapping:
        uids = plan["themes"].get(theme, [])
        ok = 0
        for i in range(0, len(uids), LOT):
            chunk = uids[i:i + LOT]
            if dry:
                ok += len(chunk); continue
            try:
                typ, res = M.uid("store", ",".join(chunk).encode(),
                                 "+X-GM-LABELS", '("%s")' % raw)
            except Exception as e:
                typ, res = "EXC", str(e)
            if typ != "OK":
                rapport["erreurs"].append({"theme": theme, "lot": i, "reponse": str(res)[:200]})
            else:
                ok += len(chunk)
            print("  %-16s %5d/%d" % (lab, min(i + LOT, len(uids)), len(uids)), end="\r")
            time.sleep(0.2)
        rapport["applique"][lab] = ok
        print("  %-16s %d mails traites" % (lab, ok))

    typ, d = M.select(ALL, readonly=True)
    total_apres = int(d[0])
    apres = {}
    for _, lab, raw in mapping:
        typ, d = M.select('"%s"' % raw, readonly=True)
        apres[lab] = int(d[0])
    rapport["total_apres"] = total_apres
    rapport["labels_apres"] = apres
    print("\nAPRES  total=%d  (inchange: %s)" % (total_apres, total_apres == total_avant))
    for lab, n in apres.items():
        print("  %-18s %6d  (avant %d, +%d)" % (lab, n, baseline[lab], n - baseline[lab]))
    json.dump(rapport, open(plan_path.with_name("rapport_application.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1)
    M.logout()
    return 0


if __name__ == "__main__":
    sys.exit(main())
