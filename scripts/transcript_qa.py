"""Source-aligned transcription QA. It never rewrites the transcript or guesses a number."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from pipeline_core import check_cues, write_json

_NUM = re.compile(r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?%?(?![A-Za-z0-9])")
_SPOKEN = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|thousand|million|billion)\b", re.I
)
_TERM = re.compile(r"\b[A-Z]{2,8}(?:-[A-Z0-9]+)*\b")
_SPACE = re.compile(r"\s+")


def numbers(text):
    """Keep digits exactly as heard; ignore formatting thousands separators only."""
    return sorted(match.replace(",", "") for match in _NUM.findall(str(text)))


def _flags(text):
    digits = numbers(text)
    flags = []
    if digits:
        flags.append("number_requires_source_check")
    if _SPOKEN.search(text):
        flags.append("spoken_number_words")
    if any(re.fullmatch(r"\d{3}", token) for token in digits):
        flags.append("three_digit_context_check")
    if _TERM.search(text):
        flags.append("technical_acronym")
    return flags


def _alternatives(cues, alternate):
    """Accept an ID-to-English mapping or timestamped second-pass cue list."""
    if alternate is None:
        return {}
    if isinstance(alternate, dict):
        output = {}
        for key, value in alternate.items():
            if not str(key).isdigit() or not 1 <= int(key) <= len(cues):
                raise ValueError(f"Second-pass cue ID out of range: {key!r}")
            if isinstance(value, dict):
                value = value.get("en")
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Second-pass cue {key}: expected nonempty English")
            output[int(key)] = value.strip()
        return output
    if not isinstance(alternate, list):
        raise ValueError("Second-pass input must be an ID mapping or timestamped cue list")
    check_cues(alternate)
    output = {}
    for index, cue in enumerate(cues, 1):
        overlapping = [
            item["en"] for item in alternate
            if max(0.0, min(cue["end"], item["end"]) -
                   max(cue["start"], item["start"])) >=
            min(.2, (cue["end"] - cue["start"]) * .25)
        ]
        if overlapping:
            output[index] = " ".join(overlapping)
    return output


def _slide_text(slide):
    parts = [slide.get("title", "")]
    parts.extend(slide.get("bullets", []))
    for field in ("formula", "quote"):
        if slide.get(field):
            parts.append(slide[field])
    table = slide.get("table") or {}
    parts.extend(table.get("columns", []))
    for row in table.get("rows", []):
        parts.extend(row.get("cells", row) if isinstance(row, dict) else row)
    return " ".join(parts)


def audit(cues, *, second_pass=None, slides=None, source="none"):
    """Identify review candidates, never alter speech, translations or slide values."""
    check_cues(cues)
    alternatives = _alternatives(cues, second_pass)
    issues = []
    for index, cue in enumerate(cues, 1):
        flags = _flags(cue["en"])
        candidate = alternatives.get(index)
        if candidate is not None:
            if numbers(candidate) != numbers(cue["en"]):
                flags.append("second_pass_number_disagreement")
            elif (flags and _SPACE.sub(" ", candidate).strip().casefold()
                  != _SPACE.sub(" ", cue["en"]).strip().casefold()):
                flags.append("second_pass_wording_disagreement")
        if not flags:
            continue
        issues.append({
            "kind": "cue", "cue_id": index, "start": round(cue["start"], 3),
            "end": round(cue["end"], 3), "source_text": cue["en"],
            "source_numbers": numbers(cue["en"]), "second_pass_text": candidate,
            "second_pass_numbers": numbers(candidate) if candidate is not None else None,
            "flags": flags,
            "disposition": "review_required" if "second_pass_number_disagreement" in flags
                            or "three_digit_context_check" in flags else "source_check",
        })
    if slides:
        for index, slide in enumerate(slides, 1):
            original = " ".join(
                cues[i - 1]["en"]
                for i in range(slide["cue_start"], slide["cue_end"] + 1)
            )
            extra = sorted(set(numbers(_slide_text(slide))) - set(numbers(original)))
            if extra:
                issues.append({
                    "kind": "slide", "slide_id": index,
                    "cue_start": slide["cue_start"], "cue_end": slide["cue_end"],
                    "unmatched_numbers": extra,
                    "flags": ["slide_number_not_in_source_cues"],
                    "disposition": "document_textbook_or_calculation_evidence",
                })
    return {
        "schema_version": 1,
        "source": source,
        "policy": "Read original audio and reliable material; never infer or overwrite uncertain numbers automatically.",
        "source_cues": len(cues), "second_pass_compared": len(alternatives),
        "issue_count": len(issues),
        "disagreements": sum(
            "second_pass_number_disagreement" in entry["flags"] for entry in issues
        ),
        "issues": issues,
    }


def recheck_selected(audio, cues, *, model_name="small", language="en", limit=12):
    """Optional targeted local ASR; compare candidates only, never pick a winner."""
    check_cues(cues)
    if limit < 1:
        raise ValueError("Recheck limit must be positive")
    targets = [(i, cue) for i, cue in enumerate(cues, 1) if _flags(cue["en"])][:limit]
    if not targets:
        return {}
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install faster-whisper for --qa-recheck") from exc
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    results = {}
    with tempfile.TemporaryDirectory(prefix="transcript-qa-") as temporary:
        for cue_id, cue in targets:
            start = max(0.0, float(cue["start"]) - 1.5)
            end = float(cue["end"]) + 1.5
            clip = Path(temporary) / f"cue-{cue_id}.wav"
            result = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{start:.3f}", "-t", f"{end-start:.3f}",
                "-i", str(audio), "-ar", "16000", "-ac", "1", str(clip)
            ], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"QA clip {cue_id}: {result.stderr[-500:]}")
            segments, _ = model.transcribe(
                str(clip), language=language, beam_size=8, vad_filter=False,
                condition_on_previous_text=False, word_timestamps=True
            )
            segments = list(segments)
            selected = [
                word.word.strip()
                for segment in segments for word in (segment.words or [])
                if word.word.strip() and word.start is not None and word.end is not None
                and cue["start"] - .15 <= start + (word.start + word.end)/2
                <= cue["end"] + .15
            ]
            text = " ".join(selected).strip()
            if not text:
                # No safe in-cue alignment: preserve an explicit empty comparison.
                text = "[no aligned words]"
            results[cue_id] = text
    return results


def write_report(project, report):
    project = Path(project)
    write_json(project / "transcript-qa.json", report)
    out = [
        "# Transcription quality review",
        "",
        f"Original cues: {report['source_cues']} | Review items: {report['issue_count']} "
        f"| Second-pass numeric disagreements: {report['disagreements']}",
        "",
        "Do not treat a calculation match as proof that a figure was spoken.",
        "Every cue timestamp refers to the original, uncompressed recording.",
        "Do not silently replace uncertain values; record evidence before revising.",
        "",
        "| ID | Original time | Flags | Original English | Second pass / issue |",
        "| --- | --- | --- | --- | --- |",
    ]
    for issue in report["issues"]:
        esc = lambda value: str(value).replace("|", r"\|").replace("\n", " ")
        if issue["kind"] == "cue":
            time = f"{issue['start']:.2f}–{issue['end']:.2f}s"
            out.append(f"| {issue['cue_id']} | {time} | "
                       f"{esc(', '.join(issue['flags']))} | "
                       f"{esc(issue['source_text'])} | "
                       f"{esc(issue['second_pass_text'] or '—')} |")
        else:
            out.append(f"| slide {issue['slide_id']} | cues "
                       f"{issue['cue_start']}–{issue['cue_end']} | "
                       f"number not in source | — | "
                       f"{esc(', '.join(issue['unmatched_numbers']))} |")
    (project / "transcript-qa.md").write_text("\n".join(out) + "\n", encoding="utf-8")
