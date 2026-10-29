# Recording to Bilingual PPT

Turn **any** teaching, training, lecture, workshop, or interview recording into
content-specific Chinese–English PowerPoint courseware. Preserve the lecturer's
cleaned original voice, align sentence-level subtitles to each topic, and choose
the slide structure from what the recording actually teaches.

**Do not use a fixed deck for every class.** Accounting tables, science
process diagrams, historical timelines and language-study quotations are
illustrative possibilities, not universal templates. The completed deck is
based on a source-anchored courseware plan; without such a plan the pipeline
produces an explicitly labelled extractive **draft**.

## Requirements

- Python 3.10+; `pip install -r requirements.txt`
- `ffmpeg` and `ffprobe`, with libass, libx264, libmp3lame
- An installed Noto Sans CJK font for bilingual image slides and subtitles
- Local Whisper transcription weights (first use may download the ASR model)
- **No local translation model is required.** ChatGPT can translate the
  timestamped cues and supply `sentence_cn.json`. Ollama is available only
  when explicitly requested with `--translator ollama`.

## Finished courseware: two passes

**1. Transcribe the actual lecture**

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --stage transcribe
```

This produces `enhanced_master.wav` and `merged_cues.json`.

**2. Curate its content**

- Use ChatGPT to translate each English cue into Simplified Chinese as a
  1-based JSON map (`"1"`, `"2"`, ...); preserve technical terms and figures.
- Analyze that **specific** lecture, identify topic boundaries, and construct
  `courseware-plan.json` with one or more of these layouts:
  `bullets`, `steps`, `table`, `comparison`, `formula`, `quote`.
- Choose the actual slide count and mix, not a predetermined number.
- Verify the lecture supports all claims. Recompute arithmetic only when
  relevant, flag uncertain transcription, and identify inferred values.
- Read [the plan format](references/plan-schema.md) for exact JSON rules.

**3. Render either image-based or editable PPTX**

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --resume --translations ./lecture-output/sentence_cn.json \
  --courseware-plan ./lecture-output/courseware-plan.json \
  --mode editable --autoplay
```

Choose `--mode image` for fixed-design slide images; with `--mode editable`,
text and data tables are native PowerPoint objects.

All narrated slides have the original speaker's cleaned audio embedded in a
video subtitle strip. Captions are English over Chinese and remain outside
the content area.

### Default quiet-audio and short-caption optimization

- Compress only detected non-speech silence lasting at least **2.5 s** to around
  **0.8 s**, protecting all transcript cue intervals. The FFmpeg quiet threshold
  after loudness normalization defaults to **-14 dB**.
- Merge captions shorter than **1 s** with adjacent captions on the same slide
  if bilingual text fits. Otherwise, extend their display into available gaps
  toward **1.5 s**. Never drop English or Chinese transcript text.
- Preserve `enhanced_master.wav` and `merged_cues.json`. Emit
  `optimized_master.wav`, `optimized_cues.json`, `silence-report.json` and
  `subtitle-report.json`; every slide clip uses the new synchronized clock.
- Disable with `--no-silence-compression` and/or `--no-caption-merge`;
  tune using `--min-silence`, `--target-pause`, `--silence-db`,
  `--short-caption` and `--min-caption`.

## Draft or explicit Ollama option

A preliminary **draft** can omit `--courseware-plan` and use `--slides 8`
(or another count); its first-cue/next-cue text is not a finished lesson.

Ollama is opt-in only:

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --resume --translator ollama --courseware-plan ./lecture-output/courseware-plan.json
```

Do not use this if the user declines local-model translation.

## Validation

```bash
python3 scripts/validate.py --manifest lecture-output/manifest.json \
  --ppt lecture-output/courseware-editable.pptx
python3 -B -m unittest discover -s tests -v
```

Inspect subtitle QA frames and playback in the recipient's PowerPoint
version: autoplay and video codecs depend on software support.

The project directory retains the cleaned audio, timestamped transcript,
translations, plan, source-aligned slide timeline, MP3/ASS/MP4 subtitle
strips, slide images, QA frames and final PPTX.

For one subject-specific example only, see
[Chapter 13 accounting](examples/ch13-curated.md). It is **not** a default
slide template or a source of numbers for other recordings.
