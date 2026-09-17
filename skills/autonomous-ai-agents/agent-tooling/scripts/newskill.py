#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
newskill.py - Genere, valide et installe un skill Hermes.

Prend un corps markdown + des metadonnees, produit un SKILL.md conforme, le
valide, l'installe dans $HERMES_HOME/skills/<categorie>/<nom>/ et verifie que
Hermes le voit.

Les 3 regles qui font echouer une creation de skill, appliquees ici :
  1. description <= 60 caracteres (au-dela : tronquee a 57 + '...' dans l'index
     du prompt systeme, le skill ne se declenche plus)
  2. nom en minuscules / tirets / underscores, <= 64 caracteres
  3. une section de declencheurs contenant 'When to Use' (le linter de Hermes
     cherche cette chaine anglaise ; un titre bilingue
     '## Quand l'utiliser (When to Use)' satisfait les deux)

Usage :
  python newskill.py --name mon-skill --description "Faire X." \
                     --category devops --tags a,b --body corps.md
  python newskill.py ... --dry-run          # affiche sans ecrire
  python newskill.py --check mon-skill      # valide un skill deja installe

Codes de sortie : 0 = ok, 2 = validation echouee, 3 = erreur d'E/S.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import date

DESC_MAX = 60
NAME_MAX = 64
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

TRIGGER_MARKERS = ("when to use", "quand l'utiliser", "quand lutiliser")
# Le linter de Hermes (tools/skill_linter.py) teste ^#+\s+When to Use : la chaine
# anglaise doit etre au DEBUT du titre. '## Quand l'utiliser (When to Use)' echoue.
LINTER_HEADING_RE = re.compile(r"^#+\s+When to [Uu]se", re.M)
REQUIRED_BODY_SECTIONS = [
    ("declencheurs", TRIGGER_MARKERS,
     "Ajouter une section '## When to Use — quand l'utiliser' avec les phrases "
     "exactes que l'utilisateur emploiera. Sans elle, le skill ne se declenche jamais."),
]
RECOMMENDED_SECTIONS = [
    ("procedure", ("## procedure", "## proc", "## steps", "## etapes"),
     "une section '## Procedure' avec des etapes numerotees et les commandes exactes"),
    ("pieges", ("## pieges", "## pitfalls", "## limites"),
     "une section '## Pieges' : ce qui casse et comment l'eviter"),
    ("verification", ("## verification", "## verify", "## tests"),
     "une section '## Verification' : la commande qui prouve que ca marche"),
]

SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\d{8,10}:[A-Za-z0-9_-]{30,})")


# --------------------------------------------------------------------- chemins

def hermes_home():
    env = os.environ.get("HERMES_HOME")
    if env and os.path.isdir(env):
        return env
    for cand in ("~/AppData/Local/hermes", "~/.hermes"):
        p = os.path.expanduser(cand)
        if os.path.isdir(p):
            return p
    return os.path.expanduser("~/.hermes")


def skills_root():
    return os.path.join(hermes_home(), "skills")


def find_installed(name):
    root = skills_root()
    for dirpath, dirnames, filenames in os.walk(root):
        if "SKILL.md" in filenames and os.path.basename(dirpath) == name:
            return os.path.join(dirpath, "SKILL.md")
    return None


def list_categories():
    root = skills_root()
    if not os.path.isdir(root):
        return []
    return sorted(d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d)) and not d.startswith("."))


# ------------------------------------------------------------------ validation

class Problems(object):
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, msg, fix=""):
        self.errors.append((msg, fix))

    def warn(self, msg, fix=""):
        self.warnings.append((msg, fix))

    def report(self):
        for msg, fix in self.errors:
            print("  [BLOQUANT] %s" % msg)
            if fix:
                print("             -> %s" % fix)
        for msg, fix in self.warnings:
            print("  [conseil]  %s" % msg)
            if fix:
                print("             -> %s" % fix)
        return len(self.errors)


