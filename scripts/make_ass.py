#!/usr/bin/env python3
"""Generic bilingual ASS builder for recording-to-bilingual-ppt.

Inputs (in the project folder):
  merged_cues.json : [{"start": float, "end": float, "en": str}, ...]
                     cues are whole sentences; short cues already merged
                     into the next cue, never split.
  sentence_cn.json : {"1": "Chinese for cue 1", ...}  (1-based, one per cue)
  slides.json      : {"1": {"cues": [1, 2, 3], "offset": 0.0}, ...}
                     For a normal slide, cues are the cue indices fully
                     inside that slide's time range, and offset is the
                     slide's start time (so times become video-relative).
                     For a spliced trap slide, build the cue list and
                     offsets in slides.json by hand from sentence
                     boundaries, as described in SKILL.md step 3.

Output: slideNN.ass per slide, PlayRes 1920x260, bar colour is the
video background itself (see make_videos.sh); subtitle text is bold,
MIDDLE-CENTRE (alignment 5).
Bottom-centre (2) is deliberately NOT used: PowerPoint player
controls cover the bottom line, which is always the Chinese line.

Colours are parameters, never hard-coded. Pass the sampled slide
background with --bar-color (RRGGBB, e.g. the reference deck's
F6FBF3) and, when you have a chosen text colour, with --text-color
(RRGGBB, e.g. that deck's 1B4332). When --text-color is omitted,
this script auto-chooses by contrast: light background -> near-black
text with white outline, dark background -> near-white text with
black outline. On a different deck the colours must change; do not
copy the reference deck's pair as a default.

Usage: python3 make_ass.py --project . --bar-color <sampled RRGGBB> [--text-color <RRGGBB>]
"""
import argparse, json, os, sys, textwrap

def fmt(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def has_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)

def to_ass_bgr(rrggbb):
    rrggbb = rrggbb.lstrip("#")
    assert len(rrggbb) == 6, rrggbb
    r, g, b = rrggbb[0:2], rrggbb[2:4], rrggbb[4:6]
    return f"&H00{b}{g}{r}"

def auto_text_outline(bar_rrggbb):
    """Contrast choice from the sampled background, no fixed pair."""
    h = bar_rrggbb.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    if luminance > 0.6:
        return "1A1A1A", "FFFFFF"  # light background -> dark text, light outline
    return "FFFFFF", "000000"  # dark background -> light text, dark outline

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--bar-color", default=None,
                    help="Sampled slide background, RRGGBB. Required for the auto text choice.")
    ap.add_argument("--text-color", default=None,
                    help="Chosen subtitle text colour, RRGGBB. Omit for auto contrast choice.")
    ap.add_argument("--outline-color", default=None,
                    help="Outline colour, RRGGBB. Omit for the opposite of the text colour.")
    args = ap.parse_args()
    if args.text_color is None:
        if args.bar_color is None:
            raise SystemExit("--bar-color is required when --text-color is omitted (auto contrast needs it)")
        text_rrggbb, outline_rrggbb = auto_text_outline(args.bar_color)
    else:
        text_rrggbb = args.text_color
        outline_rrggbb = args.outline_color or ("FFFFFF" if text_rrggbb.upper() not in ("FFFFFF",) else "000000")
    print(f"bar={args.bar_color} text={text_rrggbb} outline={outline_rrggbb}")
    proj = args.project
    outdir = args.out or os.path.join(proj, "subtitle_videos")
    os.makedirs(outdir, exist_ok=True)
    cues = json.load(open(os.path.join(proj, "merged_cues.json"), encoding="utf-8"))
    cn_raw = json.load(open(os.path.join(proj, "sentence_cn.json"), encoding="utf-8"))
    cn = {int(k): v for k, v in cn_raw.items()}
    slides = json.load(open(os.path.join(proj, "slides.json"), encoding="utf-8"))
    assert len(cn) == len(cues), f"CN entries {len(cn)} != cues {len(cues)}"
    for i, v in cn.items():
        assert v and has_cjk(v), f"cue {i} has no Chinese translation"
    for slide_no in sorted(slides, key=lambda x: int(x)):
        spec = slides[slide_no]
        # spec may be {"cues": [...], "offset": float} or
        # {"segments": [{"cues": [...], "trap_start": float}, ...]} for spliced slides
        events = []
        if "segments" in spec:
            offset = 0.0
            for seg in spec["segments"]:
                for idx in seg["cues"]:
                    c = cues[idx - 1]
                    events.append((offset + c["start"] - seg["trap_start"],
                                   offset + c["end"] - seg["trap_start"], idx))
                last = cues[seg["cues"][-1] - 1]
                offset += last["end"] - seg["trap_start"]
        else:
            off = spec.get("offset", 0.0)
            for idx in spec["cues"]:
                c = cues[idx - 1]
                events.append((c["start"] - off, c["end"] - off, idx))
        lines = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920",
                 "PlayResY: 260", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
                 "[V4+ Styles]",
                 "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
                 # colours from parameters / auto contrast, bold, alignment 5 = middle-centre
                 f"Style: Default,Noto Sans CJK SC,32,{to_ass_bgr(text_rrggbb)},{to_ass_bgr(text_rrggbb)},{to_ass_bgr(outline_rrggbb)},&H00000000,1,0,0,0,100,100,0,0,1,1,0,5,80,80,0,1",
                 "", "[Events]",
                 "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
        for st, en, idx in events:
            if en <= st:
                continue
            elines = textwrap.wrap(cues[idx - 1]["en"], width=85) or [""]
            clines = textwrap.wrap(cn[idx], width=30) or [""]
            all_lines = elines + clines
            fs = 32 if len(all_lines) <= 4 else 26
            txt = "\\N".join(all_lines)
            if fs != 32:
                txt = f"{{\\fs{fs}}}" + txt
            assert has_cjk(txt), idx
            lines.append(f"Dialogue: 0,{fmt(st)},{fmt(en)},Default,,0,0,0,,{txt}")
        path = os.path.join(outdir, f"slide{int(slide_no):02d}.ass")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"slide {slide_no}: {len(events)} cues -> {path}")

if __name__ == "__main__":
    main()
