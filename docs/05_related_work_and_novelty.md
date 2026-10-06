# Related Work and Novelty Boundary

This note records the closest 2026 work and, importantly, what **cannot** be claimed as novel by Opt4D.

## 4DCodeBench

**Shen et al., 2026 — 4DCodeBench: Benchmarking Agents on Inverse Graphics of Dynamic Scenes**  
https://arxiv.org/abs/2610.03715

4DCodeBench defines the target problem: reconstruct a dynamic scene from video as an executable graphics program. It contains 200 scenes (100 real, 100 synthetic) and explicitly evaluates appearance, geometry, and dynamics.

The paper's central empirical finding is that strong static reconstruction does not translate into reliable complex-dynamics reconstruction.

The project page/paper also reports that pooled solutions are dominated by analytic motion rather than simulation. This supports the hypothesis that current coding agents often fit trajectories rather than identify physical mechanisms.

### Gap used by this project

4DCodeBench is primarily a benchmark. Opt4D focuses on a resource-constrained solver:

- 1B–7B models;
- one ~22 GB GPU;
- explicit mathematical system identification;
- benchmark-aligned proxy optimization;
- dynamics-first evaluation.

## LEGO-Anything

**Li et al., 2026 — LEGO-Anything: Coding Agents for 3D Scene Reconstruction**  
https://arxiv.org/abs/2609.36380

LEGO-Anything studies image-to-code static 3D scene reconstruction with iterative Blender execution and inspection. Its analysis identifies recurring failures such as weak initialization, regressive edits, and unreliable self-evaluation, and introduces a training-free harness plugin.

### Relevance

This is strong evidence that a better agent harness can improve executable inverse graphics without training a larger model.

### Difference

LEGO-Anything is primarily static 3D reconstruction from images. Opt4D targets dynamic video reconstruction and continuous physical parameter fitting.

Opt4D should emphasize **numerical self-correction**, not merely language-based render critique.

## PhysMind

**Yang et al., 2026 — PhysMind: From Video to Executable Worlds for Training-Free Physical Reasoning**  
https://arxiv.org/abs/2608.04575

PhysMind builds reusable executable worlds from video for physical reasoning and counterfactual questions. It performs training-free world construction and continuous-time dynamics fitting.

### Relevance

PhysMind demonstrates that executable-world construction can outperform direct VLM reasoning for physics.

### Difference

Its primary objective is physical reasoning/question answering, not high-fidelity 4DCodeBench reconstruction under official geometry/dynamics metrics.

Opt4D therefore must measure reconstruction quality, executable validity, and dynamics fidelity rather than QA accuracy.

## Asking the World

**Zeng et al., 2026 — Asking the World: Generalist Physical Reasoning through Agentic World Modeling and Probing**  
https://arxiv.org/abs/2609.39135

Asking the World develops a programmable Warp-based multiphysics engine and explicitly uses **CEM-based system identification** to calibrate dynamics.

### Critical novelty warning

**CEM-based system identification by itself is not a novel contribution for Opt4D.**

This directly changes our paper positioning.

The novelty must instead come from one or more of:

1. benchmark-aware gauge fixing for 4D inverse graphics;
2. proxy objectives aligned with 4DCodeBench's dynamics metrics;
3. spline-to-physics homotopy / continuation;
4. small-model discrete–continuous factorization;
5. compute-budgeted program-hypothesis search;
6. evidence that mathematical optimization closes the performance gap between 1B and 7B agents;
7. resource-constrained operation on one ~22 GB GPU.

CEM should be treated as an implementation component/baseline optimizer, not the headline idea.

## SimuScene (code generation for physical simulation)

**Wang et al., 2026 — SimuScene: Training and Benchmarking Code Generation to Simulate Physical Scenarios**  
https://arxiv.org/abs/2602.10840

This work trains language models to generate simulation code across physics domains and uses visual rewards for RL.

Reported results show that specialized training can strongly improve a 7B model's executable simulation behavior.

### Relevance

It supports the premise that 7B-class models can become substantially better at simulation code.

### Resource constraint

The reported training recipe is expensive relative to this project's one-22GB-GPU setting. Therefore Opt4D version 1 should be training-free and use optimization first.

Fine-tuning or distillation should be phase 2 only after a working optimization loop exists.

## Novelty matrix

| Capability | 4DCodeBench | LEGO-Anything | PhysMind | Asking the World | SimuScene | Opt4D target |
|---|---|---|---|---|---|---|
| Executable scene/code | yes | yes | yes | yes | yes | yes |
| Video input | yes | no / static image focus | yes | yes | textual/scene simulation focus | yes |
| 4D reconstruction metrics | yes | no | no | no | no | yes |
| Iterative harness | benchmark agent loop | yes | yes | yes | training pipeline | yes |
| System identification | agent-dependent | limited | yes | yes, CEM | not main focus | yes |
| Gauge-aware optimization | not a solver contribution | no | not the headline | not the headline | no | **target contribution** |
| Spline-to-physics homotopy | no | no | no | not identified as core method | no | **target contribution** |
| 1B–7B / ~22 GB focus | no | no | no | no | 7B training but expensive | **target contribution** |

## Strongest current paper claim

Do **not** claim:

> "We use CEM to optimize a simulator from video."

That is already too close to Asking the World.

Prefer:

> "We factor executable 4D inverse graphics into a small-model discrete program search and a gauge-fixed continuous optimization problem, then use observation-to-physics homotopy to recover dynamics under a single-GPU budget."

This claim is narrower, technically sharper, and more defensible.

## Immediate implication for experiments

The first ablation table must separate:

1. small model only;
2. small model + DSL;
3. + CEM;
4. + gauge fixing;
5. + free-trajectory initialization;
6. + homotopy.

If step 3 already gives all the gain and steps 4–6 do not help, the proposed novelty is weak and the project should pivot before large-scale evaluation.

