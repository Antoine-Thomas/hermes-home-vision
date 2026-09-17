# -*- coding: utf-8 -*-
"""Supprime un document SiYuan en respectant la regle qui evite le PANIC du noyau.

    python supprimer_document_siyuan.py "<titre exact>"
    python supprimer_document_siyuan.py "<titre>" --notebook hermes-skills
    python supprimer_document_siyuan.py --simuler "<titre>"      (ne supprime rien)

POURQUOI CE SCRIPT EXISTE
SiYuan 3.8.2 peut lever, dans son journal :

    removed children dir [...]
    PANIC RECOVERED: interface conversion: interface {} is nil, not string
      siyuan/kernel/api/filetree.go:758

lorsqu'on appelle `removeDocByID` sur un document **parent** : l'API renvoie une erreur 500, mais
les fichiers sont bel et bien supprimes, enfants compris. Deux consequences :

  1. on croit avoir supprime une enveloppe vide et on perd le contenu de l'enfant ;
  2. l'erreur 500 fait croire a un echec alors que l'operation a eu lieu.

REGLE APPLIQUEE ICI : supprimer les enfants un par un, du plus profond au plus proche, puis le
parent. Le script :

  1. trouve le document par son titre ;
  2. liste toute sa descendance (`hpath` sous ce document), triee du plus profond au plus proche ;
  3. affiche ce qu'il va faire et REFUSE de continuer si un descendant n'est pas vide (`--forcer`
     pour passer outre, en connaissance de cause) ;
  4. supprime chaque descendant en partant du plus profond, puis le document lui-meme ;
  5. verifie apres coup que plus aucun descendant ne subsiste.

Ne supprime jamais rien sans affichage prealable : `--simuler` montre le plan complet.
"""
import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request

SIYUAN = os.environ.get("SIYUAN_URL", "http://127.0.0.1:6806")


def jeton():
    chemin = os.path.join(os.environ["LOCALAPPDATA"], "hermes", ".env")
    for ligne in io.open(chemin, encoding="utf-8"):
        if ligne.startswith("SIYUAN_TOKEN"):
            return ligne.split("=", 1)[1].strip()
    raise SystemExit("SIYUAN_TOKEN introuvable dans %s" % chemin)


def api(chemin, charge, jeton_):
    r = urllib.request.Request(SIYUAN + "/api/" + chemin, data=json.dumps(charge).encode(),
                               headers={"Authorization": "Token " + jeton_,
                                        "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=30).read().decode())
    except urllib.error.HTTPError as e:
        # le PANIC du noyau se manifeste ici : erreur 500 alors que la suppression a eu lieu
        return {"code": e.code, "msg": "erreur HTTP %s (verifier si la suppression a eu lieu "
                                       "malgre tout : c'est le symptome du PANIC)" % e.code}


def blocs(requete, jeton_):
    return (api("query/sql", {"stmt": requete}, jeton_).get("data") or [])


def plan_de_suppression(titre, notebook, jeton_):
    """Rend (document, descendants du plus profond au plus proche, enfants_vides)."""
    filtre = ""
    if notebook:
        nid = [n["id"] for n in api("notebook/lsNotebooks", {}, jeton_)["data"]["notebooks"]
               if n["name"] == notebook]
        if not nid:
            raise SystemExit("notebook introuvable : %s" % notebook)
        filtre = " AND box='%s'" % nid[0]
    docs = blocs("SELECT id, hpath FROM blocks WHERE type='d' AND content='%s'%s"
                 % (titre.replace("'", "''"), filtre), jeton_)
    if not docs:
        raise SystemExit("document introuvable : %s" % titre)
    if len(docs) > 1:
        print("  ATTENTION : %d documents portent ce titre. Precisez --notebook." % len(docs))
    doc = docs[0]
    # descendance : tout bloc dont le hpath commence par le hpath du document suivi de '/'
    desc = blocs("SELECT id, hpath, type FROM blocks WHERE hpath LIKE '%s/%%'"
                 % doc["hpath"].replace("'", "''"), jeton_)
    # seuls les SOUS-DOCUMENTS ont un type='d'
    sous_docs = [b for b in desc if b.get("type") == "d"]
    sous_docs.sort(key=lambda b: -len(b["hpath"]))          # plus profond d'abord
    return doc, sous_docs


def contenu(doc_id, jeton_):
    n = blocs("SELECT COUNT(*) AS n FROM blocks WHERE root_id='%s' AND type<>'d'" % doc_id, jeton_)
    return n[0]["n"] if n else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("titre")
    p.add_argument("--notebook", default=None)
    p.add_argument("--simuler", action="store_true")
    p.add_argument("--forcer", action="store_true",
                   help="supprimer meme si un descendant contient du texte")
    a = p.parse_args()
    j = jeton()

    doc, sous_docs = plan_de_suppression(a.titre, a.notebook, j)
    print("document cible : %s  (%s)" % (doc["hpath"], doc["id"]))
    print("  blocs de contenu : %d" % contenu(doc["id"], j))
    if sous_docs:
        print("  %d sous-document(s), du plus profond au plus proche :" % len(sous_docs))
        for s in sous_docs:
            n = contenu(s["id"], j)
            etat = "VIDE" if n <= 1 else "%d blocs de contenu" % n
            print("    - %-44s %s" % (s["hpath"], etat))
            if n > 1 and not a.forcer:
                raise SystemExit("  ARRET : un descendant contient du texte. Republier d'abord si "
                                 "c'est un contenu a garder, ou --forcer en connaissance de cause.")

    if a.simuler:
        print("\n--simuler : rien n'a ete supprime.")
        sys.exit(0)

    print("\nsuppression, enfants d'abord :")
    for s in sous_docs:                       # du plus profond au plus proche
        r = api("filetree/removeDocByID", {"id": s["id"]}, j)
        print("  %-44s code %s" % (s["hpath"], r.get("code")))
    r = api("filetree/removeDocByID", {"id": doc["id"]}, j)
    print("  %-44s code %s" % (doc["hpath"], r.get("code")))

    restants = blocs("SELECT id FROM blocks WHERE hpath LIKE '%s/%%'"
                     % doc["hpath"].replace("'", "''"), j)
    print("\ncontrole : %d descendant(s) restant(s)" % len(restants))
    sys.exit(0 if not restants else 1)
