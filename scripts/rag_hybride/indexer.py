# -*- coding: utf-8 -*-
"""Indexe la documentation dans une base vectorielle locale (RAG du second cerveau).

Sources, par ordre de priorite :
  1. SiYuan      : tous les documents, via l'API (kramdown nettoye)
  2. skills      : les fichiers SKILL.md du dossier de skills Hermes
  3. wiki        : le wiki d'architecture %LOCALAPPDATA%\hermes\wiki (*.md uniquement)
  4. scripts v4  : Desktop\hermes_tuto_v4 (*.py, *.sh, *.txt, *.md) — retiree le 27/09/2026
  5. wordpress   : le depot hermes-wordpress-skills present sur le disque

Sortie : la racine RACINE ci-dessous. La variable d'environnement HERMES_RAG_RACINE permet de
rediriger la SORTIE vers un dossier temporaire (indexation a blanc, verifiee avant bascule) ;
les sources restent lues a leurs chemins reels.

Modele : intfloat/multilingual-e5-small. Attention : les modeles e5 exigent les prefixes
"passage: " (indexation) et "query: " (recherche), sinon la qualite chute nettement.

Sorties dans %LOCALAPPDATA%\\hermes\\data\\rag :
  index.faiss    index vectoriel (produit scalaire sur vecteurs normalises = cosinus)
  chunks.jsonl   un enregistrement par fragment (source, chemin, titre, texte)
  manifeste.json compte par source, modele, date, taille
"""
import io
import json
import os
import re
import sys
import urllib.request

# Surcharge optionnelle de la racine de SORTIE (indexation a blanc, verifiable avant bascule) :
# HERMES_RAG_RACINE=<dossier> redirige index.faiss / chunks.jsonl / manifeste.json / cache.db
# vers cet emplacement. Les sources (skills, wiki, .env SiYuan) restent lues a leurs chemins reels.
_SURCHARGE = os.environ.get("HERMES_RAG_RACINE")
RACINE = os.path.expanduser(_SURCHARGE or os.path.join(os.environ["LOCALAPPDATA"], "hermes", "data", "rag"))
INDEX = os.path.join(RACINE, "index.faiss")
CHUNKS = os.path.join(RACINE, "chunks.jsonl")
MANIFESTE = os.path.join(RACINE, "manifeste.json")
MODELE = "intfloat/multilingual-e5-base"   # small insuffisant sur le vocabulaire metier
SKILLS = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "skills")
WIKI = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "wiki")
SCRIPTS_V4 = os.path.join(os.environ["USERPROFILE"], "Desktop", "hermes_tuto_v4")
DEPOT_WP = os.path.join(os.environ["USERPROFILE"], "Code", "hermes-wordpress-skills")
SIYUAN = "http://127.0.0.1:6806"
MAX_CAR = 900           # fragments plus courts : meilleure precision (constate sur la question des levres)
RECOUVREMENT = 200      # recouvrement pour les textes sans structure