def validate_meta(name, description, category, p):
    if not name:
        p.err("nom manquant")
    else:
        if len(name) > NAME_MAX:
            p.err("nom trop long (%d > %d)" % (len(name), NAME_MAX))
        if not NAME_RE.match(name):
            p.err("nom invalide : '%s'" % name,
                  "minuscules, chiffres, tirets et underscores uniquement "
                  "(ex: 'ssl-expiry-check')")

    if not description:
        p.err("description manquante")
    else:
        n = len(description)
        if n > DESC_MAX:
            p.err("description de %d caracteres (max %d)" % (n, DESC_MAX),
                  "raccourcir de %d caracteres. Hermes tronque a 57 + '...' dans "
                  "l'index du prompt systeme, ce qui detruit le declenchement.\n"
                  "             actuel : %r" % (n - DESC_MAX, description))
        if not description.rstrip().endswith("."):
            p.warn("la description ne finit pas par un point")
        if description[:1].islower():
            p.warn("la description commence par une minuscule")

    if category and not NAME_RE.match(category):
        p.err("categorie invalide : '%s'" % category, "minuscules et tirets")
    cats = list_categories()
    if category and cats and category not in cats:
        p.warn("categorie '%s' inexistante (elle sera creee)" % category,
               "categories existantes : %s" % ", ".join(cats))


def validate_body(body, p):
    low = body.lower()
    if len(body.strip()) < 200:
        p.err("corps trop court (%d caracteres)" % len(body.strip()),
              "un skill utile decrit au minimum : declencheurs, etapes, verification")

    for label, markers, fix in REQUIRED_BODY_SECTIONS:
        if not any(m in low for m in markers):
            p.err("section obligatoire absente : %s" % label, fix)

    if not LINTER_HEADING_RE.search(body):
        p.warn("aucun titre commencant par 'When to Use'",
               "le linter de Hermes teste ^#+\\s+When to Use : la chaine anglaise doit "
               "etre au DEBUT du titre.\n"
               "             OK   : '## When to Use — quand l'utiliser'\n"
               "             ECHEC: '## Quand l'utiliser (When to Use)'")

    for label, markers, fix in RECOMMENDED_SECTIONS:
        if not any(m in low for m in markers):
            p.warn("section recommandee absente : %s" % label, "ajouter %s" % fix)

    if not re.search(r"^#\s+\S", body, re.M):
        p.warn("aucun titre de niveau 1 (# Titre) dans le corps")

    m = SECRET_RE.search(body)
    if m:
        p.err("le corps contient ce qui ressemble a un secret (%s...)" % m.group(0)[:8],
              "les skills sont en clair et passent dans le prompt systeme : "
              "retirer la valeur et referencer une variable d'environnement")

    if "```" in body and body.count("```") % 2 != 0:
        p.err("bloc de code non ferme (nombre impair de ```)")


def validate_file(path, p):
    """valide un SKILL.md deja ecrit"""
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            content = fh.read()
    except OSError as exc:
        p.err("lecture impossible : %s" % exc)
        return None, None

    if not content.lstrip().startswith("---"):
        p.err("frontmatter YAML absent", "le fichier doit commencer par '---'")
        return content, None

    parts = content.split("---", 2)
    if len(parts) < 3:
        p.err("frontmatter non ferme", "ajouter une ligne '---' apres les metadonnees")
        return content, None

    fm, body = parts[1], parts[2]
    name = desc = None
    mn = re.search(r"^name:\s*(.+)$", fm, re.M)
    md = re.search(r'^description:\s*"?(.*?)"?\s*$', fm, re.M)
    if mn:
        name = mn.group(1).strip().strip('"').strip("'")
    else:
        p.err("cle 'name' absente du frontmatter")
    if md:
        desc = md.group(1).strip()
    else:
        p.err("cle 'description' absente du frontmatter")

    for key in ("version", "author", "license"):
        if not re.search(r"^%s:" % key, fm, re.M):
            p.warn("cle '%s' absente du frontmatter" % key)

    if name or desc:
        validate_meta(name, desc, None, p)
    validate_body(body, p)
    return content, name


# ------------------------------------------------------------------- rendu

def render(name, description, category, tags, author, version, platforms,
           related, body, prereq_cmds):
    tag_list = ", ".join(t.strip() for t in tags if t.strip())
    lines = [
        "---",
        "name: %s" % name,
        'description: "%s"' % description.replace('"', "'"),
        "version: %s" % version,
        "author: %s" % author,
        "license: MIT",
        "platforms: [%s]" % ", ".join(p.strip() for p in platforms if p.strip()),
        "metadata:",
        "  hermes:",
        "    tags: [%s]" % tag_list,
    ]
    if related:
        lines.append("    related_skills: [%s]" % ", ".join(r.strip() for r in related))
    if category:
        lines.append("    category: %s" % category)
    lines.append('    created: "%s"' % date.today().isoformat())
    if prereq_cmds:
        lines.append("prerequisites:")
        lines.append("  commands: [%s]" % ", ".join(c.strip() for c in prereq_cmds))
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body.lstrip("\n").rstrip() + "\n"


