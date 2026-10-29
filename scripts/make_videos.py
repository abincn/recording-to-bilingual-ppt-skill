#!/usr/bin/env python3
"""Render every subtitle strip to MP4; no shell interpolation or hidden uploads."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from pipeline_core import hex_color, read_json, safe_project_file

def run(command, *, cwd=None):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{command[0]} failed: {result.stderr[-2000:]}")
    return result.stdout.strip()

def duration(path):
    value = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(value)

def render_one(audio, ass, bg, output, *, overwrite=False):
    audio, ass, output = map(Path, (audio, ass, output))
    if output.exists() and not overwrite:
        raise FileExistsError(f"MP4 exists: {output}")
    for name in ("ffmpeg", "ffprobe"):
        if shutil.which(name) is None:
            raise RuntimeError(f"{name} is required on PATH")
    # Work with a fixed, relative ASS basename to avoid ffmpeg filter expression injection.
    if ass.name.startswith("slide") is False or not ass.name.endswith(".ass"):
        raise ValueError("ASS filename must follow slideNN.ass convention")
    if ass.parent.resolve() != output.parent.resolve():
        raise ValueError("ASS and MP4 must be in the same directory")
    exact = duration(audio)
    if exact <= 0:
        raise ValueError("Cannot render zero-length audio")
    color = hex_color(bg)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error",
               "-y" if overwrite else "-n",
               "-f", "lavfi", "-i", f"color=c=0x{color}:s=1920x260:r=10",
               "-i", str(audio.resolve()), "-vf", f"subtitles=filename={ass.name}",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
               "-t", f"{exact:.3f}", "-movflags", "+faststart", str(output.resolve())]
    run(command, cwd=ass.parent)
    actual = duration(output)
    if abs(actual-exact) > .25:
        raise RuntimeError(f"Video/audio duration mismatch: {actual:.2f}s vs {exact:.2f}s")
    return {"video":str(output), "audio_duration":exact, "video_duration":actual}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    manifest = Path(args.manifest).resolve()
    data = read_json(manifest)
    result = []
    for i, slide in enumerate(data["slides"], 1):
        audio = safe_project_file(manifest.parent, slide["audio"])
        ass = safe_project_file(manifest.parent, slide["ass"])
        video = safe_project_file(manifest.parent, slide["video"])
        result.append(render_one(audio, ass, slide["bar_color"], video, overwrite=args.force))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
