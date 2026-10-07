# Opt4D Research Autopilot Program

## Goal

Improve 4DCodeBench performance under a single ~22 GB GPU using 1B–7B models plus mathematical optimization.

Primary success metrics:

1. `dynamic_iou`
2. `flow_distribution` where applicable
3. `track2d_dtw` where applicable
4. `trajectory_dtw` on synthetic cases
5. `emd_step` on synthetic cases

Secondary metrics:

- `scene_3d`
- `semantic_dinov3`
- depth error
- geometry-quality metrics
- checker/build success
- peak VRAM
- wall time

A result does **not** count as success if it improves appearance while dynamics regress, uses privileged benchmark ground truth inside the agent, or materially increases failure rate.

## Repository roles

This repository contains the research method, optimizer code, experiment configuration, and logs.

The official benchmark remains the source of truth:

https://github.com/4DCodeBench/4DCodeBench

Do not modify the official scorer to improve results.

## Editable scope

Safe to edit:

- `docs/`
- `opt4d/`
- `scripts/`
- `configs/`
- `results.tsv`
- experiment-specific job/runtime configuration stored in this repository

When an upstream 4DCodeBench checkout is used, only add wrappers/templates needed for the candidate method. Keep scorer/evaluation logic fixed.

## Non-editable evaluation scope

Treat these upstream components as fixed:

- `scorer/`
- official metric definitions
- official benchmark reference data
- privileged synthetic reference worlds
- real-video annotations not available to the benchmark agent
- checker semantics

Do not feed privileged scoring artifacts back into the agent.

## Current implementation / next milestone

Implemented and engineering-validated (native-only):

- `prepare.py` readiness checks and deterministic dev10 freeze;
- offline unit tests and CPU-only CI smoke tests;
- the `scene.json` DSL/compiler for cube/UV-sphere objects with static,
  linear-rigid, and hinge-articulated motion;
- native Blender build plus official 4DCodeBench checker and scorer on
  `synthetic/B_01`.

The frozen 10-case split is committed in `configs/dev10.txt` (5 real and 5
synthetic cases). The B_01 checker/scorer run is an engineering acceptance
result, not a method comparison or an Opt4D efficacy claim.

Research status: the first dev10 B1-B4 run and a corrected B3-B4 replay have
completed on the native GPU host. `results.tsv` records per-case outputs,
including failed and invalidated runs. These are developmental results, not
confirmatory evidence; see `docs/dev10_b1b4_20261007.md` for run IDs, validity
decisions, and the observed trade-offs.

The runner fixes each arm as follows: B1 asks the same model for the complete
scene JSON; B2 asks it only for the object DSL and fixes video/camera metadata in
the wrapper; B3 applies projection-preserving scene center/scale gauge
normalization to B2; B4 starts from B3 and fits motion parameters to optical flow
computed only from the input video. CEM and gauge smoke checks are engineering
checks, not benchmark results.

The initial fixed dev10 comparison used the same model, data, sampling, and
official scorer across arms:

1. B1: Direct generation.
2. B2: Scene DSL.
3. B3: Scene DSL + gauge fixing.
4. B4: Scene DSL + gauge fixing + CEM.

The first B3/B4 attempt used the wrong camera transform convention and is
explicitly rejected in `results.tsv`; corrected B3/B4 runs replayed the exact
B2 scenes. B1 produced no checker-valid outputs. Do not treat the initial matrix
as a clean win: first repair B1 and run a prospective, fully-valid comparison
before proceeding to free trajectories, homotopy, or multi-hypothesis/model-
scale experiments.

## Setup

### Required software

Use a **native environment only**. Docker is explicitly out of scope.

Verify:

```bash
python --version
nvidia-smi
conda --version
blender --version
ffmpeg -version
```

Before each research session, refresh the project-local Research Autopilot checkout:

```bash
bash scripts/update_research_autopilot.sh
```

Then read `.tools/research-autopilot/SKILL.md` and follow the newest applicable workflow instructions.

### Upstream benchmark preparation

From the 4DCodeBench repository:

```bash
python scripts/download_data.py --videos-only
```

Download full evaluation data/checkpoints only on the scoring machine/process when needed.

Create the official **native conda scorer environment**:

```bash
conda env create -f environment.yml
conda activate 4dcodebench
scripts/setup_env.sh
```

Do not build or invoke Docker images. The Opt4D inference path must be implemented as native Python/Blender wrappers, and official scoring should use the direct Python entrypoints from the 4DCodeBench repository.

### Readiness checks

Before an experiment:

1. GPU is visible.
2. benchmark video exists for every selected case;
3. the native Python environment imports required packages;
4. Blender CLI starts without a display;
5. a trivial legal submission passes `python -m checker`;
6. the same run can be scored through the direct scorer entrypoint and produces `results/reward.json`;
7. this repository's `results.tsv` is writable.

## Baseline commands

Opt4D inference is intentionally **native** and must not call the Docker/SIF harness. The target command is:

