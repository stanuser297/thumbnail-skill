---
name: thumbnail-generator
description: Generate 16:9 (1280x720) YouTube thumbnails for a Hindi explainer channel. Use when a video needs a thumbnail - the workflow analyzes the video, selects design references, collects missing inputs, renders, and shows the result for approval before any upload.
---

# Thumbnail Generator

Agent workflow + deterministic renderer for channel-style thumbnails. The package supplies style rules, fonts, frame tools and the renderer; the host agent supplies understanding and judgment.

## Workflow

1. **Video/topic analysis (host agent capability)**: read the video's title, description, chapters/transcript and sample frames (`scripts/extract_frames.py VIDEO --out frames/`). Decide what the thumbnail must honestly communicate. The package does not understand video content by itself; it needs a host that can read video metadata, frames and text.
2. **Reference selection (host agent capability)**: from the creator's private reference library, pick 2-3 references whose composition fits this video's subject, and note the concrete patterns (text size/placement, colour contrast, subject position). References inform the design; they are never copied or redistributed, and are never shipped inside this package.
3. **Collect missing inputs**: thumbnail text (2-4 words, honest to the video), the ONE accent word, style mood (one of the five in `styles.json`), language (Hindi/English), and the chosen frame (a real video moment that matches the subject, not just the sharpest still). Ask the creator for anything still missing.
4. **Render + manifest**: `scripts/run_thumbnail.py --video V --title T --accent A --style S [--label L] [--lang hi] --frame F --frame-time SECONDS --concept "..." --refs IDs --ref-notes "..." --out thumb.jpg` writes the thumbnail and a `*.manifest.json` run record (input video identity, references inspected, concept, chosen frame, output). For a quick render without a manifest use `scripts/make_thumbnail.py` directly.
5. **Verify**: open the image - text readable at small size, accent word is the highlighted one, frame matches the video subject, file under 2MB, 1280x720.
6. **Approve**: creator approves before any upload. Targeted edits: re-run `make_thumbnail.py --spec thumb.spec.json` with only the changed flags.

## Scope - what this package does and doesn't

- It DOES: extract/score video stills, apply the fixed style system (fonts, colours, layout), render the final image in Hindi or English, keep an editable spec and a run manifest per thumbnail.
- It does NOT: understand the video semantically, choose the hook or concept by itself, verify honesty of the message, or upload anything. Those are host-agent/creator judgments, supplied as declared inputs. CTR learning would need channel analytics access and controlled data - not part of this package.

## Styles and fonts

Five combos in `styles.json` (documentary, finance, tech, podcast, boldred): one background, one text colour, one accent. Rule: 2-4 words, ONE accent word (highlighted colour + underline), one font family. Fonts in `fonts/` are SIL OFL 1.1 (verified 9 Nov 2026 against each official OFL.txt in github.com/google/fonts); their OFL-*.txt license files ship in `fonts/` because bundling requires keeping the license and copyright notice. Modified fonts may not use the Reserved Font Name; font files may not be sold alone.

## Requirements

Python 3 with Pillow and numpy; ffmpeg on PATH for frame extraction and video metadata. No network needed at render time.

## Reference library

Design patterns are learned from the creator's private reference library (bold condensed uppercase text, dark high-contrast backgrounds, single accent colour). The library stays private: never include its images in this package or any distribution.
