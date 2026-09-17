# -*- coding: utf-8 -*-
"""Desaturation de la memoire native Hermes (MEMORY.md / USER.md).

Regles de decision : skill productivity/hermes-memory, references/desaturation.md.
  Candidate a l'archivage si une entree :
    - contient une date de plus de 90 jours (toutes ses dates sont perimees) ;
    - reference un chemin ou un outil qui n'existe plus sur disque ;
    - mentionne un etat termine / clos / abandonne / rejete / supprime ;
    - est redondante avec une autre entree du meme fichier (recouvrement de
      mots-cles >= 80 %) : le membre le plus long d'une paire survit toujours, et
      sur une chaine d'entrees quasi identiques seul le plus long survit (le texte
      integral reste de toute facon dans l'archive SiYuan) ;
    - est superseded par une entree plus recente de meme cle (recouvrement >= 50 %).
  Garde-fou : si les candidats pesent plus de 50 % du contenu du fichier, rien
  n'est ecrit (une condensation de cette ampleur reste manuelle).
  Jamais archivees (garde-fous) :
    - les lignes de section (## ...) ;
    - les entrees contenant jamais / toujours / obligatoire / regle ;
    - les chemins vers outils actifs (router_memoire, indexer, chercher, check_memory) ;
    - les ports actifs (6806, 8200, 9119) ;
    - les taches planifiees (HHhMM, schtasks, planifie).
  Les sections « ## Environnement », « ## Regles transversales » et « ## Preferences »
  sont integralement protegees (aucune entree n'y est candidate).

Securite (ordre strict, cf. references/desaturation.md) :
  1. SiYuan (127.0.0.1:6806) doit repondre, sinon RIEN n'est modifie (exit 1) ;
  2. archivage du contenu integral du fichier dans SiYuan AVANT toute reecriture ;
  3. .bak de MEMORY.md / USER.md avant modification ;
  4. apres reecriture la taille est re-mesuree : si elle depasse encore le seuil
     d'alerte, restauration du .bak (rollback, exit 2).

Taille mesuree : en CARACTERES, CRLF compris, comme scripts/check_memory.ps1
((Get-Content -Raw).Length), qui fait foi pour l'alerte.

Usages :
  python desaturer_memoire.py             # dry-run (defaut) : affiche, ne touche a rien
  python desaturer_memoire.py --dry-run   # idem
  python desaturer_memoire.py --auto      # applique UNIQUEMENT si un fichier depasse
                                          # son seuil d'alerte, sinon ne fait rien

Tache planifiee : « Hermes - desaturer memoire », dimanche 04h00, action --auto.
Log : %LOCALAPPDATA%\\hermes\\scripts\\desaturation.log
"""
import datetime
import io
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.error
import urllib.request

HERMES = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
MEM_DIR = os.path.join(HERMES, "memories")
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(SCRIPTS, "desaturation.log")
SIYUAN = "http://127.0.0.1:6806"
# Notebook SiYuan « journal » (workspace C:\\Users\\searc\\SiYuan\\hermes-projects)
NOTEBOOK_JOURNAL = "20260915170850-sjbhg88"

# Seuils : seuil = ligne d'alerte de check_memory.ps1 (fait foi) ; cible = objectif
# de desaturation ; plafond = limite dure d'injection de la config.
SEUILS = {
    "MEMORY.md": {"seuil": 2100, "cible": 1800, "plafond": 2200},
    "USER.md": {"seuil": 1300, "cible": 1040, "plafond": 1375},
}
FICHIERS = ["MEMORY.md", "USER.md"]

SECTIONS_PROTEGEES = ["environnement", "regles transversales", "preferences"]
MOTS_PROTEGES = ["jamais", "toujours", "obligatoire", "regle"]
OUTILS_ACTIFS = ["router_memoire", "indexer", "chercher", "check_memory"]
PORTS_ACTIFS = ["6806", "8200", "9119"]
TACHES_PLANIFIEES = re.compile(r"\d{1,2}h\d{2}|schtasks|planifi", re.IGNORECASE)
OUTIL_INTERDIT = "desaturer_memoire"  # ce script : ne se protege pas lui-meme

# Etats clos (recherche sans accents, minuscules)
ETATS_CLOS = re.compile(
    r"\b(termine|terminee|termines|terminees|fini|finie|clos|close|abandonne|abandonnee"
    r"|rejete|rejetee|supprime|supprimee|obsolete|annule|annulee)\b")
DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_FR = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")

# Chemins : absolu (lecteur) ou relatif dont la premiere brique est un dossier reel
RACINES = ("data", "scripts", "skills", "memories", "snapshot", "repo", "dev",
           "projects", "wordpress", "video_youtube", "desktop", "siyuan", "hermes-agent")
CHEMIN_ABSOLU = re.compile(r"[A-Za-z]:[\\/][^\s,;()\[\]\"'`]+")
CHEMIN_RELATIF = re.compile(r"(?<![\w.:\\/-])([A-Za-z][\w.\-]*[\\/][^\s,;()\[\]\"'`]+)")

MOTS_VIDES = set("""le la les de des du un une et ou a au aux en dans pour par sur avec sans
que qui est sont ce cet cette il elle on nous vous ils elles plus moins tres bien aussi meme
puis mais donc car si ne pas sa son ses leur leurs au ceci cela tout tous toute toutes""".split())


def journal(message, etat="INFO"):
    """Ecrit une ligne horodatee sur stdout et dans desaturation.log."""
    ligne = "%s | %-5s | %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                etat, message)
    print(ligne, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(ligne + "\n")


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFKD", texte)
                   if not unicodedata.combining(c))


def lire(chemin):
    with io.open(chemin, encoding="utf-8", newline="") as f:
        return f.read()


def taille(contenu):
    """Taille en caracteres, CRLF compris — meme lecture que check_memory.ps1."""
    return len(contenu.lstrip("\ufeff"))


def mots_cles(texte):
    t = sans_accents(texte.lower())
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return {m for m in t.split() if len(m) > 2 and not m.isdigit() and m not in MOTS_VIDES}


def recouvrement(a, b):
    ma, mb = mots_cles(a), mots_cles(b)
    if not ma or not mb:
        return 0.0
    return len(ma & mb) / float(min(len(ma), len(mb)))


# --------------------------------------------------------------------------- #
# SiYuan
# --------------------------------------------------------------------------- #
def jeton_siyuan():
    chemin = os.path.join(HERMES, ".env")
    try:
        for ligne in io.open(chemin, encoding="utf-8"):
            if ligne.startswith("SIYUAN_TOKEN="):
                return ligne.split("=", 1)[1].strip()
    except OSError:
        return None
    return None


def siyuan_vivant():
    """Le noyau repond-il ? 401/403 prouvent qu'il ecoute (comme reindex_auto.py)."""
    for url in ("%s/api/system/version" % SIYUAN, "%s/" % SIYUAN):
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return True
        except Exception:
            continue
    return False


