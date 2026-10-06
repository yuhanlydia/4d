# Mathematical Methods

This document defines the mathematical core of Opt4D.

## 1. Discrete–continuous factorization

Let the input video be

[
I = {I_t}_{t=1}^{T}.
]

A small model predicts a discrete hypothesis

[
z sim q_phi(z mid I)
]

containing object count, primitive families, dynamic/static labels, solver family, and contact/joint topology.

Given (z), a deterministic compiler creates a parameterized executable world

[
W(z,	heta).
]

Optimization solves

[
	heta^*
=
argmin_{	heta in Theta(z)}
mathcal L_{	ext{proxy}}(I,W(z,	heta)).
]

The final deliverable is rebuilt from (z,	heta^*), not from copied video pixels.

---

## 2. Gauge fixing

Monocular inverse graphics has redundant coordinate freedoms. Because the synthetic scorer performs similarity registration, optimize in a canonical frame.

For dynamic points (X_0 in mathbb R^{N	imes 3}), impose

[
rac{1}{N}sum_i X_{0,i}=0,
]

and

[
sqrt{rac1Nsum_i|X_{0,i}|^2}=1.
]

Optionally orient the dominant ground plane to (z=0) and align its normal with (+hat z).

Instead of optimizing unconstrained scale (s>0), parameterize

[
s=exp(alpha)
]

only when the downstream build actually needs a metric scale.

For rotations, prefer Lie-algebra or quaternion parameterizations rather than unconstrained matrices.

### Hypothesis

Gauge fixing should:

- reduce flat directions;
- improve black-box optimizer sample efficiency;
- reduce camera/object scale coupling;
- make 1B/7B initialization errors less harmful.

---

## 3. Observation-space proxy objective

The optimizer must use only signals derivable from the input video and its own reconstruction.

Define:

- (M_t^{obs}): observed dynamic mask;
- (U_t^{obs}): observed 2D motion/flow sample set;
- (P_{i,t}^{obs}): observed feature tracks;
- (hat M_t(	heta), hat U_t(	heta), hat P_{i,t}(	heta)): reconstruction-side counterparts.

Use

[
mathcal L_{	ext{dyn}}
=
lambda_M mathcal L_{	ext{mask}}
+
lambda_F mathcal L_{	ext{flow}}
+
lambda_T mathcal L_{	ext{track}}.
]

### 3.1 Soft mask loss

A differentiable approximation is

[
operatorname{softIoU}(M,hat M)
=
rac{sum_p M_phat M_p+epsilon}
{sum_p M_p+sum_p hat M_p-sum_p M_phat M_p+epsilon}.
]

Then

[
mathcal L_{	ext{mask}}
=
1-
rac1Tsum_t
operatorname{softIoU}(M_t^{obs},hat M_t).
]

The reconstruction mask can be approximated cheaply with low-resolution differentiable splatting during optimization and validated with Blender only at selected checkpoints.

### 3.2 Motion-distribution loss

The official flow metric compares motion distributions using a sliced-Wasserstein style distance. Use a related proxy:

[
mathcal L_{	ext{flow}}
=
rac1{T-1}sum_t
operatorname{SWD}(U_t^{obs},hat U_t).
]

For random unit directions (omega_k),

[
operatorname{SWD}(A,B)
approx
rac1K
sum_{k=1}^{K}
W_1(
{omega_k^	op a}_{ain A},
{omega_k^	op b}_{bin B}
).
]

This is cheap and naturally handles unordered motion samples.

### 3.3 Track loss

Use robust DTW or soft-DTW:

[
mathcal L_{	ext{track}}
=
rac1Nsum_i
operatorname{softDTW}
(P_i^{obs},hat P_i).
]

For early prototypes, ordinary DTW is acceptable because the outer optimizer can be derivative-free.

---

## 4. Free-trajectory initialization

Directly optimizing collision or articulated simulator parameters is highly non-convex. First fit low-dimensional trajectories.

### 4.1 Rigid trajectory

Translation:

[
x(t)=sum_{k=1}^{K} B_k(t)c_k.
]

Rotation can be represented with a spline in the Lie algebra:

[
R(t)=R_0exp([omega(t)]_	imes),
qquad
omega(t)=sum_k B_k(t)d_k.
]

Fit

[
min_{c,d}
mathcal L_{	ext{dyn}}
+
lambda_vint|ddot x(t)|^2dt
+
lambda_omegaint|dotomega(t)|^2dt.
]

This creates an observation-aligned trajectory without yet requiring a correct physical mechanism.

---

## 5. Spline-to-physics homotopy

Let (X) denote the free trajectory and (operatorname{Sim}(	heta)) a simulator trajectory.

