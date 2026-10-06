# -*- coding: utf-8 -*-
"""
Audit mensuel du RAG (anti-accumulation).

Inspiré critique Eliott Meunier : une mémoire vectorielle non curé accumule du bruit.
Ce script produit un rapport de fragments candidats à la suppression, sans rien supprimer.

Usage :
  python audit_rag.py                    # rapport complet
  python audit_rag.py --since 30         # fragments non cités dans les 30 derniers jours
  python audit_rag.py --json             # sortie JSON

Sortie : liste de fragments avec raison (jamais cité, redondant, obsolète)
"""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

RACINE = os.path.dirname(os.path.abspath(__file__))
CHUNKS = os.path.join(RACINE, "chunks.jsonl")
MANIFESTE = os.path.join(RACINE, "manifeste.json")
# Les fragments `wiki` portent un chemin RELATIF a la racine du wiki (voir indexer.source_wiki).
WIKI = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "wiki")
RECHERCHES_LOG = os.path.join(RACINE, "recherches.log")  # à créer/maintenir par le routeur/serveur

# Seuil de similarité pour détecter redondance (cosinus sur embeddings normalisés = produit scalaire)
SEUIL_REDONDANCE = 0.95


def charger_chunks():
    """Charge tous les fragments depuis chunks.jsonl."""
    chunks = []
    with open(CHUNKS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def charger_manifeste():
    with open(MANIFESTE, "r", encoding="utf-8") as f:
        return json.load(f)


def charger_historique_recherches(jours: int = 30) -> set:
    """Charge les IDs de fragments cités dans les recherches récentes.
    Retourne un set d'index (position dans chunks.jsonl)."""
    cites = set()
    if not os.path.exists(RECHERCHES_LOG):
        return cites

    cutoff = datetime.now() - timedelta(days=jours)
    with open(RECHERCHES_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                ts = datetime.fromisoformat(entry.get("timestamp", ""))
                if ts >= cutoff:
                    for idx in entry.get("fragments_cites", []):
                        cites.add(idx)
            except Exception:
                continue
    return cites


def detecter_obsolète(chunk: dict) -> list:
    """Détecte si un fragment référence des chemins/outils qui n'existent plus."""
    raisons = []
    texte = chunk.get("texte", "")
    chemin = chunk.get("chemin", "")
    source = chunk.get("source", "")

    # Chemins locaux qui n'existent plus (siyuan a un hpath virtuel, pas un chemin disque).
    # `wiki` porte un chemin RELATIF a wiki/ : il se resout contre WIKI et non contre le CWD,
    # sinon 100 % des fragments wiki seraient signales « chemin_inexistant » a tort.
    if chemin:
        if source == "wiki":
            cible = os.path.join(WIKI, chemin)
        elif source in ("skill", "script_v4", "wordpress"):
            cible = chemin
        else:                                    # siyuan : hpath virtuel, rien a tester
            cible = None
        if cible and not os.path.exists(cible):
            raisons.append(f"chemin_inexistant:{chemin}")

    # Outils/versions obsolètes (patterns connus)
    patterns_obsolètes = [
        (r"transformers\s*[<>=!]+\s*4\.\d+", "transformers_version_ancienne"),
        (r"diffusers\s*[<>=!]+\s*0\.\d+", "diffusers_version_ancienne"),
        (r"torch\s*[<>=!]+\s*1\.\d+", "torch_version_ancienne"),
        (r"python\s*3\.[0-7]\b", "python_version_ancienne"),
        (r"cuda\s*1[01]\b", "cuda_version_ancienne"),
    ]
    for pattern, label in patterns_obsolètes:
        if re.search(pattern, texte, re.IGNORECASE):
            raisons.append(label)

    return raisons


def detecter_redondants(chunks: list, embeddings_dict: dict) -> list:
    """Détecte les fragments redondants par similarité d'embedding.
    Retourne liste de (idx1, idx2, score) pour paires > seuil.
    Note: nécessite les embeddings - optionnel si non dispo."""
    # Pour l'instant, placeholder - nécessite accès aux embeddings FAISS
    # Peut être implémenté plus tard avec faiss.read_index
    return []


import re


def auditer(jours_inactivite: int = 30) -> dict:
    """Lance l'audit complet."""
    chunks = charger_chunks()
    manifeste = charger_manifeste()
    cites_recents = charger_historique_recherches(jours_inactivite)

    resultats = {
        "date_audit": datetime.now().isoformat(),
        "total_fragments": len(chunks),
        "par_source": manifeste.get("par_source", {}),
        "fragments_jamais_cites": [],
        "fragments_obsolètes": [],
        "fragments_redondants": [],
        "resume": {}
    }

    # 1. Fragments jamais cités dans la période
    for idx, chunk in enumerate(chunks):
        if idx not in cites_recents:
            resultats["fragments_jamais_cites"].append({
                "index": idx,
                "source": chunk.get("source"),
                "titre": chunk.get("titre", "")[:100],
                "chemin": chunk.get("chemin", ""),
                "raison": f"non_cité_depuis_{jours_inactivite}_jours"
            })

    # 2. Fragments obsolètes
    for idx, chunk in enumerate(chunks):
        raisons = detecter_obsolète(chunk)
        if raisons:
            resultats["fragments_obsolètes"].append({
                "index": idx,
                "source": chunk.get("source"),
                "titre": chunk.get("titre", "")[:100],
                "chemin": chunk.get("chemin", ""),
                "raisons": raisons
            })

    # 3. Redondance (placeholder - à implémenter avec embeddings)
    # resultats["fragments_redondants"] = detecter_redondants(chunks, {})

    # Résumé
    resultats["resume"] = {
        "jamais_cites": len(resultats["fragments_jamais_cites"]),
        "obsolètes": len(resultats["fragments_obsolètes"]),
        "redondants": len(resultats["fragments_redondants"]),
        "total_candidats_suppression": (
            len(resultats["fragments_jamais_cites"]) +
            len(resultats["fragments_obsolètes"]) +
            len(resultats["fragments_redondants"])
        )
    }

    return resultats


def main():
    parser = argparse.ArgumentParser(description="Audit mensuel RAG - détection fragments à curer")
    parser.add_argument("--since", type=int, default=30, help="Jours d'inactivité pour 'jamais cité'")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    parser.add_argument("--output", help="Fichier de sortie (défaut: stdout)")
    args = parser.parse_args()

    rapport = auditer(args.since)

    if args.json:
        sortie = json.dumps(rapport, ensure_ascii=False, indent=2)
    else:
        # Format lisible
        lignes = [
            f"=== AUDIT RAG - {rapport['date_audit']} ===",
            f"Total fragments: {rapport['total_fragments']}",
            f"Par source: {rapport['par_source']}",
            "",
            f"--- RÉSUMÉ ---",
            f"Jamais cités ({args.since}j): {rapport['resume']['jamais_cites']}",
            f"Obsolètes: {rapport['resume']['obsolètes']}",
            f"Redondants: {rapport['resume']['redondants']}",
            f"Total candidats: {rapport['resume']['total_candidats_suppression']}",
            "",
        ]
        if rapport["fragments_obsolètes"]:
            lignes.append("--- OBSOLÈTES ---")
            for f in rapport["fragments_obsolètes"][:20]:
                lignes.append(f"  [{f['index']}] {f['source']} | {f['titre']} | {f['raisons']}")
        if rapport["fragments_jamais_cites"]:
            lignes.append(f"\n--- JAMAIS CITÉS ({args.since}j) - top 20 ---")
            for f in rapport["fragments_jamais_cites"][:20]:
                lignes.append(f"  [{f['index']}] {f['source']} | {f['titre']} | {f['chemin']}")
        sortie = "\n".join(lignes)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(sortie)
        print(f"Rapport écrit dans {args.output}")
    else:
        print(sortie)


if __name__ == "__main__":
    main()