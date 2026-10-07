#!/usr/bin/env python3
"""Paired developmental statistics from retained TSV rows; no method tuning."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np
METRICS=("dynamic_iou","flow_distribution","track2d_dtw","trajectory_dtw","emd_step","scene_3d")
def boot(d,n,seed):
 rng=np.random.default_rng(seed);d=np.asarray(d,float);means=np.mean(rng.choice(d,size=(n,len(d)),replace=True),axis=1);return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--results",type=Path,default=Path("results.tsv"));ap.add_argument("--baseline",required=True);ap.add_argument("--treatment",required=True);ap.add_argument("--resamples",type=int,default=10000);ap.add_argument("--seed",type=int,default=20261007);args=ap.parse_args()
 rows=list(csv.DictReader(args.results.open(),delimiter="\t"));groups={}
 for r in rows:groups.setdefault(r["experiment_id"],[]).append(r)
 a,b=groups.get(args.baseline,[]),groups.get(args.treatment,[])
 if len(a)!=len(b) or not a:raise ValueError("paired arms must have equal nonzero retained row counts")
 out={"baseline":args.baseline,"treatment":args.treatment,"n":len(a),"metrics":{}}
 for m in METRICS:
  pairs=[(float(x[m]),float(y[m])) for x,y in zip(a,b) if x.get(m) and y.get(m)]
  if pairs:
   d=[y-x for x,y in pairs];out["metrics"][m]={"mean_raw_delta":float(np.mean(d)),"bootstrap_95":boot(d,args.resamples,args.seed),"positive":sum(x>0 for x in d),"tie":sum(x==0 for x in d),"negative":sum(x<0 for x in d)}
 print(json.dumps(out,indent=2,sort_keys=True))
if __name__=="__main__":main()
