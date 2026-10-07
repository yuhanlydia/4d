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

B1 qualifies as an operational dev10 baseline only if at least 8 of 10 cases
complete the full local-validation, build, official-checker, and applicable
official-scoring path, with at least 4 of 5 real and 4 of 5 synthetic cases
completing. Cases with missing applicable official metrics, malformed output,
checker failure, or scorer failure count as incomplete. Missing scores are not
dropped from the denominator. This criterion is fixed before the rerun; it says
nothing about whether B1 has good reconstruction quality.

## Debugging boundaries

- Do not repair inferred object identities, geometry, positions, or motion.
- Preserve each raw generation, checker log, official reward file, and failure.
- A response that hits the token ceiling is a generation/truncation failure, not
  an empty-object model prediction.
- Repair only deterministic pipeline defects demonstrated by raw evidence.
- This B1-only run does not authorize starting the deferred follow-on ideas.

