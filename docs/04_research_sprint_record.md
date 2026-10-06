# Research Sprint Record

This file organizes the requested **eight-hour research scope** into eight work blocks and records the concrete deliverables now stored in the repository. It is a deliverable map rather than automated wall-clock telemetry.

## Block 1 — Benchmark reverse engineering

Reviewed the official 4DCodeBench repository structure and identified:

- inference entrypoint: `harness/runtime/infer.py`;
- scoring entrypoint: `harness/runtime/score.py`;
- final metric source: `results/reward.json`;
- required executable-world format;
- checker/build gates;
- separation between agent-visible input and privileged evaluation data.

Key conclusion: the project is an executable inverse-graphics pipeline, not a standard model-training benchmark.

Deliverable:
- benchmark constraints embedded in `program.md`.

## Block 2 — Metric analysis

Mapped the official metrics relevant to a small-model optimization strategy:

- Dynamic IoU;
- flow distribution;
- Track2D DTW;
- synthetic trajectory DTW;
- EMD step;
- Scene3D;
- DINOv3 similarity;
- depth normalization and geometry-quality checks.

Key conclusion: dynamics metrics admit close legal proxy objectives derived from input video and the reconstructed world.

Deliverable:
- proxy formulation in `docs/02_math_methods.md`.

## Block 3 — Hardware-constrained research framing

Applied the single ~22 GB GPU constraint to the research design.

Key decisions:

- sequential rather than simultaneous model residency;
- 1B–2B and ~7B tracks;
- no multi-GPU prerequisite;
- low-dimensional optimizer state;
- scoring separated from agent/model inference;
- no early RL or expensive end-to-end differentiable rendering.

Deliverable:
- `docs/03_experiment_plan_22gb.md`.

## Block 4 — Discrete–continuous decomposition

Reframed the task as

[
z = 	ext{discrete scene/program structure}
]

and

[
	heta = 	ext{continuous camera/geometry/dynamics parameters}.
]

Small models solve (z); numerical optimization solves (	heta).

Key conclusion: model capacity should be spent on semantic/program decisions, not on estimating every continuous parameter through language generation.

Deliverable:
- core thesis in `docs/01_research_thesis.md`.

## Block 5 — Mathematical optimization design

Developed the first optimization stack:

- similarity-gauge fixing;
- soft mask IoU;
- sliced-Wasserstein motion loss;
- track/DTW loss;
- B-spline free trajectories;
- physical residuals;
- CEM/CMA-ES style black-box parameter fitting;
- block-coordinate optimization;
- multi-fidelity candidate evaluation.

Deliverable:
- `docs/02_math_methods.md`.

## Block 6 — Homotopy research idea

Developed the main paper-level idea:

> fit an observation-aligned free trajectory first, then gradually project it toward an executable physical simulator.

Objective:

[
mathcal J(X,	heta;eta)
=
mathcal L_{obs}(X)
+
eta D(X,operatorname{Sim}(	heta))
+
gamma E_{phys}(X).
]

Increase (eta) gradually to avoid poor direct simulator initialization.

Key contribution candidate:
- **Spline-to-Physics Homotopy System Identification**.

Deliverable:
- homotopy section in `docs/02_math_methods.md`.

## Block 7 — Experiment and ablation design

Designed staged experiments:

- direct model baseline;
- DSL baseline;
- gauge-fixing ablation;
- CEM continuous optimization;
- free trajectory;
- homotopy;
- multi-hypothesis search;
- model-scale sweep;
- later spectral rope/cloth extension.

Also defined:

- official primary metrics;
- efficiency metrics;
- paired per-case statistics;
- proxy-vs-official correlation validation.

Deliverables:
- `docs/03_experiment_plan_22gb.md`;
- `results.tsv`.

## Block 8 — Research-autopilot execution contract

Converted the research direction into an autonomous experimental loop with:

- editable/non-editable scope;
- setup checks;
- official baseline commands;
- output contract;
- keep/discard rules;
- crash policy;
- baseline-first requirement;
- ordered ablation sequence.

Deliverable:
- `program.md`.

## Current recommended paper direction

Working title:

**Opt4D: Optimization-Augmented Small Agents for Executable 4D Inverse Graphics**

Stronger method-oriented alternative:

**From Trajectory Fitting to Physical Programs: Homotopy System Identification for Small 4D Coding Agents**

## Next implementation milestone

The native engineering loop is now closed on one synthetic case:

1. freeze the audited `configs/dev10.txt` split;
2. run `prepare.py --strict --require-gpu`;
3. compile and render a native Blender workspace;
4. pass the official checker;
5. pass the official geometry/dynamics scorer;
6. record the result without treating it as a method comparison.

The next research step is the fixed dev10 baseline and ablation matrix. Do not
start broad sweeps or fine-tuning before those rows have reproducible outputs.

