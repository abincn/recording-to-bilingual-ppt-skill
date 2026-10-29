#!/usr/bin/env python3
"""Render validated bilingual ASS subtitles; per-slide WCAG contrast and safe layout."""
from __future__ import annotations
import argparse
import json
import re
import textwrap
from pathlib import Path

from pipeline_core import check_cues, hex_color, palette, read_json, require_translation

def timestamp(seconds):
    if seconds < -.02:
        raise ValueError(f"Negative subtitle timestamp: {seconds}")
    seconds = max(0, seconds)
    centiseconds = round(seconds * 100)
    h, remainder = divmod(centiseconds, 360000)
    m, remainder = divmod(remainder, 6000)
    s, cs = divmod(remainder, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def bgr(value):
    h = hex_color(value)
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}"

def escaped(value):
    # Never let transcript text introduce ASS override blocks or new events.
    return re.sub(r"\s+", " ", value.replace("{", "（").replace("}", "）").replace("\\", "＼")).strip()

def lines_for(en, cn):
    en = escaped(en)
    cn = escaped(cn)
    english = textwrap.wrap(en, width=85, break_long_words=True, break_on_hyphens=False) or [""]
    chinese = textwrap.wrap(cn, width=30, break_long_words=True, break_on_hyphens=False) or [""]
    lines = english + chinese
    # 260px canvas, with 15px safety margins top and bottom; estimated line-height
    font_size = min(32, int(225 / (len(lines) * 1.35)))
    if font_size < 14:
        raise ValueError(f"Cue requires {len(lines)} lines and would overflow subtitle strip")
    return font_size, lines

def slide_events(cues, spec):
    if "segments" in spec:
        segments = spec["segments"]
        offset = 0.
        result = []
        for segment in segments:
            ids = segment.get("cues", [])
            if not ids:
                raise ValueError("Empty splice segment")
            beginning = float(segment.get("source_start", segment.get("trap_start", cues[ids[0]-1]["start"])))
            finish = float(segment.get("source_end", cues[ids[-1]-1]["end"]))
            if finish <= beginning:
                raise ValueError("Invalid splice interval")
            for idx in ids:
                cue = cues[idx-1]
                if cue["start"] < beginning-.02 or cue["end"] > finish+.02:
                    raise ValueError("A subtitle crosses a splice edge")
                result.append((offset+cue["start"]-beginning, offset+cue["end"]-beginning, idx))
            offset += finish-beginning
    else:
        off = float(spec.get("offset", spec.get("start", 0)))
        result = [(cues[idx-1]["start"]-off, cues[idx-1]["end"]-off, idx)
                  for idx in spec["cues"]]
    previous = 0.
    for start, end, idx in result:
        if not 1 <= idx <= len(cues):
            raise ValueError(f"Bad cue number {idx}")
        if start < -.02 or end <= start or start < previous-.035:
            raise ValueError(f"Invalid or overlapping subtitle event in slide: cue {idx}")
        if spec.get("end") is not None and "segments" not in spec:
            if end > float(spec["end"])-float(spec.get("offset", spec.get("start", 0)))+.05:
                raise ValueError(f"Cue {idx} crosses slide end")
        previous = end
    return result

