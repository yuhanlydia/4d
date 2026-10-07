#!/usr/bin/env python3
"""Run the paired B1-B4 matrix on the frozen native dev10 split."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.infer_qwen3vl_scene import generate
from opt4d.gauge import gauge_fix_scene
from opt4d.scene import compile_solution, validate_scene
from opt4d.video_proxy import optimize_motion


ARMS = ("B1", "B2", "B3", "B4", "P0", "P1", "P2")
PROXY_ARM_MODE = {"B4": "flow", "P0": "flow", "P1": "flow_mask", "P2": "flow_mask_track"}
SCORE_TYPES = "dynamic_iou,flow,track2d,trajectory,dynamics,scene_3d"
MIN_FREE_BYTES = 6 * 1024**3


def _json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_cases(path: Path) -> list[str]:
    cases = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if len(cases) != 10 or len(set(cases)) != 10:
        raise ValueError(f"expected exactly 10 unique frozen cases, got {len(cases)}")
    return cases


def _run_checker(workspace: Path, reference_video: Path, benchmark: Path,
                 log_path: Path) -> bool:
    live = Path("/workspace")
    backup = Path(f"/workspace.opt4d-backup-{os.getpid()}")
    live_input = Path("/input")
    input_backup = Path(f"/input.opt4d-backup-{os.getpid()}")
    if not live.is_dir() or live.is_symlink():
        raise RuntimeError("expected the existing /workspace directory to be a real directory")
    if not live_input.is_dir() or live_input.is_symlink():
        raise RuntimeError("expected the existing /input directory to be a real directory")
    if backup.exists() or backup.is_symlink():
        raise RuntimeError(f"refusing to overwrite workspace backup: {backup}")
    if input_backup.exists() or input_backup.is_symlink():
        raise RuntimeError(f"refusing to overwrite input backup: {input_backup}")
    os.replace(live, backup)
    try:
        shutil.copytree(workspace, live)
        os.replace(live_input, input_backup)
        try:
            live_input.mkdir()
            shutil.copy2(reference_video, live_input / "reference.mp4")
            result = subprocess.run([sys.executable, "-m", "checker"], cwd=benchmark,
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=600, check=False)
            log_path.write_text(result.stdout, encoding="utf-8")
            return result.returncode == 0
        finally:
            if live_input.exists():
                shutil.rmtree(live_input)
            os.replace(input_backup, live_input)
    finally:
        if live.exists():
            shutil.rmtree(live)
        os.replace(backup, live)


def _method_scene(arm: str, case: str, video: Path, run_root: Path,
                  model_path: Path, max_new_tokens: int) -> tuple[Path | None, dict[str, Any]]:
    case_root = run_root / arm / case
    scene_path = case_root / "scene.json"
    raw_path = case_root / "generation.json"
    started = time.perf_counter()
    record: dict[str, Any] = {"case": case, "arm": arm, "status": "pending"}
    if arm in {"B1", "B2"}:
        mode = "direct" if arm == "B1" else "dsl"
        try:
            scene, raw = generate(video, model_path, mode, max_new_tokens)
            _json(raw_path, raw)
            record.update({"status": raw["status"], "wall_s": raw.get("wall_s"),
                           "peak_vram_gb": raw.get("peak_vram_gib"), "model_calls": 1})
            if scene is None:
                record["error"] = raw.get("validation_error", "model output invalid")
                return None, record
            _json(scene_path, scene)
            return scene_path, record
        except Exception as exc:
            record.update({"status": "generation_failed", "error": f"{type(exc).__name__}: {exc}",
                           "wall_s": time.perf_counter() - started, "model_calls": 1})
            _json(raw_path, record)
            return None, record

    source = run_root / "B2" / case / "scene.json"
    record["model_calls"] = 0
    if not source.is_file():
        record.update({"status": "blocked_by_B2", "error": "B2 scene missing"})
        return None, record
    scene = json.loads(source.read_text(encoding="utf-8"))
    if arm in {"B3", "B4", "P0", "P1", "P2"}:
        scene, transform = gauge_fix_scene(scene)
        _json(case_root / "gauge.json", transform)
    if arm in PROXY_ARM_MODE:
        scene, result, proxy = optimize_motion(
            scene, video, population=32, iterations=8, seed=0,
            proxy_mode=PROXY_ARM_MODE[arm])
        _json(case_root / "cem.json", {
            "objective": result.fun, "iterations": result.iterations,
            "evaluations": result.evaluations, "history": result.history,
            "seed": 0, "population": 32, "proxy": proxy,
        })
        record.update({"proxy_loss": result.fun, "proxy_evals": result.evaluations,
                       "proxy_mode": proxy["mode"],
                       "proxy_components": proxy["components"]})
    validate_scene(scene)
    _json(scene_path, scene)
    record.update({"status": "locally_validated", "wall_s": time.perf_counter() - started})
    return scene_path, record


def _build_and_check(scene_path: Path | None, arm: str, case: str,
                     run_root: Path, benchmark: Path, record: dict[str, Any]) -> None:
    started = time.perf_counter()
    prior_wall = float(record.get("wall_s") or 0.0)
    case_root = run_root / arm / case
    workspace = case_root / "workspace"
    solution = workspace / "solution"
    workspace.mkdir(parents=True, exist_ok=True)
    build_ok = False
    if scene_path is not None:
        try:
            compile_solution(scene_path, solution)
            with (case_root / "build.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(["bash", str(solution / "build.sh")], cwd=solution,
                                        stdout=log, stderr=subprocess.STDOUT,
                                        timeout=3600, check=False)
            world = workspace / "world"
            world_complete = (
                (world / "camera.json").is_file()
                and (world / "render.mp4").is_file()
                and (world / "meshes").is_dir()
                and any((world / "meshes").glob("*.npz"))
                and (world / "dynamics").is_dir()
            )
            build_ok = result.returncode == 0 and world_complete
            if result.returncode == 0 and not world_complete:
                record["build_error"] = "Blender returned success but world artifacts are incomplete"
        except Exception as exc:
            record["build_error"] = f"{type(exc).__name__}: {exc}"
    if build_ok:
        frames = workspace / "world" / "frames"
        if frames.is_dir():
            shutil.rmtree(frames)
    record["build_ok"] = build_ok
    try:
        record["checker_ok"] = _run_checker(
            workspace, benchmark / "cases" / case / "reference.mp4",
            benchmark, case_root / "checker.log")
    except Exception as exc:
        record["checker_ok"] = False
        record["checker_error"] = f"{type(exc).__name__}: {exc}"
    record["wall_s"] = prior_wall + time.perf_counter() - started
    _json(case_root / "run.json", record)


def _manifest(run_id: str, arm: str, cases: list[str], run_root: Path) -> Path:
    entries = []
    for case in cases:
        relative = f"runs/{run_id}/{arm}/{case}"
        entries.append({"case": case, "world": f"{relative}/workspace/world", "out": relative})
    path = run_root / arm / "manifest.json"
    _json(path, entries)
    return path


def _score_arm(arm: str, run_id: str, cases: list[str], run_root: Path,
               benchmark: Path) -> tuple[int, str]:
    manifest = _manifest(run_id, arm, cases, run_root)
    argv = [sys.executable, "-m", "scorer", "--manifest", str(manifest),
            "--cases", str(benchmark / "cases"), "--data", str(benchmark / "data"),
            "--runs", str(ROOT / "runs"), "--checkpoints", str(benchmark / "checkpoints"),
            "--type", SCORE_TYPES, "--task-timeout", "1800", "--prepare-timeout", "600"]
    result = subprocess.run(argv, cwd=benchmark, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=6 * 3600, check=False)
    (run_root / arm / "scorer.log").write_text(result.stdout, encoding="utf-8")
    return result.returncode, result.stdout


def _value(reward: dict[str, Any], key: str) -> str:
    value = reward.get(key, "")
    return "" if value is None else str(value)


def _append_results(run_id: str, arm: str, cases: list[str], run_root: Path) -> None:
    result_path = ROOT / "results.tsv"
    with result_path.open("r", encoding="utf-8", newline="") as stream:
        fields = next(csv.reader(stream, delimiter="\t"))
    rows = []
    for case in cases:
        case_root = run_root / arm / case
        record_path = case_root / "run.json"
        record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {}
        reward_path = case_root / "results" / "reward.json"
        reward = json.loads(reward_path.read_text(encoding="utf-8")) if reward_path.exists() else {}
        rows.append({
            "experiment_id": f"{run_id}-{arm}", "commit": record.get("commit", ""),
            "case_set": "dev10", "case_id": case, "model": "Qwen3-VL-2B-Instruct", "params_b": "2.0",
            "quantization": "fp16", "method": arm,
            "gauge_fix": "yes" if arm in {"B3", "B4", "P0", "P1", "P2"} else "no",
            "optimizer": "CEM" if arm in PROXY_ARM_MODE else "none",
            "proxy_loss": record.get("proxy_loss", ""),
            "dynamic_iou": _value(reward, "dynamic_iou"),
            "flow_distribution": _value(reward, "flow_distribution"),
            "track2d_dtw": _value(reward, "track2d_dtw"),
            "trajectory_dtw": _value(reward, "trajectory_dtw"),
            "emd_step": _value(reward, "emd_step"),
            "scene_3d": _value(reward, "scene_3d"),
            "semantic_dinov3": _value(reward, "semantic_dinov3"),
            "checker_ok": record.get("checker_ok", False),
            "build_ok": record.get("build_ok", False),
            "peak_vram_gb": record.get("peak_vram_gb", ""),
            "wall_s": record.get("wall_s", ""),
            "model_calls": record.get("model_calls", 0),
            "proxy_evals": record.get("proxy_evals", 0),
            "blender_renders": int(bool(record.get("build_ok"))),
            "keep": "pending", "notes": record.get("error", record.get("build_error", "")),
        })
    with result_path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=ROOT.parent / "4DCodeBench")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS))
    parser.add_argument("--reuse-b2-from", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=1200)
    parser.add_argument("--min-free-gb", type=float, default=6.0)
    args = parser.parse_args()
    selected_arms = args.arms
    if any(arm in selected_arms for arm in ("B3", "B4", "P0", "P1", "P2")) and "B2" not in selected_arms and not args.reuse_b2_from:
        parser.error("B3/B4/P0/P1/P2 without B2 require --reuse-b2-from RUN_ID")
    benchmark = args.benchmark.resolve()
    model_path = (args.model or Path(os.environ.get(
        "OPT4D_MODEL", "/root/rivermind-data/models/Qwen3-VL-2B-Instruct"))).resolve()
    cases = _read_cases(ROOT / "configs" / "dev10.txt")
    if shutil.disk_usage(ROOT).free < max(MIN_FREE_BYTES, int(args.min_free_gb * 1024**3)):
        raise RuntimeError("free disk is below the configured reserve; refusing to start")
    if not benchmark.is_dir() or not model_path.is_dir():
        raise FileNotFoundError(f"benchmark or local model missing: {benchmark}, {model_path}")
    run_id = args.run_id or "dev10-b1b4-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = ROOT / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=False)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        commit = "unknown"
    patch = subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT)
    code_paths = ["program.md", "opt4d/scene.py", "opt4d/blender_runtime.py",
                  "opt4d/cem.py", "opt4d/losses.py", "opt4d/gauge.py",
                  "opt4d/video_proxy.py", "scripts/infer_qwen3vl_scene.py",
                  "scripts/run_dev10_matrix.py"]
    code_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                   for name in code_paths if (ROOT / name).is_file()}
    video_hashes = {case: hashlib.sha256(
        (benchmark / "cases" / case / "reference.mp4").read_bytes()).hexdigest()
        for case in cases}
    try:
        benchmark_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=benchmark, text=True).strip()
    except Exception:
        benchmark_commit = "unknown"
    try:
        gpu = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            text=True).strip()
    except Exception:
        gpu = "unavailable"
    _json(run_root / "protocol.json", {
        "run_id": run_id, "mode": "developmental", "cases": cases,
        "model": str(model_path), "method_arms": selected_arms,
        "reuse_b2_from": args.reuse_b2_from,
        "B1": "model generates complete scene JSON directly",
        "B2": "model generates object-only scene DSL; wrapper fixes camera/video",
        "B3": "B2 scene with projection-preserving center/scale gauge normalization",
        "B4": "legacy name for flow-only CEM",
        "proxy_ablation": {"P0": "flow", "P1": "flow+mask occupancy",
                           "P2": "flow+mask occupancy+LK tracks"},
        "optimizer": {"population": 32, "iterations": 8, "seed": 0},
        "official_scorer_types": SCORE_TYPES, "commit": commit,
        "benchmark_commit": benchmark_commit,
        "dirty_patch_sha256": hashlib.sha256(patch).hexdigest(),
        "code_sha256": code_hashes, "input_video_sha256": video_hashes,
        "model_config_sha256": hashlib.sha256((model_path / "config.json").read_bytes()).hexdigest(),
        "gpu": gpu,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "interpretation": "developmental paired ablation; not confirmatory",
    })
    print(f"RUN_START {run_id} cases={len(cases)} commit={commit}", flush=True)

    generation: dict[tuple[str, str], dict[str, Any]] = {}
    scenes: dict[tuple[str, str], Path | None] = {}
    if args.reuse_b2_from and "B2" not in selected_arms:
        source_root = ROOT / "runs" / args.reuse_b2_from / "B2"
        for case in cases:
            source_case = source_root / case
            scene_source = source_case / "scene.json"
            if not scene_source.is_file():
                raise FileNotFoundError(f"missing reusable B2 scene: {scene_source}")
            target_case = run_root / "B2" / case
            target_case.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scene_source, target_case / "scene.json")
            generation_source = source_case / "generation.json"
            if generation_source.is_file():
                shutil.copy2(generation_source, target_case / "generation.json")
    for arm in ("B1", "B2"):
        if arm not in selected_arms:
            continue
        for case in cases:
            video = benchmark / "cases" / case / "reference.mp4"
            scene_path, record = _method_scene(arm, case, video, run_root,
                                              model_path, args.max_new_tokens)
            record["commit"] = commit
            record["input_video"] = str(video)
            record["started_at"] = datetime.now(timezone.utc).isoformat()
            generation[(arm, case)] = record
            scenes[(arm, case)] = scene_path
            print(f"GENERATED {arm} {case} status={record['status']} wall_s={record.get('wall_s', '')}",
                  flush=True)

    for arm in selected_arms:
        for case in cases:
            if arm in {"B1", "B2"}:
                scene_path = scenes[(arm, case)]
                record = generation[(arm, case)]
            else:
                video = benchmark / "cases" / case / "reference.mp4"
                scene_path, record = _method_scene(arm, case, video, run_root,
                                                   model_path, args.max_new_tokens)
                record["commit"] = commit
                record["input_video"] = str(video)
            print(f"BUILD_START {arm} {case}", flush=True)
            _build_and_check(scene_path, arm, case, run_root, benchmark, record)
            print(f"BUILD_DONE {arm} {case} build={record.get('build_ok')} checker={record.get('checker_ok')}",
                  flush=True)
        print(f"SCORING_START {arm}", flush=True)
        code, output = _score_arm(arm, run_id, cases, run_root, benchmark)
        print(f"SCORING_DONE {arm} exit={code}\n{output[-1500:]}", flush=True)
        _append_results(run_id, arm, cases, run_root)
        print(f"RESULTS_APPENDED {arm}", flush=True)

    _json(run_root / "complete.json", {
        "status": "complete", "run_id": run_id, "commit": commit,
        "cases": cases, "arms": selected_arms, "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    print(f"RUN_COMPLETE {run_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

