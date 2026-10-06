"""Cheap proxy losses for observation-aligned 4D optimization."""

from __future__ import annotations

import numpy as np


def soft_iou(a: np.ndarray, b: np.ndarray, eps: float = 1e-8) -> float:
    """Soft intersection-over-union for masks with values in [0, 1]."""

    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("soft_iou inputs must have equal shapes")

    intersection = float(np.sum(a * b))
    union = float(np.sum(a) + np.sum(b) - intersection)
    return (intersection + eps) / (union + eps)


def _quantile_w1(x: np.ndarray, y: np.ndarray, quantiles: int = 128) -> float:
    """Approximate 1D Wasserstein-1 distance using matched quantiles."""

    if x.size == 0 or y.size == 0:
        raise ValueError("Wasserstein inputs must be non-empty")
    q = (np.arange(quantiles, dtype=np.float64) + 0.5) / quantiles
    xq = np.quantile(x, q)
    yq = np.quantile(y, q)
    return float(np.mean(np.abs(xq - yq)))


def sliced_wasserstein(
    a: np.ndarray,
    b: np.ndarray,
    *,
    projections: int = 32,
    quantiles: int = 128,
    seed: int = 0,
) -> float:
    """Approximate sliced Wasserstein distance between two point sets.

    Point counts may differ. The final axis is treated as point dimension.
    """

    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("inputs must have shape (N, D) and (M, D)")
    if a.shape[1] != b.shape[1]:
        raise ValueError("point dimensions must match")
    if a.shape[0] == 0 or b.shape[0] == 0:
        raise ValueError("point sets must be non-empty")

    rng = np.random.default_rng(seed)
    directions = rng.normal(size=(projections, a.shape[1]))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True).clip(min=1e-12)

    distances = []
    for direction in directions:
        pa = a @ direction
        pb = b @ direction
        distances.append(_quantile_w1(pa, pb, quantiles=quantiles))

    return float(np.mean(distances))


def dtw_distance(
    a: np.ndarray,
    b: np.ndarray,
    *,
    normalize: bool = True,
) -> float:
    """Classic dynamic-time-warping distance for vector trajectories."""

    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("trajectories must have shape (T, D)")
    if a.shape[1] != b.shape[1]:
        raise ValueError("trajectory dimensions must match")
    if len(a) == 0 or len(b) == 0:
        raise ValueError("trajectories must be non-empty")

    prev = np.full(len(b) + 1, np.inf, dtype=np.float64)
    prev[0] = 0.0

    for i in range(1, len(a) + 1):
        cur = np.full(len(b) + 1, np.inf, dtype=np.float64)
        for j in range(1, len(b) + 1):
            cost = float(np.linalg.norm(a[i - 1] - b[j - 1]))
            cur[j] = cost + min(prev[j], cur[j - 1], prev[j - 1])
        prev = cur

    value = float(prev[-1])
    if normalize:
        value /= (len(a) + len(b))
    return value
