# Thumbnail Generator Skill

Portable, standalone 16:9 (1280x720) YouTube thumbnail generator: an agent
workflow plus a deterministic renderer. Multi-channel by design - channel
profiles and layout templates adapt it to different niches. Own code, no
platform dependency. Requires Python 3 + Pillow + numpy + ffmpeg installed;
developed and tested on Linux - other setups are not yet verified.

The package supplies the style system, fonts, frame tools and renderer.
A host agent (or the creator) supplies the judgment: what the video is about,
which design references to follow, and the final text. The code does not
understand video content by itself. When the host environment provides an
image-editing model, the workflow can also edit the video character's
expression for the thumbnail (identity preserved, edit recorded in the run
manifest); the package itself embeds no image model and assumes no paid
provider.

## Quick start

Every command below is a copy of a real, verified run.

```bash
# 1. candidate frames from a video (optional; scores stills, you pick the moment)
python3 scripts/extract_frames.py video.mp4 --out frames/

# 2. render the thumbnail (title rule: 2-4 words, one accent word)
python3 scripts/make_thumbnail.py --title "AI vs ARTISTS?" \
  --accent "ARTISTS?" --style tech --label "THE HONEST ANSWER" \
  --frame frames/f_0017.jpg --layout stack-left --mobile-preview --out thumb.jpg

# 3. targeted edit later (a thumb.spec.json is written next to every output;
#    pass it back with only the fields you want to change)
python3 scripts/make_thumbnail.py --spec thumb.spec.json --accent "ARTISTS?"
```

Titles outside 2-4 words are rejected, and the accent must match a title word
exactly, punctuation included.

```bash
# 4. full run: 3 variants + manifest, using a channel profile for defaults
python3 scripts/run_thumbnail.py --video video.mp4 \
  --title "AI vs ARTISTS?" --accent "ARTISTS?" --profile general --variants 3 \
  --frame frames/f_0017.jpg --frame-time 330 \
  --concept "why this visual and text fit this video" \
  --refs REF1,REF2 --ref-notes "patterns you observed" --out thumb.jpg

# 5. ground style choices in YOUR OWN private reference folder (stays local)
python3 scripts/analyze_references.py /path/to/references --labels sources.csv
```

## Layouts (learned from real reference thumbnails)

- `bottom-left` - text block bottom-left over a darkened frame
- `stack-left` - one word per line, accent word on a highlight bar
- `center-big` - huge centred title with a small kicker (travel style)
- `split` - before/after: two frames side by side with small labels

## Channel profiles

`profiles.json` holds named profiles (general, podcast, gaming, travel,
hindi-explainer) with default style + layout + language. `--profile NAME`
applies the defaults; any explicit flag overrides them. Add your own channel
as a profile entry - no code change needed. Without a profile, `general`
applies, so the tool works for any channel out of the box.

## What's inside

- `SKILL.md` - the full agent workflow, scope limits, and font license terms
- `styles.json` - 5 colour combos (documentary, finance, tech, podcast, boldred) + font map
- `profiles.json` - optional per-channel defaults
- `scripts/extract_frames.py` - ffmpeg frame sampling + sharpness/colour scoring
- `scripts/make_thumbnail.py` - deterministic renderer, 4 layouts, English + Hindi/Devanagari
- `scripts/run_thumbnail.py` - variants + JSON run manifest
- `scripts/analyze_references.py` - pixel stats over a local reference folder
- `fonts/` - 9 SIL OFL 1.1 fonts, each with its official OFL license text
- `examples/` - sample renders on plain backgrounds

## Examples and privacy

`examples/` contains only renders on solid backgrounds - fully original output
of this package. Demo renders that use frames from real videos are kept
private: those stills belong to the videos they came from and are not
redistributed here. The layout templates were learned from a private reference
library; no reference images are included in this repository, and
`analyze_references.py` reads a local folder without uploading anything.

## License

Code: MIT (see LICENSE). Fonts: SIL Open Font License 1.1 - each font ships
with its OFL text in `fonts/`. Modified fonts may not use the Reserved Font
Name; font files may not be sold on their own.
