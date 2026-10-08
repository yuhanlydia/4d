# Web handoff — 2026-10-08 E04 proxy audit

Status: generated_unexecuted diagnostic source; no additional native run, no scientific gate passed.

## Upstream evidence and frozen decision

- Project: yuhanlydia/4d, target main; official 4DCodeBench pinned
  aa05fb426273b59f47fac71825f77ca1b7a64c08.
- Current Research_Autopilot upstream observed: a8343aeb4f51303e2eb651081d4fe51c24c5ed3f.
- Prior completed run: dev10-proxy-ablation-20261007T212228Z,
  run source 1e2146e29d720b0bff2405bdbcf16fb98700c361.
- Native results: P0/P1/P2 each 10/10 official checker/scorer successful,
  dev10 development-only, parent B2 scenes reused, no new model calls.
- Corrected official metric direction: six reported rewards are higher-is-better.
- P0 retained as reference, P1 current occupancy implementation without observed
  benefit, P2 INCONCLUSIVE. B1 operational qualification FAILED.
- The prior PR #7 is merged to main (merge 4f751a618028a01ae4117998438774e5162826ee).
- No confirmatory claim, no T0/H0 dispatch authorization.

## Earliest pending E04 prerequisite

Find whether occupancy and distribution-only LK tracking affect candidate motion
ranking under fixed perturbations. Document numerical/semantic sensitivity,
denominators, scorer parity and optimizer-convergence gaps; do not revise the method
until these mechanism checks and a predeclared decision rule are reviewed.

The exact diagnostic/falsifiers are in docs/e04_proxy_sensitivity_20261008.md.
Implementation: scripts/diagnose_proxy_sensitivity.py.
Software contract tests: tests/test_proxy_sensitivity.py.
No official reward/scorer path is used by the new script.

## Local acceptance and diagnostic

On the actual user-computer Local controller, use SSH and the installed
Research_Autopilot native harness to select the separate Conda host. Restore the
host alias, controller project root, real harness CLI and existing job identity
before dispatch. Existing raw source run artifacts must be present.

Review the source, stage the pinned revision and submit an admitted zero-GPU task
whose inner command is:

    python scripts/diagnose_proxy_sensitivity.py \
      --benchmark ../4DCodeBench \
      --source-run dev10-proxy-ablation-20261007T212228Z \
      --cases configs/dev10.txt \
      --out runs/e04-proxy-sensitivity-20261008.json

The task must first pass the existing native software tests, retain stdout/stderr
and all 10 case/video/scene SHA-256 hashes, output status and exact task identity.
Verify no illegal scorer reads and no hidden-reference-data access.
Do not overwrite existing outputs or rerun P0/P1/P2 before necessity is established.

## Return and next gate

Return the exact executed commit, harness attempt receipts, all ten component
ranges/rankings, implementation validation, failure status and an E04 review packet
to the existing GitHub repo. Missing native setup/path identities are unresolved,
not silently inferred. New method/trajectory/homotopy code requires an independent
method/design decision, not merely this handoff.
