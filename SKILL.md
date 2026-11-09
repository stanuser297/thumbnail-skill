---
name: thumbnail-generator
description: Generate 16:9 (1280x720) YouTube thumbnails for any channel. Use when a video needs a thumbnail - the workflow analyzes the video, selects design references, collects missing inputs, renders variants, and shows the result for approval before any upload.
---

# Thumbnail Generator

Agent workflow + deterministic renderer, adaptable to any channel. The package supplies style rules, layout templates, fonts, frame tools and the renderer; the host agent supplies understanding and judgment.

## Workflow

1. **Video/topic analysis (host agent capability)**: read the video's title, description, chapters/transcript and sample frames (`scripts/extract_frames.py VIDEO --out frames/`). Decide what the thumbnail must honestly communicate. The package does not understand video content by itself; it needs a host that can read video metadata, frames and text.
2. **Reference selection (host agent capability)**: from the creator's private reference library, pick 2-3 references whose composition fits this video's subject, and note the concrete patterns (text size/placement, colour contrast, subject position). `scripts/analyze_references.py FOLDER [--labels sources.csv]` gives pixel-level stats (brightness, contrast, dark/colourful share) over the creator's own local library folder to ground those choices; the library never leaves local disk and is never shipped inside this package.
3. **Collect missing inputs**: thumbnail text (2-4 words, honest to the video), the ONE accent word, layout, style mood (one of the five in `styles.json`), language (Hindi/English), and the chosen frame (a real video moment that matches the subject, not just the sharpest still). A channel profile (`profiles.json`) can supply defaults; explicit choices always override. Ask the creator for anything still missing.
4. **Render + manifest**: `scripts/run_thumbnail.py --video V --title T --accent A [--profile P] [--style S] [--layout L] [--variants N] [--label K] [--lang hi] --frame F --frame-time SECONDS --concept "..." --refs IDs --ref-notes "..." --out thumb.jpg` writes up to N variants and a `*.manifest.json` run record (input video identity, profile, references inspected, concept, chosen frame, every output). For a quick render without a manifest use `scripts/make_thumbnail.py` directly; `--mobile-preview` adds a 380px-wide render for the phone-size readability check.
5. **Verify**: open the image (and the mobile preview) - text readable at small size, accent word is the highlighted one, no overlap with the frame's subject, frame matches the video subject, file under 2MB, 1280x720.
6. **Approve**: creator approves before any upload. Targeted edits: re-run `make_thumbnail.py --spec thumb.spec.json` with only the changed flags.

## Scope - what this package does and doesn't

- It DOES: extract/score video stills, apply the style system (fonts, colours, 4 layouts), render variants in Hindi or English, analyze a local reference folder for grounded style choices, keep an editable spec and a run manifest per thumbnail.
- It does NOT: understand the video semantically, choose the hook or concept by itself, verify honesty of the message, or upload anything. Those are host-agent/creator judgments, supplied as declared inputs. CTR learning would need channel analytics access and controlled data - not part of this package.

## Layouts and styles

Four layouts (`bottom-left`, `stack-left`, `center-big`, `split`), learned from the dominant patterns in a 97-image reference library: stacked huge words with a highlight bar, centred destination titles, before/after splits, and bottom-left blocks over graded frames. Five colour combos in `styles.json` (documentary, finance, tech, podcast, boldred): one background, one text colour, one accent. Rules: 2-4 words, ONE accent word (highlighted), one font family.

## Requirements

Python 3 with Pillow and numpy; ffmpeg on PATH for frame extraction and video metadata. No network needed at render time.

## Reference library

Design patterns are learned from the creator's private reference library (97 thumbnails across reaction-face, bold typography, podcast, gaming, travel and other families). The library stays private: never include its images in this package or any distribution. `analyze_references.py` reads only a local folder the creator points it at.
