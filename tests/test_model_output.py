from __future__ import annotations

import unittest

from opt4d.model_output import parse_json_response


class ModelOutputTests(unittest.TestCase):
    def test_parses_fenced_json(self):
        self.assertEqual(parse_json_response('```json\n{"objects": []}\n```'), {"objects": []})

    def test_parses_json_after_prose(self):
        self.assertEqual(parse_json_response('Result:\n{"objects": []}\nDone.'), {"objects": []})

    def test_rejects_truncated_root_instead_of_salvaging_nested_object(self):
        response = '```json\n{"video": {"width": 640}, "camera": {"extrinsic": ['
        with self.assertRaisesRegex(ValueError, "complete top-level"):
            parse_json_response(response)


if __name__ == "__main__":
    unittest.main()

