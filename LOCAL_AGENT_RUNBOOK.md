# Opt4D Local Agent Runbook

## Identity
Repository: yuhanlydia/4d, branch `main`. This Web delivery is **generated_unexecuted** until Local runs software/native acceptance. Research_Autopilot source is refreshed by `scripts/update_research_autopilot.sh`.

## Host/path map
Expected sibling checkout: `<workspace>/4d` and official `<workspace>/4DCodeBench`. Model defaults to `/root/rivermind-data/models/Qwen3-VL-2B-Instruct` or `$OPT4D_MODEL`. GPU target is one ~22GB device. If these paths differ, bind them explicitly with CLI flags; do not create Docker substitutes.

## Ordered acceptance
```bash
git status --short
bash scripts/update_research_autopilot.sh
python prepare.py --benchmark ../4DCodeBench --strict --require-gpu
python -m unittest discover -s tests -v
```
Acceptance requires readiness PASS and all software tests PASS. These are software checks, not scientific evidence.

## Development experiment queue

B1 requalification is closed: FAIL (3/10 checker-valid, 2/10 scorer-complete).
Do not spend additional development budget repairing duplicate names, truncation,
or inferred motion on B1. The strict parser repair is retained as software
correctness; B1 remains unqualified evidence, not a gate that must be rescued.

Dev10 has already been inspected; all runs below are developmental.

1. Proxy ablation, reusing the exact previously valid B2 parent scenes:
```bash
bash scripts/run_proxy_ablation.sh <VALID_PARENT_B2_RUN_ID> ../4DCodeBench "$OPT4D_MODEL"
```
Do not tune weights after seeing case scores. P0/P1/P2 use the same CEM population=32, iterations=8, seed=0.

2. Only after E04 gives a documented proxy KEEP/DISCARD decision, materialize trajectory/homotopy:
```bash
python scripts/materialize_trajectory_homotopy.py --benchmark ../4DCodeBench --parent-run <KEPT_PROXY_RUN_ID> --parent-arm <KEPT_ARM> --output-run <NEW_RUN_ID>
```
Each materialized scene must then go through the same `compile_solution -> build.sh -> official checker -> official scorer` path used by `scripts/run_dev10_matrix.py`. Do not select the homotopy weight by official score per case. The schedule is frozen in `configs/development_protocol_v2.json`.

## Evidence
Retain `runs/<id>/protocol.json`, every `generation.json/run.json/cem.json/trajectory.json`, build/checker/scorer logs, official `reward.json`, exact git SHA and dirty-patch hash. Append results rather than replacing failed attempts.

## Debug routing
Import/CUDA failure: inspect readiness + interpreter, repair native environment only. Validation failure: inspect raw generation and `opt4d/scene.py`; do not repair inferred semantics in B1. Checker/scorer failure: inspect official log and world artifacts; never weaken scorer. Mixed metric movement: run E04 and compare mechanism predictions before changing weights/method. OOM: record it and change resource policy only in a versioned child protocol.

## Confirmation boundary
Do not call dev10 confirmatory. After the method is frozen, create a new untouched official-case manifest by a predeclared deterministic selection rule supported by the benchmark, freeze it before scoring, and run the official scorer unchanged. Statistical analysis must be paired by `case_id`, retain all eligible cases, and use a frozen bootstrap policy.
