#!/bin/bash
# Template for SKILL.md step 4: one video per slide.
# Fill in BAR_COLOR (sampled from the slide background for that slide;
# F6FBF3 was only the reference deck's colour, never a fixed default),
# the per-slide audio file, ASS file, and the EXACT audio duration
# for -t. Without -t, ffmpeg can produce a video longer than the audio.
#
#   BAR_COLOR=<sampled RRGGBB>
#   ffmpeg -y -v error -f lavfi -i color=c=0x$BAR_COLOR:s=1920x260:r=10 \
#     -i slide02.mp3 -vf "subtitles=slide02.ass" \
#     -c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p \
#     -c:a aac -b:a 64k -t 68 slide02.mp4
#
# Verify after rendering:
#   ffprobe -v error -show_entries format=duration -of csv=p=0 slide02.mp4
# must equal the audio duration, and a frame extracted mid-cue must
# show both the English line and the Chinese line, centred in the bar.
echo "This is a template only. See SKILL.md step 4 for the filled-in form."
