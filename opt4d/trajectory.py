"""Free-trajectory and spline-to-physics homotopy for video-only motion fitting.

This module never reads benchmark scorer data. It fits a low-dimensional per-object
image-plane trajectory from legal video tracks, smooths it, then projects the
trajectory back to the existing physical scene DSL.
"""
from __future__ import annotations
import copy, math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import cv2, numpy as np
from .scene import validate_scene
from .video_proxy import _projected, observed_measurements

@dataclass
class TrajectoryFit:
    times: list[float]
    offsets_xy: list[list[float]]
    data_loss: float
    smoothness: float

def fit_free_trajectory(scene: dict[str,Any], video_path: str|Path, *, samples: int=8, smooth_lambda: float=0.25) -> TrajectoryFit:
    """Fit a shared image-plane displacement trajectory to observed LK displacements."""
    validate_scene(scene); target, intervals=observed_measurements(video_path,samples=samples)
    # Robust cumulative median LK displacement is legal and deterministic.
    increments=[]
    for d in target["track"]:
        increments.append(np.median(d,axis=0) if len(d) else np.zeros(2))
    raw=np.vstack([np.zeros(2),np.cumsum(np.asarray(increments),axis=0)])
    n=len(raw)
    # Solve min ||x-raw||^2 + lambda ||D2 x||^2 with first point fixed at zero.
    D=np.zeros((max(n-2,0),n))
    for i in range(n-2): D[i,i:i+3]=[1,-2,1]
    A=np.eye(n)+smooth_lambda*(D.T@D)
    A[0,:]=0; A[0,0]=1
    b=raw.copy(); b[0]=0
    fit=np.column_stack([np.linalg.solve(A,b[:,j]) for j in range(2)])
    data=float(np.mean((fit-raw)**2)); smooth=float(np.mean((D@fit)**2)) if len(D) else 0.0
    times=np.concatenate([[0.0],np.cumsum(intervals)])
    return TrajectoryFit(times.tolist(),fit.tolist(),data,smooth)

def _scene_anchor_centroid(scene, intervals):
    p=_projected(scene,intervals); out=[]
    for t in range(len(intervals)+1):
        pts=[obj[t] for obj in p if np.isfinite(obj[t]).all(axis=1).any()]
        valid=np.concatenate([x[np.isfinite(x).all(axis=1)] for x in pts],axis=0) if pts else np.zeros((0,2))
        out.append(np.mean(valid,axis=0) if len(valid) else np.zeros(2))
    return np.asarray(out)

def project_trajectory_to_linear(scene: dict[str,Any], fit: TrajectoryFit, *, physics_weight: float=1.0):
    """Project free image trajectory to DSL linear velocities.

    physics_weight in [0,1] interpolates from original scene motion (0) to the
    least-squares trajectory-derived velocity (1), enabling a frozen homotopy path.
    """
    if not 0<=physics_weight<=1: raise ValueError("physics_weight must be in [0,1]")
    validate_scene(scene); cand=copy.deepcopy(scene)
    times=np.asarray(fit.times,float); offsets=np.asarray(fit.offsets_xy,float)
    duration=max(float(times[-1]-times[0]),1e-9)
    slope=np.linalg.lstsq(np.column_stack([times,np.ones_like(times)]),offsets,rcond=None)[0][0]
    K=np.asarray(scene["camera"]["intrinsics"],float); w,h=scene["video"]["width"],scene["video"]["height"]
    # offsets were measured after resize to 160x90; map to native pixels.
    native=np.array([slope[0]*w/160.0,slope[1]*h/90.0])
    for obj in cand["objects"]:
        z=max(float(obj["position"][2]),1e-3)
        target=np.array([native[0]*z/K[0,0],native[1]*z/K[1,1],0.0])
        motion=obj.get("motion",{"type":"static"}); original=np.zeros(3)
        if motion["type"]=="linear": original=np.asarray(motion["velocity"],float)
        velocity=(1-physics_weight)*original+physics_weight*target
        obj["motion"]={"type":"linear","velocity":velocity.tolist()}
    validate_scene(cand); return cand

def homotopy_scenes(scene: dict[str,Any], fit: TrajectoryFit, schedule=(0.0,0.25,0.5,0.75,1.0)):
    return [(float(w),project_trajectory_to_linear(scene,fit,physics_weight=float(w))) for w in schedule]
