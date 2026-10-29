#!/usr/bin/env python3
"""Clean python-pptx builder for recording-to-bilingual-ppt.

Reads a manifest JSON:
  {"slide_width_in": 13.333, "slide_height_in": 7.5,
   "bar_color": [246, 251, 243],
   "slides": [{"picture": "slide01.png", "video": "slide01.mp4",
               "poster": "poster.png", "notes": "..."}, ...]}

Places each picture on top (10.124 x 5.695 in, centred) and each video
strip at the bottom (0, 5.695 in, 13.333 x 1.805 in), sets the slide
background to the bar colour, and saves a NEW presentation.

Do NOT strip media shapes from an existing PPT and re-add videos:
orphaned media parts stay in the package and roughly double its size.
Rebuild from scratch with this script instead.

Requires: python-pptx (pip install python-pptx)
Usage: python3 build_ppt.py --manifest manifest.json --out courseware.pptx
"""
import argparse, json, os
from pptx import Presentation
from pptx.util import Inches, Emu
from pptx.dml.color import RGBColor

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    man = json.load(open(args.manifest, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(args.manifest))
    prs = Presentation()
    prs.slide_width = Emu(int(man.get("slide_width_in", 13.333) * 914400))
    prs.slide_height = Emu(int(man.get("slide_height_in", 7.5) * 914400))
    blank = prs.slide_layouts[6]
    if "bar_color" not in man:
        raise SystemExit("manifest must contain bar_color: the sampled slide background [R, G, B]. No fixed default is used.")
    r, g, b = man["bar_color"]
    pic_w, pic_h = Inches(10.124), Inches(5.695)
    left = Inches((13.333 - 10.124) / 2)
    for item in man["slides"]:
        slide = prs.slides.add_slide(blank)
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(r, g, b)
        slide.shapes.add_picture(os.path.join(base, item["picture"]),
                                 left, Inches(0), width=pic_w, height=pic_h)
        slide.shapes.add_movie(os.path.join(base, item["video"]),
                               Inches(0), Inches(5.695),
                               width=Inches(13.333), height=Inches(1.805),
                               poster_frame_image=os.path.join(base, item["poster"]))
        if item.get("notes"):
            ns = slide.notes_slide
            for ph in ns.placeholders:
                if ph.has_text_frame:
                    ph.text_frame.text = item["notes"]
                    break
    prs.save(args.out)
    print(f"saved {args.out} ({os.path.getsize(args.out)} bytes, {len(man['slides'])} slides)")

if __name__ == "__main__":
    main()
