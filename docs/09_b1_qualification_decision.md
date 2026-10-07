# B1 qualification decision

The metadata/camera-canonicalized B1 rerun improved checker success from 0/10 to 3/10, but all five real cases still failed object validation and only two cases completed scoring without scorer failures.

Decision: **do not add automatic object repair to B1**. Repairing empty object lists, duplicate names, object count, geometry, or motion would inject method structure into the direct baseline and blur the B1-vs-B2 comparison. Retain both B1 runs as developmental evidence of direct-generation reliability. B1 is not a qualified quality baseline.

For future confirmatory comparison, predeclare a direct baseline from the benchmark/community literature or a stronger model configuration rather than iteratively repairing outputs after seeing dev10 failures. The current dev10 is now development data.
