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
- Make sentence-based English cues, preserve complete sentences, then translate
  each cue into Chinese with the same 1-based identifier. Match counts,
  identifiers, Chinese-script presence and Arabic-digit quantities automatically.
  Retry invalid model outputs; do not require manual Chinese proofreading by default.
  If punctuation is absent, pause-based/semantic sentence boundaries require review.
- **Translation source is chosen by the user, never assumed.** Local Ollama is
  only one option; assistant-supplied or user-supplied `sentence_cn.json` is
  equally valid, and is the default when the user has declined local-model
  translation. Do not start a local-model install or download on that basis.
- **Default slide mode is curated hand-table courseware, not extractive draft.**
  The extractive outline (first cue as title, next cues as bullets) is only a
  fallback draft, must be labelled as such in delivery, and must never be
  delivered as finished courseware when the user expects hand-designed slides.
  See "Curated hand-table mode" below. This rule overrides any pipeline default
  that produces extractive titles such as "Okay." as a slide title.
- **Subtitle cue merging (curated mode).** Merge short cues (< 2.5 s or
  < 12 characters) into the next cue, drop filler-only cues that carry no
  content (for example a lone "Okay."), and never split a sentence across
  cues or slides. Long cues that contain board-writing pauses are kept whole.

## Curated hand-table mode (default)

Design the slide deck from the lecture's structure, not from transcript order
alone. For an exercise-driven lecture, the deck is typically: cover, the
section map, core rules, one slide per exercise with a bilingual table,
worked examples, common mistakes, and a review checklist.

- **Slide images are hand-designed** (2560×1440 in the reference deck, same
  background as the subtitle bar). Each table is bilingual: English item name
  plus Chinese, with Change / Adjustment / Amount columns as the exercise
  requires, a distinct total row, and a footnote for anything derived or
  uncertain. In image mode the slide text is **not editable in PowerPoint**;
  in editable mode the same tables must be native PowerPoint tables, not
  bullet lists with the same numbers.
- **Arithmetic must close exactly.** Every table total is recomputed from its
  rows before delivery (for example 106,800 + 41,700 − 11,000 + 4,800 + 2,750
  + 4,900 − 1,700 = 148,250). A row whose number is back-derived from the
  total, or whose number was not clearly spoken, is footnoted with its
  derivation and marked for textbook verification; it is never presented as
  if it were spoken. A row whose number is genuinely unknown is shown as
  "—", not filled in.
- **Slide timing is topic-aligned, not equal-partitioned.** Each curated
  slide covers the recording range for its topic, aligned to sentence
  boundaries. Review slides may splice non-contiguous ranges at sentence
  boundaries only; mark them `review:true` in `slides.json`.
- **Corrections are listed, never silent.** When a later, clearer
  transcription changes a table figure (for example inventory decrease
  6,800 → 4,800, prepaid decrease 750 → 2,750, or a previously blank
  depreciation row filled with 81,750), delivery must list the old figure,
  the new figure, and where the new figure came from.
- Worked example: `examples/ch13-curated.md` records the verified Chapter 13
  tables (13-3 = 66,730; 13-4 = 502,960; 13-5 = 148,250; land gain 13,300,
  net investing −39,700; bonds issued cash 420,000, redeemed cash 138,000,
  net financing +282,000) with the derivation note for 13-4 accounts
  receivable increase 6,000.
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

   **Curated mode (default for finished courseware):** do not ship the
   pipeline's extractive deck as-is. First design the curated deck and its
   topic-aligned `slides.json` (see "Curated hand-table mode"), render or
   supply the hand-table slide images, reuse the pipeline's cleaned audio,
   merged bilingual cues and middle-centred subtitle videos for those
   ranges, then build the PPTX from the curated images + videos with
   `scripts/build_ppt.py` (image mode) or native tables (editable mode).
   Recompute every table total and record any correction before delivery.

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
6. Present the PPTX, the mode (curated hand-table image, curated hand-table
   editable, or extractive draft — labelled as a draft), the selected
   backgrounds and text colors, every table arithmetic check, every
   correction versus a previous draft, and any unresolved ASR/numerical
   discrepancies to the user.

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
