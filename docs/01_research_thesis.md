# Research Thesis: Opt4D

## Problem

4DCodeBench asks an agent to observe a dynamic-scene video and produce an executable program that reconstructs geometry, appearance, camera, and motion over time. The official benchmark separates inference from scoring and evaluates perceptual similarity, 2D dynamics, 2.5D geometry, 3D geometry, and 3D dynamics.

This repository studies a constrained setting:

- one NVIDIA GPU with roughly **22 GB VRAM**;
- **small models in the 1B–7B range**;
- no reliance on frontier-scale inference as the primary source of performance;
- use mathematical optimization and executable simulation to recover what large models would otherwise have to guess.

Primary benchmark source:
- https://github.com/4DCodeBench/4DCodeBench
- https://arxiv.org/abs/2610.03715

## Core thesis

The language/vision model should solve the **discrete** part of the inverse problem; numerical optimization should solve the **continuous** part.

Let

[
z = {	ext{object graph, primitive types, joints, motion family, solver family, contact graph}}
]

be a discrete scene-program hypothesis and let

[
	heta = {	ext{camera, dimensions, poses, velocities, angular velocities, gravity, friction, restitution, stiffness, event times, ...}}
]

be continuous parameters.

The reconstructed executable world is

[
W(z,	heta).
]

The proposed system solves

[
z^* approx q_phi(I_{1:T}), qquad
	heta^* = argmin_	heta mathcal L(I_{1:T}, W(z^*,	heta)),
]

rather than asking a small model to emit the full final Blender/simulation program in one pass.

## Why this is well matched to 4DCodeBench

The official evaluator exposes useful mathematical structure:

1. **Synthetic 3D metrics are evaluated after similarity registration.**  
   This means absolute world translation, orientation, and scale are partly gauge freedoms rather than quantities that must be guessed exactly.

2. **Real-video depth is normalized before comparison.**  
   This further reduces the need to infer a globally correct metric scale from monocular video.

3. **Dynamics metrics have explicit geometric forms.**  
   Dynamic IoU, flow-distribution comparison, Track2D DTW, trajectory DTW, and EMD-style step metrics make it possible to construct cheap proxy objectives that are aligned with the benchmark.

4. **A valid executable world is mandatory.**  
   The method must produce a reproducible `solution/build.sh` and a valid `world/`, so the optimization target cannot be a purely 2D trick.

## Research questions

### RQ1 — Small-model decomposition

How small can the learned model become when continuous inverse-graphics reasoning is outsourced to numerical optimization?

Compare approximately:

- 1B–2B class model;
- 4B class model;
- 7B class model.

The hypothesis is that the gap between 1B and 7B narrows substantially once both models operate over the same constrained scene DSL and optimizer.

### RQ2 — Gauge fixing

Does explicitly removing similarity-gauge degrees of freedom improve convergence and final benchmark performance?

Ablate:

- raw parameterization;
- center-only canonicalization;
- center + RMS-scale canonicalization;
- center + scale + canonical orientation.

### RQ3 — Homotopy system identification

Can a free trajectory fit provide a better initialization for a physical simulator than direct simulator-parameter fitting?

Proposed continuation:

[
min_X mathcal L_{	ext{obs}}(X) + lambda_s |ddot X|^2
]

followed by

[
min_{X,	heta}
mathcal L_{	ext{obs}}(X)
+
eta |X-operatorname{Sim}(	heta)|^2
+
gamma E_{	ext{phys}}(X),
]

with (eta) increased gradually.

### RQ4 — Search instead of long reasoning

For a fixed inference budget, is it better to spend compute on structured program/parameter search than on longer model reasoning traces?

Compare:

- single-shot code generation;
- repeated LLM self-reflection;
- best-of-N program hypotheses;
- bandit/successive-halving hypothesis search;
- numerical optimization under the same wall-clock envelope.

## Main method

Working name: **Opt4D**.

Pipeline:

[
	ext{video}
ightarrow
	ext{small VLM / router}
ightarrow
	ext{scene DSL}
ightarrow
	ext{parameterized executable template}
ightarrow
	ext{proxy measurement extraction}
ightarrow
	ext{numerical system identification}
ightarrow
	ext{4DCodeBench world}
]

### Small-model responsibilities

The model is allowed to decide:

- number of dominant objects;
- primitive or mesh family;
- rigid / articulated / rope / cloth / soft / granular / fluid family;
- which objects are dynamic;
- rough relative layout;
- joint/contact graph;
- which solver/template to instantiate;
- parameter bounds and priors.

### Optimizer responsibilities

The optimizer handles:

- camera focal and relative pose;
- object size and placement;
- initial linear/angular velocities;
- collision/contact timing;
- gravity scale/direction when useful;
- friction/restitution;
- low-dimensional trajectory controls;
- deformation coefficients;
- simulator parameters.

## Scope for version 1

Do **not** attempt to solve all multiphysics families immediately.

Version 1 should focus on:

1. rigid-body motion;
2. simple articulated motion;
3. a small set of primitive geometries;
4. static camera first;
5. dynamics-first optimization.

Only after this loop is stable should the project add:

- rope/cloth through spectral deformation;
- soft bodies;
- granular material;
- fluids.

## Expected contribution

A strong paper should not claim merely that "a 7B model can run 4DCodeBench." The contribution should be:

> **A discrete–continuous decomposition showing that small agents can compete in executable 4D inverse graphics when mathematical optimization absorbs continuous scene reasoning.**

The most defensible novelty is the combination of:

- benchmark-aware gauge fixing;
- low-dimensional executable scene DSL;
- proxy objectives aligned with official 4D dynamics metrics;
- homotopy from free trajectories to physical simulation;
- budgeted search suitable for a single ~22 GB GPU.

## Failure conditions

The research thesis should be rejected or substantially revised if:

- gains come only from perceptual appearance while 2D/3D dynamics do not improve;
- the optimizer uses privileged benchmark ground truth unavailable to the agent;
- the method only works by overfitting individual test videos manually;
- improvements disappear when model size is reduced;
- runtime becomes so large that the single-GPU setting is no longer credible.

## Primary success criterion

The first publishable milestone is:

> On a fixed development subset, a 1B–7B small-model + optimizer system achieves a reproducible improvement in the benchmark's dynamics metrics over the same model without optimization, while keeping executability and geometry quality intact.

