# Single-22GB-GPU Experiment Plan

## Hardware constraint

Target environment:

- one NVIDIA GPU;
- approximately **22 GB VRAM**;
- no multi-GPU training requirement;
- experiments must be resumable and cheap enough to iterate frequently.

This constraint is part of the research claim, not an inconvenience to hide.

## Model strategy

The system should avoid keeping a large VLM, coder, Blender, and scoring models resident simultaneously.

Use **sequential model residency**:

1. load the small VLM/router;
2. inspect the video and emit `scene.json`;
3. unload it and clear CUDA memory;
4. load a small code model if code/template repair is required;
5. unload it;
6. run numerical optimization/simulation;
7. use official scoring separately.

### Model-size tracks

Run at least two tracks:

- **Tiny track:** approximately 1B–2B parameters;
- **Small track:** approximately 7B parameters.

Optional middle point:

- 3B–4B vision-language model.

Use quantization when required. The paper should report:

- parameter count;
- quantization;
- peak VRAM;
- inference wall time;
- optimizer wall time;
- total wall time;
- number of model calls;
- number of simulator/proxy evaluations.

The key claim is not that a specific model is best; it is that the **mathematical scaffold reduces dependence on model scale**.

## Initial benchmark slice

Do not start with all 200 scenes.

Build a development subset of roughly 12–24 cases with these properties:

- rigid translation/rotation;
- one or more collisions;
- simple articulated motion;
- varying camera perspective;
- both real and synthetic cases if practical.

Freeze this development set before tuning.

After method choices are frozen, expand to a larger held-out set.

## Experiment ladder

### E0 — validity baseline

Goal: ensure the pipeline can produce legal submissions.

For each case:

1. generate a trivial scene;
2. run `solution/build.sh`;
3. run `python -m checker`;
4. ensure video/world gates pass;
5. record official reward output.

No research claim is valid before this baseline is stable.

### E1 — small model direct generation

The 1B/7B model sees the video and task description and generates the scene program directly.

Purpose:

- quantify how weak the direct baseline actually is;
- measure failure types;
- create a fair baseline for the optimizer.

Log:

- build success;
- checker success;
- official metrics;
- token count;
- wall time.

### E2 — constrained scene DSL

The model outputs only structured `scene.json`, compiled with fixed templates.

Compare to E1.

Expected effect:

- higher build success;
- fewer syntax/API failures;
- reduced variance.

### E3 — gauge fixing

Add canonical center/scale/orientation.

Compare:

- no gauge fix;
- center;
- center + scale;
- center + scale + orientation.

Primary metric:

- optimizer evaluations required to reach a target proxy loss;
- final official dynamics score.

### E4 — continuous parameter optimization

Optimize:

- camera focal;
- object dimensions;
- relative positions;
- initial velocities;
- angular velocities;
- gravity scale;
- friction;
- restitution;
- collision/event times.

Start with CEM.

Ablate optimizer:

- random search;
- coordinate descent;
- CEM;
- CMA-ES if available.

### E5 — free trajectory

Add B-spline rigid trajectories.

Compare:

- direct physics fit;
- free trajectory only;
- free trajectory initialized physics fit.

### E6 — homotopy

Apply increasing simulator-consistency weight (eta).

Ablate schedules:

- direct (eta=1);
- linear;
- geometric;
- adaptive based on observation loss plateau.

### E7 — multi-hypothesis search

Request K scene hypotheses from the model.

Compare:

- K=1;
- best-of-4;
- successive halving over 4 or 8 hypotheses.

Keep total wall-clock or total evaluation budget approximately matched.

### E8 — model scaling

Freeze the algorithm and evaluate:

- 1B–2B;
- ~4B if available;
- ~7B.

The key analysis is the interaction:

[
	ext{model size}
	imes
	ext{optimizer scaffold}.
]

We want to show that optimization narrows the scale gap.

## Metrics

### Primary

From official `reward.json`:

- `dynamic_iou`;
- `flow_distribution` where applicable;
- `track2d_dtw` where applicable;
- `trajectory_dtw` on synthetic scenes;
- `emd_step` on synthetic scenes.

### Secondary

- `semantic_dinov3`;
- `scene_3d`;
- depth error;
- geometry-quality metrics;
- executable/checker success rate.

### Efficiency

- peak VRAM;
- total GPU-seconds;
- optimizer evaluations;
- Blender renders;
- model tokens;
- end-to-end wall time.

## Proxy-vs-official validation

The optimizer cannot use privileged official reference-world information.

However, during method development we can evaluate correlation between our legal proxy and official scores after a run.

For candidates (j), compute Spearman correlation

[
ho(
-mathcal L_{	ext{proxy}}^{(j)},
S_{	ext{official}}^{(j)}
).
]

If the proxy is poorly correlated, improve the proxy before increasing optimizer complexity.

This is a crucial early experiment.

## Statistics

Per-case paired comparison is preferred.

For a method A and baseline B:

[
Delta_i = S_i^A-S_i^B.
]

Report:

- mean/median (Delta);
- bootstrap 95% confidence interval;
- win/tie/loss count;
- paired permutation or Wilcoxon signed-rank test where appropriate.

Do not rely only on one aggregate benchmark number.

## Practical VRAM policy

### During model inference

- quantize where needed;
- avoid loading scorer networks;
- use sparse sampled video frames initially;
- keep batch size 1;
- unload model before optimization.

### During optimization

The state should be low-dimensional. GPU memory should mostly hold:

- primitive geometry;
- a few hundred/thousand projected points;
- low-resolution masks;
- candidate populations;
- optional simulator state.

This should leave significant VRAM headroom.

### During official scoring

Run scoring as a separate stage so optimizer/model memory does not coexist with evaluator models.

## First 10-case milestone

Before adding cloth, fluids, RL, or fine-tuning, hit this milestone:

- 10 fixed rigid/articulated cases;
- all submissions pass checker;
- optimizer runs automatically;
- structured `results.tsv`;
- at least one legal proxy significantly correlates with one official dynamics metric;
- small-model + optimizer beats the same small-model direct-generation baseline.

If this fails, do not add more model training. Fix the inverse problem formulation first.

## What not to do initially

Avoid:

- full-model fine-tuning before proving the optimization loop;
- RL on expensive Blender reward;
- end-to-end differentiable rendering of the entire benchmark;
- full cloth/fluid support;
- optimizing hundreds of arbitrary Blender parameters;
- using benchmark ground-truth world data inside the agent;
- spending most compute on long chain-of-thought generation.

