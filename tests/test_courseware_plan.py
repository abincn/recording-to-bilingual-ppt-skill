"""Regression tests: a courseware plan must adapt to its recording, not a subject."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from courseware_plan import validate_plan, specs_from_plan, render_image


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.cues = [
            {"start": .3, "end": 1.1, "en": "First topic."},
            {"start": 1.8, "end": 2.4, "en": "Evidence."},
            {"start": 3.1, "end": 3.8, "en": "Next topic."},
            {"start": 4.2, "end": 4.9, "en": "Comparison."},
        ]
        self.plan = {"schema_version": 1, "slides": [
            {"cue_start": 1, "cue_end": 2, "title": "How it works | 工作原理",
             "layout": "steps", "bullets": ["Observe / 观察", "Explain / 解释"]},
            {"cue_start": 3, "cue_end": 4, "title": "Comparison | 对比",
             "layout": "comparison",
             "table": {"columns": ["Feature / 特征", "A", "B"],
                       "rows": [["Method / 方法", "Option A", "Option B"],
                                {"cells": ["Result / 结果", "1", "2"], "emphasis": True}],
                       "footnote": "Illustrative values only / 示例值"}},
        ]}

    def test_topic_aligned_cues(self):
        slides = validate_plan(self.plan, self.cues, 5.2)
        specs = specs_from_plan(slides, self.cues, 5.2)
        self.assertEqual([s["cues"] for s in specs], [[1, 2], [3, 4]])
        self.assertEqual(specs[0]["start"], 0)
        self.assertEqual(specs[0]["end"], self.cues[2]["start"])
        self.assertEqual(specs[-1]["end"], 5.2)
        self.assertEqual(slides[1]["table"]["rows"][-1]["emphasis"], True)

    def test_no_omissions_or_overlap(self):
        self.plan["slides"][1]["cue_start"] = 4
        with self.assertRaisesRegex(ValueError, "contiguous"):
            validate_plan(self.plan, self.cues, 5.2)

    def test_layout_validation(self):
        self.plan["slides"][0]["layout"] = "accounting-only"
        with self.assertRaisesRegex(ValueError, "unknown layout"):
            validate_plan(self.plan, self.cues, 5.2)
        self.plan["slides"][0]["layout"] = "steps"
        self.plan["slides"][1]["table"]["rows"][0] = ["too few cells"]
        with self.assertRaisesRegex(ValueError, "column count"):
            validate_plan(self.plan, self.cues, 5.2)

    def test_no_silent_footnote_truncation(self):
        self.plan["slides"][1]["table"]["footnote"] = "注意" * 130
        with self.assertRaisesRegex(ValueError, "footnote"):
            validate_plan(self.plan, self.cues, 5.2)

    def test_render_multiple_domains(self):
        from PIL import ImageFont
        font = str(Path(ImageFont.__file__).parent / "fonts" / "DejaVuSans.ttf")
        if not Path(font).exists():
            font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if not Path(font).exists():
            self.skipTest("No font for rendering test")
        slides = validate_plan(self.plan, self.cues, 5.2)
        with tempfile.TemporaryDirectory() as temp:
            for i, slide in enumerate(slides):
                target = Path(temp) / f"slide{i}.png"
                render_image(target, slide, "F6FBF3", font)
                self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
