# -*- coding: utf-8 -*-
"""Pousse l'audit dans SiYuan (apprentissage-continu) et range le notebook des projets.

1. Crée le document d'audit avec la convention Statut / Dernière mise à jour, puis
   Fait / Reste à faire / Pièges / Commandes, suivi du rapport complet.
2. Remplace les 5 fiches de sites (les sites Local ont été supprimés le 15/09) par un
   seul document d'historique qui conserve les versions et les listes d'extensions.
"""
import io
import json
import os
import urllib.request

BASE = "http://127.0.0.1:6806"
MAJ = "15/09/2026"
RACINE = os.path.dirname(os.path.abspath(__file__))


def jeton():
    env = os.path.join(os.environ["LOCALAPPDATA"], "hermes", ".env")
    with io.open(env, encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("SIYUAN_TOKEN="):
                return ligne.split("=", 1)[1].strip()
    raise SystemExit("SIYUAN_TOKEN introuvable")


TOKEN = jeton()


def api(route, charge):
    req = urllib.request.Request(
        BASE + route,
        data=json.dumps(charge, ensure_ascii=True).encode("utf-8"),
        headers={"Authorization": "Token " + TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def notebook(nom):
    r = api("/api/notebook/lsNotebooks", {})
    for nb in (r.get("data") or {}).get("notebooks") or []:
        if nb.get("name") == nom:
            return nb["id"]
    r = api("/api/notebook/createNotebook", {"name": nom})
    return r["data"]["notebook"]["id"]


def docs(nb_id):
    r = api("/api/query/sql",
            {"stmt": "SELECT id, content FROM blocks WHERE type='d' AND box='%s'" % nb_id})
    return (r.get("data") or [])


def creer(nb_id, chemin, markdown):
    r = api("/api/filetree/createDocWithMd",
            {"notebook": nb_id, "path": chemin, "markdown": markdown})
    return r.get("code")


# ---------------------------------------------------------------- document d'audit
corps = io.open(os.path.join(os.path.dirname(RACINE), "Desktop", "hermes_install",
                             "TRAINING_AUDIT.md"), encoding="utf-8").read() \
    if False else io.open(os.path.join(os.environ["USERPROFILE"], "Desktop", "hermes_install",
                                       "TRAINING_AUDIT.md"), encoding="utf-8").read()

entete = """> **Statut** : actif
> **Dernière mise à jour** : %s

## Fait

- Inventaire des 7 environnements IA, des corpus présents et des scripts v4 : aucun n'a de paquets
  d'entraînement (`peft`, `bitsandbytes`, `datasets`, `trl`), aucune chaîne d'entraînement installée.
- Mesures de la matière disponible : 14 s de voix réelle (le reste est de la synthèse XTTS),
  quelques minutes d'audio transcrit par Whisper lui-même, 6 Mo de prose issue de 364 sessions,
  environ 80 skills et 78 scripts réutilisables.
- Six cibles évaluées sous la contrainte de 8 Go de VRAM, avec données, VRAM, durée, disque,
  utilité et risques.
- Constat central : les seules données réellement prêtes et propres sont celles de la documentation
  (skills, SiYuan, scripts, dépôt WordPress) — donc la cible RAG.

## Reste à faire

1. **RAG sur la documentation et les skills** — à faire maintenant : données déjà là, aucun
   entraînement, utile tous les jours. Première étape : le script d'indexation, sans installer de
   modèle avant d'avoir compté les fragments.
2. **Lexique de diction et de relecture** — sans entraînement : extraire le tableau
   « terme → graphie validée » depuis `test_diction_v8*.py`.
3. **Contrôle qualité vidéo par seuils** — puis classifieur seulement si les défauts se
   diversifient : regrouper les métriques de `diag_sauts.py`, `contour_levres.py`, `diag_cotes.py`
   dans un script unique et le passer sur le volet 4 livré (doit retrouver les 5 sauts connus).

À valider avant d'engager : le modèle d'embeddings (aucun présent sur la machine), le périmètre de
l'index, et le mode de mise à jour (manuelle ou planifiée).

## Pièges

- Fine-tuner XTTS sur 14 s de voix : ça abîme la voix, ça ne corrige pas la diction.
- Fine-tuner Whisper sur ses propres transcriptions : le modèle apprend ses erreurs.
- Entraîner un 7B local : trois modèles sont déjà installés et dix sont gratuits en ligne, le
  résultat serait inférieur pour deux à trois jours de GPU.
- Tenter Flux (12 B) ou LTX-2.3 (22 B) en LoRA : VRAM hors de portée, et nos poids LTX sont en GGUF.
- Confondre `data/xtts/voix_xtts_*.wav` (synthèse) avec de la voix réelle.
- Lancer un entraînement sans avoir compté les données, la qualité et les étiquettes.

## Commandes

```
python mesure_sessions.py                     # volume exploitable de la base de sessions
python gather_sites.py                        # etat des sites Local (vide depuis le 15/09)
grep -a "Uninitialized parameters" comfyui.log # reflexe de diagnostic avant tout telechargement
```

---

""" % MAJ

nb = notebook("apprentissage-continu")
for d in docs(nb):
    if d["content"].startswith("Audit des cibles"):
        print("audit deja present, remplace :", api("/api/filetree/removeDocByID", {"id": d["id"]}).get("code"))
print("creation du document d'audit :", creer(nb, "/Audit des cibles entrainables - 15-09-2026",
                                              entete + corps))

# ------------------------------------------------- historique des sites supprimes
nbp = notebook("hermes-projets")
sites = json.load(io.open(os.path.join(RACINE, "sites_data.json"), encoding="utf-8"))
lignes = ["# Historique — sites Local supprimés le 15/09/2026\n",
          "> **Statut** : veille\n> **Dernière mise à jour** : 15/09/2026\n",
          "## Fait",
          "- Les cinq sites Local ont été supprimés par l'utilisateur le 15/09/2026",
          "  (`sites.json` vidé, dossier `Local Sites` disparu, seul le routeur subsiste).",
          "- L'inventaire ci-dessous est conservé comme référence pour recréer un site : les",
          "  versions et les listes d'extensions étaient celles en place juste avant la suppression.",
          "", "| Site | Domaine | WordPress | PHP | MySQL | nginx | Extensions | Sauvegarde |",
          "|---|---|---|---|---|---|---|---|"]
for nom, s in sorted(sites.items()):
    lignes.append("| %s | %s | %s | %s | %s | %s | %d | %s |"
                  % (nom, s["domain"], s["wp"], s["php"], s["mysql"], s["web"],
                     len(s["extensions"]), (s["sauvegarde"] or {}).get("date", "-")))
lignes += ["", "## Reste à faire",
           "- Aucun site en production pour l'instant ; l'utilisateur préviendra à la création du",
           "  prochain. Le notebook `hermes-projets` recevra alors une fiche par site, comme prévu.",
           "", "## Pièges",
           "- Les dumps SQL (`app/sql/local.sql`) ont disparu avec les sites : plus aucune donnée de",
           "  site n'est récupérable sur cette machine.",
           "- Ne pas réutiliser les identifiants de base de Local (`root`/`root`) hors de la machine.",
           "", "## Commandes", "```",
           "python gather_sites.py   # a relancer quand un site sera recree", "```"]

for d in docs(nbp):
    if d["content"] in {n for n in sites}:
        print("  fiche obsolete supprimee : %-18s %s" % (d["content"],
              api("/api/filetree/removeDocByID", {"id": d["id"]}).get("code")))
print("creation de l'historique :", creer(nbp, "/Historique - sites supprimes le 15-09-2026",
                                          "\n".join(lignes) + "\n"))
