---
name: recording-to-bilingual-ppt
description: Convert lectures, meetings, classes, training, workshops or interviews into subject-adaptive, offline single-file HTML courseware with the original cleaned audio, synchronized English-Chinese subtitles, interactive topic navigation and 0.1x playback speed controls. Use for recording transcription, automatic Chinese translation without mandatory human proofreading, content-specific slide planning, long-silence compression, short-caption merging, and optional legacy PowerPoint export.
---

# Recording → interactive bilingual courseware

**Current release: v2.0.0.** `VERSION` is authoritative; `--version`, the
generated `manifest.json` and the HTML footer read it automatically.

Create a **different lesson from each recording**. The default deliverable is
**one standalone `courseware-interactive.html`**: all images, the original-voice
MP3 and bilingual subtitles embedded, with no CDN, external scripts, downloads
or network requirement. Users can download it and double-click to open in
Chrome or Edge. Do not upload the recording or publish the page online unless
explicitly asked. PowerPoint remains available only with `--format pptx`.

Read `README.md` for setup and `references/plan-schema.md` when preparing a
finished courseware plan.

## Rules that always apply

- **Keep the lecturer's real voice.** Clean noise and normalize loudness;
  never substitute generated speech. Shorten only verified non-speech silence
  outside all spoken cue ranges, preserving a natural pause and remapping time.
- Transcribe to time-stamped English sentences; translate every cue with its
  exact 1-based ID. Preserve numbers, formulas, names and technical terms.
  Chinese translation runs automatically by ChatGPT **without mandatory human
  proofreading**. Flag doubtful ASR content instead of pretending it was checked.
- **Do not start a local translation model by default.** Create
  `sentence_cn.json` with ChatGPT and pass `--translations`; use Ollama only
  if the user explicitly chooses `--translator ollama`. Local Whisper ASR
  and local translation are separate decisions.
- A **finished** courseware requires a plan derived from the actual lecture,
  never a fixed slide count, fixed subject or reusable topic content. The
  extractive `--slides N` fallback is **DRAFT** only.
- Cover each transcript cue exactly once across ordered chapters. Preserve
  content, speaker chronology, complete examples and audio synchronization.
  Never delete speech to shorten the course or discard words to hide subtitles.
- Use source-supported facts. Identify uncertain ASR figures and inferred
  values. Check arithmetic only for lessons containing calculations. Do not
  invent tables, diagrams or formulas for material that does not need them.
- Merge fleeting captions only across adjacent cues in the **same chapter**
  when the full bilingual text is readable; otherwise extend display into
  available gaps. Preserve the original English and Chinese strings.
- In default HTML, keep subtitles in a separate area beneath the slide image.
  Provide interactive play/pause, seeking, chapters, ±10 s, CN/EN/bilingual/off
  subtitles, fullscreen and **0.5×–2.0× speed in 0.1× steps**, preserving pitch.
  The complete package must work without internet or extracted sidecar files.
- Preserve source audio, transcripts, plan, timing reports and artifacts in
  the working project; only the final HTML needs to be shared. Avoid uploading
  classroom content to a public website without permission.

## Content-adaptive planning

1. Listen/read the transcript and identify **this lesson's** subject,
   audience, learning goals, topic boundaries, examples and questions.
2. Choose whichever layouts actually help: `bullets`, `steps`, `table`,
   `comparison`, `formula`, `quote`; diagrams and images only if grounded in
   the lesson. Accounting tables, laboratory procedures, historical timelines
   and language-study quotations are **examples**, never default sections.
3. Create `courseware-plan.json` as described in `references/plan-schema.md`.
   Map each slide to consecutive original cue IDs, not equal clock intervals.
   Chapter counts and layouts should follow natural topical changes.
4. Verify slide contents against the exact cue ranges. Preserve technical
   names, units, quotations and calculations; disclose any inference.
5. Generate visually legible slides. Tables and formulas should be clear on
   a phone and desktop; no text may overflow or collide with the subtitle area.

## Recommended workflow

1. Check Python, FFmpeg/ffprobe (`libmp3lame`; `libass`/`libx264` only for
   optional PPTX), Noto Sans CJK fonts and the preferred ASR environment.
