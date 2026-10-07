#!/usr/bin/env python3
"""Materialize T0/H0 developmental scenes from an existing valid parent run."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from opt4d.trajectory import fit_free_trajectory,project_trajectory_to_linear,homotopy_scenes
from opt4d.scene import validate_scene
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--benchmark",type=Path,default=ROOT.parent/"4DCodeBench");ap.add_argument("--parent-run",required=True);ap.add_argument("--parent-arm",default="P2");ap.add_argument("--output-run",required=True);args=ap.parse_args()
 cases=[x.strip() for x in (ROOT/"configs/dev10.txt").read_text().splitlines() if x.strip() and not x.startswith("#")];out=ROOT/"runs"/args.output_run
 for case in cases:
  src=ROOT/"runs"/args.parent_run/args.parent_arm/case/"scene.json"
  if not src.is_file():raise FileNotFoundError(src)
  scene=json.loads(src.read_text());validate_scene(scene);video=args.benchmark/"cases"/case/"reference.mp4";fit=fit_free_trajectory(scene,video,samples=8,smooth_lambda=.25)
  dump(out/"T0"/case/"trajectory.json",fit.__dict__);dump(out/"T0"/case/"scene.json",project_trajectory_to_linear(scene,fit,physics_weight=1.0))
  for weight,candidate in homotopy_scenes(scene,fit):
   tag=f"w{weight:.2f}".replace(".","p");dump(out/"H0"/case/tag/"scene.json",candidate)
 dump(out/"protocol.json",{"status":"generated_unexecuted","parent_run":args.parent_run,"parent_arm":args.parent_arm,"cases":cases,"T0":"free trajectory -> linear DSL projection","H0_schedule":[0,.25,.5,.75,1],"note":"Use the existing native compiler/checker/scorer for every scene. No scorer data is read here."});print(out)
if __name__=="__main__":main()
