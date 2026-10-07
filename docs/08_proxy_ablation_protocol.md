# Proxy objective ablation protocol

Status: **developmental / prospective**. This protocol was written after observing the flow-only B4 trade-off, so it is not confirmatory evidence.

## Scientific question

Does adding independent, legal input-video constraints repair the official-metric regressions seen with flow-only CEM?

All proxy measurements must be derived from the benchmark input video. Scorer annotations, synthetic reference worlds, and official reward components are forbidden at optimization time.

## Frozen arms

- P0 / `flow`: Farneback moving-pixel flow distribution only. This reproduces the existing B4 objective.
- P1 / `flow_mask`: P0 plus deterministic temporal foreground-change occupancy.
- P2 / `flow_mask_track`: P1 plus deterministic Lucas-Kanade feature displacement distribution.

Weights are fixed at 1.0 for each enabled component for the first run. Do not tune weights after looking at individual dev10 official scores. Each run records component values, weights, CEM seed/population/iterations, code hashes, and official scorer outputs.

The candidate proxy uses projected scene anchors only. The observed proxy uses only decoded reference-video pixels. This is intentionally a cheap mechanism test, not a claim that these measurements are optimal segmentation/tracking.

## Run order

Reuse the exact frozen B2 scenes from the corrected B3/B4 parent run. Run P0, P1, and P2 separately with identical CEM population=32, iterations=8, seed=0. Do not regenerate the VLM scenes.

Expected mechanism checks:
1. P0 should reproduce the qualitative flow-only behavior.
2. P1 is useful only if silhouette/dynamic-IoU behavior improves without destroying the existing trajectory/EMD signal.
3. P2 is useful only if temporal tracking behavior improves without a major regression elsewhere.

After all arms finish, compute paired per-case deltas and Spearman association between each proxy component/total objective and available official dynamics metrics. These correlations are analysis only and must never feed back into test-time optimization.

Do not proceed to free-trajectory fitting or spline-to-physics homotopy until this proxy study has a clear keep/discard decision.