# -------------------------------------------------------------------- actions

def do_check(name):
    path = find_installed(name)
    if not path:
        print("Skill '%s' introuvable sous %s" % (name, skills_root()))
        return 3
    print("Validation de %s\n" % path)
    p = Problems()
    validate_file(path, p)
    nerr = p.report()
    if nerr == 0 and not p.warnings:
        print("  Aucun probleme.")
    print("\n%d bloquant(s), %d conseil(s)" % (nerr, len(p.warnings)))
    return 2 if nerr else 0


# ------------------------------------------------- generation depuis session

# Un mot de commande en debut de ligne (ou dans un bloc de code) = commande.
CMD_RE = re.compile(
    r"^\s*(?:[\$>#]\s*)?("
    r"python3?|py|pip3?|uv|node|npm|npx|pnpm|yarn|deno|git|gh|glab|docker|"
    r"docker-compose|kubectl|helm|terraform|ansible|curl|wget|openssl|ssh|scp|"
    r"rsync|bash|sh|zsh|pwsh|powershell|hermes|wp|composer|php|artisan|make|"
    r"cargo|go|rustc|dotnet|java|mvn|gradle|systemctl|journalctl|crontab|"
    r"schtasks|jq|yq|rg|grep|sed|awk|find|tar|zip|unzip|mysql|psql|redis-cli|"
    r"pytest|jest|phpunit|eslint|ruff|black|mypy)\b")

TRIGGER_RE = re.compile(
    r"\b(quand|lorsqu|des que|dès que|chaque fois|a chaque|"
    r"si\s+(?:je|tu|il|on|un|une|le|la|les)\b|"
    r"je veux|je voudrais|j'?aimerais|j'?ai besoin|j'?ai demande|"
    r"me demande de|demande de)\b", re.I)

PITFALL_RE = re.compile(
    r"\b(attention|piege|prend garde|echec|echoue|erreur|ne pas|ne jamais|jamais|"
    r"probleme|casse|bloque|bloquant|limite|limitation|ne fonctionne pas|"
    r"ne marche pas|faux positif|contourn|sinon)\b", re.I)

VERIFY_RE = re.compile(
    r"\b(verifier que|valider|tester|controler|s'assurer|doit retourner|"
    r"doit afficher|doit produire|confirmer|preuve)\b", re.I)

NOISE_RE = re.compile(r"^\s*(merci|ok|parfait|super|bonjour|salut|d'accord|oui|non)\b", re.I)


def _sentences(text):
    """decoupe en unites lisibles : lignes, puces et phrases"""
    out = []
    for raw in re.split(r"\n+", text):
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^(?:[-*+\u2022]|\d+[.)])\s+", "", line).strip()
        if not line:
            continue
        for part in re.split(r"(?<=[.!?;])\s+(?=[A-Z\u00c0-\u00dc])", line):
            part = part.strip()
            if len(part) >= 12 and not NOISE_RE.match(part):
                out.append(part)
    return out


def _extract_commands(text):
    """commandes trouvees dans les blocs ```, les backticks et en debut de ligne"""
    cmds = []

    def push(c):
        c = c.strip().strip("`").strip()
        c = re.sub(r"^[\$>#]\s*", "", c)
        if 3 <= len(c) <= 300 and c not in cmds and CMD_RE.match(c):
            cmds.append(c)

    for block in re.findall(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.S):
        for line in block.splitlines():
            push(line)
    for inline in re.findall(r"`([^`\n]{3,200})`", text):
        push(inline)
    for line in text.splitlines():
        push(line)
    return cmds


def describe_from_session(text, name):
    """description <= 60 caracteres, derivee de la conversation"""
    for s in _sentences(text):
        s = re.sub(r"^(?:voici|voila|dans)\s+(?:la|le|les)?\s*conversation\s*(?:ou|où)?\s*", "", s, flags=re.I)
        s = re.sub(r"^j'?ai\s+demande\s+(?:de|d')\s*", "", s, flags=re.I)
        s = re.sub(r"^(?:je veux|je voudrais|il faut|on doit)\s+", "", s, flags=re.I)
        s = s.strip(" .,:;")
        if len(s) < 8:
            continue
        s = s[:1].upper() + s[1:]
        if len(s) > 59:
            cut = s[:59].rsplit(" ", 1)[0]
            s = cut if len(cut) >= 20 else s[:59]
        return (s.rstrip(" .,:;") + ".")[:60]
    return (name.replace("-", " ").replace("_", " ").capitalize() + ".")[:60]


