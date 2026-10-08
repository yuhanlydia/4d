#!/usr/bin/env python3
"""E04 sensitivity audit of existing P0/P1/P2 proxies; never invokes the scorer.

This script is a diagnostic, not a new optimizer, method arm or efficacy result.
It uses only existing candidate scene JSON and pixels in the supplied input video.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from opt4d.scene import validate_scene
from opt4d.video_proxy import (
    PROXY_WEIGHTS, observed_measurements, predicted_measurements, proxy_components,
)

ARM_MODES = {"P0": "flow", "P1": "flow_mask", "P2": "flow_mask_track"}
DELTAS = (-1.0, -0.25, 0.25, 1.0)
MAX_PARAMETERS = 12
FLAT_TOLERANCE = 1e-12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def motion_parameters(scene: dict) -> list[tuple[int, str, int | None]]:
    """Match the parameter families exposed to the original CEM optimizer."""
    params = []
    for index, obj in enumerate(scene["objects"]):
        motion = obj.get("motion", {"type": "static"})
        if motion["type"] == "linear":
            params.extend((index, "velocity", axis) for axis in range(3))
        elif motion["type"] == "hinge":
            params.append((index, "angle_end", None))
    if not params:
        for index, obj in enumerate(scene["objects"]):
            if obj.get("motion", {"type": "static"})["type"] == "static":
                params.extend((index, "promote_velocity", axis) for axis in range(3))
    return params


def perturbed_scene(scene: dict, parameter: tuple[int, str, int | None], delta: float) -> dict:
    candidate = copy.deepcopy(scene)
    index, field, axis = parameter
    motion = candidate["objects"][index].setdefault("motion", {"type": "static"})
    if field == "promote_velocity":
        if motion["type"] != "static":
            raise ValueError("expected a static object for the promotion diagnostic")
        motion = {"type": "linear", "velocity": [0.0, 0.0, 0.0]}
        candidate["objects"][index]["motion"] = motion
    if field in ("velocity", "promote_velocity"):
        assert axis is not None
        motion["velocity"][axis] = float(motion["velocity"][axis]) + delta
    elif field == "angle_end":
        motion["angle_end"] = float(motion["angle_end"]) + delta
    else:
        raise ValueError(field)
    validate_scene(candidate)
    return candidate


def candidate_bank(scene: dict, *, max_parameters: int = MAX_PARAMETERS):
    """Deterministic local perturbations around the actual completed P0 scene."""
    if max_parameters < 1:
        raise ValueError("max_parameters must be positive")
    validate_scene(scene)
    params = motion_parameters(scene)
    # No result-driven choice of parameters: stable object/field order.
    selected = params[:max_parameters]
    bank = [("base", scene)]
    for i, parameter in enumerate(selected):
        for delta in DELTAS:
            bank.append((f"p{i:02d}:{delta:+.2f}", perturbed_scene(scene, parameter, delta)))
    return bank, params, selected


def average_ranks(values: list[float]) -> np.ndarray:
    data = np.asarray(values, dtype=np.float64)
    order = np.argsort(data, kind="mergesort")
    ranks = np.empty(len(data), dtype=np.float64)
    i = 0
    while i < len(data):
        j = i + 1
        while j < len(data) and data[order[j]] == data[order[i]]:
            j += 1
        ranks[order[i:j]] = (i + j - 1) / 2.0
        i = j
    return ranks


def rank_agreement(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3:
        return None
    a, b = average_ranks(left), average_ranks(right)
    if np.std(a) <= FLAT_TOLERANCE or np.std(b) <= FLAT_TOLERANCE:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def summarize_candidate_rows(rows: list[dict]) -> dict:
    """Summarize rank stability and component sensitivity; no official reward."""
    if not rows:
        raise ValueError("cannot summarize an empty candidate bank")
    components = {}
    for name in ("flow", "mask", "track"):
        values = np.asarray([r["components"][name] for r in rows], dtype=float)
        components[name] = {
            "min": float(values.min()), "max": float(values.max()),
            "range": float(np.ptp(values)), "std": float(values.std()),
            "flat_at_1e-12": bool(float(np.ptp(values)) <= FLAT_TOLERANCE),
        }
    scores = {}
    for arm in ARM_MODES:
        values = [r["objective"][arm] for r in rows]
        best = min(range(len(values)), key=lambda i: (values[i], i))
        scores[arm] = {
            "best_candidate": rows[best]["candidate"],
            "best_value": float(values[best]),
            "base_value": float(values[0]),
            "range": float(max(values) - min(values)),
            "rank_vs_p0": rank_agreement(
                [r["objective"]["P0"] for r in rows], values
            ),
        }
    scores["P1"]["same_argmin_as_p0"] = (
        scores["P1"]["best_candidate"] == scores["P0"]["best_candidate"]
    )
    scores["P2"]["same_argmin_as_p0"] = (
        scores["P2"]["best_candidate"] == scores["P0"]["best_candidate"]
    )
    return {"component_sensitivity": components, "objectives": scores}


def diagnose(scene: dict, video_path: Path, *, max_parameters: int = MAX_PARAMETERS) -> dict:
    target, intervals = observed_measurements(video_path)
    bank, all_params, selected = candidate_bank(scene, max_parameters=max_parameters)
    rows = []
    for label, candidate in bank:
        predicted = predicted_measurements(candidate, intervals)
        components = proxy_components(target, predicted)
        if not all(math.isfinite(value) for value in components.values()):
            raise ValueError(f"non-finite proxy component for {label}")
        objective = {
            arm: float(sum(
                PROXY_WEIGHTS[mode][key] * components[key]
                for key in ("flow", "mask", "track")
            )) for arm, mode in ARM_MODES.items()
        }
        rows.append({"candidate": label, "components": components, "objective": objective})
    return {
        "all_parameter_count": len(all_params),
        "selected_parameters": [
            {"object_index": i, "field": field, "axis": axis}
            for i, field, axis in selected
        ],
        "candidate_count": len(rows),
        "candidate_rows": rows,
        **summarize_candidate_rows(rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--benchmark", type=Path, required=True)
    ap.add_argument("--source-run", required=True, help="completed P0/P1/P2 run id")
    ap.add_argument("--source-arm", choices=("P0",), default="P0")
    ap.add_argument("--cases", type=Path, default=Path("configs/dev10.txt"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-parameters", type=int, default=MAX_PARAMETERS)
    args = ap.parse_args()
    if args.out.exists():
        ap.error("refusing to overwrite an existing diagnostic output")
    cases = [
        line.strip() for line in args.cases.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(cases) != 10 or len(set(cases)) != 10:
        ap.error("expected exactly ten unique frozen dev10 case IDs")
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"
    packet = {
        "status": "developmental_diagnostic_unverified",
        "source_run": args.source_run,
        "source_arm": args.source_arm,
        "code_commit": revision,
        "case_manifest": str(args.cases),
        "case_manifest_sha256": sha256(args.cases),
        "perturbation_deltas": list(DELTAS),
        "max_parameters": args.max_parameters,
        "flat_tolerance": FLAT_TOLERANCE,
        "measured_only_from": "source scene JSON and input reference.mp4 pixels",
        "official_scorer_invoked": False,
        "cases": {},
    }
    for case in cases:
        scene_file = (Path("runs") / args.source_run /
                      args.source_arm / case / "scene.json")
        video = args.benchmark / "cases" / case / "reference.mp4"
        if not scene_file.is_file() or not video.is_file():
            raise FileNotFoundError(f"missing scene/video for {case}: {scene_file} {video}")
        scene = json.loads(scene_file.read_text(encoding="utf-8"))
        validate_scene(scene)
        result = diagnose(scene, video, max_parameters=args.max_parameters)
        result["scene_sha256"] = sha256(scene_file)
        result["video_sha256"] = sha256(video)
        packet["cases"][case] = result
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(packet, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"E04_PROXY_DIAGNOSTICS_WRITTEN {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
