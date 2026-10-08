# Research Autopilot checkpoint — 2026-10-08 E04

Status at Web authoring publication: **Web source delivered / Local acceptance pending**.

Identity and role:
- Project yuhanlydia/4d, authorized source destination main.
- Web supervisor: source review, diagnostic code and handoff, no scientific execution.
- Local executor: user's computer with SSH to existing RTX 2080 Ti / ~22 GiB
  native Conda GPU host; latest host paths and harness identities must be
  restored by Local. No SSH access or live-job capability is established in this Web session.
- Research Autopilot upstream read on this round:
  a8343aeb4f51303e2eb651081d4fe51c24c5ed3f.
- Hosted ChatGPT Work task locator: **NOT ACTIVATED / UNKNOWN**.

Preserved confirmed observations:
- Native official checker/scorer completed 30/30 P0/P1/P2 arm cases as
  reported in merged PR #7; the new E04 diagnostic was not run.
- Existing input scene parent/run hashes are referenced from the retained
  native runs, not reproduced from local conversation text.
- Official reward direction corrected to higher-is-better; P1=P0, P2
  inconclusive; B1 qualification failed and must not be retroactively rescued.
- PR #7 merge commit: 4f751a618028a01ae4117998438774e5162826ee.
- Frozen dev10 exploratory status; official scorer must not be changed.

Actual source:
- scripts/diagnose_proxy_sensitivity.py
- tests/test_proxy_sensitivity.py
- docs/e04_proxy_sensitivity_20261008.md
- rounds/2026-10-08-e04-proxy/WEB_HANDOFF.md
- rounds/2026-10-08-e04-proxy/WORK_GOAL.md

Earliest pending prerequisite:
1. Local pin/readback of delivered main and native harness env.
2. Native software/semantic acceptance of diagnostic source.
3. Read-only video/scene-only per-case sensitivity/ranking packet.
4. E04 scientific review, baseline and scorer-direction audit.
5. Predeclare decision rule if pursuing a new child, with applicable
   method verification/G01 obligations. No trajectory/homotopy dispatch yet.

Unverified or blocked:
- No hosted Work task activation receipt or cloud task ID.
- No current remote SSH/job identity, tested diagnostic outputs, official
  scorer reruns, formal G01/confirmation approval or GPU budget recheck.
- Hugging Face **output** destination choice not established in this round;
  no HF push is attempted.

Publication: exact GitHub main SHA must be taken from the subsequent
GitHub delivery/readback response, not guessed inside this checkpoint.