def body_from_session(text, name, description):
    """Construit un corps de skill complet a partir d'un resume de conversation.
    Extraction deterministe : aucun appel LLM, aucune invention de contenu.
    Ce qui n'est pas trouve est marque '(a completer)' au lieu d'etre devine."""
    sents = _sentences(text)
    cmds = _extract_commands(text)

    # Chaque phrase va dans UNE seule section. Ordre de priorite : un piege et
    # une verification sont plus utiles qu'un declencheur, et une phrase d'action
    # ("il faut lancer ...") est une etape, pas un declencheur.
    pitfalls, verifs, triggers, steps = [], [], [], []
    for s in sents:
        if PITFALL_RE.search(s) and len(pitfalls) < 6:
            pitfalls.append(s)
        elif VERIFY_RE.search(s) and len(verifs) < 4:
            verifs.append(s)
        elif TRIGGER_RE.search(s) and len(triggers) < 6:
            triggers.append(s)
        elif len(steps) < 12:
            steps.append(s)
    if not steps:
        steps = [s for s in sents if s not in pitfalls][:8]

    desc = description.rstrip()
    if not desc.endswith("."):
        desc += "."
    title = name.replace("-", " ").replace("_", " ").strip().title()
    L = []
    L.append("# %s" % title)
    L.append("")
    L.append("%s Procedure reconstituee depuis une conversation de travail."
             % desc)
    L.append("")

    L.append("## When to Use — quand l'utiliser")
    L.append("")
    if triggers:
        for t in triggers:
            L.append("- %s" % t)
    else:
        L.append("- L'utilisateur demande : « %s »" % description.rstrip("."))
        L.append("- (a completer) ajouter les formulations exactes de l'utilisateur")
    L.append("")
    L.append("Ne pas utiliser ce skill hors de ce cadre : preferer une commande "
             "directe si la demande est ponctuelle.")
    L.append("")

    L.append("## Procedure")
    L.append("")
    if steps:
        for i, s in enumerate(steps, 1):
            L.append("%d. %s" % (i, s))
    else:
        L.append("1. (a completer) aucune etape identifiable dans la conversation")
    L.append("")

    if cmds:
        L.append("## Commandes")
        L.append("")
        L.append("```bash")
        for c in cmds[:15]:
            L.append(c)
        L.append("```")
        L.append("")

    L.append("## Pieges")
    L.append("")
    if pitfalls:
        for p_ in pitfalls:
            L.append("- %s" % p_)
    else:
        L.append("- (a completer) noter ici ce qui a echoue la premiere fois : "
                 "c'est la partie la plus utile d'un skill")
    L.append("")

    L.append("## Verification")
    L.append("")
    if verifs:
        for v in verifs:
            L.append("- %s" % v)
    elif cmds:
        L.append("- Rejouer la commande de reference et comparer la sortie :")
        L.append("")
        L.append("```bash")
        L.append(cmds[0])
        L.append("```")
    else:
        L.append("- (a completer) la commande qui prouve que la procedure a marche")
    L.append("")

    L.append("---")
    L.append("")
    L.append("*Corps genere par `newskill.py --from-session` le %s a partir d'un "
             "resume de conversation. Relire avant de s'y fier : l'extraction est "
             "mecanique, elle ne comprend pas le contexte.*"
             % date.today().strftime("%d/%m/%Y"))
    return "\n".join(x for x in L if x is not None)


