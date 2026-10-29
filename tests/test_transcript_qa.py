"""Conservative numeric QA: finding issues must never change source text."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from transcript_qa import audit, numbers, write_report
import run_pipeline


class TranscriptQATests(unittest.TestCase):
    def setUp(self):
        self.cues = [
            {"start": 0.2, "end": 2.0, "en": "In 211, inventory fell 4,800."},
            {"start": 2.1, "end": 4.0, "en": "Under GAAP, cash increased."},
        ]

    def test_ambiguous_number_stays_unmodified(self):
        baseline = json.dumps(self.cues)
        report = audit(self.cues)
        self.assertEqual(json.dumps(self.cues), baseline)
        self.assertEqual(report["source_cues"], 2)
        first = report["issues"][0]
        self.assertEqual(first["cue_id"], 1)
        self.assertEqual(first["start"], .2)
        self.assertIn("three_digit_context_check", first["flags"])
        self.assertEqual(first["source_numbers"], ["211", "4800"])

    def test_second_pass_missing_spoken_amount_is_flagged(self):
        comparison = {"1": "In 211, inventory fell.", "2": "Under GAAP, cash increased."}
        report = audit(self.cues, second_pass=comparison, source="supplied_second_pass")
        first = report["issues"][0]
        self.assertIn("second_pass_number_disagreement", first["flags"])
        self.assertEqual(first["source_text"], self.cues[0]["en"])
        self.assertEqual(first["second_pass_numbers"], ["211"])
        self.assertEqual(report["disagreements"], 1)

    def test_timestamps_align_when_second_pass_splits_sentences(self):
        comparison = [
            {"start": .2, "end": 1., "en": "In 2011,"},
            {"start": 1., "end": 2., "en": "inventory fell 4800."},
            {"start": 2.1, "end": 4., "en": "Under GAAP, cash increased."},
        ]
        report = audit(self.cues, second_pass=comparison)
        self.assertIn("second_pass_number_disagreement", report["issues"][0]["flags"])

    def test_formatting_does_not_create_false_number_disagreement(self):
        self.assertEqual(numbers("4,800"), numbers("4800"))
        cues = [{"start": 0., "end": 1., "en": "Value 4,800."}]
        report = audit(cues, second_pass={"1": "Value 4800."})
        self.assertNotIn("second_pass_number_disagreement", report["issues"][0]["flags"])

    def test_outside_slide_number_requires_attribution_not_overwrite(self):
        slides = [{
            "cue_start": 1, "cue_end": 2, "title": "Inventory analysis",
            "layout": "table", "table": {
                "columns": ["Item", "Amount"],
                "rows": [{"cells": ["Ending balance", "5,200"], "emphasis": True}],
            },
        }]
        report = audit(self.cues, slides=slides)
        review = [x for x in report["issues"] if x["kind"] == "slide"][0]
        self.assertEqual(review["unmatched_numbers"], ["5200"])
        self.assertEqual(review["disposition"], "document_textbook_or_calculation_evidence")

    def test_writes_readable_report_with_original_timestamps(self):
        with tempfile.TemporaryDirectory() as temp:
            report = audit(self.cues)
            write_report(temp, report)
            output = json.loads((Path(temp) / "transcript-qa.json").read_text())
            prose = (Path(temp) / "transcript-qa.md").read_text()
            self.assertEqual(output["issue_count"], report["issue_count"])
            self.assertIn("0.20–2.00s", prose)
            self.assertIn("211", prose)

    def test_transcribe_stage_outputs_qa_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                 "-i", "sine=frequency=440:duration=3.5", "-y", str(source)],
                check=True,
            )
            project = root / "project"
            args = ["run_pipeline.py", "--audio", str(source), "--project",
                    str(project), "--stage", "transcribe"]
            with patch.object(sys, "argv", args), patch.object(
                run_pipeline, "transcribe", return_value=[self.cues[0]]
            ):
                run_pipeline.main()
            self.assertTrue((project / "transcript-qa.json").exists())
            self.assertTrue((project / "transcript-qa.md").exists())
            self.assertEqual(json.loads((project / "transcript-qa.json").read_text())[
                "issues"][0]["source_numbers"], ["211", "4800"])

    def test_saved_second_pass_survives_resumption_without_rechecking(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                 "-i", "sine=frequency=440:duration=3.5", "-y", str(source)],
                check=True,
            )
            project = root / "lesson"
            alternative = root / "alternate.json"
            alternative.write_text(json.dumps({"1": "In 2011, inventory fell 4800."}))
            args = ["run_pipeline.py", "--audio", str(source), "--project", str(project),
                    "--stage", "transcribe", "--qa-compare", str(alternative)]
            with patch.object(sys, "argv", args), patch.object(
                run_pipeline, "transcribe", return_value=[self.cues[0]]
            ):
                run_pipeline.main()
            self.assertEqual(
                json.loads((project / "transcript-qa.json").read_text())["disagreements"], 1
            )
            self.assertTrue((project / "qa-second-pass.json").exists())
            resumed = ["run_pipeline.py", "--audio", str(source), "--project",
                       str(project), "--stage", "transcribe", "--resume"]
            with patch.object(sys, "argv", resumed):
                run_pipeline.main()
            self.assertEqual(
                json.loads((project / "transcript-qa.json").read_text())["disagreements"], 1
            )

    def test_targeted_recheck_never_changes_original_cues(self):
        from types import SimpleNamespace
        from transcript_qa import recheck_selected

        cue = [{"start": .2, "end": 2., "en": "In 211, revenue was 4,800."}]
        word = SimpleNamespace(word=" 2011", start=.5, end=.8)
        segment = SimpleNamespace(words=[word], text="2011")
        fake_model = SimpleNamespace(transcribe=lambda *a, **kw: ([segment], None))
        fake_whisper = SimpleNamespace(WhisperModel=lambda *a, **kw: fake_model)
        fake_ffmpeg = SimpleNamespace(returncode=0, stderr="")
        original = json.dumps(cue)
        with patch.dict(sys.modules, {"faster_whisper": fake_whisper}), patch(
            "transcript_qa.subprocess.run", return_value=fake_ffmpeg
        ):
            alternate = recheck_selected("unused.wav", cue, limit=1)
        self.assertEqual(alternate[1], "2011")
        self.assertEqual(json.dumps(cue), original)
        self.assertIn("second_pass_number_disagreement", audit(
            cue, second_pass=alternate)["issues"][0]["flags"])



if __name__ == "__main__":
    unittest.main()
