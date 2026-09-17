# SIRENE API — Crawl d'entreprises pour prospection B2B

Workflow complet pour constituer une base de prospects à partir de l'API SIRENE (data.gouv.fr) et enrichir avec des emails scrapés.

## API Annuaire des Entreprises

**Endpoint** : `https://recherche-entreprises.api.gouv.fr/search`

**Paramètres clés** :
- `code_postal=14000` — filtre par code postal (Caen). Ne PAS utiliser `commune=` (ne fonctionne pas).
- `activite_principale=62.01Z` — filtre par code NAF
- `per_page=25` — **max 25** (l'API rejette 50+)
- `page=1` — pagination

**Codes NAF pertinents (secteur créatif/numérique)** :

| Code | Libellé |
|------|---------|
| 62.01Z | Programmation informatique |
| 62.02A | Conseil systèmes/logiciels |
| 62.02B | Tierce maintenance info |
| 63.11Z | Traitement données/hébergement |
| 63.12Z | Portails Internet |
| 73.11Z | Agences de publicité |
| 73.12Z | Régie publicitaire |
| 73.20Z | Études de marché/sondages |
| 74.10Z | Design spécialisé |
| 74.20Z | Photographie |
| 70.21Z | Conseil RP/communication |
| 18.13Z | Pré-presse |
| 58.19Z | Édition |
| 59.11Z | Production films/vidéo |
| 59.12Z | Post-production |
| 59.20Z | Enregistrement sonore/musique |

**Exemple** :
```
curl -s "https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=62.01Z&per_page=25&page=1"
```

**Champs retournés** : `nom_complet`, `siege.numero_voie`, `siege.type_voie`, `siege.libelle_voie`, `activite_principale`. **Pas d'email ni de site web.**

## Workflow d'enrichissement

### Phase 1 : Crawl SIRENE
1. Pour chaque code NAF, boucler sur les pages jusqu'à épuisement (`total_results / 25` pages)
2. Sauvegarder chaque page dans des fichiers JSON séparés
3. Fusionner, dédupliquer (par `nom_complet` uppercase[:45]), filtrer les grandes entreprises nationales

### Phase 2 : DNS MX Check (génération de domaines)
1. Nettoyer le nom d'entreprise : enlever le nom commercial entre `()`, accents → ASCII, ne garder que `[a-z0-9]`
2. Générer `nomclean.fr` et `nomclean.com`
3. `nslookup -type=mx domaine` → si MX trouvé, le domaine peut recevoir des emails
4. Générer les formats probables : `contact@`, `info@`, `bonjour@` + domaine

**Taux de réussite** : ~14% (257/1851 pour Caen)

### Phase 3 : Scraper les sites web
1. Tenter `https://www.nomclean.fr` puis `.com`
2. Extraire les emails par regex `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
3. Chercher aussi sur `/contact`, `/contactez-nous`, `/nous-contacter`
4. Filtrer les faux emails : `@example.com`, `@domain.com`, `user@domain`, `votre@email`, etc.

**Script recommandé** : 10 workers ThreadPoolExecutor, timeout 6s par site, SSL verify désactivé.

**Taux de réussite** : ~9% (172/1851 pour Caen, 172 emails réels)

### Phase 4 : Hunter.io (optionnel)
- API Domain Search : `https://api.hunter.io/v2/domain-search?domain=X&api_key=Y`
- API Email Verifier : `https://api.hunter.io/v2/email-verifier?email=X&api_key=Y`
- **Limité pour les TPE françaises** — la base est orientée US/UK. 0/7 domaines trouvés sur un test caennais.
- Utile pour VÉRIFIER les emails déjà trouvés par scraper (3/4 validés à 100%)

### Phase 5 : Consolidation
Fusionner les 3 sources avec priorité :
1. Scraper (email trouvé sur le site = haute confiance ⭐⭐⭐⭐)
2. Hunter vérifié (score ≥ 90 = ⭐⭐⭐⭐⭐)
3. DNS MX (domaine actif mais email non confirmé = ⭐⭐)

## Filtrage des faux emails

```python
FAKE = ['user@domain', 'votre@email', 'jean@exemple', 'info@mysite',
        '@example.com', '@domain.com', '@mysite.com', 'email@email',
        'exemple@', 'mon@email', '@exemple.fr', 'test@test',
        'name@email', 'mail@mail', '@email.com', 'webmaster@',
        'vous@structure', 'utilisateur@domaine', 'jean@entreprise',
        'interested@domainmarket']
```

## Pièges

- **Python urllib depuis `execute_code`** : retourne HTTP 400 pour l'API SIRENE. Utiliser `curl` depuis `terminal()` à la place. Le sandbox execute_code a des restrictions réseau.
- **OpenStreetMap Overpass** : quasi-vide pour les PME françaises (~1 résultat pour Caen). Ne pas utiliser.
- **DuckDuckGo Search** (`duckduckgo_search` / `ddgs`) : résultats hors-sujet pour les recherches locales françaises. Ne pas utiliser pour ce workflow.
- **Google scraping** : bloque les requêtes curl. Ne pas essayer.
- **`per_page` max = 25** : l'API rejette les valeurs > 25 avec un message d'erreur.
- **`commune=14118`** : le paramètre ne fonctionne pas. Utiliser `code_postal=14000`.
