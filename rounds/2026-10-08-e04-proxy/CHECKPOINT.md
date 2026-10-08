# Research Autopilot checkpoint — 2026-10-08 E04

Status: **Web source delivered / awaiting_work_handoff / Local acceptance pending**.

Identity and role:
- Project yuhanlydia/4d, authorized source destination main.
- Web supervisor: source review, diagnostic code and handoff, no scientific execution.
- Local executor: user's computer with SSH to existing RTX 2080 Ti / ~22 GiB
  native Conda GPU host; latest host paths and harness identities must be
  restored by Local. No SSH access or live-job capability is established in this Web session.
- Research Autopilot upstream read on this round:
  a8343aeb4f51303e2eb651081d4fe51c24c5ed3f.
- Hosted ChatGPT Work task locator: **awaiting_work_handoff**. Current chat has no supported Work create/resume action; no hosted task was created or observed. This is not a Work task ID.

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
0. Open this project's one hosted ChatGPT Work goal from `rounds/2026-10-08-e04-proxy/WORK_GOAL.md`; verify its real task locator and enabled state, and keep hourly progress reporting. Reuse rather than duplicate any existing actual project/round Work task.
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

## 2026-10-08 status readback

- Source read at `main` commit `1bad4126d71fe5aaa1cb25504c3019fa79d7e522` (observed before this checkpoint-only update).
- User requested a two-day report and continuation using Research Autopilot's actual long-task mechanism.
- Prior PR #7 has already merged; E04 diagnostic source and handoff exist but Local diagnostic has no execution receipt.
- A filled hosted Web authoring goal is retained in `WORK_GOAL.md`. No supported Work launch/resume tool is exposed in this chat; user must open ChatGPT Work and start/resume that exact goal; retain real task identity before claiming activity.
- No reminder automation, local GPU job, external API service or duplicate research agent is created as a substitute.
- Next lawful action in Work: resume E04 proxy-source/semantics review and complete the Local packet; Local controller later performs native source acceptance/zero-GPU diagnostic over the admitted SSH harness under the original budget.
