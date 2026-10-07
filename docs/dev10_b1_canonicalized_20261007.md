# B1 Metadata/Camera-Canonicalized Rerun (2026-10-07)

## Protocol

This was a B1-only developmental rerun on the frozen 10-case split, using
Qwen3-VL-2B-Instruct and the official native 4DCodeBench checker/scorer. The
runner used `--arms B1`; B2-B4 were not rerun. Code revision:
`30f3144842efe19b5749608d751328173e30b6ea`. Run ID:
`dev10-b1-canonicalized-20261007T183007Z`.

The wrapper canonicalized `schema_version`, source-video metadata, and the
fixed camera; it did not repair or alter `objects`, geometry, or motion. One
protocol caveat: the prompt required a `schema_version` field but did not state
its exact value, while the wrapper sets it to `1`. Accordingly, this is best
described as metadata/camera-canonicalized B1, not strictly prompt-value-only
canonicalization.

## Outcome

- 3/10 scenes passed local validation and the official checker: synthetic
  `B_01`, `B_02`, and `B_05`.
- 0/5 real cases passed. Four complete responses failed on duplicate object
  names. The fifth real response (`abc_130k_02_robot_arm_uses`) and synthetic
  `B_03`/`B_04` hit the 1200-token generation ceiling and ended mid-JSON.
- Correction from raw-output inspection: the three resulting `objects must be a
  non-empty list` errors were parser misdiagnoses. The old fallback scanned into
  the truncated root and accepted a nested `video` object as the scene root.
  These were not empty model-produced object lists.
- The official scorer exited with code 1; 2/10 cases completed without scorer
  failures. `B_02` passed checker but several scorer metrics failed because no
  visible-camera or dynamic-mesh registration candidate was found.
- `B_01` and `B_05` had `dynamic_iou=0.0` and `trajectory_dtw=0.0`; `emd_step`
  was uncomputable. Do not interpret these as a positive dynamics result.

The previous B1 0/10 rows remain unchanged. The new rows are appended to
`results.tsv` with `keep=pending`. The checker improvement from 0/10 to 3/10
shows that metadata/camera canonicalization removed some interface failures,
but object-structure failures remain and the baseline is not yet qualified for
a reliable B1-vs-B2 quality comparison. No numeric qualification threshold
was predeclared, so this note makes no threshold-based qualification claim.

Raw generations, worlds, scorer logs, and model files remain on the experiment
host and are not included in this repository update. The parser bug is fixed in
PR #6; the 1200-token outputs remain preserved as evidence.

