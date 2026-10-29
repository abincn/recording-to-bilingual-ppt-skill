# Recording to Bilingual PPT with Original Audio and Subtitles

Turn a lecture recording into a bilingual (Chinese-English) PPT courseware
file where every slide carries the lecturer's own voice, with bilingual
subtitles that never cover the slide text, never split a sentence, and
never lose the Chinese line to the player controls.

This skill is a playbook, not a black box. It was distilled from a real
run: a 25-minute English accounting lecture (Chapter 13, Statement of
Cash Flows, Indirect Method) turned into a 10-slide PPT. That run is
used below only as a worked example; the steps themselves are generic.

## When to use it

- The user uploads a voice note / recording and asks for courseware in
  PPT format, in Chinese and English.
- The user asks, in any order, for: per-slide original audio, subtitles
  while the audio plays, subtitles that do not cover the slide text,
  subtitles whose background matches the slide, or subtitles that do
  not split sentences.
- Do NOT use this skill for a re-dubbed / TTS narration task. The
  audio here is always the lecturer's own recording, cleaned up, never
  re-spoken. Say that explicitly to the user: words the microphone did
  not capture cannot be restored.

## Pipeline in order

### 1. Transcribe with word timestamps, then verify the numbers

1. Transcribe locally with faster-whisper (small model is enough for a
   classroom lecture). Keep per-word start/end times, not just segments.
   Environment note from the reference run: pin `av==12.3.0`; av 19
   breaks faster-whisper in that setup.
2. Build the courseware content from the transcript, then verify every
   number by arithmetic before it goes on a slide. Do not copy a
   garbled number into a table.
3. If a later, clearer transcription contradicts a slide table, do NOT
   silently change the slide. Flag the discrepancy to the user in the
   delivery message and ask whether to correct the slide image, because
   the slides are image-based (see step 5) and fixing a table means
   rebuilding that slide.

Worked example (Chapter 13, for reference only, not universal facts):
- Three sections: Operating, Investing, Financing.
- Indirect method: start from net income; add back non-cash items
  (depreciation, loss on disposal, bond discount amortisation);
  current-asset increase = subtract, decrease = add; current-liability
  increase = add, decrease = subtract; a gain on disposal is deducted
  in Operating, while Investing records only the actual cash.
- Ex 13-3: 75,800 - 5,000 (AR up) - 7,450 (inventory up) + 3,380 (AP up)
  = 66,730. Dividends payable is Financing, not Operating.
- Ex 13-4: net income 400,200, depreciation 81,750, loss 22,300,
  AP +4,710, final 502,960 (the AR increase is then 6,000 by arithmetic).
- Ex 13-5: 106,800 + 41,700 - 11,000 (AR up) + 4,800 (inventory down)
  + 2,750 (prepaid down) + 4,900 (AP up) - 1,700 (wages payable down)
  = 148,250. Note the trap in the reference run: an early draft derived
  inventory 6,800 / prepaid 750 from the total; the clearer transcription
  gave 4,800 / 2,750, which also sums exactly to 148,250.
- Land: purchase cash paid 142,400 (outflow); sale cash received
  102,700; book cost 89,400; gain 13,300.
- Bonds 13-14: issued face 450,000, discount 30,000, cash received
  420,000; redeemed face 150,000, related discount 12,000, cash paid
  138,000; discount amortisation is a non-cash add-back in Operating.

### 2. Clean the audio, do not re-record it

Reference enhancement chain (ffmpeg, on the full recording first,
then split):

```
mono mix -> highpass 100 Hz -> afftdn nr=10
  -> equalizer +3 dB at 2500 Hz
  -> loudnorm I=-16, TP=-1.5, LRA=11 -> 32 kHz
```

In the reference run this moved the full file from about -37.6 LUFS
(mean volume about -40 dB, very quiet) to about -19 dB mean, with the
duration unchanged. Tell the user the result is cleaned-up original
audio, not a new voice.

Split the enhanced master per slide at sentence boundaries (see step 3
for how those boundaries are chosen), encoded as 48 kbps mono MP3.
Keep a durable copy of the enhanced master and the per-slide MP3s in
the project folder, never only in /tmp: /tmp is cleared between turns.

### 3. Subtitles: timeline first, English second, Chinese third, sentence by sentence

This order is the user's own workflow, and it is the core of the skill.
Do not skip a step, and do not translate before the timeline is fixed.

