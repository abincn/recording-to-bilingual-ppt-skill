"""Core correctness and adversarial input tests. Run with python -m unittest discover."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from pipeline_core import (check_cues, contrast, cues_from_words, hex_color, numbers_preserved,
                           palette, partition_cues, require_translation, safe_project_file)
from make_ass import lines_for, slide_events, escaped

class CoreTests(unittest.TestCase):
    def test_contrast_uses_srgb_not_yiq(self):
        self.assertGreaterEqual(contrast("00FF00", palette("00FF00")["text_color"]), 4.5)
        self.assertGreaterEqual(contrast("808080", palette("808080")["text_color"]), 4.5)
        self.assertRaises(ValueError, palette, "00FF00", "FFFFFF")
        self.assertRaises(ValueError, hex_color, "zzzzzz")

    def test_exact_translation_ids(self):
        cues = [{"start":0, "end":1, "en":"One."}, {"start":1.2, "end":2, "en":"Two."}]
        self.assertEqual(len(require_translation(cues, {"1":"一。","2":"二。"})), 2)
        with self.assertRaises(ValueError):
            require_translation(cues, {"2":"二。","3":"三。"})
        self.assertTrue(numbers_preserved("13-3 = 10", "13减去3等于10"))
        self.assertTrue(numbers_preserved("$75 ,800", "75,800美元"))
        self.assertFalse(numbers_preserved("13-3 = 10", "13减去4等于10"))

    def test_automated_translation_retry_and_loopback_check(self):
        from run_pipeline import translate, ollama_json
        cues = [{"start":0,"end":1,"en":"Revenue is 42."}]
        with patch("run_pipeline.ollama_json", side_effect=[
            {"1":"收入是41。"}, {"1":"收入是42。"}
        ]) as mock:
            result = translate(cues)
        self.assertEqual(result[1], "收入是42。")
        self.assertEqual(mock.call_count, 2)
        with self.assertRaises(ValueError):
            ollama_json("secret", "test", "http://127.0.0.1:11434@evil.example")

    def test_sentence_timing(self):
        words = [{"start":0, "end":.4, "word":"Hello"},
                 {"start":.5, "end":1, "word":"world."},
                 {"start":1.2, "end":1.8, "word":"Bye!"}]
        cues = cues_from_words(words)
        self.assertEqual(len(cues), 2)
        slides = partition_cues(cues, 2.5, 2)
        self.assertEqual(slides[0]["cues"], [1])
        self.assertEqual(slides[1]["cues"], [2])
        self.assertAlmostEqual(slides[0]["end"], slides[1]["start"])
        self.assertRaises(ValueError, check_cues,
                          [{"start":0,"end":3,"en":"A"},{"start":1,"end":2,"en":"B"}])

    def test_ass_escaping_and_overflow(self):
        self.assertNotIn("{", escaped(r"hello {\fs200} \N"))
        self.assertGreater(lines_for("One.", "这是中文。")[0], 20)
        with self.assertRaises(ValueError):
            lines_for("many " * 600, "很长" * 600)

    def test_splice_and_path(self):
        cues = [{"start":0,"end":1,"en":"One."}, {"start":2,"end":3,"en":"Two."}]
        specs = {"segments":[{"cues":[1],"source_start":0,"source_end":1},
                             {"cues":[2],"source_start":2,"source_end":3}]}
        self.assertEqual(slide_events(cues, specs), [(0,1,1),(1,2,2)])
        with tempfile.TemporaryDirectory() as folder:
            self.assertRaises(ValueError, safe_project_file, folder, "../secret.txt")
            self.assertEqual(safe_project_file(folder, "sub/file.txt"), Path(folder)/"sub/file.txt")

if __name__ == "__main__":
    unittest.main()