def caption_events(cues, translations, spec, *, merge_short=False,
                   short_threshold=1.0, minimum_duration=1.5,
                   maximum_duration=7.0, maximum_gap=.45):
    """Combine fleeting bilingual cues while preserving every original cue ID."""
    source = slide_events(cues, spec)
    events = [{"start":s, "end":e, "ids":[idx]} for s,e,idx in source]
    if not merge_short:
        return events
    if not (0 < short_threshold <= minimum_duration <= maximum_duration):
        raise ValueError("Invalid subtitle duration limits")

    def spoken(group):
        en = " ".join(cues[idx-1]["en"].strip() for idx in group["ids"])
        cn = " ".join(translations[idx].strip() for idx in group["ids"])
        return en, cn

    def candidate(left, right):
        gap = right["start"]-left["end"]
        if gap < -.02 or gap > maximum_gap or right["end"]-left["start"] > maximum_duration:
            return None
        if any(cues[idx-1].get("speaker") != cues[left["ids"][0]-1].get("speaker")
               for idx in right["ids"]):
            return None
        merged = {"start":left["start"], "end":right["end"],
                  "ids":left["ids"]+right["ids"]}
        en, cn = spoken(merged)
        if len(en) > 150 or len(cn) > 66 or len(lines_for(en, cn)[1]) > 4:
            return None
        prev_en, _ = spoken(left)
        next_en, _ = spoken(right)
        topic_break = bool(re.search(r"[.!?][\"')\]]?$", prev_en)) and bool(re.match(r"[A-Z]", next_en))
        return int(topic_break), gap, merged

    i = 0
    while i < len(events):
        current = events[i]
        if current["end"]-current["start"] >= short_threshold:
            i += 1
            continue
        choices = []
        if i > 0:
            previous = candidate(events[i-1], current)
            if previous is not None:
                choices.append((previous[0], previous[1], 0, i-1, previous[2]))
        if i+1 < len(events):
            following = candidate(current, events[i+1])
            if following is not None:
                choices.append((following[0], following[1], 1, i, following[2]))
        if choices:
            _, _, _, pos, merged = min(choices)
            events[pos:pos+2] = [merged]
            i = max(0, pos-1)
        else:
            i += 1

    if "end" in spec and "start" in spec:
        end_of_slide = float(spec["end"])-float(spec.get("offset", spec["start"]))
        for i, item in enumerate(events):
            if item["end"]-item["start"] >= minimum_duration:
                continue
            next_start = events[i+1]["start"] if i+1 < len(events) else end_of_slide
            item["end"] = min(next_start, item["start"]+minimum_duration)
    if [idx for event in events for idx in event["ids"]] != [idx for _,_,idx in source]:
        raise ValueError("Caption merge dropped or reordered source cues")
    return events


def render(cues, translations, slides, out, default_color=None, text_color=None, outline_color=None,
           *, merge_short=False, short_threshold=1.0, minimum_duration=1.5):
    check_cues(cues)
    cn = require_translation(cues, translations)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for key in sorted(slides, key=int):
        spec = slides[key]
        bar = spec.get("bar_color", default_color)
        if bar is None:
            raise ValueError(f"Slide {key}: sampled bar_color is required")
        colors = palette(bar, spec.get("text_color", text_color), spec.get("outline_color", outline_color))
        style = (f"Style: Default,Noto Sans CJK SC,32,{bgr(colors['text_color'])},"
                 f"{bgr(colors['text_color'])},{bgr(colors['outline_color'])},&H00000000,"
                 "1,0,0,0,100,100,0,0,1,1,0,5,80,80,0,1")
        output = [
            "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 260",
            "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            style, "", "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
        events = caption_events(cues, cn, spec, merge_short=merge_short,
                                short_threshold=short_threshold,
                                minimum_duration=minimum_duration)
        for event in events:
            start, end, ids = event["start"], event["end"], event["ids"]
            en = " ".join(cues[idx-1]["en"].strip() for idx in ids)
            chinese = " ".join(cn[idx] for idx in ids)
            size, lines = lines_for(en, chinese)
            # Literal ASS line breaks are inserted by us after escaping user input.
            content = r"\N".join(lines)
            if size != 32:
                content = r"{\fs"+str(size)+"}"+content
            output.append(f"Dialogue: 0,{timestamp(start)},{timestamp(end)},Default,,0,0,0,,{content}")
        target = out / f"slide{int(key):02d}.ass"
        target.write_text("\n".join(output)+"\n", encoding="utf-8")
        original = slide_events(cues, spec)
        results.append({"slide":int(key), "file":str(target), "events":len(events),
                        "source_cues":len(original),
                        "merged_cues":len(original)-len(events), **colors})
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--out")
    parser.add_argument("--bar-color")
    parser.add_argument("--text-color")
    parser.add_argument("--outline-color")
    args = parser.parse_args()
    project = Path(args.project)
    result = render(read_json(project/"merged_cues.json"),
                    read_json(project/"sentence_cn.json"),
                    read_json(project/"slides.json"),
                    args.out or project/"subtitle_videos",
                    args.bar_color, args.text_color, args.outline_color)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
