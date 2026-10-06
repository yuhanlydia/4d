"""A small full-covariance Cross-Entropy Method optimizer.

The optimizer is intentionally dependency-light so it can be used inside
4DCodeBench agent environments without adding a training stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class CEMResult:
    x: np.ndarray
    fun: float
    iterations: int
    evaluations: int
    history: list[dict[str, float]]


def cem_minimize(
    objective: Callable[[np.ndarray], float],
    mean: np.ndarray | list[float],
    std: np.ndarray | list[float],
    *,
    lower: np.ndarray | list[float] | None = None,
    upper: np.ndarray | list[float] | None = None,
    population: int = 128,
    elite_frac: float = 0.125,
    iterations: int = 40,
    smoothing: float = 0.7,
    min_std: float = 1e-4,
    seed: int = 0,
) -> CEMResult:
    """Minimize a black-box objective with full-covariance CEM.

    Full covariance is important for inverse dynamics because parameters such as
    initial vertical velocity and gravity are strongly correlated.
    """

    rng = np.random.default_rng(seed)
    mean = np.asarray(mean, dtype=np.float64).copy()
    std = np.asarray(std, dtype=np.float64).copy()

    if mean.ndim != 1 or std.shape != mean.shape:
        raise ValueError("mean and std must be one-dimensional arrays of equal shape")
    if np.any(std <= 0):
        raise ValueError("all initial std values must be positive")
    if population < 4:
        raise ValueError("population must be at least 4")
    if not (0.0 < elite_frac <= 0.5):
        raise ValueError("elite_frac must be in (0, 0.5]")
    if not (0.0 < smoothing <= 1.0):
        raise ValueError("smoothing must be in (0, 1]")

    dim = mean.size
    lower_arr = (
        np.full(dim, -np.inf, dtype=np.float64)
        if lower is None
        else np.asarray(lower, dtype=np.float64)
    )
    upper_arr = (
        np.full(dim, np.inf, dtype=np.float64)
        if upper is None
        else np.asarray(upper, dtype=np.float64)
    )
    if lower_arr.shape != mean.shape or upper_arr.shape != mean.shape:
        raise ValueError("bounds must match mean shape")
    if np.any(lower_arr >= upper_arr):
        raise ValueError("every lower bound must be smaller than upper bound")

    elite_n = max(2, int(np.ceil(population * elite_frac)))
    covariance = np.diag(std**2)

    best_x = np.clip(mean, lower_arr, upper_arr)
    best_f = float(objective(best_x))
    evaluations = 1
    history: list[dict[str, float]] = []

    for iteration in range(iterations):
        samples = rng.multivariate_normal(mean, covariance, size=population)
        samples = np.clip(samples, lower_arr, upper_arr)

        values = np.asarray([float(objective(x)) for x in samples], dtype=np.float64)
        evaluations += population

        order = np.argsort(values)
        elites = samples[order[:elite_n]]

        current_x = samples[order[0]]
        current_f = float(values[order[0]])
        if current_f < best_f:
            best_f = current_f
            best_x = current_x.copy()

        elite_mean = elites.mean(axis=0)
        centered = elites - elite_mean
        elite_cov = centered.T @ centered / max(1, elite_n - 1)

        mean = (1.0 - smoothing) * mean + smoothing * elite_mean
        covariance = (1.0 - smoothing) * covariance + smoothing * elite_cov

        # Numerical floor and symmetry guard.
        covariance = 0.5 * (covariance + covariance.T)
        covariance += np.eye(dim, dtype=np.float64) * (min_std**2)

        history.append(
            {
                "iteration": float(iteration),
                "best": best_f,
                "population_best": current_f,
                "mean_std": float(np.sqrt(np.mean(np.diag(covariance)))),
            }
        )

    return CEMResult(
        x=best_x,
        fun=best_f,
        iterations=iterations,
        evaluations=evaluations,
        history=history,
    )
