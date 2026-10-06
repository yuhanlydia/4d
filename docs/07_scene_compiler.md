# Native scene DSL compiler

Milestone 2 source is implemented without Docker. The current acceptance state is
**generated_unexecuted**: source and offline contract tests exist, but a machine
with Blender and the official 4DCodeBench checkout must execute the generated
world and checker before milestone 2 is closed.

## DSL v1

A scene freezes video metadata, the benchmark camera convention, and a list of
primitive objects. Supported geometry is `cube` and `uv_sphere`. Supported
motion is `static`, constant-velocity `linear`, and `hinge` rotation about a
world-space pivot/axis.

The compiler deliberately does not read `reference.mp4`. Later measurement code
may legally estimate DSL parameters from the input video, but the generated
`solution/build.sh` is self-contained.

## Compile

```bash
python compile_scene.py path/to/scene.json runs/smoke/solution
bash runs/smoke/solution/build.sh
```

The build invokes native Blender CLI and writes:

```text
world/
  camera.json
  render.mp4
  meshes/<id>.npz
  dynamics/<name>.npz   # moving objects only
```

## Milestone-2 acceptance on the target machine

Use a smoke scene whose width, height, frame count and FPS are intentionally
chosen, then check the generated video:

```bash
ffprobe -v error -select_streams v:0 -count_frames \
  -show_entries stream=nb_read_frames,width,height,r_frame_rate \
  -of csv=p=0 runs/smoke/solution/world/render.mp4
```

Run the official checker from an unmodified 4DCodeBench checkout, pointing it at
the generated world according to the checker's CLI/environment contract:

```bash
python -m checker
```

Repeat once with `linear` motion and once with `hinge` motion. Record the exact
4DCodeBench revision, Blender version, checker output, and Opt4D commit. Do not
mark this milestone complete from unit tests alone.

## Constraints

- No Docker, Podman, Apptainer, or Singularity.
- No reference video, annotations, or privileged synthetic world is read during
  `build.sh`.
- Moving material has stable vertex identity in `dynamics/*.npz`.
- Static objects have identical per-frame geometry.
- Camera JSON uses the official +x-right, +y-down, +z-forward camera-to-world
  convention; Blender's camera basis conversion happens only in the renderer.
