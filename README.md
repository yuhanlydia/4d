# Opt4D — Small-Model 4D Inverse Graphics Research

Research workspace for improving **4DCodeBench** under a single ~22 GB GPU budget, with emphasis on **1B–7B models plus mathematical optimization** rather than frontier-scale agents.

## Working thesis

> Use a small model for discrete scene/program decisions, and numerical optimization for continuous inverse-graphics and dynamics parameters.

The current paper direction is:

**Opt4D: Optimization-Augmented Small Agents for Executable 4D Inverse Graphics**

with a stronger method candidate:

**From Trajectory Fitting to Physical Programs: Homotopy System Identification for Small 4D Coding Agents**

## Repository map

- [Research thesis](docs/01_research_thesis.md)
- [Mathematical methods](docs/02_math_methods.md)
- [Single-22GB-GPU experiment plan](docs/03_experiment_plan_22gb.md)
- [Research sprint record](docs/04_research_sprint_record.md)
- [Related work and novelty boundary](docs/05_related_work_and_novelty.md)
- [Research-autopilot execution contract](program.md)
- [Experiment result schema](results.tsv)
- [Full-covariance CEM prototype](opt4d/cem.py)
- [Proxy losses](opt4d/losses.py)
- [Native pipeline entrypoints](prepare.py)

## First engineering milestone

1. Run `python prepare.py --benchmark ../4DCodeBench --strict --require-gpu`.
2. Run `python -m unittest discover -s tests -v`.
3. Compile a legal `scene.json` and run its native `build.sh`.
4. Run the official 4DCodeBench checker on the generated workspace.
5. Run the official scorer on the fixed `configs/dev10.txt` split.
6. Only after this closed loop passes, start the direct, DSL, gauge, CEM, and homotopy ablations.

## Important novelty boundary

CEM-based physical system identification already appears in **Asking the World (2026)**. CEM is therefore an optimizer component/baseline here, not the novelty claim.

The strongest current novelty candidates are:

- benchmark-aware gauge fixing;
- 4DCodeBench-aligned legal proxy objectives;
- spline-to-physics homotopy;
- small-model discrete–continuous factorization;
- evidence that optimization narrows the 1B vs 7B performance gap under a single-GPU budget.

## Upstream benchmark

- https://github.com/4DCodeBench/4DCodeBench
- https://arxiv.org/abs/2610.03715


## Native-only preparation (implemented)

**No Docker** is used by Opt4D. The current implementation includes a native
readiness checker, deterministic dev10 case-freezing, offline tests and a
CPU-only CI smoke test. See [SSH/native setup instructions](docs/06_native_bootstrap.md).

```bash
bash scripts/update_research_autopilot.sh
python prepare.py --benchmark ../4DCodeBench --json .local/readiness.json
# Only after downloading reference videos from the complete dataset:
python prepare.py --benchmark ../4DCodeBench --freeze-cases
python prepare.py --benchmark ../4DCodeBench --strict --require-gpu
python -m unittest discover -s tests -v
python compile_scene.py <scene.json> <run>/solution
bash <run>/solution/build.sh
# Then run the official checker and scorer from 4DCodeBench.
```

**Readiness is not a method comparison.** The native compiler, Blender runtime,
official checker, and official scorer have now passed an engineering validation
on `synthetic/B_01`; the recorded scores are not an Opt4D ablation claim. The
`configs/dev10.txt` split is frozen and portable, and the next experiment is
the fixed dev10 baseline/ablation matrix.


## Current E04 continuation (2026-10-08)

Proxy P0/P1/P2 completed 30/30 native checker and scorer evaluations. P1 ties P0 and P2 remains inconclusive under the pinned scorer's higher-is-better reward convention. The next legitimate step is a video-only [proxy sensitivity diagnosis](docs/e04_proxy_sensitivity_20261008.md) of existing candidate motion, **not** another method/scorer run. Read the [current round handoff](rounds/2026-10-08-e04-proxy/WEB_HANDOFF.md), [checkpoint](rounds/2026-10-08-e04-proxy/CHECKPOINT.md) and [hosted Work goal](rounds/2026-10-08-e04-proxy/WORK_GOAL.md); the hosted goal has **not** been activated in this Web chat. Local GPU execution and newly generated diagnostic software tests are pending.
