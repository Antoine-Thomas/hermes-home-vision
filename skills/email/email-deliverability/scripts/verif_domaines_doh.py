#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifie en masse la resolvabilite des domaines d'une liste d'emails (MX puis A) via
DNS-over-HTTPS (dns.google). Aucune dependance externe (urllib + concurrent.futures).

Usage:
  python verif_domaines_doh.py --csv contacts.csv [--csv autre.csv] [--out dns_domains.json]
  python verif_domaines_doh.py --emails emails.txt
  python verif_domaines_doh.py --csv contacts.csv --colonne EMAIL

Sortie : resume par categorie + echantillons des domaines non delivrables, et un JSON
{domaine: {mx, a, status, err}} reutilisable par le tri de liste.

A SAVOIR :
  status 3 = NXDOMAIN, status 2 = SERVFAIL (NS morts, zone cassee, lame delegation).
  Les DEUX sont non delivrables : classer sur `not MX and not A`, jamais sur `status == 3` seul.
  Ce script ne teste PAS les blacklists : une requete DNSBL depuis un resolveur public renvoie
  127.255.255.254 (« query refused »), qui n'est pas une inscription.
"""
import argparse
import concurrent.futures as cf
import csv
import json
import re
import sys
import urllib.request

UA = {"User-Agent": "hermes-dns-check/1.0"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
COLS = ("EMAIL", "email", "Email", "mail", "adresse", "e-mail")


def doh(name, rtype, timeout=12):
    url = "https://dns.google/resolve?name=%s&type=%s" % (name, rtype)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def check(dom):
    """MX puis A. Deux tentatives en cas d'erreur reseau."""
    res = {"domain": dom, "mx": False, "a": False, "status": None, "err": None}
    for _ in range(2):
        try:
            for rtype in ("MX", "A"):
                j = doh(dom, rtype)
                st = j.get("Status")
                if st is not None:
                    res["status"] = st if res["status"] is None else max(res["status"], st)
                if st == 0 and j.get("Answer"):
                    res["mx" if rtype == "MX" else "a"] = True
                if st == 3:
                    return res
            return res
        except Exception as e:  # reseau / JSON
            res["err"] = str(e)[:80]
    return res


def domaine(addr):
    return addr.rsplit("@", 1)[-1].strip().lower() if "@" in addr else ""


def collecter(args):
    out = []
    for f in args.csv or []:
        with open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                cols = [args.colonne] if args.colonne else COLS
                for c in cols:
                    v = (r.get(c) or "").strip()
                    if v:
                        out.append(v)
                        break
    for f in args.emails or []:
        with open(f, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser(description="Resolvabilite des domaines d'une liste d'emails (DoH)")
    ap.add_argument("--csv", action="append", default=[], help="CSV a lire (repetable)")
    ap.add_argument("--emails", action="append", default=[], help="fichier texte, une adresse par ligne")
    ap.add_argument("--colonne", default="", help="colonne email (auto par defaut)")
    ap.add_argument("--out", default="dns_domains.json", help="JSON de sortie")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--echantillon", type=int, default=30, help="domaines non delivrables a afficher")
    a = ap.parse_args()
    if not a.csv and not a.emails:
        ap.error("fournir --csv et/ou --emails")

    emails = [e for e in collecter(a) if EMAIL_RE.match(e.strip().lower())]
    doms = sorted({domaine(e.strip().lower()) for e in emails if "." in domaine(e.strip().lower())})
    if not doms:
        print("aucun domaine exploitable")
        return 2
    print("adresses lues : %d | domaines distincts testes : %d" % (len(emails), len(doms)))

    res = {}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(check, doms):
            res[r["domain"]] = r

    def cat(r):
        if r["err"]:
            return "erreur_reseau"
        if r["mx"] or r["a"]:
            return "ok"
        if r["status"] == 3:
            return "nxdomain"
        if r["status"] == 2:
            return "zone_cassee"
        return "sans_mx_ni_a"

    stats = {}
    for r in res.values():
        stats.setdefault(cat(r), []).append(r["domain"])
    for k in ("ok", "nxdomain", "zone_cassee", "sans_mx_ni_a", "erreur_reseau"):
        v = stats.get(k, [])
        print("  %-14s %d" % (k, len(v)))
        if k != "ok":
            for d in v[: a.echantillon]:
                print("      - %s" % d)
    morts = set(stats.get("nxdomain", [])) | set(stats.get("zone_cassee", [])) | set(stats.get("sans_mx_ni_a", []))
    concernees = sum(1 for e in emails if domaine(e.strip().lower()) in morts)
    print("adresses sur domaine non delivrable : %d / %d" % (concernees, len(emails)))

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("JSON : %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
