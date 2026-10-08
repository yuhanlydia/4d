# E04 proxy-component sensitivity and candidate-ranking diagnosis

Status: **generated_unexecuted** source-only diagnostic, not a method revision,
not a new benchmark score and not a completed E04 verdict.

## Frozen lineage and observed evidence

- Project: yuhanlydia/4d, official 4DCodeBench pinned at
  aa05fb426273b59f47fac71825f77ca1b7a64c08.
- Developmental sample manifest: configs/dev10.txt, five real and five synthetic.
- Completed experiment: dev10-proxy-ablation-20261007T212228Z.
- Parent model scenes: dev10-b3b4-c2w-v2-20261007T172722Z.
- P0/P1/P2 model calls: zero; CEM population 32, iterations 8, seed zero.
- Native experimental evidence: 30/30 checker-valid and 30/30 scorer-complete.
- P1 and P0 have identical official scores. P2 is **INCONCLUSIVE**.
- Official reward direction is higher-is-better for all six reported motion/scene
  columns. Flow and Track2D apply only to five real cases; 3D trajectory, EMD
  and scene_3d only to five synthetic; Dynamic IoU applies to all ten.
- Full case-level raw scene/video/scorer artifacts are resident on the native
  experiment host, not presumed uploaded to GitHub.

## E04 question, mechanism and falsifier

1. **Occupancy flatness hypothesis.** The current candidate mask is the area
   covered by radius-4 circles centered on 7 projected primitive anchors,
   averaged over the sampled timeline, rather than dynamic foreground overlap.
   Translating these anchors can leave their total occupied pixel count constant.
   Prediction: P1's mask component will be constant or nearly so across multiple
   physically distinct local motion perturbations, causing P1/P0 rankings to
   agree. Falsifier: substantial mask-component range and changed candidate
   order over the same frozen perturbations.
2. **Track identity-alignment hypothesis.** Current predicted track vectors
   equal projected anchor displacement vectors. The observed LK track vectors
   are compared as an unordered sliced-Wasserstein distribution. No query-point
   or rigid-object identity is matched, unlike the official Track2D metric.
   Prediction: adding this distribution objective will reorder some candidates
   without reliably improving identity-preserving official track scores.
   Falsifier: an independently established correspondence-aware association,
   not just a favorable five-case correlation.
3. **Model/measurement mismatch alternative.** Discrepancy could arise from
   sparse anchors, sampling, visibility, static-to-linear promotion or proxy
   scale, rather than CEM search quality itself. No one mechanism is established
   merely by a flat/bad score.

## Frozen candidate audit (no new solver, scorer or tuning)

Program: scripts/diagnose_proxy_sensitivity.py

- Input: exactly the ten P0 result scenes from the completed run plus ten
  corresponding input reference.mp4 files.
- For each case: retain the actual P0 scene as candidate 0, enumerate model
  motion parameters in stable object-index/axis order; take at most 12.
- Perturb each selected linear velocity component or hinge angle_end by exactly
  -1.0, -0.25, +0.25, +1.0 in its native parameter units. If no existing motion
  parameter exists, use the old optimizer's static-to-linear promotion rule.
- Max candidates per case: 49. No choice based on official rewards.
- For every candidate, compute input-video-only flow/mask/track proxy components
  and the existing frozen P0, P1 and P2 combined objectives.
- Save per-component min/max/range/std/flat flag and the objective-specific
  argmin/rank agreement, plus candidate data, hashes and provenance.
- Flat tolerance 1e-12 is a **numerical diagnostic**, not an efficacy or method
  qualification threshold.
- No official checker, scorer, benchmark hidden world, annotations, reward.json
  or score-dependent optimizer tuning enters this script.

### Local command (inside the admitted native harness task)

    python scripts/diagnose_proxy_sensitivity.py \
      --benchmark ../4DCodeBench \
      --source-run dev10-proxy-ablation-20261007T212228Z \
      --source-arm P0 \
      --cases configs/dev10.txt \
      --max-parameters 12 \
      --out runs/e04-proxy-sensitivity-20261008.json

The Local controller must first validate its actual repo/SSH alias, native
harness task runner, Conda, paths and GPU-host resources; do not invent a
remote harness command or execute outside its admitted task. This diagnostic
does not request a GPU reservation by design.

## Acceptance and return

Run existing CPU-only unit tests, review source semantics, and execute the
diagnostic on actual native case videos/scenes. Verify that 10 case IDs,
50 or fewer candidates per case, all required hashes and every three-component
loss are present and finite. Keep stdout/stderr, task identity and exact commit.
Do not overwrite a prior output and never alter official scorer files.

Interpret zero variation as local sensitivity failure only; it cannot certify
the corresponding method as globally ineffective. If runs lack candidate
population traces, label all retrospective optimizer-convergence claims
**unavailable**, rather than reconstructing invented traces.

Then deliver an E04 packet: exact native task receipts; all 10 per-case
component ranges and argmins; competing mechanism hypotheses; applicable
metric direction/denominator checks; existing P0/P1/P2 official-scored
results; unresolved questions and a proposed predeclared next child rule.
Do **not** start T0/H0, modify P1/P2 weights or dispatch new scorer jobs from
this packet alone. A new scientific-method design follows current method
verification and G01/parent gates.
