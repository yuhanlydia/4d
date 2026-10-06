#!/usr/bin/env python3
"""Compile a validated scene.json into a self-contained Blender solution."""
from __future__ import annotations
import argparse
from pathlib import Path
from opt4d.scene import compile_solution

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("scene", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    out = compile_solution(args.scene, args.output)
    print(f"OPT4D_COMPILED={out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
