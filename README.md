# Thumbnail Generator Skill

Portable, standalone 16:9 (1280x720) YouTube thumbnail generator: an agent
workflow plus a deterministic renderer. Own code, no platform dependency.
Requires Python 3 + Pillow + numpy + ffmpeg installed; developed and tested
on Linux - other setups are not yet verified.

The package supplies the style system, fonts, frame tools and renderer.
A host agent (or the creator) supplies the judgment: what the video is about,
which design references to follow, and the final text. The code does not
understand video content by itself.

## Quick start

```bash
# 1. candidate frames from a video (optional; scores stills, you pick the moment)
python3 scripts/extract_frames.py video.mp4 --out frames/

# 2. render the thumbnail (title rule: 2-4 words, one accent word)
python3 scripts/make_thumbnail.py --title "AI vs ARTISTS?" \
  --accent "ARTISTS?" --style tech --label "THE HONEST ANSWER" \
  --frame frames/f_0017.jpg --out thumb.jpg

# 3. targeted edit later (a thumb.spec.json is written next to every output;
#    pass it back with only the fields you want to change)
python3 scripts/make_thumbnail.py --spec thumb.spec.json --accent "ARTISTS?"
```

Titles outside 2-4 words are rejected, and the accent must match a title word
exactly, punctuation included. For a full run with a manifest (video identity,
references inspected, concept, chosen frame), use `scripts/run_thumbnail.py`.

## What's inside

- `SKILL.md` - the full agent workflow, scope limits, and font license terms
- `styles.json` - 5 colour combos (documentary, finance, tech, podcast, boldred) + font map
- `scripts/extract_frames.py` - ffmpeg frame sampling + sharpness/colour scoring
- `scripts/make_thumbnail.py` - deterministic renderer (English + Hindi/Devanagari)
- `scripts/run_thumbnail.py` - render + JSON run manifest
- `fonts/` - 9 SIL OFL 1.1 fonts, each with its official OFL license text
- `examples/` - sample renders on plain backgrounds

## Examples and privacy

`examples/` contains only renders on solid backgrounds - fully original output
of this package. Demo renders that use frames from real videos are kept
private: those stills belong to the videos they came from and are not
redistributed here. The design patterns were tuned against a private reference
library; no reference images are included in this repository.

## License

Code: MIT (see LICENSE). Fonts: SIL Open Font License 1.1 - each font ships
with its OFL text in `fonts/`. Modified fonts may not use the Reserved Font
Name; font files may not be sold on their own.
