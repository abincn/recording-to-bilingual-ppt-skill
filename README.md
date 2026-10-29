# Recording → Interactive Bilingual Courseware

**Version 2.1.1** · [Check `VERSION`](VERSION)

Turn lectures, classes, workshops, meetings or training recordings from **any
subject** into a downloadable **single-file HTML** learning experience. The
page includes the lecturer's cleaned **original voice**, every relevant
Chinese–English subtitle, illustrated courseware slides, topic navigation,
and live speed controls. **No unzip, server, JavaScript framework, internet or
external assets are needed to play it.** Just download the `.html` and open it
in Chrome or Edge.

PowerPoint is retained as a separately requested legacy option; HTML is the
default as of v2.0.0. The repository name remains unchanged so existing links
and installations keep working.

## Interactive player

- Play/pause, jump back/forward 10 seconds and drag the whole-recording timeline.
- Choose content-adaptive chapters and automatically switch slides/subtitles.
- Display English, Chinese, both or neither.
- Adjust **0.5× to 2.0×** in **0.1× steps**; keep the original speaker pitch.
- Compress verified long gaps without cutting speech; merge very short
  adjacent subtitles to avoid one-frame flashes.
- Single self-contained output, including MP3 audio and embedded slide images.
- A visible skill version in the page footer and `manifest.json`.
- A source-timestamped transcription QA report flags suspicious numbers,
  years, abbreviations and potential slide-vs-subtitle inconsistencies.
  Results are review prompts, never automatic corrections.

## Requirements

- Python 3.10+; `pip install -r requirements.txt`
- `ffmpeg` and `ffprobe` with `libmp3lame`; legacy PPTX also needs `libass`
  and `libx264`
- Noto Sans CJK or equivalent Chinese-font support for generating slide images
- Local faster-whisper ASR weights (may download upon first use)
- No local translation model required: the active AI agent prepares an
  ID-keyed Simplified Chinese translation JSON. Local Ollama translation is
  optional only when explicitly selected.

## Install for an AI coding assistant

This repository uses the common `SKILL.md` format. The agent needs permission
to read files and execute Python/FFmpeg; pasting `SKILL.md` into a web-only AI
chat cannot by itself run the scripts.

For project-scoped installation, place the **whole repository** (not just
`SKILL.md`) in one of these locations:

| Agent | Skill folder relative to your project |
| --- | --- |
| Codex, Cursor, Gemini CLI, OpenCode | `.agents/skills/recording-to-bilingual-ppt/` |
| Claude Code | `.claude/skills/recording-to-bilingual-ppt/` |

Example for the shared `.agents` location, from your project root:

```bash
mkdir -p .agents/skills
git clone https://github.com/abincn/recording-to-bilingual-ppt-skill.git \
  .agents/skills/recording-to-bilingual-ppt
python3 -m pip install -r .agents/skills/recording-to-bilingual-ppt/requirements.txt
```

For Claude Code, replace `.agents/skills` with `.claude/skills`. The local
folder is named `recording-to-bilingual-ppt` to match the frontmatter
`name` in `SKILL.md`. On Windows use equivalent PowerShell commands and
`python` if `python3` is unavailable. Follow the FFmpeg, font and ASR
requirements above.

The skill is **AI-provider neutral**: its host AI translates and plans the
lesson, while Python handles deterministic media and HTML generation. To invoke
it, ask the agent: "Use recording-to-bilingual-ppt for this lecture audio.
Generate an offline single-file Chinese-English interactive HTML lesson, with
automatic Chinese translation and no mandatory manual proofreading."

Update an installed copy with
`git -C .agents/skills/recording-to-bilingual-ppt pull --ff-only` (adjust the path
for Claude). `VERSION` identifies the release; it does **not** install
updates automatically.

## Generate a finished lesson

The commands in this section assume you are in the **skill repository root**
and `lecture.m4a` is in that directory. AI agents working elsewhere should
instead invoke the scripts by their **absolute paths** and pass absolute audio
and output paths, as shown in `SKILL.md`.

