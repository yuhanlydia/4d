"""Offline tests for the native Opt4D preparation contract.

Run from repository root:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import prepare


class PrepareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bench = self.root / "4DCodeBench"
        for file in (
            "README.md",
            "environment.yml",
            "checker/__init__.py",
            "scorer/__init__.py",
            "scorer/prepare/__main__.py",
        ):
            path = self.bench / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test fixture\n", encoding="utf-8")

    def populate(self, kind: str, n: int) -> None:
        for i in range(n):
            video = self.bench / "cases" / kind / f"C_{i:02}" / "reference.mp4"
            video.parent.mkdir(parents=True, exist_ok=True)
            video.write_bytes(b"test-fixture-video-nonzero")

    def test_detects_official_layout(self) -> None:
        result = prepare.check_benchmark(self.bench)
        self.assertTrue(result["ok"], result)

    def test_missing_official_component(self) -> None:
        (self.bench / "scorer" / "prepare" / "__main__.py").unlink()
        self.assertFalse(prepare.check_benchmark(self.bench)["ok"])

    def test_reproducible_balanced_freeze_and_refuse_overwrite(self) -> None:
        self.populate("real", 8)
        self.populate("synthetic", 9)
        cases = prepare.discover_cases(self.bench)
        expected = prepare.choose_dev10(cases)
        manifest = self.root / "configs" / "dev10.txt"
        frozen = prepare.write_frozen_cases(manifest, cases)
        self.assertEqual(frozen, expected)
        self.assertEqual(sum(x.startswith("real/") for x in frozen), 5)
        self.assertEqual(sum(x.startswith("synthetic/") for x in frozen), 5)
        self.assertTrue(prepare.read_frozen_cases(manifest, self.bench)["ok"])
        with self.assertRaises(FileExistsError):
            prepare.write_frozen_cases(manifest, cases)

    def test_insufficient_cases_does_not_write_manifest(self) -> None:
        self.populate("real", 4)
        self.populate("synthetic", 5)
        manifest = self.root / "configs" / "dev10.txt"
        with self.assertRaises(ValueError):
            prepare.write_frozen_cases(manifest, prepare.discover_cases(self.bench))
        self.assertFalse(manifest.exists())

    def test_rejects_traversal_and_duplicates(self) -> None:
        manifest = self.root / "dev10.txt"
        self.populate("real", 5)
        self.populate("synthetic", 5)
        original = prepare.choose_dev10(prepare.discover_cases(self.bench))
        manifest.write_text("\n".join(original[:-1] + ["real/../private"]) + "\n")
        self.assertFalse(prepare.read_frozen_cases(manifest, self.bench)["ok"])
        manifest.write_text("\n".join(original[:-1] + [original[0]]) + "\n")
        self.assertFalse(prepare.read_frozen_cases(manifest, self.bench)["ok"])

    def test_missing_video_fails_a_frozen_manifest(self) -> None:
        self.populate("real", 5)
        self.populate("synthetic", 5)
        manifest = self.root / "dev10.txt"
        selected = prepare.write_frozen_cases(manifest, prepare.discover_cases(self.bench))
        (self.bench / "cases" / selected[0] / "reference.mp4").unlink()
        report = prepare.read_frozen_cases(manifest, self.bench)
        self.assertFalse(report["ok"])
        self.assertEqual(report["detail"]["missing_videos"], [selected[0]])

    def test_machine_readable_dry_readiness(self) -> None:
        # No actual GPU, Blender or Hugging Face files needed in unit tests.
        self.populate("real", 5)
        self.populate("synthetic", 5)
        manifest = self.root / "dev10.txt"
        prepare.write_frozen_cases(manifest, prepare.discover_cases(self.bench))
        with (
            patch.object(prepare, "check_skill", return_value={"ok": True, "detail": "sha"}),
            patch.object(prepare, "probe_command", return_value={"ok": True, "detail": "ok"}),
            patch.object(prepare, "check_gpu", return_value={"ok": True, "detail": []}),
        ):
            report = prepare.make_report(self.bench, manifest, 20.0, True)
        self.assertTrue(report["ready"])
        json.dumps(report, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
