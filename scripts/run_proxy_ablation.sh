#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 1 ]; then echo "usage: $0 <parent-B2-run-id> [benchmark] [model]"; exit 2; fi
PARENT="$1"; BENCHMARK="${2:-../4DCodeBench}"; MODEL="${3:-${OPT4D_MODEL:-/root/rivermind-data/models/Qwen3-VL-2B-Instruct}}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"; RUN_ID="dev10-proxy-ablation-$STAMP"
python scripts/run_dev10_matrix.py --benchmark "$BENCHMARK" --model "$MODEL" --run-id "$RUN_ID" --arms P0 P1 P2 --reuse-b2-from "$PARENT"
python scripts/analyze_proxy_ablation.py --run-id "$RUN_ID"
echo "PROXY_ABLATION_COMPLETE $RUN_ID"
