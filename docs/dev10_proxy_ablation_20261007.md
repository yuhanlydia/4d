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

Means use available official metrics. Dynamic IoU is available on 10 cases; Flow and Track2D are available on five real cases; Trajectory DTW, EMD step, and Scene 3D are available on five synthetic cases. Under the pinned official scorer, all listed metrics are higher-is-better.

| Arm | Dynamic IoU (n=10, higher) | Flow dist. (n=5, higher) | Track DTW (n=5, higher) | Trajectory DTW (n=5, higher) | EMD step (n=5, higher) | Scene 3D (n=5, higher) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P0 flow | 0.016129 | 0.051263 | 0.006752 | 0.118757 | 0.038248 | 0.774218 |
| P1 flow + occupancy | 0.016129 | 0.051263 | 0.006752 | 0.118757 | 0.038248 | 0.774218 |
| P2 + LK tracks | 0.016693 | 0.040725 | 0.005002 | 0.119099 | 0.039824 | 0.774218 |

Every P1-vs-P0 paired official metric delta is exactly zero on its available cases. A post-run hash audit found nine byte-identical scene JSON pairs; the only differing file was `real/abc_130k_04_dual_arm_robot`, where one velocity component differs by only 3e-17. In that case P1 records flow=1.800475 and mask=0.170179, and its total objective is their sum, so occupancy is wired into the objective but did not materially change the selected motion or official outcome.

Paired P2-minus-P1 deltas are mixed:

- Dynamic IoU: +0.000563 on 10 cases (6 positive, 2 negative, 2 ties).
- Flow distribution: -0.010538 on 5 cases (2 improve, 3 regress).
- Track2D DTW: -0.001750 on 5 cases (2 improve, 1 regress, 2 ties).
- Trajectory DTW: +0.000343 on 5 cases (4 improve, 1 tie).
- EMD step: +0.001576 on 5 cases (3 improve, 2 regress).
- Scene 3D is unchanged.

Exploratory Spearman values are unstable at n=5. For example, P2 total proxy loss versus Track2D reward is rho=-0.90 (n=5). A negative association is directionally consistent with a lower-is-better proxy loss and higher-is-better official reward; it is not reliable evidence at this sample size. Correlation is diagnostic only and did not enter optimization.

## Decision and limits

- P0: retain as the flow-only reference; it reproduces the corrected B4 aggregate metrics.
- P1: **DISCARD this implementation for now**. It produced no official metric change over P0. This does not rule out better occupancy measurements; first verify their sensitivity and effect on candidate ranking.
- P2: **INCONCLUSIVE; no keep/discard efficacy decision**. Flow and Track2D means decline, while Trajectory DTW and EMD step means rise; Dynamic IoU rises slightly and Scene 3D is unchanged. This is a mixed profile, with small metric-specific samples and no preregistered aggregate threshold. Do not claim overall improvement or reject tracking as an idea.

The split is small, metrics apply to different subsets, and no numerical keep threshold was preregistered for this developmental child. Do not claim overall improvement or proceed to free trajectories/homotopy. Next work should diagnose proxy-component sensitivity and candidate ranking, then freeze a decision rule before another run. The committed summary does not include per-candidate population/rank traces; SSH access to the experiment host was unavailable during this audit, so no retrospective sensitivity/ranking result is claimed. No new GPU run or official scoring was started. Raw scenes and scorer outputs remain on the experiment host; the 30 per-case summary rows are in `results.tsv`.
