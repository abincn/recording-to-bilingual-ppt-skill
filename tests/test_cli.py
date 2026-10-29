"""Orchestrator smoke test with stub ASR/translation; no model or API dependency."""
import sys
import tempfile
import subprocess
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import run_pipeline
from validate import validate
from pipeline_core import write_json, read_json
from pptx import Presentation

EXPECTED_VERSION = (Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip()

class PipelineTests(unittest.TestCase):
    def test_end_to_end_image_then_editable_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/"source.wav"
            subprocess.run(["ffmpeg","-loglevel","error","-f","lavfi","-i",
                            "sine=frequency=440:duration=3.5","-y",str(source)],check=True)
            project = root/"generated"
            cues = [{"start":.2,"end":.8,"en":"Revenue increased."},
                    {"start":1.8,"end":2.5,"en":"Check cash flow."}]
            cn = {1:"收入增加。", 2:"检查现金流量。"}
            first = ["run_pipeline.py", "--audio",str(source),"--project",str(project),
                     "--slides","2","--colors","00FF00,F6FBF3","--mode","image",
                     "--format","pptx",
                     "--translator","ollama","--autoplay"]
            with patch.object(sys,"argv",first), patch.object(run_pipeline,"transcribe",return_value=cues), \
                 patch.object(run_pipeline,"translate",return_value=cn):
                run_pipeline.main()
            self.assertEqual(validate(project/"manifest.json",project/"courseware-image.pptx")["slides"],2)
            second = ["run_pipeline.py","--audio",str(source),"--project",str(project),
                      "--slides","2","--colors","00FF00,F6FBF3","--mode","editable",
                      "--format","pptx",
                      "--translations",str(project/"sentence_cn.json"),"--resume","--autoplay"]
            with patch.object(sys,"argv",second):
                run_pipeline.main()
            self.assertEqual(validate(project/"manifest.json",project/"courseware-editable.pptx")["mode"],"editable")

    def test_subject_agnostic_curated_plan_uses_native_table(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/"voice.wav"
            subprocess.run(["ffmpeg","-loglevel","error","-f","lavfi","-i",
                            "sine=frequency=440:duration=3.2","-y",str(source)],check=True)
            project = root/"lesson"
            project.mkdir()
            cues = [{"start":.2,"end":.8,"en":"Plants capture sunlight."},
                    {"start":1.6,"end":2.5,"en":"They produce oxygen."}]
            write_json(project/"merged_cues.json", cues)
            write_json(project/"sentence_cn.json", {"1":"植物吸收阳光。","2":"它们产生氧气。"})
            write_json(project/"plan.json", {"schema_version":1,"slides":[
                {"cue_start":1,"cue_end":1,"title":"Energy | 能量",
                 "layout":"steps","bullets":["Sunlight / 阳光"]},
                {"cue_start":2,"cue_end":2,"title":"Outputs | 产物",
                 "layout":"table","table":{"columns":["Material / 物质","Output / 产物"],
                                           "rows":[["Air / 空气","Oxygen / 氧气"]]}}
            ]})
            common = ["run_pipeline.py","--audio",str(source),"--project",str(project),
                      "--resume","--translations",str(project/"sentence_cn.json"),
                      "--courseware-plan",str(project/"plan.json"),"--autoplay",
                      "--format","pptx"]
            for mode in ("image","editable"):
                with patch.object(sys,"argv",common+["--mode",mode]):
                    run_pipeline.main()
                self.assertEqual(validate(project/"manifest.json",
                                          project/f"courseware-{mode}.pptx")["slides"], 2)
            self.assertFalse(read_json(project/"manifest.json")["draft"])
            slides = Presentation(project/"courseware-editable.pptx").slides
            self.assertTrue(any(shape.has_table for shape in slides[1].shapes))

    def test_default_is_self_contained_offline_html_with_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/"lecture.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=3.5", "-y", str(source)], check=True)
            project = root/"lesson"
            cues = [{"start":.2, "end":.8, "en":"Plants capture sunlight."},
                    {"start":1.8,"end":2.5,"en":"They produce oxygen."}]
            cn = {1:"植物吸收阳光。",2:"它们产生氧气。"}
            args = ["run_pipeline.py", "--audio", str(source), "--project", str(project),
                    "--slides", "2", "--translator", "ollama"]
            with patch.object(sys, "argv", args), \
                 patch.object(run_pipeline, "transcribe", return_value=cues), \
                 patch.object(run_pipeline, "translate", return_value=cn):
                run_pipeline.main()
            output = project/"courseware-interactive.html"
            page = output.read_text(encoding="utf-8")
            self.assertIn('src="data:audio/mpeg;base64,', page)
            self.assertEqual(page.count('data:image/png;base64,'), 2)
            self.assertNotIn('src="assets/', page)
            self.assertNotIn('src="https://', page)
            self.assertNotIn('<script src=', page)
            self.assertIn('0.1倍速', page)
            self.assertIn('2.0×', page)
            match = re.search(r'<script id="course-data" type="application/json">(.*?)</script>',
                              page, re.S)
            self.assertIsNotNone(match)
            data = json.loads(match.group(1))
            self.assertEqual(len(data["slides"]), 2)
            self.assertEqual(len(data["captions"]), 2)
            self.assertEqual(data["captions"][0]["cn"], "植物吸收阳光。")
            self.assertEqual(data["version"], EXPECTED_VERSION)
            self.assertEqual(read_json(project/"manifest.json")["format"], "html")
            self.assertFalse((project/"subtitle_videos"/"slide01.mp4").exists())

    def test_cli_version_without_audio(self):
        # Absolute script invocation works from unrelated agent/project directories.
        with tempfile.TemporaryDirectory() as temp:
            for name in ("run_pipeline.py", "build_web.py"):
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve().parents[1]/"scripts"/name),
                     "--version"], cwd=temp, capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout.strip(), EXPECTED_VERSION)

if __name__ == "__main__":
    unittest.main()
