#!/bin/bash
# Parallel pagination script for SIRENE API
# Usage: set NAFS array, run from bash
# Output: JSON files per page in $OUTDIR

OUTDIR="C:/Users/$USER/Desktop/crawl_pages"
mkdir -p "$OUTDIR"

# Define NAF codes and page counts (from first API call's total_results)
declare -A NAFS
NAFS[62.01Z]=22   # Programmation
NAFS[62.02A]=10   # Conseil systèmes
NAFS[73.11Z]=7    # Agences pub
NAFS[74.10Z]=14   # Design
# ... add more as needed

fetch_page() {
    local naf=$1 page=$2
    local out="$OUTDIR/${naf}_p${page}.json"
    local url="https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=$CODE_POSTAL&activite_principale=$naf&per_page=25&page=$page"
    curl -s --max-time 20 "$url" -o "$out"
    local sz=$(wc -c < "$out" 2>/dev/null || echo 0)
    echo "  $naf p$page: $sz bytes"
}

total=0
for naf in "${!NAFS[@]}"; do
    pages=${NAFS[$naf]}
    for ((p=1; p<=pages; p++)); do
        fetch_page "$naf" "$p" &
        total=$((total+1))
        # Batch of 8, then wait
        if [ $((total % 8)) -eq 0 ]; then
            wait
            sleep 1
        fi
    done
done
wait

echo "DONE: $total pages in $OUTDIR"
ls "$OUTDIR"/*.json | wc -l
