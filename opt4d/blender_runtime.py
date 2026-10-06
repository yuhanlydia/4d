"""Blender-side runtime emitted as solution/build.py by opt4d.scene.

Usage (normally via build.sh):
  blender --background --factory-startup --python build.py -- world
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

SCENE_SPEC = None


def args_after_dash():
    if "--" not in sys.argv:
        raise SystemExit("expected -- world")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) == 1 and SCENE_SPEC is not None:
        return SCENE_SPEC, Path(args[0])
    if len(args) == 2:
        return json.loads(Path(args[0]).read_text(encoding="utf-8")), Path(args[1])
    raise SystemExit("expected -- world")


def make_object(spec):
    kind = spec["kind"]
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1.0)
    elif kind == "uv_sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.5)
    else:
        raise ValueError(kind)
    obj = bpy.context.object
    obj.name = spec["name"]
    obj.scale = Vector(spec["size"])
    if kind == "cube":
        obj.scale *= 0.5
    obj.location = Vector(spec["position"])
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = spec.get("rotation_euler", [0, 0, 0])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def animate(obj, spec, frames, fps):
    motion = spec.get("motion", {"type": "static"})
    kind = motion["type"]
    if kind == "static":
        return False
    if kind == "linear":
        p0 = Vector(spec["position"])
        velocity = Vector(motion["velocity"])
        obj.location = p0
        obj.keyframe_insert("location", frame=1)
        obj.location = p0 + velocity * ((frames - 1) / fps)
        obj.keyframe_insert("location", frame=frames)
        for curve in action_fcurves(obj.animation_data.action):
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
        return True
    if kind == "hinge":
        pivot = Vector(motion["pivot"])
        axis = Vector(motion["axis"]).normalized()
        # Empty at the world-space hinge pivot; object keeps its world transform.
        empty = bpy.data.objects.new(spec["name"] + "__hinge", None)
        bpy.context.scene.collection.objects.link(empty)
        empty.location = pivot
        world = obj.matrix_world.copy()
        obj.parent = empty
        obj.matrix_world = world
        empty.rotation_mode = "QUATERNION"
        a0 = float(motion.get("angle_start", 0.0))
        a1 = float(motion.get("angle_end", 0.0))
        empty.rotation_quaternion = axis.rotation_difference(axis)  # identity
        empty.rotation_quaternion = Matrix.Rotation(a0, 4, axis).to_quaternion()
        empty.keyframe_insert("rotation_quaternion", frame=1)
        empty.rotation_quaternion = Matrix.Rotation(a1, 4, axis).to_quaternion()
        empty.keyframe_insert("rotation_quaternion", frame=frames)
        for curve in action_fcurves(empty.animation_data.action):
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
        return True
    raise ValueError(kind)


def action_fcurves(action):
    """Return F-curves across Blender's legacy and layered Action APIs."""
    if hasattr(action, "fcurves"):
        return action.fcurves
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                curves.extend(channelbag.fcurves)
    return curves


def configure_camera(scene, spec):
    K = np.asarray(spec["intrinsics"], dtype=np.float64)
    E = np.asarray(spec["extrinsic"], dtype=np.float64)
    data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    # Benchmark: +x right, +y down, +z forward. Blender camera: +x right,
    # +y up, -z forward. Flip benchmark y/z axes to obtain Blender c2w.
    flip = np.diag([1.0, -1.0, -1.0, 1.0])
    cam.matrix_world = Matrix((E @ flip).tolist())

    width = scene.render.resolution_x
    height = scene.render.resolution_y
    fx, fy = K[0, 0], K[1, 1]
    # DSL v1 requires square pixels and centered principal point; checker camera
    # still receives the exact supplied K.
    if abs(fx - fy) > 1e-4 * max(fx, fy):
        raise ValueError("DSL v1 Blender render requires fx ~= fy")
    if abs(K[0, 2] - width / 2) > 1e-4 or abs(K[1, 2] - height / 2) > 1e-4:
        raise ValueError("DSL v1 Blender render requires centered principal point")
    data.sensor_fit = "HORIZONTAL"
    data.sensor_width = 36.0
    data.lens = float(fx) * data.sensor_width / width
    return K, E


