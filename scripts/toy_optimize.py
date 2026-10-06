#!/usr/bin/env python3
"""Smoke test: recover a ballistic trajectory with full-covariance CEM.

This is not a 4DCodeBench experiment. It validates the low-dimensional
system-identification loop before connecting it to Blender and benchmark videos.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from opt4d.cem import cem_minimize


def trajectory(params: np.ndarray, t: np.ndarray) -> np.ndarray:
    x0, y0, vx, vy, gravity = params
    x = x0 + vx * t
    y = y0 + vy * t - 0.5 * gravity * t**2
    return np.stack([x, y], axis=-1)


def main() -> int:
    rng = np.random.default_rng(4)

    true_params = np.array([0.2, 1.1, 1.35, 2.2, 9.4], dtype=np.float64)
    times = np.linspace(0.0, 1.0, 48)
    observations = trajectory(true_params, times)
    observations += rng.normal(0.0, 0.002, size=observations.shape)

    def objective(params: np.ndarray) -> float:
        residual = trajectory(params, times) - observations
        return float(np.mean(residual**2))

    result = cem_minimize(
        objective,
        mean=[0.0, 1.0, 1.0, 1.0, 8.0],
        std=[0.7, 0.7, 1.3, 1.5, 3.0],
        lower=[-2.0, -1.0, -3.0, -3.0, 1.0],
        upper=[2.0, 3.0, 4.0, 5.0, 15.0],
        population=256,
        elite_frac=0.10,
        iterations=60,
        smoothing=0.7,
        seed=3,
    )

    summary = {
        "status": "ok",
        "objective": result.fun,
        "evaluations": result.evaluations,
        "estimated": result.x.tolist(),
        "truth": true_params.tolist(),
        "parameter_l2_error": float(np.linalg.norm(result.x - true_params)),
    }

    print("OPT4D_SMOKE " + json.dumps(summary, sort_keys=True))

    # Loose deterministic gate: this checks optimization functionality, not
    # scientific accuracy on a benchmark.
    return 0 if result.fun < 1e-4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