1. **Timeline + English, at word level.** From the word timestamps,
   group words into sentences. A sentence ends at `. ? !` (with the
   usual abbreviation care, e.g. "Inc." stays in its sentence).
   Drop filler-only cues such as a lone "Okay." Strip leading fillers.
   Apply only obvious ASR cleanups and record them (reference run:
   "funds receivable" -> "accounts receivable",
   "spending cash flows" -> "statement of cash flows").
2. **Merge short cues, never split a sentence.** A cue shorter than
   2.5 s or under 12 characters is merged into the NEXT cue. Complete
   sentences may share a cue, but no sentence is ever split across two
   cues. Long cues are kept whole even when they are long: in the
   reference run one cue lasted 41.8 s, one 63.2 s, one 71.4 s, because
   the lecturer was writing on the board. Their long display time is
   speaking pauses, not an error.
3. **Slide ranges aligned to sentence boundaries.** Choose each
   slide's audio range so that no cue crosses a slide edge. If a
   sentence starts at 344.05 s, the previous slide ends at 344 s and
   the next slide starts at 344 s. A trap / review slide that splices
   clips from several places must also splice at sentence boundaries,
   and its cue times must be offset-mapped onto the spliced timeline.
4. **Chinese translation, one per sentence.** Translate every merged
   cue, not just the long ones. Verify mechanically: the translation
   file must have exactly as many entries as there are cues, none
   empty, and every ASS dialogue must contain Chinese characters
   (count dialogues with no CJK range characters; the count must be 0).
5. **Style (the part that actually fixed the reported bug).**
   - Colours are ADAPTED to the slide, never hard-coded. No fixed
     bar colour and no fixed text colour anywhere in this skill:
     every run must sample the actual slide background first, then
     derive the bar and the text from it. If slides in one deck have
     different backgrounds, sample per slide, not once for the deck.
     - Video bar: 1920x260, background colour = the sampled slide
       background for that slide.
     - Text colour: chosen from that background by contrast, not by
       habit. Compute the background's relative luminance; a light
       background gets a dark text colour, a dark background gets a
       light text colour, aiming for a contrast ratio of at least
       4.5:1. Prefer a dark shade of the slide's dominant hue on a
       light slide, and a light shade of it on a dark slide, so the
       subtitles still belong to the deck; fall back to near-black
       on light / near-white on dark when there is no clear hue.
       Outline colour is the opposite of the text colour
       (outline 1, shadow 0). Record the sampled background and the
       chosen text colour for that deck in the delivery message.
       Example only, from the reference run, not a default: that
       deck's slide background was (246, 251, 243) = #F6FBF3, a
       light mint, so its bar used #F6FBF3 and its text used dark
       green #1B4332 (ASS BGR `&H0032431B`). On a different deck
       those two values must change.
   - Text style apart from colour: bold, font "Noto Sans CJK SC",
     size 32.
   - **Alignment: middle-centre (ASS alignment 5), NOT bottom-centre
     (2) and NOT top-centre (8).** This is the single most important
     detail in this skill. Bottom-aligned subtitles put the Chinese
     line, which is always the last line of a cue, at the very bottom
     of the video. In PowerPoint playback the player controls / bottom
     edge cover exactly that line, so the user sees English only and
     reports "most subtitles have no Chinese" even though the video
     file itself is correct. Middle-centre leaves empty space above
     and below the text, so a covered bottom edge cannot hide the
     Chinese line. A long multi-line cue still fits: centred, its
     block stays inside the 260 px bar.
   - Wrap: English about 85 characters per line, Chinese about 30
     characters per line. If a cue needs more than 4 lines total,
     shrink to size 26.
   - Slide background in the PPT itself must be set to the same
     sampled colour as the bar, so the bar and the slide read as
     one surface. That colour comes from sampling, not from this
     document.

### 4. Render each slide's audio as a video, not as bare audio

PowerPoint audio cannot carry captions, so each slide's audio becomes
a video:

```
ffmpeg -f lavfi -i color=c=0x<BAR_COLOR>:s=1920x260:r=10 -i slideXX.mp3 \
  # <BAR_COLOR> is the sampled slide background for that slide, e.g. F6FBF3 in the reference run, never a fixed value
  -vf "subtitles=slideXX.ass" -c:v libx264 -preset veryfast -crf 30 \
  -pix_fmt yuv420p -c:a aac -b:a 64k -t <exact audio duration> slideXX.mp4
```

Always pass `-t` with the exact audio duration. Without it, a previous
run produced a 73.5 s video for a 68 s clip. Verify every video with
ffprobe: its duration must equal its slide audio duration.

