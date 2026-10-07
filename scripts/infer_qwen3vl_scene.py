#!/usr/bin/env python3
"""Generate one Opt4D scene from an official benchmark reference video."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from opt4d.scene import validate_scene


DIRECT_PROMPT = """Infer a complete 4D scene from this video. Return exactly one JSON object with keys schema_version, video, camera, and objects. The exact video metadata is: {metadata}. Copy these values exactly. Use camera intrinsics [[width,0,width/2],[0,width,height/2],[0,0,1]] and identity 4x4 camera extrinsic. The object format is {{\"id\":1,\"name\":\"object_1\",\"kind\":\"cube\",\"size\":[0.5,0.5,0.5],\"position\":[0,0,3],\"rotation_euler\":[0,0,0],\"motion\":{{\"type\":\"static\"}}}}. Each object needs a unique positive id and name, kind cube or uv_sphere, positive size, position [x,y,z] with visible objects at positive z, rotation_euler in radians, and motion {{type: static}}, {{type: linear, velocity: [vx,vy,vz]}}, or {{type: hinge, axis: [x,y,z], pivot: [x,y,z], angle_start: radians, angle_end: radians}}. Observe temporal changes and encode moving objects as linear or hinge. Output the entire schema shown here, with the actual metadata values, and no prose or markdown."""

DSL_PROMPT = """Infer the visible rigid objects and their motion from this video. Return exactly one JSON object containing only an objects array, with no prose or markdown. The required top-level shape is {\"objects\":[{\"id\":1,\"name\":\"object_1\",\"kind\":\"cube\",\"size\":[0.5,0.5,0.5],\"position\":[0,0,3],\"rotation_euler\":[0,0,0],\"motion\":{\"type\":\"linear\",\"velocity\":[0.1,0,0]}}]}. Do not return a bare array. Each object needs a unique positive id and name, kind cube or uv_sphere, positive size [x,y,z], position [x,y,z] in camera coordinates with visible objects at positive z, rotation_euler in radians, and motion {type: static}, {type: linear, velocity: [vx,vy,vz]}, or {type: hinge, axis: [x,y,z], pivot: [x,y,z], angle_start: radians, angle_end: radians}. Use exactly these field names; do not use `rotation` instead of `rotation_euler`. Compare early and late frames and encode moving objects as linear or hinge. Use one object per visually distinct rigid or articulated part. The compiler supplies video metadata and camera. Output only the JSON object in the example shape."""


def generate(video_path: Path, model_path: Path, method: str, max_new_tokens: int) -> tuple[dict | None, dict]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    metadata = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
    }
    if min(metadata["width"], metadata["height"], metadata["frames"]) <= 0 or metadata["fps"] <= 0:
        cap.release()
        raise RuntimeError(f"invalid video metadata: {metadata}")
    indices = np.linspace(0, metadata["frames"] - 1, num=min(8, metadata["frames"]), dtype=int)
    frames = []
    for index in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, frame = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError(f"failed to decode frame {index}")
        frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    cap.release()

    prompt = (DIRECT_PROMPT.format(metadata=json.dumps(metadata, sort_keys=True))
              if method == "direct" else DSL_PROMPT)
    duration = metadata["frames"] / metadata["fps"]
    messages = [{"role": "user", "content": [
        {"type": "video", "video": frames, "sample_fps": len(frames) / duration,
         "raw_fps": metadata["fps"], "max_pixels": 256 * 32 * 32,
         "total_pixels": 2048 * 32 * 32},
        {"type": "text", "text": prompt},
    ]}]

    started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(str(model_path), local_files_only=True)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        str(model_path), dtype=torch.float16, device_map="auto",
        attn_implementation="sdpa", local_files_only=True,
    )
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs, video_kwargs = process_vision_info(
        messages, image_patch_size=processor.image_processor.patch_size,
        return_video_kwargs=True, return_video_metadata=True,
    )
    video_metadata = None
    if video_inputs is not None:
        video_inputs, video_metadata = zip(*video_inputs)
        video_inputs, video_metadata = list(video_inputs), list(video_metadata)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs,
                       video_metadata=video_metadata, do_resize=False,
                       return_tensors="pt", **video_kwargs).to(model.device)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    generated = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    prompt_tokens = int(inputs.input_ids.shape[-1])
    response = processor.batch_decode(generated[:, prompt_tokens:], skip_special_tokens=True,
                                      clean_up_tokenization_spaces=False)[0]
    generated_tokens = int(generated.shape[-1] - prompt_tokens)
    peak_vram = (round(torch.cuda.max_memory_allocated() / 1024**3, 3)
                 if torch.cuda.is_available() else None)
    elapsed = time.perf_counter() - started
    del model, processor, inputs, generated
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    raw = {
        "status": "generated_unexecuted",
        "method": method,
        "model": "Qwen3-VL-2B-Instruct",
        "model_revision": "89644892e4d85e24eaac8bacfd4f463576704203",
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "video_sha256": hashlib.sha256(video_path.read_bytes()).hexdigest(),
        "metadata": metadata,
        "response": response,
        "prompt_tokens": prompt_tokens,
        "generated_tokens": generated_tokens,
        "wall_s": elapsed,
        "peak_vram_gib": peak_vram,
    }
    try:
        code_blocks = re.findall(r"```(?:json)?\s*(.*?)```", response, flags=re.DOTALL | re.IGNORECASE)
        payload = code_blocks[0].strip() if code_blocks else response.strip()
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            parsed = None
            for offset, char in enumerate(payload):
                if char in "{[":
                    try:
                        parsed, _ = decoder.raw_decode(payload[offset:])
                        break
                    except json.JSONDecodeError:
                        continue
            if parsed is None:
                raise ValueError("model response contains no complete JSON value")
        if method == "dsl":
            if isinstance(parsed, list):
                parsed = {"objects": parsed}
            if set(parsed) != {"objects"}:
                raise ValueError("DSL response must contain only the objects field")
            scene = {
                "schema_version": 1,
                "video": metadata,
                "camera": {
                    "intrinsics": [[metadata["width"], 0, metadata["width"] / 2],
                                   [0, metadata["width"], metadata["height"] / 2],
                                   [0, 0, 1]],
                    "extrinsic": [[1, 0, 0, 0], [0, 1, 0, 0],
                                  [0, 0, 1, 0], [0, 0, 0, 1]],
                },
                "objects": parsed["objects"],
            }
        else:
            if not isinstance(parsed, dict):
                raise ValueError("direct response must be a JSON object")
            # Direct-generation qualification repair: canonicalize only fields whose
            # exact values are already supplied verbatim in DIRECT_PROMPT. This
            # removes serialization/copying failures without repairing inferred
            # objects, geometry, motion, or adding information unavailable to B1.
            scene = dict(parsed)
            scene["schema_version"] = 1
            scene["video"] = metadata
            scene["camera"] = {
                "intrinsics": [[metadata["width"], 0, metadata["width"] / 2],
                               [0, metadata["width"], metadata["height"] / 2],
                               [0, 0, 1]],
                "extrinsic": [[1, 0, 0, 0], [0, 1, 0, 0],
                              [0, 0, 1, 0], [0, 0, 0, 1]],
            }
            raw["direct_canonicalized_fields"] = ["schema_version", "video", "camera"]
        validate_scene(scene)
    except Exception as exc:
        raw["status"] = "failed_validation"
        raw["validation_error"] = f"{type(exc).__name__}: {exc}"
        return None, raw
    raw["status"] = "locally_validated"
    return scene, raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("direct", "dsl"), required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=1200)
    args = parser.parse_args()
    try:
        scene, raw = generate(args.video, args.model, args.method, args.max_new_tokens)
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        if scene is None:
            print(f"GENERATION_FAILED: {raw['validation_error']}")
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "method": args.method,
                          "scene": str(args.output), "wall_s": raw["wall_s"],
                          "peak_vram_gib": raw["peak_vram_gib"]}))
        return 0
    except Exception as exc:
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_text(json.dumps({"status": "failed", "method": args.method,
                                               "error": f"{type(exc).__name__}: {exc}"},
                                              indent=2) + "\n", encoding="utf-8")
        print(f"GENERATION_FAILED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
