#!/usr/bin/env bash
# Rerun a specific list of rcheck shards (klass:seed:k triples) in parallel with the
# overnight exit-gate budgets, writing JSONL per shard to OUT_DIR. Used for the cached-vs-
# baseline A/B (Task 11-4): baseline = engine/build/rcheck_out (pre-cache code).
# Usage: rcheck_rerun_shards.sh OUT_DIR "uniform:1:0 uniform:1:2 ..." [extra rcheck flags...]
set -euo pipefail
BUILD=engine/build
OUT_DIR=$1; shift
SHARDS=$1; shift
mkdir -p "$OUT_DIR"
pids=()
for spec in $SHARDS; do
  IFS=: read -r klass seed k <<<"$spec"
  out="$OUT_DIR/${klass}_seed${seed}_shard${k}of10.jsonl"
  "$BUILD/rcheck" --klass "$klass" --seed "$seed" --n 100 --shard "$k/10" \
    --exact-leaves 20000 --exact-nodes 12000 --b-visits 20000 --b-depth 100 \
    --out "$out" "$@" &
  pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
echo "rcheck_rerun_shards: done fail=$fail"
exit $fail