Sample frames before delivery, including at least one long cue and the
exact timestamp a user reports, and read them: both lines must be
visible, the text must be readable on the bar at the chosen contrast,
and no line may be cut at the bottom edge. Extracting a frame from the video file
alone is not enough if the user reports a playback problem: also
check the frame against the user's screenshot time, because a
standalone video can be correct while PPT playback crops it.

### 5. Assemble the PPT so subtitles can never cover slide text

- Slide size 13.333 x 7.5 in.
- Slide picture (the courseware image for that slide) on top only:
  10.124 in wide x 5.695 in high, centred horizontally, top at 0.
- Video strip at the bottom only: left 0, top 5.695 in,
  13.333 in wide x 1.805 in high. Its aspect (7.386) matches
  1920x260 (7.385), so the player does not crop it.
- Slide background: the same sampled colour as the video bar for
  that slide.
- Poster frame: a poster in the slide colour with a contrasting
  play triangle, not a black poster.
- Speaker notes per slide: the slide's topic and its recording time
  range, plus one line explaining the subtitle setup (bar matching
  the slide, contrasting text, sentence-based bilingual subtitles,
  middle-centred).
- Slides in this pipeline are image-based: the slide text is a picture,
  not editable PowerPoint text. Say that to the user up front, and
  only rebuild a slide image if they ask for an editable-text version
  or a corrected table.

Build the PPT cleanly from pictures + videos with python-pptx. Do NOT
strip old media shapes from an existing PPT and re-add new ones: the
old media parts stay orphaned in the package and roughly double the
file size (in the reference run, 34 MB became 62 MB that way). Rebuild
from scratch; a clean rebuild returned to 34 MB for 10 slides.

### 6. Verify before delivery, every time

- python-pptx reopen: 10 slides (or the actual slide count), each
  slide exactly 1 picture + 1 media shape.
- Every ASS file: every dialogue contains Chinese characters.
- Every video: ffprobe duration equals its audio duration.
- Sample frames: at least one frame per long cue, one frame at any
  timestamp the user reported, and one frame per slide if time allows.
  Check both lines, bottom-edge safety, and that a sentence is not
  split across the frame boundary.
- File size sanity: the reference 10-slide deck with full-lesson audio
  on two slides was about 34 MB. A sudden jump usually means orphaned
  media or duplicated full-length videos.
- If a user reports "only a few subtitles have Chinese", do NOT
  re-check only the ASS files. Check (a) the exact slide and timestamp
  in their screenshot against the video frame at that time, (b)
  whether they are opening an older file (same filename overwritten
  is a cache trap: deliver a new filename such as `-v2` / `-v3`),
  and (c) whether the subtitle is bottom-aligned. A standalone video
  that shows Chinese while the PPT version does not is the signature
  of the bottom-cropping bug in step 3, not of missing translations.

## What to deliver and what to say

Deliver the PPT file itself as an attachment, with a short message in
the user's language, conclusion first, covering:

- Subtitle bar sampled from the slide background, text colour chosen
  for contrast against it; report both sampled and chosen colours.
- Subtitles were redone in the requested order (word timeline +
  English sentences first, then per-sentence Chinese, every cue
  bilingual, no sentence split).
- Subtitles are middle-centred in the bottom bar, so the player
  controls cannot hide the Chinese line.
- Any number discrepancies found against the slide tables, with the
  slide numbers affected, and a question whether to correct those
  slide images. Do not silently change a slide table.
- That the audio is cleaned-up original audio, not re-dubbed.

## Files in this skill

- `scripts/make_ass.py` — generic ASS builder: reads
  `merged_cues.json` (list of `{start, end, en}`), a translation
  module or JSON with one Chinese string per cue, and `slides.json`
  (per-slide cue ranges or spliced trap ranges), and writes one ASS
  per slide in the step-3 style. Colours are parameters, not
  hard-coded: `--bar-color` (sampled slide background) and
  `--text-color` / `--outline-color`, or auto contrast choice when
  no text colour is given (light background -> dark text, dark
  background -> light text). It asserts every dialogue contains
  Chinese before writing.
- `scripts/build_ppt.py` — clean python-pptx builder: reads a manifest
  of slide pictures + videos + notes, sets the slide background to
  the manifest's sampled video-bar colour (required, no fixed
  default), places picture on top and video strip at the
  bottom, and saves a new PPT (never edits media shapes in place).
- `scripts/make_videos.sh` — ffmpeg template for step 4; fill in the
  sampled bar colour, audio file, ASS file and exact `-t` duration
  per slide.

No recording, transcript, API key, password, or personal file is
included in this skill. The reference lecture's numbers above are
teaching content from a classroom recording, included only as a worked
example of the verification arithmetic.
