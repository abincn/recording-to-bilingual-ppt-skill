#!/usr/bin/env python3
"""Package a source-aligned courseware project into one offline interactive HTML file."""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
from pathlib import Path

from make_ass import caption_events
from pipeline_core import check_cues, read_json, require_translation, safe_project_file


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_VERSION = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
TEMPLATE = SKILL_ROOT / "assets" / "interactive_player.html"


def _data_uri(path: Path, media_type: str) -> str:
    return f"data:{media_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _media_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _encode_audio(source: Path, target: Path, overwrite: bool) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    if target.exists() and not overwrite:
        if abs(_media_duration(target) - _media_duration(source)) < 0.5:
            return
        raise ValueError(f"Previously encoded audio has an invalid duration: {target}")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
               "-vn", "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "96k", str(target)]
    subprocess.run(command, check=True)
    if target.stat().st_size < 100 or abs(_media_duration(target) - _media_duration(source)) > 0.5:
        raise ValueError("Incomplete or incorrectly timed encoded audio")


def build(project: Path, output: Path | None = None, *, overwrite: bool = False) -> Path:
    """Build a self-contained HTML with no external media, fonts, scripts or network calls."""
    project = Path(project).resolve()
    output = Path(output).resolve() if output else project / "courseware-interactive.html"
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output}")

    manifest = read_json(project / "manifest.json")
    slide_specs = read_json(project / "slides.json")
    cues = check_cues(read_json(project / "optimized_cues.json"))
    chinese = require_translation(cues, read_json(project / "sentence_cn.json"))
    report = read_json(project / "silence-report.json")
    master = project / "optimized_master.wav"
    media = project / "courseware-audio.mp3"
    _encode_audio(master, media, overwrite=overwrite)
    duration = _media_duration(master)

    slides = []
    subtitles = []
    accounted_ids = []
    for index, info in enumerate(manifest["slides"], 1):
        spec = slide_specs[str(index)]
        start = float(spec["start"])
        end = float(spec["end"])
        if not (0 <= start < end <= duration + 0.15):
            raise ValueError(f"Invalid chapter range {index}: {start}..{end}")
        picture = safe_project_file(project, info["picture"])
        if not picture.is_file():
            raise FileNotFoundError(picture)
        slides.append({
            "title": info["title"], "section": info.get("section") or "课程内容",
            "start": round(start, 3), "end": round(end, 3),
            "image": _data_uri(picture, "image/png"),
        })
        events = caption_events(
            cues, chinese, spec, merge_short=manifest.get("caption_merge", True),
            short_threshold=float(manifest.get("short_caption", 1)),
            minimum_duration=float(manifest.get("min_caption", 1.5)),
        )
        for event in events:
            ids = event["ids"]
            accounted_ids.extend(ids)
            subtitles.append({
                "start": round(start + event["start"], 3),
                "end": round(min(end, start + event["end"]), 3),
                "en": " ".join(cues[cue_id - 1]["en"].strip() for cue_id in ids),
                "cn": " ".join(chinese[cue_id].strip() for cue_id in ids),
            })
    if accounted_ids != list(range(1, len(cues) + 1)):
        raise ValueError("Chapter plan omitted or duplicated source subtitle IDs")
    if len(slides) < 1 or not subtitles:
        raise ValueError("A complete course needs chapters and bilingual captions")

    course = {
        "version": SKILL_VERSION,
        "title": str(manifest.get("title") or "交互式双语课件"),
        "draft": bool(manifest.get("draft")),
        "duration": round(duration, 3),
        "originalDuration": report.get("original_seconds", round(duration, 3)),
        "savedSeconds": report.get("saved_seconds", 0),
        "slides": slides,
        "captions": subtitles,
        "mergedCount": len(cues) - len(subtitles),
    }
    # Avoid terminating the script element if untrusted transcript text contains HTML.
    content = json.dumps(course, ensure_ascii=False, separators=(",", ":"))
    content = (content.replace("<", "\\u003c").replace(">", "\\u003e")
                      .replace("&", "\\u0026"))
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__COURSE_JSON__") != 1 or template.count("__AUDIO_SOURCE__") != 1:
        raise ValueError("Interactive player template must have exactly one of each marker")
    html = (template.replace("__COURSE_JSON__", content)
                    .replace("__AUDIO_SOURCE__", _data_uri(media, "audio/mpeg")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    if "__COURSE_JSON__" in html or "__AUDIO_SOURCE__" in html:
        raise ValueError("Unresolved embedded player template marker")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Existing processed courseware directory")
    parser.add_argument("--output", help="Final one-file HTML path")
    parser.add_argument("--force", action="store_true", help="Replace a previous generated HTML")
    parser.add_argument("--version", action="version", version=SKILL_VERSION)
    args = parser.parse_args()
    path = build(Path(args.project), Path(args.output) if args.output else None,
                 overwrite=args.force)
    print(f"Offline interactive courseware: {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