Optimize

[
mathcal J(X,	heta;eta)
=
mathcal L_{	ext{obs}}(X)
+
eta D(X,operatorname{Sim}(	heta))
+
gamma E_{	ext{phys}}(X).
]

Use a continuation schedule such as

[
eta in {0, 10^{-2}, 10^{-1}, 1, 10}.
]

At (eta=0), fit video observations.
As (eta) increases, project the trajectory toward the simulator manifold.

### Physical residual examples

Ballistic rigid motion between contacts:

[
r_t^{dyn}
=
x_{t+1}-2x_t+x_{t-1}-gDelta t^2.
]

Contact non-penetration:

[
r_t^{contact}
=
max(0,-d(x_t,mathcal S)).
]

Constant angular momentum between impulses can provide another regularizer.

The physical residual does not have to replace the simulator; it can stabilize the transition into simulator fitting.

---

## 6. Black-box parameter optimization

Many Blender/Bullet parameters are not convenient to differentiate through. Use a low-dimensional black-box optimizer.

### Cross-Entropy Method

At iteration (j),

[
	heta_i^{(j)}
sim
mathcal N(mu_j,Sigma_j).
]

Evaluate all candidates with a cheap proxy and keep elite set (E_j).

Update

[
mu_{j+1}
=
(1-eta)mu_j
+
eta
rac1{|E_j|}
sum_{iin E_j}	heta_i^{(j)}
]

and similarly for covariance.

Use transformed parameters to enforce constraints:

- positive values: (exp(a));
- probabilities/friction-like bounded values: sigmoid;
- angles: wrapped representation;
- ordered event times: cumulative softplus increments.

### Why CEM/CMA-ES fits the project

The critical continuous search space can be kept near 10–40 dimensions for rigid/articulated templates. That is dramatically smaller than generating all mesh vertices or all frames independently.

---

## 7. Multi-fidelity evaluation

Full Cycles rendering is too expensive for inner-loop search.

Use a fidelity ladder:

### F0 — analytic projection

- project primitive vertices/points;
- Gaussian-splat a low-resolution mask;
- compute analytic 2D motion.

### F1 — rasterized preview

- 32–64 px;
- sparse keyframes;
- no expensive materials.

### F2 — coarse Blender render

- 64–128 px;
- more frames;
- simplified lighting.

### F3 — final benchmark-compatible build

- required dimensions/framerate;
- complete meshes/dynamics;
- final render.

Use successive halving:

[
N_0 > N_1 > N_2 > N_3
]

where only the best candidates survive to higher fidelity.

---

## 8. Program-hypothesis search

A 1B/7B model should produce several structured hypotheses instead of one unconstrained program.

Example hypothesis:

```json
{
  "objects": [
    {"type": "box", "dynamic": true},
    {"type": "plane", "dynamic": false}
  ],
  "motion_family": "rigid",
  "solver": "bullet",
  "events": ["impact"],
  "priors": {
    "gravity": [7.0, 12.0],
    "restitution": [0.0, 0.9]
  }
}
```

For hypotheses (z_1,ldots,z_m), allocate budget adaptively.

A simple successive-halving strategy:

1. cheap optimize every hypothesis for a few iterations;
2. rank by proxy score;
3. discard the bottom half;
4. double optimizer budget for survivors;
5. repeat.

This changes the role of test-time compute from language-token expansion to structured executable search.

---

## 9. Spectral extension for rope/cloth

For a mesh with Laplacian (L),

[
LU=ULambda.
]

Keep the first (k) non-rigid eigenmodes (U_k). Represent

[
X_t
=
R_tX_0+b_t+U_k a_t.
]

Parameterize modal coefficients temporally:

[
a_t
=
sum_j B_j(t)c_j.
]

Regularize elastic energy by

[
E_{	ext{spec}}
=
a_t^	opLambda_k a_t.
]

This turns per-vertex animation into a compact set of modal coefficients and is the preferred first extension beyond rigid/articulated dynamics.

---

## 10. Optimization order

Do not jointly optimize everything from the start.

Recommended block-coordinate schedule:

1. camera + frame-0 layout;
2. free trajectory;
3. dimensions + relative depth;
4. event timing;
5. simulator parameters;
6. appearance;
7. final joint polish.

This ordering reduces identifiability problems and makes failures diagnosable.

---

## 11. Keep/discard rule

Every experiment must be compared against a fixed baseline on the same development cases.

A change is **kept** only if:

1. executability does not regress;
2. mean dynamics proxy improves;
3. official development-set dynamics metrics improve or remain statistically indistinguishable while runtime falls meaningfully;
4. no improvement is explained by privileged test information.

The final paper must report both aggregate and per-case results.

