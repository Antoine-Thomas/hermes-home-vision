# -*- coding: utf-8 -*-
"""Rassemble les donnees reelles de chaque site Local (pour le notebook hermes-projets).

Lit, sans rien modifier :
  - %APPDATA%\\Local\\sites.json          -> versions PHP / MySQL / nginx, domaine
  - <site>\\app\\public\\wp-includes\\version.php -> version WordPress
  - <site>\\app\\public\\wp-content\\plugins\\*    -> nom + version de chaque extension
  - <site>\\app\\sql\\local.sql                   -> derniere sauvegarde (taille, date)
  - le dump SQL                                  -> extensions ACTIVES (option active_plugins)

Sortie : JSON sur la sortie standard (pour relecture avant import).
"""
import io
import json
import os
import re
import sys

APPDATA = os.environ["APPDATA"]
LOCAL_SITES = os.path.join(os.path.expanduser("~"), "Local Sites")


def sites():
    d = json.load(io.open(os.path.join(APPDATA, "Local", "sites.json"), encoding="utf-8"))
    out = {}
    for sid, s in d.items():
        chemin = s.get("path") or ""
        if chemin.startswith("~"):
            # Local stocke "~\Local Sites\<site>" : le ~ n'est pas developpe
            chemin = os.path.expanduser("~") + chemin[1:]
        out[s["name"]] = {
            "id": sid,
            "path": chemin,
            "domain": s.get("domain"),
            "php": (s.get("services", {}).get("php") or {}).get("version"),
            "mysql": (s.get("services", {}).get("mysql") or {}).get("version"),
            "web": ((s.get("services", {}).get("nginx") or {}).get("version")
                    or (s.get("services", {}).get("apache") or {}).get("version")),
            "web_nom": "nginx" if s.get("services", {}).get("nginx") else "apache",
        }
    return out


def version_wp(racine):
    p = os.path.join(racine, "wp-includes", "version.php")
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8", errors="replace") as f:
        for ligne in f:
            m = re.match(r"\s*\$wp_version\s*=\s*'([^']+)'", ligne)
            if m:
                return m.group(1)
    return None


def extensions(racine):
    dossier = os.path.join(racine, "wp-content", "plugins")
    if not os.path.isdir(dossier):
        return []
    out = []
    for nom in sorted(os.listdir(dossier)):
        chemin = os.path.join(dossier, nom)
        if not os.path.isdir(chemin):
            continue
        entete = None
        for f in sorted(os.listdir(chemin)):
            if f.endswith(".php"):
                with io.open(os.path.join(chemin, f), encoding="utf-8", errors="replace") as fh:
                    tete = fh.read(6000)
                m = re.search(r"^\s*\*?\s*Version:\s*(.+)$", tete, re.M)
                n = re.search(r"^\s*\*?\s*Plugin Name:\s*(.+)$", tete, re.M)
                if m:
                    entete = (n.group(1).strip() if n else nom, m.group(1).strip())
                    break
        if entete is None:
            entete = (nom, "version inconnue")
        out.append({"dossier": nom, "nom": entete[0], "version": entete[1]})
    return out


def actives(dump):
    """Extensions actives : option active_plugins du dump SQL (lecture seule)."""
    if not os.path.exists(dump):
        return None
    with io.open(dump, encoding="utf-8", errors="replace") as f:
        txt = f.read(6_000_000)
    i = txt.find("active_plugins")
    if i < 0:
        return None
    morceau = txt[i:i + 4000]
    return sorted(set(re.findall(r'([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\.]+\.php)', morceau)))


def sauvegarde(site_dir):
    dossier = os.path.join(site_dir, "app", "sql")
    if not os.path.isdir(dossier):
        return None
    fichiers = [f for f in os.listdir(dossier) if f.endswith(".sql")]
    if not fichiers:
        return None
    f = max(fichiers, key=lambda x: os.path.getmtime(os.path.join(dossier, x)))
    p = os.path.join(dossier, f)
    return {"fichier": f, "taille_Mo": round(os.path.getsize(p) / 1e6, 2),
            "date": __import__("datetime").datetime.fromtimestamp(os.path.getmtime(p)).strftime("%d/%m/%Y %H:%M")}


if __name__ == "__main__":
    res = {}
    for nom, infos in sites().items():
        d = infos["path"] or os.path.join(LOCAL_SITES, nom)
        racine = os.path.join(d, "app", "public")
        infos["wp"] = version_wp(racine)
        infos["extensions"] = extensions(racine)
        infos["actives"] = actives(os.path.join(d, "app", "sql", "local.sql"))
        infos["sauvegarde"] = sauvegarde(d)
        res[nom] = infos
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
