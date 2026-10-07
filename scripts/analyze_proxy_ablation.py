#!/usr/bin/env python3
"""Analyze a completed P0/P1/P2 proxy ablation without feeding scores back to optimization."""
from __future__ import annotations
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np

METRICS=("dynamic_iou","flow_distribution","track2d_dtw","trajectory_dtw","emd_step","scene_3d")
ARMS=("P0","P1","P2")

def rankdata(x):
    order=np.argsort(x,kind="mergesort"); ranks=np.empty(len(x),float); i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[order[j]]==x[order[i]]: j+=1
        ranks[order[i:j]]=(i+j-1)/2+1; i=j
    return ranks

def spearman(x,y):
    if len(x)<3:return None
    rx,ry=rankdata(np.asarray(x,float)),rankdata(np.asarray(y,float))
    if np.std(rx)==0 or np.std(ry)==0:return None
    return float(np.corrcoef(rx,ry)[0,1])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--run-id",required=True); ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); args=ap.parse_args()
    run=args.root/"runs"/args.run_id; rows=[]
    for arm in ARMS:
        for case_dir in sorted((run/arm).iterdir() if (run/arm).is_dir() else []):
            if not case_dir.is_dir():continue
            reward=case_dir/"results"/"reward.json"; cem=case_dir/"cem.json"; record=case_dir/"run.json"
            if not (reward.exists() and cem.exists() and record.exists()):continue
            rw=json.loads(reward.read_text()); ce=json.loads(cem.read_text()); rr=json.loads(record.read_text())
            row={"arm":arm,"case":case_dir.name,"checker_ok":bool(rr.get("checker_ok")),"objective":ce.get("objective")}
            row.update({f"proxy_{k}":v for k,v in ce.get("proxy",{}).get("components",{}).items()})
            for m in METRICS: row[m]=rw.get(m)
            rows.append(row)
    summary={"run_id":args.run_id,"n_rows":len(rows),"arms":{},"spearman":{}}
    for arm in ARMS:
        rr=[r for r in rows if r["arm"]==arm]; summary["arms"][arm]={"n":len(rr),"checker_pass":sum(r["checker_ok"] for r in rr)}
        for m in METRICS:
            vals=[float(r[m]) for r in rr if isinstance(r.get(m),(int,float)) and math.isfinite(float(r[m]))]
            if vals: summary["arms"][arm][m]={"mean":float(np.mean(vals)),"n":len(vals)}
        for p in ("objective","proxy_flow","proxy_mask","proxy_track"):
            for m in METRICS:
                pairs=[(float(r[p]),float(r[m])) for r in rr if isinstance(r.get(p),(int,float)) and isinstance(r.get(m),(int,float))]
                rho=spearman([a for a,b in pairs],[b for a,b in pairs])
                if rho is not None: summary["spearman"][f"{arm}:{p}:{m}"]={"rho":rho,"n":len(pairs)}
    # Paired deltas are raw metric deltas; direction interpretation stays in the report.
    paired={}
    by={(r["arm"],r["case"]):r for r in rows}
    for child in ("P1","P2"):
        parent="P0" if child=="P1" else "P1"
        for m in METRICS:
            ds=[]
            for case in sorted({r["case"] for r in rows}):
                a,b=by.get((parent,case)),by.get((child,case))
                if a and b and isinstance(a.get(m),(int,float)) and isinstance(b.get(m),(int,float)): ds.append(float(b[m])-float(a[m]))
            if ds: paired[f"{child}-{parent}:{m}"]={"mean_delta":float(np.mean(ds)),"n":len(ds),"win_positive":sum(d>0 for d in ds),"tie":sum(d==0 for d in ds),"win_negative":sum(d<0 for d in ds)}
    summary["paired_raw_deltas"]=paired
    out=run/"proxy_ablation_analysis.json"; out.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n"); print(out)
if __name__=="__main__": main()
