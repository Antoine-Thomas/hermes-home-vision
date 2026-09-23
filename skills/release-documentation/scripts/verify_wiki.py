"""Verification independante du wiki L1 (ne fait confiance a aucune sortie de run).

Usage : python verify_wiki.py
Wiki vise : $WIKI_PATH, sinon %LOCALAPPDATA%\hermes\wiki
Sortie : code 0 = conforme ; 1 = echecs (les avertissements ne font pas echouer).

A lancer APRES tout ajout ou toute compilation, et avant d'annoncer le resultat :
il ne partage aucun code avec le compilateur, donc il voit ce que celui-ci a rate.
"""
import os
import re
import sys
from pathlib import Path

WIKI = Path(os.environ.get("WIKI_PATH")
            or (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "hermes" / "wiki"))
SECTIONS = ("concepts", "entities", "comparisons", "queries", "syntheses")
TYPES = {"entity": "entities", "concept": "concepts", "comparison": "comparisons",
         "query": "queries", "summary": "syntheses"}

schema = (WIKI / "SCHEMA.md").read_text(encoding="utf-8")
m = re.search(r"^## Taxonomie des tags(.*?)^## ", schema, re.S | re.M)
tax = set(re.findall(r"`([a-z0-9][a-z0-9._-]*)`", m.group(1))) if m else set()

pages = sorted(f for d in SECTIONS for f in (WIKI / d).rglob("*.md"))
slugs = {f.stem for f in pages}
print("pages : %d" % len(pages))

fails, warnings = [], []
raws = {f.relative_to(WIKI).as_posix() for f in (WIKI / "raw").rglob("*.md")}

for f in pages:
    rel = f.relative_to(WIKI).as_posix()
    txt = f.read_text(encoding="utf-8")
    if not txt.startswith("---"):
        fails.append("%s : pas de frontmatter" % rel); continue
    fm = txt.split("---", 2)[1]
    body = txt.split("---", 2)[2]
    for k in ("title", "created", "updated", "type", "tags", "sources"):
        if not re.search(r"^%s:" % k, fm, re.M):
            fails.append("%s : frontmatter sans `%s`" % (rel, k))
    t = (re.search(r"^type:\s*(\S+)", fm, re.M) or [None, ""])[1]
    if t not in TYPES:
        fails.append("%s : type invalide %r" % (rel, t))
    elif TYPES[t] != f.parent.name:
        fails.append("%s : type %s mais dossier %s" % (rel, t, f.parent.name))
    if tax:
        for tag in re.findall(r"[a-z0-9][a-z0-9._-]*", (re.search(r"^tags:\s*\[(.*?)\]", fm, re.M) or [None, ""])[1]):
            if tag not in tax:
                fails.append("%s : tag hors taxonomie %r" % (rel, tag))
    for src in re.findall(r"raw/[\w./-]+\.md", fm):
        if src not in raws:
            fails.append("%s : source inexistante %s" % (rel, src))
    links = re.findall(r"\[\[([^\]]+)\]\]", body)
    if len(links) < 2:
        fails.append("%s : %d wikilien(s)" % (rel, len(links)))
    for l in links:
        if l.split("|")[0].strip() not in slugs:
            fails.append("%s : lien mort [[%s]]" % (rel, l))
    fr = len(re.findall(r"\b(le|la|les|des|une?|est|sont|pour|avec|dans|sur|par|qui|que|du|aux|au|ce|cette)\b", body, re.I))
    en = len(re.findall(r"\b(the|and|with|for|from|that|this|which|are|is|was|of|to|in|on|by)\b", body, re.I))
    if en > fr:
        warnings.append("%s : langue plutot anglaise (fr=%d en=%d)" % (rel, fr, en))

# index : chaque page y figure, aucune entree orpheline, pas de doublon
idx = (WIKI / "index.md").read_text(encoding="utf-8")
entries = re.findall(r"^- \[\[([^\]]+)\]\]", idx, re.M)
for f in pages:
    if f.stem not in entries:
        fails.append("index.md : page %s absente du catalogue" % f.stem)
for e in entries:
    if e not in slugs:
        fails.append("index.md : entree orpheline [[%s]]" % e)
if len(entries) != len(set(entries)):
    fails.append("index.md : entrees en doublon")
declared = re.search(r"Total pages:\s*(\d+)", idx)
if declared and int(declared.group(1)) != len(pages):
    fails.append("index.md : 'Total pages: %s' mais %d pages sur disque" % (declared.group(1), len(pages)))
for d in SECTIONS:
    if "## %s" % d.capitalize() not in idx:
        fails.append("index.md : section %s absente" % d)

# log : une entree datee par compilation
log = (WIKI / "log.md").read_text(encoding="utf-8")
n_log = len(re.findall(r"^## \[\d{4}-\d{2}-\d{2}\] ingest \| compilation one-shot", log, re.M))
print("entrees de log 'compilation one-shot' : %d" % n_log)
if n_log == 0:
    fails.append("log.md : aucune entree 'compilation one-shot'")

print("\nsources de raw/ : %d, toutes citees : %s" % (len(raws), all(
    any(r in (WIKI / p).read_text(encoding="utf-8") for p in [f.relative_to(WIKI).as_posix() for f in pages])
    for r in raws)))

print("\n--- echecs (%d) ---" % len(fails))
for x in fails:
    print("   X", x)
print("--- avertissements (%d) ---" % len(warnings))
for x in warnings:
    print("   !", x)
sys.exit(1 if fails else 0)
