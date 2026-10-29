---
name: recording-to-bilingual-ppt
description: Convert a lecture recording or voice note into a Chinese-English subtitled PowerPoint with cleaned original speaker audio on every slide. Use for bilingual courseware, sentence-timed subtitles, per-slide subtitle strips, and optionally editable PowerPoint text. Never substitute synthetic narration for the recording.
---

# Recording → bilingual PPT

Use the bundled scripts for a reproducible, inspectable workflow. Read `README.md`
for prerequisites and user-facing setup; it documents the local Whisper/Ollama options.

## Rules

- Keep the **original speaker's voice**. Audio processing may remove noise and normalize
  volume, but cannot recover words missing from the microphone.
- Transcribe locally with **word timestamps**. Confirm any ambiguous figures, formulae,
  names and terminology with the user; never silently "correct" the source.
- Make sentence-based English cues, preserve complete sentences, then **automatically**
  translate each cue into Chinese with the same 1-based identifier. Match counts,
  identifiers, Chinese-script presence and Arabic-digit quantities automatically.
  Retry invalid model outputs; do not require manual Chinese proofreading by default.
  If punctuation is absent, pause-based/semantic sentence boundaries require review.
- Do not send audio/transcript to cloud translation providers automatically. The provided
  pipeline uses **local Ollama** at a loopback address, or user-supplied translation JSON.
  Whisper model weights may be downloaded on first use; inform the user.
- Sample the **actual per-slide background**. Calculate WCAG sRGB contrast
  (minimum 4.5:1). Subtitle ASS style uses alignment 5 (middle-centre).
  Any cue too tall for 1920×260 fails rather than being silently cropped.
- Encode video strips with FFmpeg/libass, check actual durations within encoding tolerance,
  and extract QA frames. Keep images, cleaned master and split audio in the project folder.
- User-facing delivery must state which mode was produced: image slides are
  **not editable text**, editable mode uses native PowerPoint text shapes.
- Video playback is software-dependent: `--autoplay` sets the PPTX video timing to
  begin on slide entry, but inspect in the recipient's PowerPoint version.
- Flag transcript/table number disagreements. Never invent numbers or claim that the
  extractive fallback is a human-verified lecture summary.

## Standard workflow

1. Check `ffmpeg`, `ffprobe`, CJK fonts, Python requirements, and optional Ollama.
2. For a full run, call:

   ```bash
   python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
     --slides 10 --mode image --autoplay --ollama-model qwen2.5:7b
   ```

   For native editable slide text, pass `--mode editable`. Multiple backgrounds:
   `--colors F6FBF3,243044,EEE8D5`.

3. Only if the user explicitly wants to supply translations, or Ollama is
   unavailable, offer the optional two-pass path:

   ```bash
   python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
     --stage transcribe
   # Review merged_cues.json; prepare sentence_cn.json with exact "1", "2", ... keys.
   python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
     --translations ./lecture-output/sentence_cn.json --resume --mode editable
   ```

4. Run `python3 scripts/validate.py --manifest lecture-output/manifest.json
   --ppt lecture-output/courseware-image.pptx` (change filename for editable mode).
5. Inspect `lecture-output/qa/` for visual clipping and PPT playback controls.
   The program performs automatic Chinese coverage and number checks; human
   *Chinese translation proofreading* is optional, never a default gate.
6. Present the PPTX, the modes/limitations, the selected backgrounds and text colors,
   and any unresolved ASR/numerical discrepancies to the user.

## Input and outputs

- Input: lecture audio file, and optionally existing `sentence_cn.json`.
- Transcription: `merged_cues.json` contains `{start,end,en}` entries.
- Slide timing: `slides.json`, per-slide `{start,end,offset,cues,bar_color}`.
  Special review/spliced slides may use `segments`; mark `review:true` if they
  intentionally repeat source cues. Never splice a word or sentence.
- `manifest.json`: one item per slide with `bar_color`, relative `audio`,
  `ass`, `video`, `poster`, optional `picture`, `title`, `bullets`, `notes`.
- Outputs: `enhanced_master.wav`, per-slide MP3/ASS/MP4, QA frames and final PPTX.

## Individual scripts

- `scripts/pipeline_core.py`: pure validators, sentence timing, contrast and safe paths.
- `scripts/make_ass.py`: construct bilingual ASS with per-slide colors.
- `scripts/make_videos.py` or `make_videos.sh`: actually render synchronized MP4s.
- `scripts/build_ppt.py`: create image-slide or editable-text PPT from a manifest,
  with one embedded MP4 per slide and optional autoplay.
- `scripts/validate.py`: inspect text, cue mapping, media duration, fonts/QA
  sample visibility and PPTX structure.
- `scripts/run_pipeline.py`: end-to-end orchestration.

Run `python3 -B -m unittest discover -s tests -v` after changes. Do not change
existing source media or overwrite previous generated files without explicit `--force`.
