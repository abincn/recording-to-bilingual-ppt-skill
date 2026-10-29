"""Speech-safe trim and subtitle consolidation regression checks."""
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from timing_optimize import calculate_cuts, remap_cues, optimize_audio
from make_ass import caption_events


class TimeOptimizationTests(unittest.TestCase):
    def test_does_not_cut_inside_speech(self):
        cues = [{"start":1., "end":2., "en":"Hello."},
                {"start":10., "end":11., "en":"Next."}]
        cuts = calculate_cuts([(3.,9.5),(10.1,10.8)], cues,12.)
        self.assertEqual(len(cuts),1)
        self.assertAlmostEqual(cuts[0][0],3.4)
        self.assertAlmostEqual(cuts[0][1],9.1)
        mapped = remap_cues(cues,cuts)
        self.assertAlmostEqual(mapped[1]["start"],4.3)
        self.assertAlmostEqual(mapped[1]["end"]-mapped[1]["start"],1.)

    def test_real_pcm_duration_matches_time_map(self):
        cues = [{"start":.5,"end":1.,"en":"One."},
                {"start":6.,"end":6.5,"en":"Two."}]
        with tempfile.TemporaryDirectory() as tmp:
            source,output=Path(tmp)/"raw.wav",Path(tmp)/"optimized.wav"
            with wave.open(str(source),"wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(1000)
                out.writeframes(b"\x00\x00"*8000)
            with patch("timing_optimize.detect_silences",return_value=[(1.2,5.8)]):
                aligned,duration,report=optimize_audio(source,output,cues)
            self.assertGreater(report["saved_seconds"],3.)
            with wave.open(str(output),"rb") as result:
                self.assertAlmostEqual(duration,result.getnframes()/result.getframerate())
            self.assertAlmostEqual(aligned[1]["end"]-aligned[1]["start"],.5)


class CaptionTests(unittest.TestCase):
    def test_merges_short_intro_into_continuation(self):
        cues=[{"start":0.,"end":.55,"en":"And then"},
              {"start":.55,"end":2.8,"en":"we subtract inventory."}]
        cn={1:"然后",2:"我们减去存货。"}
        spec={"start":0.,"end":3.,"offset":0.,"cues":[1,2]}
        display=caption_events(cues,cn,spec,merge_short=True)
        self.assertEqual(len(display),1)
        self.assertEqual(display[0]["ids"],[1,2])

    def test_does_not_join_across_topic_or_large_pause(self):
        cues=[{"start":0.,"end":.4,"en":"Yes."},
              {"start":3.,"end":4.,"en":"A new topic."}]
        cn={1:"是。",2:"新主题。"}
        a=caption_events(cues,cn,{"start":0.,"end":3.,"offset":0.,"cues":[1]},merge_short=True)
        b=caption_events(cues,cn,{"start":3.,"end":5.,"offset":3.,"cues":[2]},merge_short=True)
        self.assertEqual([item["ids"] for item in a+b],[[1],[2]])
        self.assertAlmostEqual(a[0]["end"],1.5)

    def test_keeps_dense_independent_captions(self):
        cues=[{"start":0.,"end":.5,"en":"Brief."},
              {"start":.5,"end":5.,"en":"Many "+"long words "*15}]
        cn={1:"简短。",2:"很多"*36}
        spec={"start":0.,"end":6.,"offset":0.,"cues":[1,2]}
        captions=caption_events(cues,cn,spec,merge_short=True)
        self.assertEqual([x["ids"] for x in captions],[[1],[2]])


if __name__ == "__main__":
    unittest.main()
