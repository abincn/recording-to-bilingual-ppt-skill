"""Core validation, colour and timeline operations for the courseware skill."""
from __future__ import annotations
import json
import math
import re
from pathlib import Path

HAN = re.compile(r"[\u3400-\u9fff]")
HEX = re.compile(r"#?[0-9a-fA-F]{6}\Z")

def rgb(value):
    if isinstance(value, (tuple, list)) and len(value) == 3 and all(type(n) is int and 0 <= n <= 255 for n in value):
        return tuple(value)
    if isinstance(value, str) and HEX.fullmatch(value):
        h = value.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    raise ValueError(f"Invalid RGB colour: {value!r}")

def hex_color(value):
    return "".join(f"{n:02X}" for n in rgb(value))

def luminance(value):
    a = []
    for c in rgb(value):
        x = c / 255
        a.append(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4)
    return sum(x*y for x, y in zip(a, (0.2126, 0.7152, 0.0722)))

def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + .05) / (low + .05)

def palette(background, text=None, outline=None):
    background = hex_color(background)
    if text is None:
        # Pure black/white guarantees one candidate >= 4.5:1 for any RGB background.
        text = max(("000000", "FFFFFF"), key=lambda c: contrast(background, c))
    text = hex_color(text)
    if contrast(background, text) < 4.5:
        raise ValueError(f"Contrast is only {contrast(background, text):.2f}:1; at least 4.5:1 required")
    if outline is None:
        outline = "FFFFFF" if luminance(text) < .5 else "000000"
    return {"bar_color": background, "text_color": text, "outline_color": hex_color(outline)}

def require_translation(cues, translations):
    if isinstance(translations, list):
        translations = {str(i): v for i, v in enumerate(translations, 1)}
    if not isinstance(translations, dict):
        raise ValueError("Expected a 1-based mapping or translation list")
    expected = {str(i) for i in range(1, len(cues)+1)}
    actual = {str(k) for k in translations}
    if expected != actual:
        raise ValueError(f"Translation IDs: missing {sorted(expected-actual)}, extra {sorted(actual-expected)}")
    translated = {}
    for i in range(1, len(cues)+1):
        value = translations[str(i)]
        if not isinstance(value, str) or not HAN.search(value.strip()):
            raise ValueError(f"Translation {i} does not contain Chinese")
        translated[i] = value.strip()
    return translated

def numbers_preserved(english, chinese):
    """Automated guard against dropped or invented Arabic-digit quantities."""
    def tokens(text):
        found = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
        return sorted(token.replace(",", "") for token in found)
    return tokens(english) == tokens(chinese)

def check_cues(cues):
    if not isinstance(cues, list) or not cues:
        raise ValueError("No cues")
    previous = 0.
    for i, cue in enumerate(cues, 1):
        if not all(k in cue for k in ("start", "end", "en")):
            raise ValueError(f"Cue {i}: missing start/end/en")
        start, end = cue["start"], cue["end"]
        if not all(isinstance(t, (float, int)) and math.isfinite(t) for t in (start, end)):
            raise ValueError(f"Cue {i}: invalid timestamp")
        if start < 0 or end <= start or start < previous - .035:
            raise ValueError(f"Cue {i}: negative, reversed or overlapping timestamp")
        if not isinstance(cue["en"], str) or not cue["en"].strip():
            raise ValueError(f"Cue {i}: empty English text")
        previous = end
    return cues

def cues_from_words(words):
    cues, part = [], []
    for w in words:
        token = str(w["word"]).strip()
        if not token:
            continue
        part.append((float(w["start"]), float(w["end"]), token))
        end = bool(re.search(r"[.!?。！？][\"')\]]*$", token))
        if end and token.lower() not in {"mr.", "mrs.", "dr.", "inc.", "e.g.", "i.e."}:
            cues.append({"start":part[0][0], "end":part[-1][1], "en":" ".join(x[2] for x in part)})
            part = []
    if part:
        cues.append({"start":part[0][0], "end":part[-1][1], "en":" ".join(x[2] for x in part)})
    return check_cues(cues)

def partition_cues(cues, duration, count):
    check_cues(cues)
    if not 1 <= count <= len(cues) or duration < cues[-1]["end"]:
        raise ValueError("Invalid slide count or audio duration")
    bounds = [0]
    for step in range(1, count):
        candidates = range(bounds[-1]+1, len(cues)-(count-step)+1)
        target = duration * step/count
        bounds.append(min(candidates, key=lambda i: abs(cues[i]["start"]-target)))
    bounds.append(len(cues))
    slides = []
    for i in range(count):
        first, after = bounds[i:i+2]
        start = 0. if i == 0 else cues[first]["start"]
        end = duration if i == count-1 else cues[after]["start"]
        slides.append({"start":start, "end":end, "offset":start, "cues":list(range(first+1, after+1))})
    return slides

def simple_outline(cues, slide_spec, ordinal):
    source = [cues[i-1]["en"] for i in slide_spec["cues"]]
    title = " ".join(source[0].split())
    if len(title) > 72:
        title = title[:69].rsplit(" ", 1)[0]+"…"
    bullets = []
    for raw in source[1:]:
        item = " ".join(raw.split())
        if len(item) > 140:
            item = item[:137].rsplit(" ", 1)[0]+"…"
        if item and item not in bullets:
            bullets.append(item)
        if len(bullets) == 5:
            break
    return {"title":title or f"Part {ordinal}", "bullets":bullets or ["Listen to the original recording for details."]}

def safe_project_file(project, path):
    root = Path(project).resolve()
    if not isinstance(path, str):
        raise ValueError("Manifest path must be text")
    target = (root/path).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError(f"Path escapes the project: {path!r}")
    return target

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

