# WEB_HANDOFF — formal Opt4D developmental experiments

Status: **generated_unexecuted**.

## Current evidence
B1 direct generation failed its predeclared operational requalification (3/10 checker-valid; 2/10 scorer-complete). The strict top-level parser fix correctly distinguishes genuine token truncation from malformed/nested recovery. B1 is closed as an unqualified developmental baseline and must not be post-hoc repaired on dev10. B2 established a valid structured DSL path. Corrected B3 showed projection-preserving gauge behavior. Flow-only B4 improved some motion proxies/metrics while worsening others, motivating a prospective developmental proxy decomposition.

## Frozen next decisions
A. Run P0/P1/P2 exactly as `docs/08_proxy_ablation_protocol.md` and `configs/development_protocol_v2.json`.
B. Perform E04. Keep a proxy only if its predicted mechanism improves without unacceptable cross-metric regression; retain negative arms.
C. Only then run T0/H0 using the kept parent. The homotopy schedule is fixed at [0,.25,.5,.75,1].
D. Dev10 remains development-only. A future confirmation requires an untouched official manifest frozen after method selection and before scoring.

## Code map
- video measurements/CEM: `opt4d/video_proxy.py`
- free trajectory/homotopy: `opt4d/trajectory.py`
- native compiler: `opt4d/scene.py`, `opt4d/blender_runtime.py`
- dev matrix: `scripts/run_dev10_matrix.py`
- proxy entry: `scripts/run_proxy_ablation.sh`
- trajectory materializer: `scripts/materialize_trajectory_homotopy.py`
- statistics: `compare.py`
- ledger: `results.tsv`

No scientific execution has been performed for the newly delivered P1/P2/T0/H0 code at this Web revision.
