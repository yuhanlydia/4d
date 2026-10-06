# Native Opt4D bootstrap (no Docker)

This document describes the actual first milestone. It **does not** claim that
the 4DCodeBench scoring campaign or small-model inference has run.

## Repositories

Use adjacent checkouts:

```text
work/
├── 4d/           # this research repository
└── 4DCodeBench/  # unmodified official benchmark
```

## Install / refresh the latest Research Autopilot skill

Run from the `4d` checkout:

```bash
bash scripts/update_research_autopilot.sh
cat .tools/research-autopilot/SKILL.md
git -C .tools/research-autopilot rev-parse HEAD
```

The updater tracks upstream `main`; record the displayed SHA in experiment
notes. Updating or reading this local skill does not mean it is automatically
activated inside every agent framework: the running research agent must read
and apply `SKILL.md`.

The most recently verified upstream commit as of 2026-10-06 is
`ad24d74bce450afb58c6b2eb898651d747f7b5a5`. This reference is
informational only: the updater must check for newer commits.

## Native environment preparation

A supported setup path is Miniconda/Mamba, not containers.

From the benchmark checkout:

```bash
conda env create -f environment.yml
conda activate 4dcodebench
scripts/setup_env.sh
```

The official environment is documented for **direct scorer invocation**. The
small-model agent runner, Opt4D DSL compiler and model service do not exist
yet and must not be confused with the official container harness.

Check binaries in the active environment:

```bash
python --version
blender --version
ffmpeg -version
ffprobe -version
nvidia-smi
```

Download reference videos using the upstream script:

```bash
cd ../4DCodeBench
python scripts/download_data.py --videos-only
cd ../4d
```

Do not give the inference agent access to `data/` from the official benchmark,
which contains privileged scoring information.

## First milestone: readiness and fixed case selection

Run:

```bash
python prepare.py --benchmark ../4DCodeBench \
    --json .local/readiness.json
```

The command prints an `OPT4D_PREPARE {...}` machine-readable status. Readiness
may be false until all prerequisite tools and videos exist. Without
`--strict`, this is diagnostic and exits zero even if the environment is not
ready.

After at least 5 **downloaded reference videos of each kind** exist, freeze the
development split:

```bash
python prepare.py --benchmark ../4DCodeBench --freeze-cases
```

This writes `configs/dev10.txt` once, with 5 real and 5 synthetic IDs
chosen by a stable hash rank from the locally present cases.

**Important:** for cross-machine comparability, first download the full set of
reference videos. A split chosen from a partial download is deterministic but
will not necessarily match a split chosen after the remaining videos arrive.

Commit and review `configs/dev10.txt` before any score-guided optimization.
The script refuses to overwrite an existing split. Re-run readiness with
strict gates:

```bash
python prepare.py --benchmark ../4DCodeBench \
    --strict --require-gpu --min-vram-gb 20 \
    --json .local/readiness.json
```

A `--strict` success verifies **core binary, GPU and case-list readiness**,
not that the official scorer has successfully produced a benchmark score.
The milestone to prove a legal world and official score remains separate.

## Offline tests

Before using a real GPU:

```bash
python -m unittest discover -s tests -v
python scripts/toy_optimize.py
```

The tests use dummy videos created in a temporary directory. They do not
perform official 4DCodeBench inference or scoring.

## What must happen next

The next milestone is implementing a real
`scene.json -> solution/build.sh -> world/` compiler that can create a
legal rigid-body reconstruction. After that, run the **official**
`python -m checker` on a generated `world/`, then implement native
`run_experiment.py` and direct official scoring.

Do not claim any results from `results.tsv` until the actual official
`reward.json` files have been produced and parsed.

## Known constraints

- The current chat environment has no authenticated SSH session to your GPU,
  so GPU tests and native scoring cannot be verified from here.
- `bpy`, Warp and Taichi availability depends on the native Python
  environment. The presence of Blender CLI alone does not imply `bpy`
  is importable from the selected Python.
- The official scorer loads neural checkpoints; capacity and runtime must
  be tested on the actual single ~22 GB GPU.
