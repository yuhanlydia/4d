"""Video-only proxy measurements and bounded CEM refinement for scene DSLs."""

from __future__ import annotations
import copy, math
from pathlib import Path
from typing import Any
import cv2
import numpy as np
from .cem import CEMResult, cem_minimize
from .losses import sliced_wasserstein
from .scene import validate_scene

PROXY_MODES = ("flow", "flow_mask", "flow_mask_track")
PROXY_WEIGHTS = {
    "flow": {"flow": 1.0, "mask": 0.0, "track": 0.0},
    "flow_mask": {"flow": 1.0, "mask": 1.0, "track": 0.0},
    "flow_mask_track": {"flow": 1.0, "mask": 1.0, "track": 1.0},
}

def _sample_video(video_path: str | Path, samples: int = 8):
    cap=cv2.VideoCapture(str(video_path))
    if not cap.isOpened(): raise RuntimeError(f"cannot open video: {video_path}")
    count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps=float(cap.get(cv2.CAP_PROP_FPS))
    if count < 2 or not math.isfinite(fps) or fps <= 0:
        cap.release(); raise RuntimeError("video must contain at least two frames and positive fps")
    indices=np.linspace(0,count-1,num=min(samples,count),dtype=int); frames=[]
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES,int(idx)); ok,frame=cap.read()
        if not ok: cap.release(); raise RuntimeError(f"failed to decode frame {idx}")
        frames.append(cv2.cvtColor(cv2.resize(frame,(160,90),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY))
    cap.release()
    return frames, indices, fps

def observed_measurements(video_path: str | Path, *, samples: int = 8, max_vectors: int = 2048):
    """Deterministic measurements derived only from the input video."""
    frames,indices,fps=_sample_video(video_path,samples)
    rng=np.random.default_rng(0); flows=[]; masks=[]; tracks=[]; times=[]
    for i,(left,right) in enumerate(zip(frames,frames[1:])):
        flow=cv2.calcOpticalFlowFarneback(left,right,None,0.5,3,15,3,5,1.2,0)
        mag=np.linalg.norm(flow,axis=-1)
        active=np.flatnonzero((mag>0.5)&(mag<80.0))
        if len(active)>max_vectors: active=rng.choice(active,size=max_vectors,replace=False)
        vec=flow.reshape(-1,2)[active].astype(np.float64)
        flows.append(vec if len(vec) else np.zeros((1,2),dtype=np.float64))
        # Foreground-change occupancy: robust threshold on temporal intensity change.
        diff=cv2.absdiff(left,right).astype(np.float32)
        threshold=max(12.0,float(np.median(diff)+2.5*np.median(np.abs(diff-np.median(diff)))))
        masks.append(float(np.mean(diff>threshold)))
        pts=cv2.goodFeaturesToTrack(left,maxCorners=256,qualityLevel=0.01,minDistance=5)
        disp=np.zeros((1,2),dtype=np.float64)
        if pts is not None:
            nxt,status,_=cv2.calcOpticalFlowPyrLK(left,right,pts,None)
            good=status.reshape(-1).astype(bool) if status is not None else np.zeros(len(pts),bool)
            if nxt is not None and np.any(good):
                d=(nxt[good]-pts[good]).reshape(-1,2).astype(np.float64)
                sane=np.linalg.norm(d,axis=1)<80.0
                if np.any(sane): disp=d[sane]
        tracks.append(disp)
        times.append(float(indices[i+1]-indices[i])/fps)
    return {"flow":flows,"mask":masks,"track":tracks},times

def observed_flow(video_path: str | Path, *, samples: int = 8, max_vectors: int = 2048):
    m,t=observed_measurements(video_path,samples=samples,max_vectors=max_vectors)
    return m["flow"],t

def _rotation_xyz(e):
    x,y,z=e; sx,cx=math.sin(x),math.cos(x); sy,cy=math.sin(y),math.cos(y); sz,cz=math.sin(z),math.cos(z)
    return np.array([[cy*cz,cz*sx*sy-cx*sz,sx*sz+cx*cz*sy],[cy*sz,cx*cz+sx*sy*sz,cx*sy*sz-cz*sx],[-sy,cy*sx,cx*cy]],dtype=np.float64)

def _axis_rotation(axis,angle):
    axis=axis/max(float(np.linalg.norm(axis)),1e-12); x,y,z=axis; c,s,q=math.cos(angle),math.sin(angle),1-math.cos(angle)
    return np.array([[c+x*x*q,x*y*q-z*s,x*z*q+y*s],[y*x*q+z*s,c+y*y*q,y*z*q-x*s],[z*x*q-y*s,z*y*q+x*s,c+z*z*q]],dtype=np.float64)

def _projected(scene, intervals):
    validate_scene(scene); K=np.asarray(scene["camera"]["intrinsics"],float); E=np.asarray(scene["camera"]["extrinsic"],float)
    w,h=scene["video"]["width"],scene["video"]["height"]; projection=np.diag([160/w,90/h,1.0])@K
    duration=(scene["video"]["frames"]-1)/float(scene["video"]["fps"]); ts=np.linspace(0,duration,num=len(intervals)+1)
    per_obj=[]
    for obj in scene["objects"]:
        size=np.asarray(obj["size"],float)
        anchors=np.vstack([np.zeros(3),np.diag(size/2),-np.diag(size/2)])
        base=_rotation_xyz(obj.get("rotation_euler",[0,0,0])); motion=obj.get("motion",{"type":"static"}); positions=[]
        for time in ts:
            center=np.asarray(obj["position"],float); rotation=base
            if motion["type"]=="linear": center=center+np.asarray(motion["velocity"])*time
            elif motion["type"]=="hinge":
                pivot=np.asarray(motion["pivot"],float); frac=time/max(duration,1e-12)
                angle=float(motion["angle_start"])+frac*(float(motion["angle_end"])-float(motion["angle_start"]))
                hr=_axis_rotation(np.asarray(motion["axis"]),angle); center=pivot+hr@(center-pivot); rotation=hr@base
            world=center+anchors@rotation.T; camera=(world-E[:3,3])@E[:3,:3]; pix=camera@projection.T
            valid=pix[:,2]>1e-5; xy=np.full((len(pix),2),np.nan); xy[valid]=pix[valid,:2]/pix[valid,2:3]; positions.append(xy)
        per_obj.append(positions)
    return per_obj

def predicted_measurements(scene: dict[str,Any], intervals):
    projected=_projected(scene,intervals); flows=[]; masks=[]; tracks=[]
    for i in range(len(intervals)):
        ds=[]; occupied=np.zeros((90,160),dtype=np.uint8)
        for positions in projected:
            a,b=positions[i],positions[i+1]; valid=np.isfinite(a).all(1)&np.isfinite(b).all(1)
            if np.any(valid):
                ds.append(b[valid]-a[valid])
                for p in np.vstack([a[valid],b[valid]]):
                    x,y=np.rint(p).astype(int)
                    if 0<=x<160 and 0<=y<90: cv2.circle(occupied,(x,y),4,1,-1)
        d=np.concatenate(ds) if ds else np.zeros((1,2))
        flows.append(d); tracks.append(d); masks.append(float(occupied.mean()))
    return {"flow":flows,"mask":masks,"track":tracks}

def predicted_flow(scene,intervals): return predicted_measurements(scene,intervals)["flow"]

def proxy_components(target,prediction):
    flow=float(np.mean([sliced_wasserstein(a,b,projections=8,quantiles=32,seed=i) for i,(a,b) in enumerate(zip(target["flow"],prediction["flow"]))]))
    track=float(np.mean([sliced_wasserstein(a,b,projections=8,quantiles=32,seed=100+i) for i,(a,b) in enumerate(zip(target["track"],prediction["track"]))]))
    mask=float(np.mean(np.abs(np.asarray(target["mask"])-np.asarray(prediction["mask"]))))
    return {"flow":flow,"mask":mask,"track":track}

def optimize_motion(scene: dict[str,Any], video_path: str|Path, *, population=32, iterations=8, seed=0, proxy_mode="flow"):
    if proxy_mode not in PROXY_MODES: raise ValueError(f"proxy_mode must be one of {PROXY_MODES}")
    validate_scene(scene); target,intervals=observed_measurements(video_path); parameters=[]; mean=[]; std=[]; lower=[]; upper=[]
    for idx,obj in enumerate(scene["objects"]):
        motion=obj.get("motion",{"type":"static"})
        if motion["type"]=="linear":
            for axis,value in enumerate(motion["velocity"]):
                parameters.append((idx,f"velocity:{axis}")); mean.append(float(value)); std.append(1.0); lower.append(-8.0); upper.append(8.0)
        elif motion["type"]=="hinge":
            parameters.append((idx,"angle_end")); mean.append(float(motion["angle_end"])); std.append(.5); lower.append(-2*math.pi); upper.append(2*math.pi)
    if not parameters:
        parameters=[(idx,f"velocity:{axis}") for idx,obj in enumerate(scene["objects"]) if obj.get("motion",{"type":"static"})["type"]=="static" for axis in range(3)]
        mean=[0.0]*len(parameters); std=[1.0]*len(parameters); lower=[-8.0]*len(parameters); upper=[8.0]*len(parameters)
    def materialize(values):
        cand=copy.deepcopy(scene)
        for value,(idx,field) in zip(values,parameters):
            if field.startswith("velocity:"):
                obj=cand["objects"][idx]; motion=obj.setdefault("motion",{"type":"linear","velocity":[0.,0.,0.]})
                if motion["type"]=="static": motion={"type":"linear","velocity":[0.,0.,0.]}; obj["motion"]=motion
                motion["velocity"][int(field.split(":")[1])]=float(value)
            else: cand["objects"][idx]["motion"][field]=float(value)
        return cand
    weights=PROXY_WEIGHTS[proxy_mode]
    def components(values): return proxy_components(target,predicted_measurements(materialize(values),intervals))
    def objective(values):
        c=components(values); return sum(weights[k]*c[k] for k in weights)
    result=cem_minimize(objective,mean,std,lower=lower,upper=upper,population=population,iterations=iterations,seed=seed)
    final=components(result.x)
    return materialize(result.x),result,{"mode":proxy_mode,"weights":weights,"components":final}
