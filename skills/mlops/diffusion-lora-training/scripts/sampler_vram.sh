#!/bin/bash
# Background VRAM sampler for a training run.
#   bash sampler_vram.sh <output_file> [max_samples]
# One measurement every 30 s; the max survives even when the run is killed at its timeout.
OUT="${1:-vram.log}"
MAX="${2:-380}"
rm -f "$OUT"
for i in $(seq 1 "$MAX"); do
  nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits >> "$OUT" 2>/dev/null
  sleep 30
done