```bash
python run_experiment.py \
  --method direct \
  --model <model> \
  --cases configs/dev10.txt
```

Official scoring should use the 4DCodeBench direct Python entrypoints with a manifest.

First prepare reference estimates once:

```bash
roots="--manifest manifest.json --cases cases --data data --checkpoints checkpoints"
python -m scorer.prepare $roots
```

Then score candidate worlds:

```bash
python -m scorer $roots --runs runs
```

Optional visualization:

```bash
python -m visualizer $roots --runs runs
```

The project-level `evaluate.py` wrapper should construct the manifest, invoke these direct entrypoints, and parse the resulting `reward.json` files.

## Output contract

For each benchmark run, inspect:

- `runs/<kind>/<case>/<system>/<trial>/run.json`
- `runs/<kind>/<case>/<system>/<trial>/results/reward.json`
- `runs/<kind>/<case>/<system>/<trial>/results/reward.detail.json`
- `workspace/world/`
- `workspace/solution/`

Each research experiment must append one aggregate row or a clearly identified group of per-case rows to `results.tsv`.

Required stable summary fields:

- experiment id;
- git commit;
- model size/quantization;
- method switches;
- checker/build success;
- proxy loss;
- official dynamics metrics;
- peak VRAM;
- wall time;
- keep/discard decision.

The official `reward.json` is the metric source of truth.

## Development-set policy

Freeze a small development set before optimization.

Recommended first milestone:

- 10 rigid/articulated cases;
- include real and synthetic cases if practical;
- do not change the case set after seeing method failures unless the change is documented.

After the method stabilizes, expand evaluation.

## Success criteria

A focused change is **KEEP** when all conditions hold:

1. checker/build success does not regress;
2. mean available official dynamics metrics improve on the fixed development set, or are statistically indistinguishable while resource cost decreases substantially;
3. no major secondary geometry regression appears;
4. the gain is not caused by privileged evaluator information;
5. results reproduce in at least one repeated run for stochastic methods.

Tie-break order:

1. dynamics score;
2. executable success rate;
3. geometry;
4. peak VRAM;
5. wall time.

## Experiment loop

For every experiment:

1. Inspect git state and last `results.tsv` rows.
2. Make exactly one focused methodological change.
3. Run the cheapest legal proxy/smoke test.
4. If the smoke test fails, fix only obvious implementation defects.
5. Run the fixed development-set experiment.
6. Run official scoring.
7. Parse `reward.json`.
8. Append results to `results.tsv`.
9. Compare against the exact parent baseline.
10. KEEP or DISCARD.
11. Commit only reproducible kept changes; log discarded ideas as notes if informative.

## Required baseline and ablation sequence

B0 is an infrastructure-only trivial-world validation and is already separate
from the research comparison. The first research matrix is paired on the frozen
dev10 cases and must keep model, video sampling, prompts/information access,
resource limits, and official scoring fixed except for the named intervention:

1. B1 — Direct generation: same small model, without the structured DSL or
   numerical optimization.
2. B2 — Scene DSL: constrain the model output to the typed scene representation.
3. B3 — Scene DSL + gauge fixing.
4. B4 — Scene DSL + gauge fixing + CEM.

Record every case and failure in `results.tsv` and preserve raw official scorer
outputs. Do not credit later methods until B1-B4 have been compared. Then proceed
in order to free-trajectory fitting, spline-to-physics homotopy, and
multi-hypothesis/model-scale experiments.

Do not jump to fine-tuning or RL unless this sequence shows the optimization scaffold is viable.

## Proxy-objective validation

The legal optimization proxy must use only the input video and candidate reconstruction.

After runs are complete, evaluate whether proxy scores correlate with official metrics. This correlation analysis is allowed for research validation but must not leak privileged official targets into test-time optimization.

Prefer Spearman correlation between:

[
-mathcal L_{proxy}
]

and each relevant official dynamics metric.

If correlation is weak, improve measurement/proxy design before adding a more sophisticated optimizer.

## Crash handling

### Retry automatically

Retry once when failure is clearly infrastructural:

- transient native process launch failure;
- file-lock issue;
- interrupted process;
- temporary GPU allocation failure.

### Fix and rerun

Fix obvious deterministic defects:

- invalid JSON;
- checker-format mismatch;
- wrong array dtype/shape;
- missing executable bit;
- missing output directory;
- NaN caused by a clear transform bug.

### Discard

Discard the experiment if:

- the idea requires privileged ground truth;
- runtime exceeds the agreed single-GPU envelope without clear benefit;
- the optimization objective does not correlate with the target behavior;
- the method needs case-specific manual tuning;
- dynamics consistently regress.

## First research run

The first substantive run after infrastructure must compare on the same cases:

1. direct small-model baseline;
2. structured scene-DSL baseline;
3. scene DSL + gauge fixing;
4. scene DSL + gauge fixing + CEM continuous optimization.

No homotopy or deformable extension until these four rows exist.

