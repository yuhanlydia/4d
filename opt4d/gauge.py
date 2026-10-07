"""Similarity-gauge normalization for DSL scenes."""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from .scene import validate_scene


def gauge_fix_scene(scene: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Center and normalize a scene while preserving its camera projection."""
    validate_scene(scene)
    fixed = copy.deepcopy(scene)
    objects = fixed["objects"]
    centers = np.asarray([obj["position"] for obj in objects], dtype=np.float64)
    center = centers.mean(axis=0)
    extent = max(
        float(np.linalg.norm(np.asarray(obj["position"]) - center))
        + 0.5 * float(np.linalg.norm(np.asarray(obj["size"])))
        for obj in objects
    )
    if not math.isfinite(extent) or extent <= 1e-12:
        raise ValueError("scene extent must be finite and positive")
    scale = 1.0 / extent

    extrinsic = np.asarray(fixed["camera"]["extrinsic"], dtype=np.float64)
    translation = extrinsic[:3, 3]
    # The benchmark extrinsic is camera-to-world, so both points and camera
    # position receive the same world-space similarity transform.
    extrinsic[:3, 3] = scale * (translation - center)
    fixed["camera"]["extrinsic"] = extrinsic.tolist()

    for obj in objects:
        obj["position"] = (scale * (np.asarray(obj["position"]) - center)).tolist()
        obj["size"] = (scale * np.asarray(obj["size"], dtype=np.float64)).tolist()
        motion = obj.get("motion", {"type": "static"})
        if motion["type"] == "linear":
            motion["velocity"] = (scale * np.asarray(motion["velocity"])).tolist()
        elif motion["type"] == "hinge":
            motion["pivot"] = (scale * (np.asarray(motion["pivot"]) - center)).tolist()

    validate_scene(fixed)
    return fixed, {"center": center.tolist(), "scale": scale}
