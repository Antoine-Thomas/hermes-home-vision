# Semantic Scholar (Citations, Related Papers, Author Profiles)

arXiv doesn't provide citation data or recommendations. Use the **Semantic Scholar API** for that — free, no key needed for basic use (1 req/sec), returns JSON.

### Get paper details + citations

```bash
# By arXiv ID
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,authors,citationCount,referenceCount,influentialCitationCount,year,abstract" | python -m json.tool

# By Semantic Scholar paper ID or DOI
curl -s "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1234/example?fields=title,citationCount"
```

### Get citations OF a paper (who cited it)

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/citations?fields=title,authors,year,citationCount&limit=10" | python -m json.tool
```

### Get references FROM a paper (what it cites)

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/references?fields=title,authors,year,citationCount&limit=10" | python -m json.tool
```

### Search papers (alternative to arXiv search, returns JSON)

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=GRPO+reinforcement+learning&limit=5&fields=title,authors,year,citationCount,externalIds" | python -m json.tool
```

### Get paper recommendations

```bash
curl -s -X POST "https://api.semanticscholar.org/recommendations/v1/papers/" \
  -H "Content-Type: application/json" \
  -d '{"positivePaperIds": ["arXiv:2402.03300"], "negativePaperIds": []}' | python -m json.tool
```

### Author profile

```bash
curl -s "https://api.semanticscholar.org/graph/v1/author/search?query=Yann+LeCun&fields=name,hIndex,citationCount,paperCount" | python -m json.tool
```

### Useful Semantic Scholar fields

`title`, `authors`, `year`, `abstract`, `citationCount`, `referenceCount`, `influentialCitationCount`, `isOpenAccess`, `openAccessPdf`, `fieldsOfStudy`, `publicationVenue`, `externalIds` (contains arXiv ID, DOI, etc.)

---
