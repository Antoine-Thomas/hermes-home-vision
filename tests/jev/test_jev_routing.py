import sys
import time
import json
sys.path.insert(0, 'skills/typesafe-ai/scripts')
from jev_helper import choice

# Define the 10 test cases with expected route
test_cases = [
    ("Définition de 'écologie' dans mes notes", "SiYuan"),
    ("Trouve-moi un passage dans mes PDF sur le climat", "RAG"),
    ("Le concept 'Psychopomp' existe-t-il déjà ?", "SiYuan"),
    ("Résume mes 50 derniers documents sur l'IA", "RAG"),
    ("Créer une fiche sur 'transformer' et la relier", "SiYuan"),
    ("Quels documents parlent de 'reward model' ?", "RAG"),
    ("Mettre à jour la fiche 'JEV' avec la latence mesurée", "SiYuan"),
    ("Classer ces 100 emails par urgence", "RAG"),
    ("Le concept 'alignment' a-t-il évolué ?", "SiYuan"),
    ("Chercher dans mes conversations passées", "RAG"),
]

options = {
    "RAG": "recherche vectorielle dans les documents indexés",
    "SiYuan": "wiki conceptuel, notes compilées",
}

results = []
total_cost = 0.0
total_latency = 0.0

print("=== Test de routage RAG vs SiYuan ===")
for i, (query, expected) in enumerate(test_cases, 1):
    start = time.perf_counter()
    r = choice(query, f"route_{i}", "Choisir parmi : [RAG, SiYuan]", options)
    elapsed = time.perf_counter() - start
    ans = r.get('answers', {}).get(f'route_{i}', {})
    decision = ans.get('choice', 'N/A')
    conf = ans.get('confidence', 'N/A')
    cost = r.get('usage', {}).get('cost', 0)
    total_cost += cost
    total_latency += elapsed
    
    ok = "OK" if decision == expected else "ÉCHEC"
    results.append({
        "num": i,
        "query": query,
        "expected": expected,
        "decision": decision,
        "confidence": conf,
        "ok": ok,
        "latency": elapsed,
        "cost": cost,
        "raw": r
    })
    print(f"{i:2d}. {query[:50]:50s} -> {decision:8s} (attendu: {expected:6s}) {ok}  latence={elapsed:.3f}s  coût={cost:.2e}")

success = sum(1 for r in results if r['ok'] == 'OK')
print(f"\nTaux de réussite: {success}/{len(results)} = {success/len(results)*100:.1f}%")
print(f"Latence moyenne: {total_latency/len(results):.3f} s")
print(f"Coût total: {total_cost:.6e} $")
print(f"Coût moyen: {total_cost/len(results):.3e} $")

# Save results for later comparison
with open('jev_routing_results.json', 'w', encoding='utf-8') as f:
    # Remove raw for compactness? Keep it for now.
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nRésultats sauvegardés dans jev_routing_results.json")