def siyuan_api(route, donnees):
    req = urllib.request.Request(
        SIYUAN + route,
        data=json.dumps(donnees, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Token " + (jeton_siyuan() or ""),
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def archiver_siyuan(nom_fichier, contenu_origine, candidats, date_jour):
    """Archive le contenu integral dans SiYuan. Retourne (ok, message)."""
    titre = "Archive %s - %s" % (nom_fichier.replace(".md", ""), date_jour)
    details = "\n".join(
        "- **%s** — %s\n  ```\n  %s\n  ```" % (c["raison"], c["explication"], c["texte"].strip())
        for c in candidats) or "_aucune entree archivee (reecriture de confort)_"
    markdown = (
        "# Archive %s - %s\n\n"
        "> **Statut** : archive\n"
        "> **A reverifier** : jamais\n\n"
        "Contenu integral de `%%LOCALAPPDATA%%\\hermes\\memories\\%s` avant desaturation "
        "automatique (`desaturer_memoire.py`), plus la liste des entrees archivees et leur "
        "motif. Rien n'est perdu : le texte d'origine est reproduit ci-dessous.\n\n"
        "## Entrees archivees et motifs\n\n%s\n\n"
        "## Contenu integral avant desaturation\n\n"
        "```\n%s\n```\n\n"
        "*Document cree le %s par desaturer_memoire.py.*\n"
        % (nom_fichier.replace(".md", ""), date_jour, nom_fichier, details,
           contenu_origine.lstrip("\ufeff").rstrip(), date_jour))

    # SiYuan n'impose pas l'unicite du chemin : on verifie avant pour ne pas empiler
    # deux docs de meme nom dans le notebook journal.
    titre_pris = False
    try:
        deja = siyuan_api("/api/filetree/listDocsByPath",
                          {"notebook": NOTEBOOK_JOURNAL, "path": "/"}).get("data", {}).get("files", [])
        titre_pris = any(d.get("name") == titre for d in deja)
    except Exception:
        titre_pris = False

    for suffixe in (["-%s" % datetime.datetime.now().strftime("%H%M%S")] if titre_pris else [""]):
        chemin = "/%s%s" % (titre, suffixe)
        try:
            r = siyuan_api("/api/filetree/createDocWithMd", {
                "notebook": NOTEBOOK_JOURNAL, "path": chemin, "markdown": markdown})
        except Exception as e:
            return False, "appel SiYuan en echec (%s)" % e
        if r.get("code") == 0:
            return True, "doc %s (id %s)" % (chemin, r.get("data"))
    return False, "SiYuan a refuse la creation du document (code=%s msg=%s)" % (
        r.get("code"), r.get("msg"))


# --------------------------------------------------------------------------- #
# Analyse d'un fichier memoire
# --------------------------------------------------------------------------- #
def chemins_morts(texte):
    """Liste les chemins references qui n'existent plus sur disque."""
    trouves = []
    for motif in (CHEMIN_ABSOLU, CHEMIN_RELATIF):
        for brut in motif.findall(texte):
            jeton = brut.strip().rstrip(".,;:'\"`*/\\ ")
            if not jeton or len(jeton) < 4:
                continue
            jeton = jeton.replace("\\", "/")
            if "%" in jeton:
                jeton = (jeton.replace("%LOCALAPPDATA%", os.environ.get("LOCALAPPDATA", ""))
                              .replace("%USERPROFILE%", os.environ.get("USERPROFILE", ""))
                              .replace("%APPDATA%", os.environ.get("APPDATA", "")))
            if "/" not in jeton:
                continue
            absolu = re.match(r"^[A-Za-z]:/", jeton)
            if not absolu and jeton.split("/")[0].lower() not in RACINES:
                continue  # ex. « 8.2.29/MySQL » ou « LivePortrait/SadTalker »
            if jeton in trouves:
                continue
            if not existe(jeton, absolu):
                trouves.append(jeton)
    return trouves


def existe(jeton, absolu):
    """Vrai si le chemin ou l'un de ses prefixes existe (fichier, dossier, ou racine connue)."""
    morceaux = [m for m in jeton.split("/") if m]
    while morceaux:
        relatif = "/".join(morceaux)
        for base in ([relatif] if absolu
                     else [os.path.join(HERMES, relatif), os.path.join(HERMES, "..", relatif),
                           os.path.join(os.environ.get("USERPROFILE", ""), relatif),
                           os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", relatif)]):
            if os.path.exists(base):
                return True
        morceaux.pop()
    return False


def entree_backup(morceau):
    """Une ligne d'entree = ligne non vide, non titre de section."""
    return bool(morceau.strip()) and not morceau.lstrip().startswith("#")


def protegee(ligne, section):
    """Garde-fous : cette entree ne doit jamais etre archivee."""
    plat = sans_accents(ligne.lower())
    if sans_accents(section.lower()) in SECTIONS_PROTEGEES:
        return True, "section protegee (## %s)" % section
    for mot in MOTS_PROTEGES:
        if re.search(r"\b%s" % mot, plat):
            return True, "mot-cle interdit (%s)" % mot
    for outil in OUTILS_ACTIFS:
        if outil in plat:
            return True, "outil actif (%s)" % outil
    for port in PORTS_ACTIFS:
        if port in plat:
            return True, "port actif (%s)" % port
    if TACHES_PLANIFIEES.search(plat):
        return True, "tache planifiee"
    return False, ""


def cle_entree(ligne):
    """Cle = texte avant le premier ':', si court et sans ponctuation de phrase."""
    t = ligne.strip().lstrip("-* ").strip()
    if ":" not in t:
        return None
    tete = t.split(":", 1)[0].strip()
    if not tete or len(tete) > 25 or "." in tete or len(tete.split()) > 3:
        return None
    return sans_accents(tete.lower())


def analyser(nom_fichier, contenu, aujourdhui):
    """Retourne (candidats, protegees, sections, total_entrees)."""
    lignes = contenu.lstrip("\ufeff").splitlines(keepends=True)
    entrees = []          # (index, texte, section)
    section = ""
    protegees = []
    for i, morceau in enumerate(lignes):
        nu = morceau.rstrip("\r\n")
        if nu.lstrip().startswith("## "):
            section = nu.lstrip().lstrip("#").strip()
            continue
        if not entree_backup(nu):
            continue
        ok, motif = protegee(nu, section)
        if ok:
            protegees.append(nu.strip()[:60])
            continue
        entrees.append({"i": i, "texte": nu.strip(), "section": section})

    candidats = []
    marques = set()

    # R1 date > 90 jours (toutes les dates de l'entree sont perimees)
    for e in entrees:
        dates = []
        for m in DATE_ISO.finditer(e["texte"]):
            dates.append(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        for m in DATE_FR.finditer(e["texte"]):
            dates.append(datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        if dates and all((aujourdhui - d).days > 90 for d in dates):
            candidats.append({"i": e["i"], "texte": e["texte"], "raison": "date > 90 jours",
                              "explication": "dates les plus recentes : %s"
                                             % ", ".join(sorted({d.isoformat() for d in dates}))})

    # R2 chemin mort
    for e in entrees:
        morts = chemins_morts(e["texte"])
        if morts:
            candidats.append({"i": e["i"], "texte": e["texte"], "raison": "chemin mort",
                              "explication": "introuvable : %s" % ", ".join(morts)})

    # R3 etat clos
    for e in entrees:
        m = ETATS_CLOS.search(sans_accents(e["texte"].lower()))
        if m:
            candidats.append({"i": e["i"], "texte": e["texte"], "raison": "etat clos",
                              "explication": "motif de cloture : %s" % m.group(1)})

    # R4 redondance intra-fichier / R5 superseded (meme cle)
    # On ne marque que le membre le plus court d'une paire (et, a longueur egale,
    # le plus recent) : le plus long de chaque paire survit toujours.
    for x in range(len(entrees)):
        for y in range(len(entrees)):
            if x == y:
                continue
            a, b = entrees[x], entrees[y]
            r = recouvrement(a["texte"], b["texte"])
            plus_court = len(a["texte"]) < len(b["texte"]) or (
                len(a["texte"]) == len(b["texte"]) and a["i"] > b["i"])
            if r >= 0.80 and plus_court:
                candidats.append({"i": a["i"], "texte": a["texte"], "raison": "redondance > 80 %",
                                  "explication": "recouvrement %.0f %% — entree conservee : %s"
                                                 % (r * 100, b["texte"][:70])})
            elif 0.50 <= r < 0.80 and plus_court and cle_entree(a["texte"]) \
                    and cle_entree(a["texte"]) == cle_entree(b["texte"]):
                candidats.append({"i": a["i"], "texte": a["texte"], "raison": "superseded",
                                  "explication": "meme cle « %s », entree conservee : %s"
                                                 % (cle_entree(a["texte"]), b["texte"][:70])})

    # dedoublonnage par ligne (premiere regle qui declenche gagne)
    vus, uniques = set(), []
    for c in candidats:
        if c["i"] in vus:
            continue
        vus.add(c["i"])
        uniques.append(c)
    return sorted(uniques, key=lambda c: c["i"]), len(protegees), len(entrees), lignes


def reecrire(lignes, indices):
    garde = [l for i, l in enumerate(lignes) if i not in indices]
    texte = "".join(garde)
    return re.sub(r"\n{3,}", "\n\n", texte).replace("\r\r\n", "\r\n")


# --------------------------------------------------------------------------- #
# Programme
# --------------------------------------------------------------------------- #
def traiter(nom_fichier, mode_auto, aujourdhui, date_jour):
    chemin = os.path.join(MEM_DIR, nom_fichier)
    if not os.path.exists(chemin):
        journal("%s introuvable (%s) : ignore" % (nom_fichier, chemin), "WARN")
        return 0
    contenu = lire(chemin)
    n = taille(contenu)
    seuil = SEUILS[nom_fichier]
    journal("%s : %d / %d caracteres (seuil %d, cible %d, plafond %d)"
            % (nom_fichier, n, seuil["seuil"], seuil["seuil"], seuil["cible"], seuil["plafond"]))
    journal("%s : %.0f %% du seuil d'alerte, %.0f %% de la cible"
            % (nom_fichier, 100.0 * n / seuil["seuil"], 100.0 * n / seuil["cible"]))

    candidats, nb_protegees, total, lignes = analyser(nom_fichier, contenu, aujourdhui)
    journal("%s : %d entrees analysees, %d protegees, %d candidate(s)"
            % (nom_fichier, total, nb_protegees, len(candidats)))
    for c in candidats:
        journal("  CANDIDAT [%s] %s" % (c["raison"], c["texte"][:110]))
        journal("           -> %s" % c["explication"])
    if not candidats:
        journal("  aucune entree candidate : rien a archiver")
    if n > seuil["seuil"]:
        journal("  etat : AU-DESSUS du seuil d'alerte -> --auto agira")
    elif n > seuil["cible"]:
        journal("  etat : au-dessus de la cible mais sous le seuil d'alerte "
                "(--auto ne fait rien : mode prudent)")
    else:
        journal("  etat : sous la cible")

    if not mode_auto:
        journal("%s : dry-run, aucune modification" % nom_fichier)
        return 0
    if n <= seuil["seuil"]:
        journal("%s : sous le seuil d'alerte, --auto ne fait rien" % nom_fichier)
        return 0
    if not candidats:
        journal("%s : au-dessus du seuil mais aucune entree archivable — "
                "condensation manuelle requise, rien fait" % nom_fichier, "WARN")
        return 0
    # garde-fou : retirer une large part du contenu n'est jamais automatique
    part = sum(len(c["texte"]) for c in candidats) / float(max(1, taille(contenu)))
    if part > 0.5:
        journal("%s : garde-fou — les candidats representent %.0f %% du contenu (> 50 %%), "
                "abandon sans ecriture (condensation manuelle requise)"
                % (nom_fichier, part * 100), "ERREUR")
        return 2

    # 1. archivage SiYuan (obligatoire avant toute ecriture)
    ok, msg = archiver_siyuan(nom_fichier, contenu, candidats, date_jour)
    if not ok:
        journal("%s : archivage SiYuan impossible (%s) — AUCUNE modification" % (nom_fichier, msg),
                "ERREUR")
        return 1
    journal("%s : archive SiYuan OK — %s" % (nom_fichier, msg))

    # 2. backup local
    sauvegarde = chemin + ".bak"
    shutil.copy2(chemin, sauvegarde)
    journal("%s : sauvegarde %s" % (nom_fichier, os.path.basename(sauvegarde)))

    # 3. reecriture
    nouveau = reecrire(lignes, {c["i"] for c in candidats})
    with io.open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write(nouveau)
    n2 = taille(nouveau)
    journal("%s : reecrit — %d -> %d caracteres" % (nom_fichier, n, n2))

    # 4. rollback si le seuil d'alerte n'est pas repasse
    if n2 > seuil["seuil"]:
        shutil.copy2(sauvegarde, chemin)
        journal("%s : ROLLBACK — %d caracteres reste au-dessus du seuil %d, .bak restaure"
                % (nom_fichier, n2, seuil["seuil"]), "ERREUR")
        return 2
    journal("%s : desaturation OK (%d caracteres liberes, cible %d)"
            % (nom_fichier, n - n2, seuil["cible"]))
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = [a.lower() for a in sys.argv[1:]]
    dry = "--dry-run" in args or "-n" in args
    auto = "--auto" in args
    if auto and dry:
        journal("--dry-run l'emporte sur --auto : aucune modification", "WARN")
        auto = False
    if not dry and not auto:
        dry = True
        journal("aucun mode explicite : dry-run par defaut (le dry-run est obligatoire avant --auto)")

    journal("=== desaturation memoire — mode %s ===" % ("AUTO" if auto else "DRY-RUN"))
    if not os.path.isdir(MEM_DIR):
        journal("dossier memoire introuvable (%s)" % MEM_DIR, "ERREUR")
        return 3
    if not siyuan_vivant():
        journal("SiYuan ne repond pas sur %s : AUCUNE modification (exit 1)" % SIYUAN, "ERREUR")
        return 1
    journal("SiYuan repond sur %s" % SIYUAN)

    aujourdhui = datetime.date.today()
    date_jour = aujourdhui.isoformat()
    code = 0
    for nom in FICHIERS:
        code = max(code, traiter(nom, auto, aujourdhui, date_jour))
    journal("=== fin (code %d) ===" % code)
    return code


if __name__ == "__main__":
    sys.exit(main())
