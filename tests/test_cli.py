"""Orchestrator smoke test with stub ASR/translation; no model or API dependency."""
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import run_pipeline
from validate import validate

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
                     "--slides","2","--colors","00FF00,F6FBF3","--mode","image","--autoplay"]
            with patch.object(sys,"argv",first), patch.object(run_pipeline,"transcribe",return_value=cues), \
                 patch.object(run_pipeline,"translate",return_value=cn):
                run_pipeline.main()
            self.assertEqual(validate(project/"manifest.json",project/"courseware-image.pptx")["slides"],2)
            second = ["run_pipeline.py","--audio",str(source),"--project",str(project),
                      "--slides","2","--colors","00FF00,F6FBF3","--mode","editable",
                      "--translations",str(project/"sentence_cn.json"),"--resume","--autoplay"]
            with patch.object(sys,"argv",second):
                run_pipeline.main()
            self.assertEqual(validate(project/"manifest.json",project/"courseware-editable.pptx")["mode"],"editable")

if __name__ == "__main__":
    unittest.main()