def do_create(a):
    body = getattr(a, "body_text", None)
    if body is None:
        if not a.body or not os.path.isfile(a.body):
            print("Corps introuvable : %s" % a.body)
            return 3
        try:
            with open(a.body, "r", encoding="utf-8-sig") as fh:
                body = fh.read()
        except OSError as exc:
            print("Lecture impossible : %s" % exc)
            return 3

    # un corps qui contient deja un frontmatter : on le retire
    if body.lstrip().startswith("---"):
        chunks = body.split("---", 2)
        if len(chunks) >= 3:
            print("[info] frontmatter detecte dans le corps : il sera regenere")
            body = chunks[2]

    p = Problems()
    validate_meta(a.name, a.description, a.category, p)
    validate_body(body, p)

    print("Validation :")
    nerr = p.report()
    if nerr == 0 and not p.warnings:
        print("  Aucun probleme.")
    print("")

    if nerr:
        print("ECHEC : %d probleme(s) bloquant(s). Rien n'a ete ecrit." % nerr)
        return 2

    content = render(
        a.name, a.description, a.category,
        (a.tags or "").split(","),
        a.author, a.version,
        (a.platforms or "windows, linux, macos").split(","),
        (a.related or "").split(",") if a.related else [],
        body,
        (a.requires or "").split(",") if a.requires else [],
    )

    dest_dir = os.path.join(skills_root(), a.category, a.name) if a.category \
        else os.path.join(skills_root(), a.name)
    dest = os.path.join(dest_dir, "SKILL.md")

    if a.dry_run:
        print("--- SKILL.md (dry-run, non ecrit) ---")
        print(content)
        print("--- cible : %s" % dest)
        return 0

    existing = find_installed(a.name)
    if existing and not a.force:
        print("Un skill '%s' existe deja : %s" % (a.name, existing))
        print("Utiliser --force pour l'ecraser (une sauvegarde .bak sera creee),")
        print("ou skill_manage(action='patch') pour une modification ciblee.")
        return 2
    if existing and a.force:
        shutil.copy2(existing, existing + ".bak")
        print("[info] sauvegarde : %s.bak" % existing)
        if os.path.dirname(existing) != dest_dir:
            dest_dir = os.path.dirname(existing)
            dest = existing

    try:
        os.makedirs(dest_dir, exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
    except OSError as exc:
        print("Ecriture impossible : %s" % exc)
        return 3

    print("Installe : %s" % dest)
    print("Taille   : %d caracteres" % len(content))

    # relecture : ce qui est sur le disque est-il valide ?
    p2 = Problems()
    validate_file(dest, p2)
    if p2.errors:
        print("\nATTENTION : le fichier ecrit ne passe pas la validation :")
        p2.report()
        return 2

    # verification par Hermes lui-meme
    hermes = shutil.which("hermes")
    if hermes:
        try:
            r = subprocess.run([hermes, "skills", "list"], capture_output=True,
                               text=True, timeout=120, encoding="utf-8", errors="replace")
            if a.name in (r.stdout or ""):
                print("Verifie  : 'hermes skills list' voit le skill")
            else:
                print("Note     : absent de 'hermes skills list' (index en cache).")
                print("           Taper /reload-skills dans la session en cours.")
        except Exception as exc:
            print("Note     : verification hermes impossible (%s)" % exc)
    else:
        print("Note     : commande 'hermes' absente du PATH, verification sautee")

    print("")
    print("Pour l'utiliser tout de suite dans cette session : /reload-skills")
    print("Puis : skill_view(name='%s')" % a.name)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Genere, valide et installe un skill Hermes",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", metavar="NOM", help="valider un skill deja installe")
    ap.add_argument("--name")
    ap.add_argument("--description", help="60 caracteres maximum")
    ap.add_argument("--category", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--body", help="fichier markdown du corps (sans frontmatter)")
    ap.add_argument("--from-session", metavar="TEXTE_OU_FICHIER",
                    help="genere le corps depuis un resume de conversation "
                         "(texte direct ou chemin de fichier). Remplace --body ; "
                         "--description devient optionnelle.")
    ap.add_argument("--author", default="Hermes Agent")
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--platforms", default="windows, linux, macos")
    ap.add_argument("--related", default="", help="skills lies, separes par des virgules")
    ap.add_argument("--requires", default="", help="commandes requises, separees par des virgules")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list-categories", action="store_true")
    a = ap.parse_args()

    if a.list_categories:
        print("Categories sous %s :" % skills_root())
        for c in list_categories():
            print("  " + c)
        return 0
    if a.check:
        return do_check(a.check)

    if a.from_session:
        src = a.from_session
        if os.path.isfile(src):
            try:
                with open(src, "r", encoding="utf-8-sig") as fh:
                    text = fh.read()
            except OSError as exc:
                print("Lecture impossible : %s" % exc)
                return 3
            origine = "fichier %s" % src
        else:
            text = src
            origine = "texte fourni en argument"
        if len(text.strip()) < 30:
            print("--from-session : contenu trop court (%d caracteres) pour en "
                  "extraire une procedure." % len(text.strip()))
            return 2
        if not a.name:
            ap.error("--from-session exige aussi --name")
        if not a.description:
            a.description = describe_from_session(text, a.name)
            print("Description deduite : %r" % a.description)
        a.body_text = body_from_session(text, a.name, a.description)
        print("Corps genere depuis %s : %d caracteres" % (origine, len(a.body_text)))
        print("")
        return do_create(a)

    missing = [f for f in ("name", "description", "body") if not getattr(a, f)]
    if missing:
        ap.error("arguments requis manquants : --" + ", --".join(missing))
    return do_create(a)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
