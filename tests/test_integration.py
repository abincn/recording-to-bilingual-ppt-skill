"""Small end-to-end media/PPT smoke test; no model download or external API."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from build_ppt import build
from make_ass import render
from make_videos import render_one
from pipeline_core import write_json
from run_pipeline import poster, sample_frame, slide_image
from validate import validate
from pptx import Presentation

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg not installed")
class IntegrationTests(unittest.TestCase):
    def test_two_backgrounds_two_modes_and_autoplay(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder/"subtitle_videos").mkdir()
            (folder/"slide_images").mkdir()
            (folder/"qa").mkdir()
            cues = [{"start":.2,"end":.8,"en":"Revenue increased."},
                    {"start":1.7,"end":2.3,"en":"Check cash flow."}]
            translation = {"1":"收入增加。","2":"检查现金流量。"}
            specs = {"1":{"cues":[1],"start":0,"end":1.5,"offset":0,"bar_color":"00FF00"},
                     "2":{"cues":[2],"start":1.5,"end":3,"offset":1.5,"bar_color":"F6FBF3"}}
            write_json(folder/"merged_cues.json", cues)
            write_json(folder/"sentence_cn.json", translation)
            write_json(folder/"slides.json", specs)
            result = render(cues, translation, specs, folder/"subtitle_videos")
            self.assertEqual([r["events"] for r in result], [1, 1])
            items = []
            for i, color in enumerate(("00FF00", "F6FBF3"), 1):
                id = f"{i:02d}"
                a = folder/"subtitle_videos"/f"slide{id}.mp3"
                subprocess.run(["ffmpeg","-v","error","-f","lavfi","-i",
                                "sine=frequency=440:duration=1.5","-q:a","5","-y",str(a)], check=True)
                s = folder/"subtitle_videos"/f"slide{id}.ass"
                v = folder/"subtitle_videos"/f"slide{id}.mp4"
                render_one(a,s,color,v)
                pic = folder/"slide_images"/f"slide{id}.png"
                p = folder/"subtitle_videos"/f"poster{id}.png"
                slide_image(pic, f"Test {i}", [f"English lecture part {i}"], color)
                poster(p,color)
                sample_frame(v,s,folder/"qa"/f"slide{id}.png")
                items.append({"title":f"Test {i}", "bullets":[f"Bullet {i}"],
                              "picture":f"slide_images/slide{id}.png",
                              "audio":f"subtitle_videos/slide{id}.mp3",
                              "ass":f"subtitle_videos/slide{id}.ass",
                              "video":f"subtitle_videos/slide{id}.mp4",
                              "poster":f"subtitle_videos/poster{id}.png",
                              "notes":f"Part {i}", "bar_color":color})
            manifest = folder/"manifest.json"
            for mode in ("image","editable"):
                write_json(manifest, {"slides":items, "mode":mode, "autoplay":True})
                ppt = folder/f"{mode}.pptx"
                build(manifest,ppt)
                result = validate(manifest,ppt)
                self.assertEqual(result["slides"],2)
                self.assertGreater(ppt.stat().st_size,1000)
                deck = Presentation(ppt)
                for slide in deck.slides:
                    starts = slide._element.xpath(".//p:video//p:stCondLst/p:cond")
                    self.assertEqual(len(starts),1)
                    self.assertEqual(starts[0].get("delay"),"0")

if __name__ == "__main__":
    unittest.main()