def jeton():
    env = os.path.join(os.environ["LOCALAPPDATA"], "hermes", ".env")
    with io.open(env, encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("SIYUAN_TOKEN="):
                return ligne.split("=", 1)[1].strip()
    return None

# Patterns de secrets a exclure de l'indexation (ne pas indexer un token/document sensible)
SECRET_PATTERNS = [
    r'token\s*[=:]\s*\S{8,}',
    r'api[_-]?key\s*[=:]\s*\S{6,}',
    r'password\s*[=:]\s*\S{6,}',
    r'secret\s*[=:]\s*\S{8,}',
    r'sk-[A-Za-z0-9]{20,}',
    r'Bearer\s+[A-Za-z0-9_\-\.]{20,}',
    r'Authorization:\s*\S{10,}',
    r'SIYUAN_TOKEN\s*=\s*\S{6,}',
    r'OPENROUTER_API_KEY\s*=\s*\S{6,}',
    r'OPENAI_API_KEY\s*=\s*\S{6,}',
    r'PRIVATE\s+KEY',
]

def contient_secret(texte):
    """Vrai si le texte contient un motif sensible (token, cle, password)."""
    for pat in SECRET_PATTERNS:
        if re.search(pat, texte, re.IGNORECASE):
            return True
    return False


TOKEN = jeton()


def api(route, charge):
    req = urllib.request.Request(
        SIYUAN + route,
        data=json.dumps(charge, ensure_ascii=True).encode("utf-8"),
        headers={"Authorization": "Token " + TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


# --------------------------------------------------------------------- decoupage
def decouper(texte, taille=MAX_CAR, recouvrement=RECOUVREMENT):
    """Decoupe en respectant les titres markdown quand il y en a, sinon par fenetre."""
    texte = texte.strip()
    if not texte:
        return []
    sections = re.split(r"\n(?=#{1,3} )", texte)
    fragments = []
    for section in sections:
        if len(section) <= taille:
            if section.strip():
                fragments.append(section.strip())
            continue
        paragraphes = section.split("\n\n")
        courant = ""
        for p in paragraphes:
            if len(courant) + len(p) + 2 <= taille:
                courant = (courant + "\n\n" + p).strip()
            else:
                if courant:
                    fragments.append(courant)
                while len(p) > taille:            # paragraphe trop long : fenetre glissante
                    fragments.append(p[:taille])
                    p = p[taille - recouvrement:]
                courant = p
        if courant.strip():
            fragments.append(courant.strip())
    return [f for f in fragments if len(f.strip()) > 40]


def nettoyer_kramdown(txt):
    """Retire les identifiants de bloc SiYuan ({: id="..." updated="..."}) du kramdown."""
    txt = re.sub(r"\{:\s*[^}]*\}", "", txt)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


# --------------------------------------------------------------------- sources
def source_siyuan():
    """Tous les documents SiYuan, un fragment par section."""
    out = []
    nbs = {n["id"]: n["name"] for n in api("/api/notebook/lsNotebooks", {})["data"]["notebooks"]}
    for box, nom_nb in nbs.items():
        docs = api("/api/query/sql", {"stmt": "SELECT id, content, hpath FROM blocks WHERE "
                                              "type='d' AND box='%s'" % box}).get("data") or []
        for d in docs:
            try:
                k = api("/api/block/getBlockKramdown", {"id": d["id"]})["data"]["kramdown"]
            except Exception:
                continue
            texte = nettoyer_kramdown(k)
            for i, frag in enumerate(decouper(texte)):
                out.append({"source": "siyuan", "notebook": nom_nb, "titre": d["content"],
                            "chemin": d.get("hpath") or d["content"], "partie": i,
                            "texte": frag})
    return out


def source_skills():
    out = []
    for racine, _, fichiers in os.walk(SKILLS):
        if ".archive" in racine or "node_modules" in racine:
            continue
        for f in fichiers:
            if f != "SKILL.md":
                continue
            chemin = os.path.join(racine, f)
            rel = os.path.relpath(chemin, SKILLS)
            txt = io.open(chemin, encoding="utf-8", errors="replace").read()
            for i, frag in enumerate(decouper(txt)):
                out.append({"source": "skill", "titre": rel.replace(os.sep, "/"),
                            "chemin": chemin, "partie": i, "texte": frag})
    return out


def source_scripts():
    out = []
    if not os.path.isdir(SCRIPTS_V4):
        return out
    # Exclusions demandees : les transcriptions Whisper brutes (timestamps et erreurs de
    # reconnaissance a nettoyer avant tout usage) et les journaux d'execution (*.log), dont
    # l'essentiel est deja consigne, formatte, dans les documents SiYuan.
    for f in sorted(os.listdir(SCRIPTS_V4)):
        chemin = os.path.join(SCRIPTS_V4, f)
        if not os.path.isfile(chemin) or os.path.splitext(f)[1].lower() not in (".py", ".sh", ".txt", ".md", ".json"):
            continue
        if f.lower().endswith(".log") or "transcript" in f.lower():
            continue
        if os.path.getsize(chemin) > 3_000_000:        # on saute les gros journaux
            continue
        txt = io.open(chemin, encoding="utf-8", errors="replace").read()
        for i, frag in enumerate(decouper(txt)):
            out.append({"source": "script_v4", "titre": f, "chemin": chemin,
                        "partie": i, "texte": frag})
    return out


def source_wordpress():
    out = []
    if not os.path.isdir(DEPOT_WP):
        return out
    for racine, _, fichiers in os.walk(DEPOT_WP):
        if ".git" in racine:
            continue
        for f in fichiers:
            if os.path.splitext(f)[1].lower() not in (".md", ".php", ".txt"):
                continue
            chemin = os.path.join(racine, f)
            if os.path.getsize(chemin) > 1_000_000:
                continue
            txt = io.open(chemin, encoding="utf-8", errors="replace").read()
            for i, frag in enumerate(decouper(txt)):
                out.append({"source": "wordpress", "titre": os.path.relpath(chemin, DEPOT_WP),
                            "chemin": chemin, "partie": i, "texte": frag})
    return out


def source_wiki():
    """Wiki d'architecture Hermes (%LOCALAPPDATA%\\hermes\\wiki), un fragment par section.

    Seuls les *.md sont indexes : le dossier contient aussi scripts/ (*.py, __pycache__/*.pyc),
    qui sont des outils et non du contenu. Le champ `chemin` est RELATIF a wiki/ (le wiki est
    versionne et deplace avec le home) ; audit_rag.py resout donc ce chemin contre WIKI.
    """
    out = []
    if not os.path.isdir(WIKI):
        return out
    for racine, sous_dirs, fichiers in os.walk(WIKI):
        sous_dirs[:] = [d for d in sous_dirs if d != "__pycache__"]
        for f in sorted(fichiers):
            if not f.lower().endswith(".md"):
                continue
            chemin = os.path.join(racine, f)
            try:
                if os.path.getsize(chemin) > 1_000_000:
                    continue
                txt = io.open(chemin, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            rel = os.path.relpath(chemin, WIKI).replace(os.sep, "/")
            for i, frag in enumerate(decouper(txt)):
                out.append({"source": "wiki", "titre": rel, "chemin": rel,
                            "partie": i, "texte": frag})
    return out


def construire(seulement=None):
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    morceaux = []
    # script_v4 retire le 27/09/2026 : le dossier Desktop\hermes_tuto_v4 n'existe plus
    # (suppression definitive, corbeille vide). source_scripts() reste definie plus bas
    # pour ne casser aucun import, mais n'est plus appelee (elle renvoyait deja []).
    for nom, fonction in (("siyuan", source_siyuan), ("skill", source_skills),
                          ("wiki", source_wiki), ("wordpress", source_wordpress)):
        if seulement and nom not in seulement:
            continue
        avant = len(morceaux)
        morceaux += fonction()
        print("  %-12s %5d fragments" % (nom, len(morceaux) - avant), flush=True)

    # Filtre de secrets : exclut tout fragment contenant un motif sensible.
    # Empêche qu'un token API / mot de passe réel écrit dans une source soit
    # indexé et diffusé par la recherche vectorielle.
    avant_secret = len(morceaux)
    morceaux = [m for m in morceaux if not contient_secret(m.get("texte", ""))]
    if len(morceaux) != avant_secret:
        print("filtre secrets : %d -> %d fragments" % (avant_secret, len(morceaux)), flush=True)

    print("total : %d fragments | modele %s" % (len(morceaux), MODELE), flush=True)
    # Dedoublonnage : les skills WordPress existent a la fois dans les skills Hermes et dans
    # le depot source. Sans cela, l'index renvoie deux fois le meme contenu et gaspille des
    # places dans le top-k.
    vus, uniques = set(), []
    for m in morceaux:
        empreinte = hash(re.sub(r"\s+", " ", m["texte"]).strip().lower())
        if empreinte in vus:
            continue
        vus.add(empreinte)
        uniques.append(m)
    if len(uniques) != len(morceaux):
        print("dedoublonnage : %d -> %d fragments" % (len(morceaux), len(uniques)), flush=True)
    morceaux = uniques
    modele = SentenceTransformer(MODELE, device="cpu")
    textes = ["passage: " + m["texte"] for m in morceaux]
    vecteurs = modele.encode(textes, batch_size=32, show_progress_bar=True,
                             normalize_embeddings=True, convert_to_numpy=True)
    vecteurs = np.asarray(vecteurs, dtype="float32")
    index = faiss.IndexFlatIP(vecteurs.shape[1])
    index.add(vecteurs)
    faiss.write_index(index, INDEX)
    with io.open(CHUNKS, "w", encoding="utf-8") as f:
        for m in morceaux:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    manifeste = {"modele": MODELE, "fragments": len(morceaux), "dimensions": int(vecteurs.shape[1]),
                 "index_octets": os.path.getsize(INDEX),
                 "par_source": {s: sum(1 for m in morceaux if m["source"] == s)
                                for s in ("siyuan", "skill", "wiki", "wordpress")}}
    io.open(MANIFESTE, "w", encoding="utf-8").write(json.dumps(manifeste, ensure_ascii=False, indent=1))
    print("index ecrit :", INDEX, "(%.1f Mo)" % (os.path.getsize(INDEX) / 1e6))

    # invalider le cache SQLite : l'index a change, les resultats en cache sont perimes
    import sqlite3
    cache_db = os.path.join(RACINE, "cache.db")
    if os.path.exists(cache_db):
        try:
            conn = sqlite3.connect(cache_db)
            conn.execute("DELETE FROM cache")
            conn.commit()
            print("cache invalide : %d entree(s) supprimee(s)" % conn.total_changes)
            conn.close()
        except Exception as e:
            print("AVERTISSEMENT invalidation cache :", e)
    return manifeste


if __name__ == "__main__":
    os.makedirs(RACINE, exist_ok=True)
    seulement = [a for a in sys.argv[1:] if not a.startswith("-")] or None
    print("indexation :", seulement or "toutes les sources")
    print(json.dumps(construire(seulement), ensure_ascii=False, indent=1))
