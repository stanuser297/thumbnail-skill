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

# 6. (optional) character cut-out: host image tool puts the character on a flat
#    uniform background, local keying removes it; compose with --subject
python3 scripts/make_cutout.py shot.png --out subject.png
python3 scripts/run_thumbnail.py --video video.mp4 \
  --title "AI vs ARTISTS?" --accent "ARTISTS?" --subject subject.png \
  --frame-time 330 --concept "why it fits" --refs REF1,REF2 \
  --ref-notes "patterns" --out thumb.jpg

# 7. 2-3 genuinely distinct concepts (different hook/frame/composition) in one run
python3 scripts/run_thumbnail.py --video video.mp4 --concepts concepts.json --out set.jpg

# 8. automatic quality gate (runs inside run_thumbnail.py too; results land in
#    the manifest's quality_checks, exit 1 on FAIL)
python3 scripts/check_thumbnail.py thumb.jpg --layout stack-left --subject subject.png

# 9. video brief + hook evidence (transcript terms + scene cuts; keyword
#    overlap is evidence for the truthfulness review, not proof)
python3 scripts/video_brief.py --video video.mp4 --transcript subs.srt --scenes --out brief.json
python3 scripts/video_brief.py --brief brief.json --hook "AI vs ARTISTS?"
python3 scripts/run_thumbnail.py --video video.mp4 --title "AI vs ARTISTS?" --accent "ARTISTS?" \
  --frame-time 330 --concept "why it fits" --refs R1 --ref-notes "patterns" \
  --brief brief.json --channel mychannel --out thumb.jpg

# 10. scene-cut frame shortlist + reference matching over a PRIVATE tag file
python3 scripts/extract_frames.py video.mp4 --out frames/ --scenes
python3 scripts/match_references.py --tags /path/to/reference_tags.json \
  --topic "technology,explainer" --mood "dramatic"
```

`--channel` keeps a per-channel design memory (outside the repo) and warns when
a new render would repeat the channel's recent pattern - warnings, never blocks.

Known issue: every render is recorded, including rejected iterations, so an
iteration loop can pollute the channel history and trigger false repeat-pattern
warnings. Until the record step moves to approved designs only, rebuild the
channel history from delivered manifests (`design_memory.py --record`) before a
final render.

The gate is measurable checks only: dimensions, 2MB limit, text contrast at
380px phone size, and pasted-cutout brightness when a cutout was used (known
placement, not a face detector). Hook truthfulness, imagery-topic match and
style-mood fit stay a human/host review - SKILL.md lists that checklist.

`--concepts` takes a JSON list where each entry has its own `title`, `accent`,
optional `frame`, `style`, `layout`, `subject`, `reaction_edit` and `concept`
note; it writes one file per entry plus one manifest for the set. Prefer this
over `--variants`, which only rotates styles of the same text.

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
- `scripts/make_thumbnail.py` - deterministic renderer, 4 layouts, English + Hindi/Devanagari, optional cut-out subject composition
- `scripts/make_cutout.py` - local uniform-background keying -> transparent PNG subject
- `scripts/run_thumbnail.py` - variants or distinct concept sets + JSON run manifest with automatic quality checks, hook evidence and design memory
- `scripts/check_thumbnail.py` - local quality gate: size, 2MB limit, phone-size text contrast, cutout brightness
- `scripts/video_brief.py` - transcript terms + scene cuts into a brief JSON; hook-evidence lookup
- `scripts/design_memory.py` - per-channel design history + repeat-pattern warnings
- `scripts/match_references.py` - rank a private reference library by topic/mood tags (host-written, schema in examples/)
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
