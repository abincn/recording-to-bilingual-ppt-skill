"""Speech-safe silence compression with traceable, remapped timestamps.

Only intervals confirmed by FFmpeg and fully outside transcript cues are cut.
The original cleaned WAV and numbered transcript are retained unchanged.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import wave
from pathlib import Path

from pipeline_core import check_cues


def detect_silences(audio, *, minimum=2.5, noise_db=-14):
    command = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(audio),
               "-af", f"silencedetect=noise={noise_db}dB:d={minimum}",
               "-f", "null", "-"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Silence analysis failed: {result.stderr[-1000:]}")
    spans, pending = [], None
    for line in result.stderr.splitlines():
        start = re.search(r"silence_start:\s*([\d.]+)", line)
        stop = re.search(r"silence_end:\s*([\d.]+)", line)
        if start:
            pending = float(start.group(1))
        if stop and pending is not None:
            end = float(stop.group(1))
            if end > pending:
                spans.append((pending, end))
            pending = None
    if pending is not None:
        with wave.open(str(audio), "rb") as stream:
            end = stream.getnframes()/stream.getframerate()
        if end > pending:
            spans.append((pending, end))
    return spans


def calculate_cuts(silences, cues, duration, *, minimum=2.5,
                   target_pause=.8, guard=.08):
    check_cues(cues)
    if not (0 < target_pause < minimum) or guard < 0 or duration < cues[-1]["end"]:
        raise ValueError("Invalid silence settings or duration")
    gaps = [(0., float(cues[0]["start"]))]
    gaps += [(float(a["end"]), float(b["start"])) for a, b in zip(cues, cues[1:])]
    gaps.append((float(cues[-1]["end"]), float(duration)))
    cuts = []
    for silent_start, silent_end in silences:
        for gap_start, gap_end in gaps:
            begin = max(float(silent_start), gap_start + guard)
            finish = min(float(silent_end), gap_end - guard)
            if finish - begin < minimum:
                continue
            cut_start = begin + target_pause/2
            cut_end = finish - target_pause/2
            if cut_end - cut_start > .001:
                cuts.append((cut_start, cut_end))
    cuts.sort()
    for (_, prior_end), (next_start, _) in zip(cuts, cuts[1:]):
        if next_start < prior_end - 1e-6:
            raise ValueError("Overlapping silence cuts")
    return cuts


def remap_time(value, cuts):
    removed = 0.
    for begin, end in cuts:
        if value >= end:
            removed += end - begin
        elif value > begin:
            removed += value - begin
            break
        else:
            break
    return max(0., value - removed)


def remap_cues(cues, cuts):
    converted = []
    for cue in check_cues(cues):
        item = dict(cue)
        item["start"] = remap_time(float(cue["start"]), cuts)
        item["end"] = remap_time(float(cue["end"]), cuts)
        if abs((item["end"] - item["start"]) - (cue["end"] - cue["start"])) > .003:
            raise ValueError("Silence cut intersects spoken cue")
        converted.append(item)
    return check_cues(converted)


def cut_pcm_wave(source, destination, cuts):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("Keep uncompressed source WAV unchanged")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not cuts:
        shutil.copyfile(source, destination)
        return
    with wave.open(str(source), "rb") as reader:
        rate, frames = reader.getframerate(), reader.getnframes()
        keep, cursor = [], 0
        for begin, end in cuts:
            first = max(cursor, min(frames, round(begin*rate)))
            after = min(frames, round(end*rate))
            if after <= first:
                continue
            if first > cursor:
                keep.append((cursor, first))
            cursor = after
        if cursor < frames:
            keep.append((cursor, frames))
        with wave.open(str(destination), "wb") as writer:
            writer.setparams(reader.getparams())
            for start, finish in keep:
                reader.setpos(start)
                remaining = finish - start
                while remaining:
                    count = min(65536, remaining)
                    writer.writeframesraw(reader.readframes(count))
                    remaining -= count


def optimize_audio(source, destination, cues, *, minimum=2.5,
                   target_pause=.8, noise_db=-14):
    with wave.open(str(source), "rb") as stream:
        original_duration = stream.getnframes()/stream.getframerate()
    silences = detect_silences(source, minimum=minimum, noise_db=noise_db)
    cuts = calculate_cuts(silences, cues, original_duration,
                          minimum=minimum, target_pause=target_pause)
    aligned = remap_cues(cues, cuts)
    cut_pcm_wave(source, destination, cuts)
    with wave.open(str(destination), "rb") as stream:
        duration = stream.getnframes()/stream.getframerate()
    report = {"enabled": True,
              "original_seconds": round(original_duration, 3),
              "optimized_seconds": round(duration, 3),
              "saved_seconds": round(original_duration-duration, 3),
              "silences_detected": len(silences), "cuts": len(cuts),
              "minimum_silence_seconds": minimum,
              "target_pause_seconds": target_pause,
              "noise_threshold_db": noise_db,
              "removed_intervals_original_seconds":
                  [[round(a, 3), round(b, 3)] for a, b in cuts],
              "preserved_cues": len(aligned)}
    return aligned, duration, report
