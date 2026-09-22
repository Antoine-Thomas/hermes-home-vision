import re, sys
from pathlib import Path

WIKI = Path(r"C:\Users\searc\AppData\Local\hermes\wiki")
SECTIONS = [("concepts", "Concepts"), ("entities", "Entities"),
            ("comparisons", "Comparisons"), ("queries", "Queries"),
            ("syntheses", "Syntheses")]

def summary_of(path):
    txt = path.read_text(encoding="utf-8", errors="replace")
    parts = txt.split("---", 2)
    body = parts[2] if len(parts) >= 3 else txt
    lines = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            if lines: break
            continue
        if line[0] in "#-*" or line.startswith("<!--"):
            if lines: break
            continue
        lines.append(line)
        if re.search(r"[.!?](\s|$)", line):
            break
    joined = " ".join(lines)
    m = re.match(r"^(.+?[.!?])(\s|$)", joined)
    return (m.group(1) if m else joined[:180]).strip()

out = [
    "# Wiki Index", "",
    "> Catalogue du contenu. Chaque page wiki est listée sous son type avec un",
    "> résumé d'une ligne. **Lire ce fichier en premier** pour trouver les pages",
    "> pertinentes d'une question.",
    "> Last updated: 2026-09-22 | Total pages: 0", "",
]
total = 0
for folder, title in SECTIONS:
    d = WIKI / folder
    files = sorted(d.glob("*.md"), key=lambda p: p.stem.lower()) if d.is_dir() else []
    out.append("## " + title)
    if not files:
        out.append("<!-- ordre alphabetique -->")
    else:
        for f in files:
            out.append("- [[%s]] — %s" % (f.stem, summary_of(f)))
            total += 1
    out.append("")

text = re.sub(r"Total pages: \d+", "Total pages: %d" % total, "\n".join(out))
(WIKI / "index.md").write_text(text + "\n", encoding="utf-8")
print("index.md reconstruit : %d entrees" % total)
