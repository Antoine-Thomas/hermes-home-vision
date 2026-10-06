#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validation statique d'un template de mail HTML de campagne, avant envoi.

Repond en une commande aux controles de la section « Valider la structure en
statique » du skill campaign-presend-qa : balises equilibrees, meta viewport,
largeur de conteneur, media query, compte de liens / images / iframes,
balises de fusion de l'ESP, et termes interdits.

Usage :
    python check_html_static.py <fichier.html> [options]

Options :
    --forbid TERME       Terme interdit (option repetable) : 0 occurrence exigee.
    --expect-links N     Nombre exact de liens <a href> attendu.
    --expect-images N    Nombre exact d'<img> attendu.
    --max-width N        Largeur max attendue du conteneur (defaut : 600).
    --json               Sortie JSON au lieu du rapport lisible.

Code retour : 0 si aucune erreur bloquante, 1 sinon.
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class StructureChecker(HTMLParser):
    """Empile les balises ouvrantes et signale les desequilibres."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []          # (tag, ligne d'ouverture)
        self.errors = []
        self.links = []          # href
        self.images = []         # src
        self.iframes = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.links.append(d["href"])
        if tag == "img":
            self.images.append(d.get("src", ""))
        if tag == "iframe":
            self.iframes += 1
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        # <br/> <img .../> : rien a empiler, mais compter les ressources.
        d = dict(attrs)
        if tag == "img":
            self.images.append(d.get("src", ""))
        if tag == "iframe":
            self.iframes += 1

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append("balise </%s> fermante sans ouvrante" % tag)
            return
        if self.stack[-1][0] != tag:
            self.errors.append(
                "desordre : </%s> rencontre, </%s> attendue (ouverte ligne %d)"
                % (tag, self.stack[-1][0], self.stack[-1][1])
            )
            if any(t == tag for t, _ in self.stack):
                while self.stack and self.stack[-1][0] != tag:
                    self.stack.pop()
                if self.stack:
                    self.stack.pop()
            return
        self.stack.pop()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fichier")
    ap.add_argument("--forbid", action="append", default=[],
                    help="terme interdit (repetable)")
    ap.add_argument("--expect-links", type=int, default=None)
    ap.add_argument("--expect-images", type=int, default=None)
    ap.add_argument("--max-width", type=int, default=600)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    with open(args.fichier, encoding="utf-8") as fh:
        raw = fh.read()

    checker = StructureChecker()
    checker.feed(raw)
    checker.close()

    errors = list(checker.errors)
    for tag, line in checker.stack:
        errors.append("balise <%s> ouverte ligne %d jamais fermee" % (tag, line))

    has_viewport = bool(re.search(r'name\s*=\s*["\']viewport["\']', raw))
    if not has_viewport:
        errors.append("meta viewport absent")

    maxw_re = re.compile(r"max-width\s*:\s*%dpx" % args.max_width)
    if not maxw_re.search(raw):
        errors.append("largeur de conteneur max-width: %dpx absente" % args.max_width)
    if "@media" not in raw:
        errors.append("aucune media query (@media)")
    if checker.iframes:
        errors.append("%d <iframe> trouve(s) — les clients mail les suppriment"
                      % checker.iframes)

    merge_tags = re.findall(r"\{\{[^{}]+\}\}", raw)

    if args.expect_links is not None and len(checker.links) != args.expect_links:
        errors.append("liens : %d trouve(s), %d attendu(s)"
                      % (len(checker.links), args.expect_links))
    if args.expect_images is not None and len(checker.images) != args.expect_images:
        errors.append("images : %d trouvee(s), %d attendue(s)"
                      % (len(checker.images), args.expect_images))

    forbidden_hits = []
    for term in args.forbid:
        n = raw.count(term)
        if n:
            forbidden_hits.append((term, n))
            errors.append("terme interdit present %dx : %r" % (n, term))

    report = {
        "fichier": args.fichier,
        "octets": len(raw.encode("utf-8")),
        "balises_non_fermees": ["%s (ligne %d)" % (t, l) for t, l in checker.stack],
        "liens": len(checker.links),
        "images": len(checker.images),
        "iframes": checker.iframes,
        "meta_viewport": has_viewport,
        "max_width": args.max_width,
        "media_query": "@media" in raw,
        "balises_fusion": len(merge_tags),
        "termes_interdits": forbidden_hits,
        "erreurs": errors,
        "verdict": "OK" if not errors else "ERREUR",
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("fichier        : %s (%d octets)" % (args.fichier, report["octets"]))
        print("liens          : %d" % report["liens"])
        print("images         : %d" % report["images"])
        print("iframes        : %d" % report["iframes"])
        print("meta viewport  : %s" % ("oui" if has_viewport else "NON"))
        print("max-width      : %dpx (%s)" % (args.max_width,
              "oui" if maxw_re.search(raw) else "NON"))
        print("media query    : %s" % ("oui" if report["media_query"] else "NON"))
        print("balises fusion : %d (resolues par l'ESP a l'envoi, pas un defaut)"
              % report["balises_fusion"])
        if forbidden_hits:
            print("termes interdits:")
            for term, n in forbidden_hits:
                print("  - %r : %d occurrence(s)" % (term, n))
        if errors:
            print("erreurs (%d):" % len(errors))
            for e in errors:
                print("  - %s" % e)
        print("VERDICT        : %s" % report["verdict"])

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
