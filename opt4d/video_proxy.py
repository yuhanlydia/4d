"""Video-only motion proxy and bounded CEM refinement for scene DSLs."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .cem import CEMResult, cem_minimize
from .losses import sliced_wasserstein
from .scene import validate_scene


def observed_flow(video_path: str | Path, *, samples: int = 8,
                  max_vectors: int = 2048) -> tuple[list[np.ndarray], list[float]]:
    """Extract deterministic moving-pixel flow samples from a benchmark video."""
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if count < 2 or not math.isfinite(fps) or fps <= 0:
        capture.release()
        raise RuntimeError("video must contain at least two frames and positive fps")
    indices = np.linspace(0, count - 1, num=min(samples, count), dtype=int)
    frames: list[np.ndarray] = []
    for index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise RuntimeError(f"failed to decode frame {index}")
        frame = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    capture.release()

    rng = np.random.default_rng(0)
    flows: list[np.ndarray] = []
    times: list[float] = []
    for i, (left, right) in enumerate(zip(frames, frames[1:])):
        flow = cv2.calcOpticalFlowFarneback(left, right, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        magnitude = np.linalg.norm(flow, axis=-1)
        active = np.flatnonzero((magnitude > 0.5) & (magnitude < 80.0))
        if len(active) > max_vectors:
            active = rng.choice(active, size=max_vectors, replace=False)
        vectors = flow.reshape(-1, 2)[active].astype(np.float64)
        flows.append(vectors if len(vectors) else np.zeros((1, 2), dtype=np.float64))
        times.append(float(indices[i + 1] - indices[i]) / fps)
    return flows, times


def _rotation_xyz(euler: list[float]) -> np.ndarray:
    x, y, z = euler
    sx, cx = math.sin(x), math.cos(x)
    sy, cy = math.sin(y), math.cos(y)
    sz, cz = math.sin(z), math.cos(z)
    return np.array([
        [cy * cz, cz * sx * sy - cx * sz, sx * sz + cx * cz * sy],
        [cy * sz, cx * cz + sx * sy * sz, cx * sy * sz - cz * sx],
        [-sy, cy * sx, cx * cy],
    ], dtype=np.float64)


def _axis_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = axis / max(float(np.linalg.norm(axis)), 1e-12)
    x, y, z = axis
    c, s, q = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return np.array([
        [c + x*x*q, x*y*q - z*s, x*z*q + y*s],
        [y*x*q + z*s, c + y*y*q, y*z*q - x*s],
        [z*x*q - y*s, z*y*q + x*s, c + z*z*q],
    ], dtype=np.float64)


def predicted_flow(scene: dict[str, Any], intervals: list[float]) -> list[np.ndarray]:
    """Project primitive surface anchors and return their interval pixel flow."""
    validate_scene(scene)
    K = np.asarray(scene["camera"]["intrinsics"], dtype=np.float64)
    E = np.asarray(scene["camera"]["extrinsic"], dtype=np.float64)
    width, height = scene["video"]["width"], scene["video"]["height"]
    resize = np.diag([160.0 / width, 90.0 / height, 1.0])
    projection = resize @ K
    duration = (scene["video"]["frames"] - 1) / float(scene["video"]["fps"])
    sample_times = np.linspace(0.0, duration, num=len(intervals) + 1)
    output: list[list[np.ndarray]] = [[] for _ in intervals]

    for obj in scene["objects"]:
        size = np.asarray(obj["size"], dtype=np.float64)
        anchors = np.vstack([np.zeros(3), np.diag(size / 2), -np.diag(size / 2)])
        base_rotation = _rotation_xyz(obj.get("rotation_euler", [0, 0, 0]))
        motion = obj.get("motion", {"type": "static"})
        positions: list[np.ndarray] = []
        for time in sample_times:
            center = np.asarray(obj["position"], dtype=np.float64)
            rotation = base_rotation
            if motion["type"] == "linear":
                center = center + np.asarray(motion["velocity"]) * time
            elif motion["type"] == "hinge":
                pivot = np.asarray(motion["pivot"], dtype=np.float64)
                fraction = time / max(duration, 1e-12)
                angle = float(motion["angle_start"]) + fraction * (
                    float(motion["angle_end"]) - float(motion["angle_start"]))
                hinge_rotation = _axis_rotation(np.asarray(motion["axis"]), angle)
                center = pivot + hinge_rotation @ (center - pivot)
                rotation = hinge_rotation @ base_rotation
            world = center + anchors @ rotation.T
            camera = (world - E[:3, 3]) @ E[:3, :3]
            pixels = camera @ projection.T
            valid = pixels[:, 2] > 1e-5
            xy = np.full((len(pixels), 2), np.nan, dtype=np.float64)
            xy[valid] = pixels[valid, :2] / pixels[valid, 2:3]
            positions.append(xy)
        for i in range(len(intervals)):
            delta = positions[i + 1] - positions[i]
            valid = np.isfinite(delta).all(axis=1)
            if np.any(valid):
                output[i].append(delta[valid])

    return [np.concatenate(parts, axis=0) if parts else np.zeros((1, 2)) for parts in output]


def optimize_motion(scene: dict[str, Any], video_path: str | Path, *,
                    population: int = 32, iterations: int = 8,
                    seed: int = 0) -> tuple[dict[str, Any], CEMResult]:
    """Fit linear velocities and hinge end angles to video-only optical flow."""
    validate_scene(scene)
    target, intervals = observed_flow(video_path)
    parameters: list[tuple[int, str]] = []
    mean: list[float] = []
    std: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    for index, obj in enumerate(scene["objects"]):
        motion = obj.get("motion", {"type": "static"})
        if motion["type"] == "linear":
            for axis, value in enumerate(motion["velocity"]):
                parameters.append((index, f"velocity:{axis}"))
                mean.append(float(value)); std.append(1.0); lower.append(-8.0); upper.append(8.0)
        elif motion["type"] == "hinge":
            parameters.append((index, "angle_end"))
            mean.append(float(motion["angle_end"])); std.append(0.5)
            lower.append(-2 * math.pi); upper.append(2 * math.pi)

    if not parameters:
        parameters = [(index, f"velocity:{axis}")
                      for index, obj in enumerate(scene["objects"])
                      if obj.get("motion", {"type": "static"})["type"] == "static"
                      for axis in range(3)]
        mean = [0.0] * len(parameters); std = [1.0] * len(parameters)
        lower = [-8.0] * len(parameters); upper = [8.0] * len(parameters)

    def materialize(values: np.ndarray) -> dict[str, Any]:
        candidate = copy.deepcopy(scene)
        for value, (index, field) in zip(values, parameters):
            if field.startswith("velocity:"):
                obj = candidate["objects"][index]
                motion = obj.setdefault("motion", {"type": "linear", "velocity": [0.0, 0.0, 0.0]})
                if motion["type"] == "static":
                    motion = {"type": "linear", "velocity": [0.0, 0.0, 0.0]}
                    obj["motion"] = motion
                motion["velocity"][int(field.split(":")[1])] = float(value)
            else:
                candidate["objects"][index]["motion"][field] = float(value)
        return candidate

    def objective(values: np.ndarray) -> float:
        prediction = predicted_flow(materialize(values), intervals)
        costs = [sliced_wasserstein(a, b, projections=8, quantiles=32, seed=i)
                 for i, (a, b) in enumerate(zip(target, prediction))]
        return float(np.mean(costs))

    result = cem_minimize(objective, mean, std, lower=lower, upper=upper,
                          population=population, iterations=iterations, seed=seed)
    return materialize(result.x), result
