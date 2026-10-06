#!/usr/bin/env python3
"""Native (no Docker) readiness checker and frozen-case selector for Opt4D.

This script never downloads benchmark data, changes the official scorer, or
touches privileged reference worlds. It can create a deterministic case list
from video filenames that exist on the target machine.

Examples:
    python prepare.py --benchmark ../4DCodeBench
    python prepare.py --benchmark ../4DCodeBench --freeze-cases
    python prepare.py --benchmark ../4DCodeBench --strict
    python prepare.py --benchmark ../4DCodeBench --json .local/readiness.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
VALID_CASE = re.compile(r"^(real|synthetic)/([A-Za-z0-9][A-Za-z0-9_.-]*)$")
REQUIRED_TOOLS = ("blender", "ffmpeg", "ffprobe")
NATIVE_MODULES = ("numpy", "torch", "bpy", "warp", "taichi")


def probe_command(argv: list[str]) -> dict[str, Any]:
    binary = shutil.which(argv[0])
    if binary is None:
        return {"ok": False, "detail": f"{argv[0]} not found in PATH"}
    try:
        completed = subprocess.run(
            [binary, *argv[1:]],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "detail": str(exc)}
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return {
        "ok": completed.returncode == 0,
        "detail": output[0][:240] if output else f"returncode={completed.returncode}",
    }


def check_gpu(min_vram_gb: float) -> dict[str, Any]:
    gpu = probe_command(
        ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"]
    )
    if not gpu["ok"]:
        return gpu
    # nvidia-smi reports framebuffer memory in MiB, not decimal MB.
    raw = subprocess.run(
        [
            shutil.which("nvidia-smi") or "nvidia-smi",
            "--query-gpu=memory.total,name",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=12,
        check=False,
    )
    devices: list[dict[str, Any]] = []
    for line in raw.stdout.splitlines():
        parts = line.split(",", 1)
        if len(parts) != 2:
            continue
        try:
            memory_gib = float(parts[0].strip()) / 1024.0
        except ValueError:
            continue
        devices.append({"name": parts[1].strip(), "vram_gib": round(memory_gib, 2)})
    return {
        "ok": any(device["vram_gib"] >= min_vram_gb for device in devices),
        "detail": devices or "could not parse nvidia-smi",
    }


def discover_cases(benchmark: Path) -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {"real": [], "synthetic": []}
    for kind in cases:
        directory = benchmark / "cases" / kind
        if not directory.is_dir():
            continue
        for case_dir in directory.iterdir():
            if (
                case_dir.is_dir()
                and VALID_CASE.fullmatch(f"{kind}/{case_dir.name}")
                and (case_dir / "reference.mp4").is_file()
                and (case_dir / "reference.mp4").stat().st_size > 0
            ):
                cases[kind].append(f"{kind}/{case_dir.name}")
        cases[kind].sort()
    return cases


def choose_dev10(cases: dict[str, list[str]]) -> list[str]:
    """Choose 5 real + 5 synthetic by a stable SHA256 rank, not directory order."""
    selected = []
    for kind in ("real", "synthetic"):
        candidates = cases[kind]
        if len(candidates) < 5:
            raise ValueError(
                f"need >=5 downloaded {kind} reference videos; found {len(candidates)}"
            )
        ranked = sorted(
            candidates,
            key=lambda case: (hashlib.sha256(case.encode()).hexdigest(), case),
        )
        selected.extend(ranked[:5])
    return sorted(selected)


def write_frozen_cases(path: Path, cases: dict[str, list[str]]) -> list[str]:
    if path.exists():
        raise FileExistsError(
            f"{path} already exists; refusing to overwrite a frozen benchmark split"
        )
    selected = choose_dev10(cases)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# Frozen Opt4D dev10 split (5 real + 5 synthetic)\n"
        "# Deterministic SHA256 ranking on available local reference videos.\n"
        "# Commit this file to make the split portable and auditable.\n"
        "# Do not reselect after observing results.\n"
        + "\n".join(selected)
        + "\n"
    )
    # 'x' prevents races and accidental overwrites.
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)
    return selected


def read_frozen_cases(path: Path, benchmark: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "detail": f"no frozen case list at {path}"}
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(lines) != 10 or len(set(lines)) != 10:
        return {"ok": False, "detail": "expected 10 distinct cases"}
    if not all(VALID_CASE.fullmatch(line) for line in lines):
        return {"ok": False, "detail": "invalid case ID (expected real/id or synthetic/id)"}
    counts = {kind: sum(x.startswith(kind + "/") for x in lines) for kind in ("real", "synthetic")}
    if counts != {"real": 5, "synthetic": 5}:
        return {"ok": False, "detail": f"requires five cases of each kind; got {counts}"}
    missing = []
    for case in lines:
        video = benchmark / "cases" / case / "reference.mp4"
        if not video.is_file() or video.stat().st_size == 0:
            missing.append(case)
    return {"ok": not missing, "detail": {"cases": lines, "missing_videos": missing}}


def check_skill() -> dict[str, Any]:
    source = ROOT / ".tools" / "research-autopilot"
    skill_file = source / "SKILL.md"
    if not skill_file.is_file():
        return {
            "ok": False,
            "detail": "run: bash scripts/update_research_autopilot.sh",
        }
    result = probe_command(["git", "-C", str(source), "rev-parse", "HEAD"])
    return {"ok": result["ok"], "detail": result["detail"]}


def check_benchmark(benchmark: Path) -> dict[str, Any]:
    required = (
        "README.md",
        "environment.yml",
        "checker/__init__.py",
        "scorer/__init__.py",
        "scorer/prepare/__main__.py",
    )
    missing = [name for name in required if not (benchmark / name).is_file()]
    # The scorer is the official source of truth; no replacement scorer is installed.
    return {"ok": not missing, "detail": {"path": str(benchmark), "missing": missing}}


def make_report(
    benchmark: Path, cases_file: Path, min_vram_gb: float, require_gpu: bool
) -> dict[str, Any]:
    benchmark = benchmark.resolve()
    checks: dict[str, dict[str, Any]] = {
        "benchmark": check_benchmark(benchmark),
        "skill": check_skill(),
        "python": {"ok": sys.version_info >= (3, 11), "detail": sys.version.split()[0]},
    }
    for tool in REQUIRED_TOOLS:
        args = ["-version"] if tool.startswith("ff") else ["--version"]
        checks[f"tool_{tool}"] = probe_command([tool, *args])
    for module in NATIVE_MODULES:
        checks[f"module_{module}"] = {
            "ok": importlib.util.find_spec(module) is not None,
            "detail": "installed" if importlib.util.find_spec(module) is not None else "missing",
        }
    checks["gpu"] = check_gpu(min_vram_gb)
    checks["cases"] = read_frozen_cases(cases_file, benchmark)

    # A scorer environment can be different from the agent environment.
    # Some missing tools are warnings until --strict is requested.
    necessary = ("benchmark", "python", "cases", "tool_blender", "tool_ffmpeg", "tool_ffprobe")
    if require_gpu:
        necessary = (*necessary, "gpu")
    ready = all(checks[name]["ok"] for name in necessary)
    return {"ready": ready, "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark", type=Path, default=ROOT.parent / "4DCodeBench",
        help="existing official 4DCodeBench checkout (default: ../4DCodeBench)",
    )
    parser.add_argument(
        "--cases-file", type=Path, default=ROOT / "configs" / "dev10.txt",
        help="frozen selection file, created only with --freeze-cases",
    )
    parser.add_argument("--freeze-cases", action="store_true", help="freeze 5 real + 5 synthetic videos")
    parser.add_argument("--strict", action="store_true", help="exit nonzero unless core readiness checks pass")
    parser.add_argument("--require-gpu", action="store_true", help="require >= --min-vram-gb VRAM")
    parser.add_argument("--min-vram-gb", type=float, default=20.0)
    parser.add_argument("--json", type=Path, help="optional machine-readable readiness report")
    args = parser.parse_args(argv)

    if args.min_vram_gb <= 0:
        parser.error("--min-vram-gb must be positive")

    benchmark = args.benchmark.resolve()
    if args.freeze_cases:
        try:
            selected = write_frozen_cases(args.cases_file, discover_cases(benchmark))
        except (ValueError, OSError) as exc:
            print(f"FREEZE_FAILED: {exc}", file=sys.stderr)
            return 2
        print(f"FROZEN_CASES={args.cases_file}")
        print("CASES=" + ",".join(selected))

    report = make_report(benchmark, args.cases_file, args.min_vram_gb, args.require_gpu)
    print("OPT4D_PREPARE " + json.dumps(report, sort_keys=True))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if args.strict and not report["ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
