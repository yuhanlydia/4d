# B1 Requalification Protocol (2026-10-07)

## Purpose

This is a prospective operational qualification of B1, not a B1-vs-B2 efficacy
comparison. Prior B1 rows and raw outputs remain unchanged. The prompt, model,
frozen dev10 cases, native compiler, official checker, and official scorer remain
fixed. The parser fix rejects truncated top-level JSON instead of salvaging a
nested object. The generation ceiling is raised from 1200 to 2400 tokens to avoid
the already observed truncation; this budget change means the run cannot be used
as a paired B1-vs-B2 comparison.

## Qualification criterion

B1 qualifies as a complete operational dev10 baseline only if all 10 cases
complete local validation, build, official checking, and applicable official
scoring, with all applicable primary metrics present for every case. A low or
zero valid score is still a completed measurement. Missing applicable metrics,
malformed output, checker failure, or scorer failure means the criterion is not
met; no case is dropped from the denominator. This criterion is fixed before
the rerun and is about full-split measurability, not reconstruction quality.

## Debugging boundaries

- Do not repair inferred object identities, geometry, positions, or motion.
- Preserve each raw generation, checker log, official reward file, and failure.
- A response that hits the token ceiling is a generation/truncation failure, not
  an empty-object model prediction.
- Repair only deterministic pipeline defects demonstrated by raw evidence.
- This B1-only run does not authorize starting the deferred follow-on ideas.