2. Transcribe and clean the real lecture:

   ```bash
   python3 scripts/run_pipeline.py --audio lecture.m4a \
     --project ./lecture-output --stage transcribe
   ```

3. Using ChatGPT, translate each cue into Simplified Chinese in
   `lecture-output/sentence_cn.json` using keys `"1"`, `"2"`, ... and
   curate `lecture-output/courseware-plan.json` based on **this recording**.
   Chinese editing/confirmation is optional, not a blocking step.
4. Generate the **default single-file HTML**:

   ```bash
   python3 scripts/run_pipeline.py --audio lecture.m4a \
     --project ./lecture-output --resume \
     --translations ./lecture-output/sentence_cn.json \
     --courseware-plan ./lecture-output/courseware-plan.json
   ```

   The finished result is `lecture-output/courseware-interactive.html`.
   If you need to repackage a finished project without retranscribing, use
   `python3 scripts/build_web.py --project ./lecture-output --force`.

5. Keep default timing refinements on: silence of at least **2.5 s** is
   reduced to roughly **0.8 s** only when outside all cue ranges (threshold
   **−14 dB**, normalized master); captions shorter than **1 s** merge with
   short same-chapter neighbours if legible or are extended toward **1.5 s**.
   Use `--no-silence-compression` or `--no-caption-merge` to disable. Tune with
   `--min-silence`, `--target-pause`, `--silence-db`, `--short-caption`,
   `--min-caption` where necessary. Keep source IDs and both languages intact.
6. Validate the generated HTML by opening it **locally** (prefer `file://`
   in Chrome/Edge); test audio play, seek, next chapter, subtitle visibility,
   speed at 1.1× and 0.5× and offline loading. Check captions against audio
   and ensure all chapter images load, no missing external assets and no
   browser console errors. Run `python3 -B -m unittest discover -s tests -v`
   after changes to scripts.

### Optional legacy PowerPoint

Use only when the user explicitly requests a `.pptx`:

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a \
  --project ./lecture-output --resume \
  --translations ./lecture-output/sentence_cn.json \
  --courseware-plan ./lecture-output/courseware-plan.json \
  --format pptx --mode editable --autoplay
```

`--mode image` uses fixed slide images; `--mode editable` generates native
PowerPoint text and tables. PPTX contains per-slide original-voice video
subtitle strips, which may auto-play differently across PowerPoint versions.
Validate with `scripts/validate.py` and inspect sample QA frames. Do **not**
apply PPTX-only strip requirements to the HTML layout.

## Output and version contract

- `VERSION`: one-line SemVer, initially `2.0.0`. Update it on every release;
  increase the major component for incompatible deliverable/API changes.
- `python3 scripts/run_pipeline.py --version` and
  `python3 scripts/build_web.py --version` print the exact `VERSION`.
- `manifest.json` contains `skill_version` and `format` (`html` or `pptx`);
  the HTML footer displays the same version for update identification.
- `merged_cues.json` and `enhanced_master.wav`: source-aligned transcript and
  cleaned original voice.
- `optimized_master.wav`, `optimized_cues.json`, `silence-report.json`:
  compressed media, remapped time and savings; never lose original artifacts.
- `sentence_cn.json`: Chinese text with matching 1-based IDs.
- `courseware-plan.json`: actual content-based chapter plans and slide layouts.
- `slides.json`, `subtitle-report.json`, `slide_images/` and `manifest.json`:
  synchronized chapter boundaries, subtitle optimization and images.
- Default final: `courseware-interactive.html`, a single offline HTML containing
  its own MP3, slide images and full bilingual caption timeline. No other file
  needs to accompany it.
- Optional PPTX: `courseware-image.pptx` or `courseware-editable.pptx`, with
  `subtitle_videos/` and `qa/` intermediates.

Example lesson `examples/ch13-curated.md` is **accounting-specific only**.
Do not reuse its figures, count or teaching order for another subject.

In delivery, give the single HTML download, explain offline double-click
opening, summarize actual topics and duration saved, and disclose ASR
uncertainty or unverified figures. Never claim manual checking unless done.