**1. Transcribe the actual recording**

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --stage transcribe
```

This produces `enhanced_master.wav`, `merged_cues.json`, and two audit files:
`transcript-qa.json` and `transcript-qa.md`. The QA report keeps original
cue IDs and timestamps; numbers and years are **not** guessed or silently
corrected. Three-digit values such as `211` remain as recognized until the
source recording or an authoritative reference supports a correction.

Optionally request an additional local Whisper pass on up to 12 sensitive cues
(adds recognition time) or compare an independent second-pass transcript:

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --stage transcribe --resume --qa-recheck
# OR supply a second-pass JSON with original-time English cues / ID-to-text values:
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --stage transcribe --resume --qa-compare ./second-pass.json
```

Disagreements are listed for review; neither pass overwrites the other.
Optional comparison evidence is saved as `qa-second-pass.json` and reused
on `--resume` only if the source transcript is unchanged. A
correct arithmetic sum does not by itself prove individual figures were heard
correctly. When textbooks or calculations supply a figure, record the evidence
in the plan notes or table footnote instead of rewriting the speaker's words.

**2. Curate content and translations**

- Have the current AI agent translate each English cue to Simplified Chinese
  in a 1-based JSON map (`"1"`, `"2"`, ...), preserving figures, formulas and names.
  **Manual Chinese proofreading is not required**; flag uncertain ASR text.
- Analyze this specific transcript and write a source-anchored
  `courseware-plan.json`, including cue ID ranges and appropriate layouts:
  `bullets`, `steps`, `table`, `comparison`, `formula`, `quote`.
- Choose slide count, topic sequence and visual mix from the recording, never a
  fixed 10-slide template or accounting example. See
  [plan schema](references/plan-schema.md).

**3. Build the default offline HTML**

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --resume --translations ./lecture-output/sentence_cn.json \
  --courseware-plan ./lecture-output/courseware-plan.json
```

Open `lecture-output/courseware-interactive.html` in any modern Chrome or
Edge browser, directly from disk. The generated project directory also retains
source/intermediate files and audit reports; the user-facing HTML is the only
file that needs to be shared.

To regenerate a webpage after changing a prepared project's images or captions:

```bash
python3 scripts/build_web.py --project ./lecture-output --force
```

### Default silence and subtitle optimization

- Compress only confirmed **non-speech** silence at least **2.5 s** long to
  roughly **0.8 s**, excluding transcript cue intervals. The quiet threshold
  after audio normalization is **−14 dB** by default.
- Combine captions shorter than **1 s** with adjacent captions in the same
  chapter if the combined bilingual text still fits. Otherwise extend into
  available gaps toward **1.5 s**; do not drop any words.
- Generate `optimized_master.wav`, `optimized_cues.json`,
  `silence-report.json` and `subtitle-report.json`; keep the originals.
- Disable with `--no-silence-compression` / `--no-caption-merge` and tune with
  `--min-silence`, `--target-pause`, `--silence-db`, `--short-caption`,
  `--min-caption`.

### Optional PowerPoint

Request a `.pptx` explicitly:

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --resume --translations ./lecture-output/sentence_cn.json \
  --courseware-plan ./lecture-output/courseware-plan.json \
  --format pptx --mode editable --autoplay
```

Choose `--mode image` for fixed visual slide images; `--mode editable` uses
native PowerPoint text and tables. Its per-slide narrated video/subtitle strips
depend on PowerPoint and codec compatibility. The default HTML does **not**
need those video strips.

### Draft and Ollama option

Omitting `--courseware-plan` produces an extractive **DRAFT** only; `--slides
N` affects only this fallback. It must not be described as a finished lesson.

Ollama is **opt-in**, never started for translation automatically:

```bash
python3 scripts/run_pipeline.py --audio lecture.m4a --project ./lecture-output \
  --resume --translator ollama \
  --courseware-plan ./lecture-output/courseware-plan.json
```

## Version and validation

```bash
python3 scripts/run_pipeline.py --version
python3 scripts/build_web.py --version
python3 -B -m unittest discover -s tests -v
```

`VERSION` contains the authoritative SemVer (currently `2.1.1`). Every new
release updates that file (and this visible release text); the CLIs, HTML
footer and `manifest.json` automatically use the same value.

Check the actual HTML by opening it as a local file and trying audio playback,
chapter jumps, subtitles, seeking and 0.1× speed changes. Check that all
images appear and no external assets are required. For legacy PPTX, run
`python3 scripts/validate.py --manifest lecture-output/manifest.json --ppt
lecture-output/courseware-editable.pptx`.

For an **accounting-specific** example, see
[Chapter 13](examples/ch13-curated.md)—not a template for other lessons.
