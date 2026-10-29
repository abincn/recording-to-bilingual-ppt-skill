---
name: recording-to-bilingual-ppt
description: Turn lecture, training, meeting or classroom recordings from any subject into content-specific Chinese-English PowerPoint courseware with the original cleaned speaker audio and synchronized bilingual subtitles. Use for lecture transcription, translation, topic-aligned slide planning, examples, diagrams, tables, steps, formulas, and editable or image-based PPT delivery.
---

# Recording → bilingual PPT

Build a **different lesson from each recording**. Never import example content, numbers,
slides or discipline-specific assumptions into a new job. Read `README.md` for setup
and `references/plan-schema.md` when authoring a finished courseware plan.

## Non-negotiable rules

- Preserve the lecturer's **original voice**; reduce noise and normalize volume without
  inventing speech or replacing it with synthetic narration.
- Transcribe with time-stamped words, form coherent sentence cues and translate each cue
  with the same 1-based ID. Preserve numbers, formulas, names and technical terms.
  Chinese translation is automatic **without mandatory human proofreading**.
- **Do not start a local translation model by default.** If the user declines local
  translation, use ChatGPT to produce `sentence_cn.json` and pass `--translations`.
  Ollama is optional, only when explicitly selected with `--translator ollama`.
  Transcription via local Whisper is separate from translation.
- A finished deck **requires content-specific planning** from the actual recording.
  No fixed subject, 10-slide quota, chapter sequence, accounting tables or default
  visual type. The bundled extractive auto-outline is **draft-only** and must be
  called a draft, never a finished curated lesson.
- Each slide covers complete, consecutive transcript cue IDs. Do not split or omit
  taught content, alter speaker chronology, repeat audio, or break alignment to
  meet a target slide count. Optional filler reduction must not remove meaning.
- Use only values and claims supported by the recording or clearly marked external
  material. Do not silently change uncertain ASR figures. When arithmetic exists,
  check it; a derived figure needs a derivation note and a source-verification flag.
  Non-numeric lessons do not need artificial calculations or data tables.
- Keep all slide text above the reserved subtitle strip. Preserve the actual 1920×260
  colored subtitle background with English first, Chinese second, alignment 5,
  legible CJK fonts, >=4.5:1 contrast, and QA frames for actual renders.
- The final PPT must have one correctly timed original-audio video strip per
  narrated slide. Image mode is not text-editable; editable mode uses native
  PowerPoint shapes and native tables for table slides.
- State any ASR ambiguity, correction, unmatched number, source limitation,
  slide mode, and playback caveat in delivery. Never claim manual verification
  unless it actually occurred.

## Content-adaptive planning (default for finished courseware)

1. **Understand the recording first.** Determine subject, audience, learning goal,
   main topics, definitions, worked examples, demonstrations and question segments.
   Identify where topics start and stop by cue ID, not equal clock intervals.
2. **Select structures that fit the information.** Examples—not required sections:
   - Concepts/explanations → concise bilingual bullet cards.
   - Procedures or lab/workshop demonstrations → numbered steps.
   - Comparisons, categories or experimental data → comparison/native table.
   - Equations → formula with interpretation and units.
   - Literature, history, interviews and speeches → quotation plus context.
   - Numerical exercises → worked examples and calculation checks.
   - Storytelling or case studies → chronological sections; tables only if useful.
   Choose a suitable mix, and omit irrelevant types. Add maps, plots or diagrams
   only when they clarify the actual material and are source-grounded.
3. **Create a source-anchored plan** using `references/plan-schema.md`. The
   `--courseware-plan` JSON explicitly assigns each slide's cue range, title,
   layout and content. Plan count is determined by natural topics; `--slides`
   applies only to draft fallback.
4. **Cross-check every slide against its cue range**, including translated key
   terms, numbers and the ordering of examples. If an assertion is inferred,
   label the inference in notes or footnotes. A unique example never becomes
   a universal rule for other recordings.
5. **Build and inspect** image or editable output. Tables are native editable
   PowerPoint tables when `--mode editable`; other layouts stay text-editable.

The skill's general layouts are `bullets`, `steps`, `table`, `comparison`,
`formula`, and `quote`. A special diagram or illustration may be supplied
as a designed slide image when suitable; ensure its text and evidence remain
readable. Never force a lecture into a layout merely because it is available.

## Workflow

1. Check Python dependencies, FFmpeg/libass/libx264/libmp3lame, ffprobe,
   and Chinese fonts; use the user's preferred ASR/translation environment.
2. Produce the original cleaned audio and timestamped English cues:

   ```bash
   python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output --stage transcribe
   ```

3. Use ChatGPT (or the explicitly chosen translation source) to create
   `lecture-output/sentence_cn.json` with all `"1"`, `"2"`, ... cue keys,
   and independently curate `lecture-output/courseware-plan.json` from
   the **actual** recording. See `references/plan-schema.md`.
4. Generate finished image or editable courseware:

   ```bash
   python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
     --resume --translations ./lecture-output/sentence_cn.json \
     --courseware-plan ./lecture-output/courseware-plan.json --mode editable --autoplay
   ```

   For a preliminary extractive draft only, omit `--courseware-plan`
   and choose `--slides N`; label the result **DRAFT**. Do not deliver it
   as curated courseware.
5. If the user explicitly prefers Ollama, pass `--translator ollama`
   in place of `--translations`. No other network translation is automatic.
6. Run `scripts/validate.py`, check `qa/` screenshots and inspect the
   slides in the target presentation app. Use
   `python3 -B -m unittest discover -s tests -v` after code changes.

## Output contract

- `merged_cues.json`: sentence-level `{start,end,en}` transcript.
- `sentence_cn.json`: exact 1-based Chinese translations.
- `courseware-plan.json`: selected topic ranges and visual layouts.
- `slides.json`: actual sentence-timed audio/video ranges (not equal slices).
- `manifest.json`: PPT shape content, subtitle videos, timing and notes.
- `enhanced_master.wav`, `subtitle_videos/`, `slide_images/`, `qa/`,
  and final `courseware-image.pptx` or `courseware-editable.pptx`.

The example in `examples/ch13-curated.md` is **only** an accounting example.
Its numbers and layout choices must never be loaded into another lecture.

In delivery, summarize the actual lecture, slide structure and languages,
identify editable/image mode, disclose ambiguities and source corrections,
and mention that embedded video autoplay depends on PowerPoint compatibility.
