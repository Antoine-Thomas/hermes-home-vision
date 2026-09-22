"""Exporte les notes SiYuan récentes dans le wiki L1, sous `raw/notes/`.

Une note SiYuan = UNE source brute immuable dans le wiki (convention du skill
`llm-wiki` : `raw/` n'est jamais modifié ; une mise à jour de la note SiYuan
produit une NOUVELLE capture, l'ancienne n'est pas réécrite).

Idempotent : une note dont le sha256 du corps est déjà présent dans `raw/notes/`
est sautée (détection de dérive du skill, même logique).

Le jeton SiYuan est lu dans `%LOCALAPPDATA%\\hermes\\.env` ; il n'est jamais
affiché ni journalisé.

Usage :
    python siyuan_sync.py                     # 5 notes des 3 derniers jours
    python siyuan_sync.py --limit 10 --days 7
    python siyuan_sync.py --dry-run           # liste sans écrire
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERMES = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
ENV_FILE = HERMES / ".env"
WIKI = Path(os.environ.get("WIKI_PATH") or (HERMES / "wiki"))
NOTES = WIKI / "raw" / "notes"
API = "http://127.0.0.1:6806"  # les chemins appellent /api/... explicitement
TIMEOUT = 30


def token() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        if line.startswith("SIYUAN_TOKEN="):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            if val:
                return val
    raise RuntimeError("SIYUAN_TOKEN introuvable dans %s" % ENV_FILE)


TOK = token()


def api(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Token " + TOK, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("SiYuan HTTP %s sur %s: %s"
                           % (exc.code, path, exc.read().decode("utf-8", "replace")[:300])) from None
    except urllib.error.URLError as exc:
        raise RuntimeError("SiYuan injoignable: %s" % exc.reason) from None
    if out.get("code") not in (0, None):
        raise RuntimeError("SiYuan erreur %s sur %s: %s" % (out.get("code"), path, out.get("msg")))
    return out.get("data", {})


def slug(text: str, maxlen: int = 48) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text[:maxlen].rstrip("-")) or "note"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def existing_hashes() -> set:
    """sha256 déjà ingérés (frontmatter des fichiers de raw/notes/)."""
    out = set()
    if NOTES.is_dir():
        for p in NOTES.glob("*.md"):
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[:8]:
                if line.startswith("sha256:"):
                    out.add(line.split(":", 1)[1].strip())
    return out


def recent_docs(limit: int, days: int) -> list:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d%H%M%S")
    sql = ("select id, content, updated, box from blocks "
           "where type = 'd' and updated > '%s' "
           "order by updated desc limit %d" % (since, limit))
    return api("/api/query/sql", {"stmt": sql})


def doc_markdown(doc_id: str) -> str:
    data = api("/api/export/exportMdContent", {"id": doc_id})
    return data.get("content", "")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    try:
        docs = recent_docs(args.limit, args.days)
    except Exception as exc:
        print("ERREUR SiYuan : %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2

    if not docs:
        print("Aucun document SiYuan modifié depuis %d jour(s)." % args.days)
        return 0

    NOTES.mkdir(parents=True, exist_ok=True)
    known = existing_hashes()
    today = datetime.now().strftime("%Y%m%d")
    written, skipped = [], []

    for d in docs:
        title = (d.get("content") or "sans-titre").strip()
        body = doc_markdown(d["id"]).strip()
        if not body:
            skipped.append((title, "corps vide"))
            continue
        digest = sha256(body)
        if digest in known:
            skipped.append((title, "deja ingere (sha256 identique)"))
            continue
        target = NOTES / ("siyuan-%s-%s.md" % (today, slug(title)))
        fm = ("---\n"
              "source_url: siyuan://%s/%s\n"
              "ingested: %s\n"
              "sha256: %s\n"
              "---\n\n" % (d.get("box"), d["id"], datetime.now().strftime("%Y-%m-%d"), digest))
        content = fm + "# " + title + "\n\n" + body + "\n"
        if args.dry_run:
            written.append((title, str(target) + "  [dry-run]"))
            continue
        if target.exists() and sha256(target.read_text(encoding="utf-8", errors="replace")) == sha256(content):
            skipped.append((title, "fichier identique deja present"))
            continue
        target.write_text(content, encoding="utf-8")
        known.add(digest)
        written.append((title, str(target)))

    print("SiYuan -> raw/notes : %d ecrit(s), %d saute(s)" % (len(written), len(skipped)))
    for t, p in written:
        print("  + %s\n      %s" % (t, p))
    for t, why in skipped:
        print("  = %s  (%s)" % (t, why))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
