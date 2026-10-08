import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_proxy_ablation import collect_rows


class ProxyAblationAnalysisTests(unittest.TestCase):
    def test_collects_real_and_synthetic_case_layouts(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            for arm in ("P0", "P1", "P2"):
                case = "real/example" if arm == "P0" else "synthetic/B_01"
                case_dir = run / arm / case
                (case_dir / "results").mkdir(parents=True)
                (case_dir / "run.json").write_text(json.dumps({"checker_ok": True}))
                (case_dir / "cem.json").write_text(json.dumps({
                    "objective": 0.5,
                    "proxy": {"components": {"flow": 0.2}},
                }))
                (case_dir / "results" / "reward.json").write_text(
                    json.dumps({"dynamic_iou": 0.3})
                )

            rows = collect_rows(run)

        self.assertEqual(len(rows), 3)
        self.assertEqual({row["case"] for row in rows}, {"real/example", "synthetic/B_01"})
        self.assertTrue(all(row["checker_ok"] for row in rows))
        self.assertTrue(all(row["dynamic_iou"] == 0.3 for row in rows))


if __name__ == "__main__":
    unittest.main()

