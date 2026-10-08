import unittest

import numpy as np

from scripts.diagnose_proxy_sensitivity import (
    DELTAS, candidate_bank, motion_parameters, perturbed_scene,
    rank_agreement, summarize_candidate_rows,
)

SCENE = {
    "schema_version": 1,
    "video": {"width": 160, "height": 90, "frames": 8, "fps": 8.0},
    "camera": {
        "intrinsics": [[160, 0, 80], [0, 160, 45], [0, 0, 1]],
        "extrinsic": [[1, 0, 0, 0], [0, 1, 0, 0],
                      [0, 0, 1, 0], [0, 0, 0, 1]],
    },
    "objects": [{
        "id": 1, "name": "test", "kind": "cube",
        "size": [1, 1, 1], "position": [0, 0, 3],
        "rotation_euler": [0, 0, 0],
        "motion": {"type": "linear", "velocity": [0, 0, 0]},
    }],
}


class ProxySensitivityTests(unittest.TestCase):
    def test_frozen_candidate_bank(self):
        bank, all_params, selected = candidate_bank(SCENE, max_parameters=2)
        self.assertEqual(len(all_params), 3)
        self.assertEqual(len(selected), 2)
        self.assertEqual(len(bank), 1 + 2 * len(DELTAS))
        self.assertEqual(bank[0][0], "base")
        self.assertEqual(SCENE["objects"][0]["motion"]["velocity"], [0, 0, 0])

    def test_bounded_perturbation_is_non_mutating(self):
        candidate = perturbed_scene(SCENE, (0, "velocity", 0), 0.25)
        self.assertEqual(candidate["objects"][0]["motion"]["velocity"][0], 0.25)
        self.assertEqual(SCENE["objects"][0]["motion"]["velocity"][0], 0)

    def test_static_fallback_only_if_no_dynamic_parameters(self):
        scene = {**SCENE, "objects": [
            {**SCENE["objects"][0], "motion": {"type": "static"}}
        ]}
        self.assertEqual(motion_parameters(scene)[0], (0, "promote_velocity", 0))
        candidate = perturbed_scene(scene, (0, "promote_velocity", 1), 1.0)
        self.assertEqual(candidate["objects"][0]["motion"]["type"], "linear")
        self.assertEqual(candidate["objects"][0]["motion"]["velocity"], [0, 1, 0])

    def test_rank_ties_and_flat_component_are_explicit(self):
        self.assertIsNone(rank_agreement([1, 1, 1], [3, 2, 1]))
        self.assertAlmostEqual(rank_agreement([3, 2, 1], [6, 4, 2]), 1)
        rows = [
            {"candidate": "base",
             "components": {"flow": 1., "mask": 0.5, "track": 2.},
             "objective": {"P0": 1., "P1": 1.5, "P2": 3.5}},
            {"candidate": "variant",
             "components": {"flow": 0.5, "mask": 0.5, "track": 1.},
             "objective": {"P0": 0.5, "P1": 1., "P2": 2.}},
        ]
        summary = summarize_candidate_rows(rows)
        self.assertTrue(summary["component_sensitivity"]["mask"]["flat_at_1e-12"])
        self.assertTrue(summary["objectives"]["P1"]["same_argmin_as_p0"])
        self.assertEqual(summary["objectives"]["P2"]["best_candidate"], "variant")


if __name__ == "__main__":
    unittest.main()
