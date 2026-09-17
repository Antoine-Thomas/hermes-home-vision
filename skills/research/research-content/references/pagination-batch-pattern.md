# Pagination Batch Script (bash + curl)

When you need to fetch ALL pages across multiple NAF codes, use a parallel batch pattern to avoid rate-limiting while staying fast (8 concurrent, 1s between batches).

## Template

```bash
#!/bin/bash
# Crawl complet avec pagination parallèle
OUTDIR="C:/Users/<user>/Desktop/crawl_pages"
mkdir -p "$OUTDIR"

# NAF codes → page count (use (total_results + 24) // 25 to compute)
declare -A NAFS
NAFS[62.01Z]=22   # Programmation
NAFS[73.11Z]=7    # Agences pub
# ... add all target NAFs

fetch_one() {
    local naf=$1 page=$2
    local out="$OUTDIR/${naf}_p${page}.json"
    local url="https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=$naf&per_page=25&page=$page"
    curl -s --max-time 20 "$url" -o "$out"
    local sz=$(wc -c < "$out" 2>/dev/null || echo 0)
    echo "  $naf p$page: $sz bytes"
}

total=0
for naf in "${!NAFS[@]}"; do
    pages=${NAFS[$naf]}
    for ((p=1; p<=pages; p++)); do
        fetch_one "$naf" "$p" &
        total=$((total+1))
        if [ $((total % 8)) -eq 0 ]; then
            wait        # drain batch
            sleep 1     # politeness delay
        fi
    done
done
wait
echo "Done: $total pages"
```

## Merging Pages (Python)

```python
import json, os, glob

indir = "C:/Users/<user>/Desktop/crawl_pages"
all_results = []
seen = set()

for fpath in sorted(glob.glob(os.path.join(indir, "*.json"))):
    naf_code = os.path.basename(fpath).split('_')[0]
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for r in data.get('results', []):
        nom = r.get('nom_complet', '').strip()
        # Filter, deduplicate, collect...
        if nom and nom.upper()[:45] not in seen:
            seen.add(nom.upper()[:45])
            all_results.append(...)
```

## Pitfalls

- **Empty pages (162 bytes)**: The API may return more total_results than actual data. Pages beyond the real data return `{"results":[],"total_results":N,...}` (~162 bytes). The merge script handles these gracefully — they just contribute no items.
- **Path format**: On Windows, always use `C:/...` for curl output paths, never `/c/...`.
- **Shell escaping**: Put the URL in double quotes, NOT single quotes, so `$naf` expands. The `&` in the query string is safe inside double quotes.
