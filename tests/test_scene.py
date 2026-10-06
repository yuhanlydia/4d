from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from opt4d.scene import compile_solution, validate_scene


def fixture(motion=None):
    return {
        "schema_version": 1,
        "video": {"width": 64, "height": 48, "frames": 8, "fps": 24},
        "camera": {
            "intrinsics": [[50, 0, 32], [0, 50, 24], [0, 0, 1]],
            "extrinsic": [[1, 0, 0, 0], [0, 1, 0, -4], [0, 0, 1, 2], [0, 0, 0, 1]],
        },
        "objects": [{
            "id": 1, "name": "body", "kind": "cube", "size": [1, 1, 1],
            "position": [0, 0, 0], "rotation_euler": [0, 0, 0],
            "motion": motion or {"type": "static"},
        }],
    }


class SceneTests(unittest.TestCase):
    def test_static_linear_and_hinge_validate(self):
        validate_scene(fixture())
        validate_scene(fixture({"type": "linear", "velocity": [1, 0, 0]}))
        validate_scene(fixture({
            "type": "hinge", "axis": [0, 0, 1], "pivot": [0, 0, 0],
            "angle_start": 0, "angle_end": 1.2,
        }))

    def test_duplicate_ids_and_zero_hinge_rejected(self):
        scene = fixture()
        scene["objects"].append(dict(scene["objects"][0], name="other"))
        with self.assertRaises(ValueError):
            validate_scene(scene)
        with self.assertRaises(ValueError):
            validate_scene(fixture({
                "type": "hinge", "axis": [0, 0, 0], "pivot": [0, 0, 0],
                "angle_start": 0, "angle_end": 1,
            }))

    def test_compiler_is_self_contained_and_native(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "scene.json"
            src.write_text(json.dumps(fixture()), encoding="utf-8")
            out = compile_solution(src, root / "solution")
            self.assertTrue((out / "build.sh").is_file())
            self.assertTrue((out / "build.py").is_file())
            self.assertFalse((out / "scene.json").exists())
            build = (out / "build.sh").read_text(encoding="utf-8")
            self.assertIn("blender --background", build)
            self.assertIn('"$WORKSPACE/world"', build)
            self.assertNotIn("docker", build.lower())
            self.assertNotIn("reference.mp4", (out / "build.py").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()

