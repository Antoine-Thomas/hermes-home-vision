import sys
import time
import json
sys.path.insert(0, 'skills/typesafe-ai/scripts')
from jev_helper import choice

# Load previous results
with open('jev_routing_results.json', 'r', encoding='utf-8') as f:
    prev_results = json.load(f)
prev_decisions = {r['query']: r['decision'] for r in prev_results}

# Test cases in a different order (reversed + interleaved)
test_cases = [
    "Chercher dans mes conversations passées",
    "Le concept 'alignment' a-t-il évolué ?",
    "Classer ces 100 emails par urgence",
    "Mettre à jour la fiche 'JEV' avec la latence mesurée",
    "Quels documents parlent de 'reward model' ?",
    "Créer une fiche sur 'transformer' et la relier",
    "Résume mes 50 derniers documents sur l'IA",
    "Le concept 'Psychopomp' existe-t-il déjà ?",
    "Trouve-moi un passage dans mes PDF sur le climat",
    "Définition de 'écologie' dans mes notes",
]

options = {
    "RAG": "recherche vectorielle dans les documents indexés",
    "SiYuan": "wiki conceptuel, notes compilées",
}

divergences = []
print("=== Test de cohérence (ordre différent) ===")
for i, query in enumerate(test_cases, 1):
    r = choice(query, f"coh_{i}", "Choisir parmi : [RAG, SiYuan]", options)
    ans = r.get('answers', {}).get(f'coh_{i}', {})
    decision = ans.get('choice', 'N/A')
    prev = prev_decisions.get(query, 'N/A')
    match = "MATCH" if decision == prev else "DIVERGENCE"
    if decision != prev:
        divergences.append((query, prev, decision))
    print(f"{i:2d}. {query[:50]:50s} -> {decision:8s} (précédent: {prev:6s}) {match}")

print(f"\nDivergences: {len(divergences)}/10")
if divergences:
    for q, p, d in divergences:
        print(f"  - {q}: {p} -> {d}")
else:
    print("Aucune divergence : JEV est déterministe sur ces cas.")