def evaluated_mesh_world(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertices = np.asarray([evaluated.matrix_world @ v.co for v in mesh.vertices], dtype=np.float32)
        faces = []
        for poly in mesh.polygons:
            verts = list(poly.vertices)
            if len(verts) == 3:
                faces.append(verts)
            else:
                # Blender primitives are triangulated deterministically as a fan.
                for j in range(1, len(verts) - 1):
                    faces.append([verts[0], verts[j], verts[j + 1]])
        return vertices, np.asarray(faces, dtype=np.int32)
    finally:
        evaluated.to_mesh_clear()


def main():
    spec, world = args_after_dash()
    video = spec["video"]
    world.mkdir(parents=True, exist_ok=True)
    (world / "meshes").mkdir()
    (world / "dynamics").mkdir()

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = int(video["frames"])
    scene.render.resolution_x = int(video["width"])
    scene.render.resolution_y = int(video["height"])
    scene.render.resolution_percentage = 100
    scene.render.fps = int(round(float(video["fps"])))
    if abs(scene.render.fps - float(video["fps"])) > 1e-6:
        raise ValueError("DSL v1 requires integer fps")
    K, E = configure_camera(scene, spec["camera"])

    objects = []
    moving = []
    for item in spec["objects"]:
        obj = make_object(item)
        is_moving = animate(obj, item, int(video["frames"]), float(video["fps"]))
        objects.append((item, obj))
        if is_moving:
            moving.append((item, obj))

    # Simple neutral lighting; lights are not benchmark geometry.
    world_bg = scene.world or bpy.data.worlds.new("World")
    scene.world = world_bg
    world_bg.color = (0.05, 0.05, 0.05)
    light_data = bpy.data.lights.new("Key", type="AREA")
    light_data.energy = 1200
    light_data.size = 5
    light = bpy.data.objects.new("Key", light_data)
    scene.collection.objects.link(light)
    light.location = (4, -4, 6)

    mesh_frames = {item["id"]: {} for item, _ in objects}
    dyn_frames = {item["id"]: [] for item, _ in moving}
    dyn_faces = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for t in range(int(video["frames"])):
        scene.frame_set(t + 1)
        depsgraph.update()
        for item, obj in objects:
            vertices, faces = evaluated_mesh_world(obj, depsgraph)
            mesh_frames[item["id"]][f"vertices_{t:04d}"] = vertices
            mesh_frames[item["id"]][f"faces_{t:04d}"] = faces
            if any(item["id"] == moving_item["id"] for moving_item, _ in moving):
                dyn_frames[item["id"]].append(vertices)
                dyn_faces.setdefault(item["id"], faces)

    for item, _ in objects:
        np.savez_compressed(world / "meshes" / f"{item['id']}.npz", **mesh_frames[item["id"]])
    for item, _ in moving:
        oid = item["id"]
        pos = np.stack(dyn_frames[oid], axis=0).astype(np.float32)
        np.savez_compressed(
            world / "dynamics" / f"{item['name']}.npz",
            pos=pos,
            ids=np.asarray([oid], dtype=np.uint16),
            faces=dyn_faces[oid].astype(np.int32),
        )

    (world / "camera.json").write_text(
        json.dumps({"intrinsics": K.tolist(), "extrinsic": E.tolist()}, indent=2) + "\n",
        encoding="utf-8",
    )

    frames_dir = world / "frames"
    frames_dir.mkdir()
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str((frames_dir / "frame_").resolve())
    bpy.ops.render.render(animation=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(video["fps"]),
            "-i",
            str((frames_dir / "frame_%04d.png").resolve()),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str((world / "render.mp4").resolve()),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()

