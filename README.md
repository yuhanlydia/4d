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
- [Toy system-identification smoke test](scripts/toy_optimize.py)

## First engineering milestone

1. Run `python scripts/toy_optimize.py`.
2. Define a small `scene.json` DSL.
3. Compile one rigid-body template.
4. Build legal observation-only proxy measurements.
5. Run direct-small-model vs DSL vs CEM vs gauge-fixed CEM on 10 fixed cases.
6. Only then add spline-to-physics homotopy.

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
python scripts/toy_optimize.py
```

**Readiness is not a benchmark result.** The scene compiler, model integration,
and official evaluation wrapper are next milestones. No 4DCodeBench gain has
been measured yet. The `configs/dev10.txt` split is generated on the target
machine once the reference videos are available; no case IDs are fabricated.

