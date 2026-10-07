# Dev10 Proxy Ablation Results (2026-10-07)

## Scope and provenance

Developmental, paired run on the frozen 10-case dev set. This is not confirmatory evidence.

- Run: `dev10-proxy-ablation-20261007T212228Z`
- Parent B2 scenes: `dev10-b3b4-c2w-v2-20261007T172722Z`
- Run code commit: `1e2146e29d720b0bff2405bdbcf16fb98700c361`
- Benchmark commit: `aa05fb426273b59f47fac71825f77ca1b7a64c08`
- Model calls: 0; all arms reused the same 10 frozen B2 scenes
- CEM: population 32, iterations 8, seed 0; native execution, no Docker
- Host: RTX 2080 Ti, 22 GiB; completed in about 42 minutes

The runner applied the same projection-preserving gauge normalization to P0/P1/P2 as the corrected B4 parent. The main runner fix and the later analysis-path fix are recorded in PR #7. All candidate worlds passed the official checker (10/10 per arm), and all three official scorer invocations completed 10/10 without failures. The official `reward.json` files are the metric source of truth. No scorer code or reference data was changed.

## Results

Means use available official metrics. Dynamic IoU is available on 10 cases; the other listed dynamics metrics are available on the five synthetic cases.

| Arm | Dynamic IoU (n=10, higher) | Flow dist. (n=5, lower) | Track DTW (n=5, lower) | Trajectory DTW (n=5, lower) | EMD step (n=5, lower) | Scene 3D (n=5, higher) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P0 flow | 0.016129 | 0.051263 | 0.006752 | 0.118757 | 0.038248 | 0.774218 |
| P1 flow + occupancy | 0.016129 | 0.051263 | 0.006752 | 0.118757 | 0.038248 | 0.774218 |
| P2 + LK tracks | 0.016693 | 0.040725 | 0.005002 | 0.119099 | 0.039824 | 0.774218 |

Every P1-vs-P0 paired official metric delta is exactly zero on its available cases. P1 changes the recorded proxy objective, but does not change the official outcomes in this run.

Paired P2-minus-P1 deltas are mixed:

- Dynamic IoU: +0.000563 on 10 cases (6 positive, 2 negative, 2 ties).
- Flow distribution: -0.010538 on 5 cases (3 improve, 2 regress).
- Track2D DTW: -0.001750 on 5 cases (1 improves, 2 regress, 2 tie).
- Trajectory DTW: +0.000343 on 5 cases (4 regress, 1 tie).
- EMD step: +0.001576 on 5 cases (3 regress, 2 improve).
- Scene 3D is unchanged.

Exploratory Spearman values are unstable at n=5. For example, P2 total proxy objective versus track2D DTW is rho=-0.90 (n=5), opposite the desired association for two lower-is-better losses. Correlation is diagnostic only and did not enter optimization.

## Decision and limits

- P0: retain as the flow-only reference; it reproduces the corrected B4 aggregate metrics.
- P1: **DISCARD this implementation for now**. It produced no official metric change over P0. This does not rule out better occupancy measurements; first verify their sensitivity and effect on candidate ranking.
- P2: **DISCARD as the overall objective under the project success criteria**. Flow improves, but track changes are inconsistent and trajectory/EMD regress on average. Treat the tracking-specific signal as exploratory, not a win.

The split is small, several metrics are synthetic-only, and no numerical keep threshold was preregistered for this developmental child. Do not claim overall improvement or proceed to free trajectories/homotopy. Next work should diagnose proxy-component sensitivity and freeze a new decision rule before another run. Raw scenes, per-case logs, and scorer outputs remain on the experiment host; the 30 per-case summary rows are in `results.tsv`.
