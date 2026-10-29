# Recording to Bilingual PPT

Make Chinese–English lecture courseware with the **original speaker's cleaned audio**,
complete sentence-level bilingual subtitles, a reserved subtitle video strip on
every slide, and either image-based slides or **editable PowerPoint text**.

## Requirements

- Python 3.10+ and `pip install -r requirements.txt`
- FFmpeg and ffprobe on `PATH`; FFmpeg must include `libass`, `libx264` and `libmp3lame`.
- An installed `Noto Sans CJK SC` font (recommended; otherwise font substitution may alter subtitle layout).
- A local Whisper model from faster-whisper (first use downloads weights).
- For automated Chinese translation, Ollama running **locally** with a Chinese-capable
  model, e.g. `ollama pull qwen2.5:7b`. Alternatively provide a reviewed translation JSON.

No source recordings, transcripts, credentials or personal documents are bundled.
The normal workflow is **automatic Chinese translation without manual proofreading**.
The pipeline retries invalid model output and validates translation IDs, Chinese
characters and Arabic-digit quantities. Specialized terminology may still need
review in high-stakes material.

## Quick start — local translation, image slides

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --slides 10 --mode image --ollama-model qwen2.5:7b --autoplay
```

For native editable PowerPoint text, switch `--mode editable`. To vary
backgrounds per slide, add `--colors F6FBF3,273448,FFF4DD`.

The output directory retains `enhanced_master.wav`, `merged_cues.json`,
`sentence_cn.json`, `slides.json`, per-slide MP3/ASS/MP4,
`qa/slideXX.png`, `manifest.json` and `courseware-image.pptx`
(or `courseware-editable.pptx`).

## Optional supplied translations (not the default)

If Ollama is not available, transcription and translation can be separated:

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --stage transcribe
```

Review `lecture-output/merged_cues.json` and provide translations in
`lecture-output/sentence_cn.json` as a JSON mapping with exactly one
Simplified Chinese sentence per cue:

```json
{"1": "第一句翻译。", "2": "第二句翻译。"}
```

Resume without redoing the transcription:

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --translations ./lecture-output/sentence_cn.json --resume --mode editable
```

## Validate and review

```bash
python3 scripts/validate.py --manifest lecture-output/manifest.json \
  --ppt lecture-output/courseware-image.pptx
python3 -B -m unittest discover -s tests -v
```

The generated QA frames must be checked visually. Native PowerPoint playback
can differ across desktop/mobile versions; `--autoplay` writes automatic
video-start timing, but compatibility must be verified in the target player.

The default slide outline is **extractive**: it takes phrases from the
transcript, without fabricating facts. It is a usable starting draft, not a
substitute for editorial review or verification of numerical lecture content.
Image mode is intentionally not editable as text.

This pipeline does not upload recordings/transcripts to third-party services.
The Ollama URL is restricted to localhost; model downloads, if needed, are
a separate network action. Use only trusted audio and review the transcript
before publishing courseware.

See `SKILL.md` for detailed execution rules.
