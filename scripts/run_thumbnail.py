#!/usr/bin/env python3
"""Run one full thumbnail job and write a run manifest.

The agent workflow in SKILL.md supplies the semantic inputs (concept, frame
choice, reference patterns observed, text). This script executes the render
and records a product-facing manifest: what went in, what was chosen and why,
and what came out. It contains no agent internals - just the run facts.

Profiles (--profile) supply sensible defaults per channel type from
profiles.json; explicit flags always override them. --variants N renders N
style/layout combos of the same text so the creator can pick one.

Usage:
  python3 scripts/run_thumbnail.py --video video.mp4 \
      --title "AI vs ARTISTS?" --accent "ARTISTS?" --style tech \
      --label "THE HONEST ANSWER" --frame frames/cand_330.jpg --frame-time 330 \
      --concept "strike photo = human artists resisting AI" \
      --refs REF1,REF2 --ref-notes "REF1: huge condensed uppercase, dark grade" \
      --out thumb.jpg

  python3 scripts/run_thumbnail.py --video video.mp4 --title "SOLO TRIP?" \
      --accent "SOLO" --profile travel --variants 3 \
      --concept "travel vlog opener" --out thumb.jpg
"""
import argparse, hashlib, json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_thumbnail import render, STYLES, LAYOUTS, W, H

PROFILES = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles.json")))

VARIANT_ROTATION = [
    ("documentary", "stack-left"),
    ("tech", "bottom-left"),
    ("podcast", "center-big"),
    ("boldred", "stack-left"),
    ("finance", "bottom-left"),
]

def video_meta(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_name,width,height",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    stream = next((s for s in info.get("streams", []) if s.get("width")), {})
    return {"file": os.path.basename(path),
            "bytes": int(info["format"]["size"]),
            "duration_s": round(float(info["format"]["duration"]), 1),
            "resolution": f"{stream.get('width')}x{stream.get('height')}",
            "sha256_16": h.hexdigest()[:16]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--title")
    ap.add_argument("--accent")
    ap.add_argument("--style", default=None, choices=list(STYLES["styles"]))
    ap.add_argument("--layout", default=None, choices=list(LAYOUTS))
    ap.add_argument("--profile", default=None, choices=list(PROFILES["profiles"]),
                    help="defaults from profiles.json; explicit flags override")
    ap.add_argument("--label", default=None)
    ap.add_argument("--lang", default=None, choices=["en", "hi"])
    ap.add_argument("--frame", default=None)
    ap.add_argument("--frame2", default=None, help="second frame for split layout")
    ap.add_argument("--frame-time", type=float, default=None,
                    help="seconds into the video the frame was taken from")
    ap.add_argument("--variants", type=int, default=1,
                    help="render N style/layout combos of the same text")
    ap.add_argument("--reaction-edit", default=None,
                    help="provenance note when the frame's character expression was edited by a host image tool")
    ap.add_argument("--concept",
                    help="why this visual + text fits this video (required for a single run)")
    ap.add_argument("--refs", default="", help="comma-separated reference IDs inspected")
    ap.add_argument("--ref-notes", default="", help="patterns observed in those references")
    ap.add_argument("--concepts", default=None,
                    help="JSON file: list of distinct concept specs (title, accent, style, layout, frame, frame_time, concept, label, lang, subject, reaction_edit) - renders each as its own thumbnail")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.concepts:
        run_concepts(args)
        return
    if not args.title or not args.accent or not args.concept:
        ap.error("--title, --accent and --concept are required (unless --concepts is used)")
    prof = PROFILES["profiles"].get(args.profile or PROFILES["default_profile"], {})
    style = args.style or prof.get("style") or "documentary"
    layout = args.layout or prof.get("layout") or "bottom-left"

    words = len(args.title.split())
    lo, hi = STYLES["rules"]["title_words"]
    if not lo <= words <= hi:
        ap.error(f"title has {words} words; the style rule requires {lo}-{hi}")
    if args.accent.upper() not in [w.upper() for w in args.title.split()]:
        ap.error("accent must be one of the title words, with the same punctuation")
    lang = args.lang or prof.get("lang") or ("hi" if any(ord(c) > 0x900 for c in args.title) else "en")

    combos = [(style, layout)]
    if args.variants > 1:
        combos += [c for c in VARIANT_ROTATION if c != (style, layout)][: args.variants - 1]

    base, ext = os.path.splitext(args.out)
    outputs = []
    for i, (st, ly) in enumerate(combos):
        out_path = args.out if len(combos) == 1 else f"{base}-v{i+1}{ext or '.jpg'}"
        im = render(args.title, args.accent, st, args.label, lang, args.frame, ly, args.frame2)
        im.save(out_path, quality=92)
        mb = os.path.getsize(out_path) / 1e6
        outputs.append({"file": os.path.abspath(out_path), "style": st, "layout": ly,
                        "size_mb": round(mb, 2), "under_2mb": mb < 2})

    manifest = {
        "tool": "thumbnail-generator skill (portable package)",
        "run_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "input_video": video_meta(args.video),
        "profile": args.profile or PROFILES["default_profile"],
        "references_inspected": [r.strip() for r in args.refs.split(",") if r.strip()],
        "reference_patterns": args.ref_notes,
        "concept": args.concept,
        "chosen_frame": ({"file": os.path.basename(args.frame),
                          "at_seconds": args.frame_time} if args.frame else None),
        "reaction_edit": ({"applied": True, "description": args.reaction_edit,
                           "note": "character expression edited by a host image-editing tool; identity preserved from the source frame"}
                          if args.reaction_edit else {"applied": False}),
        "text": {"title": args.title, "accent_word": args.accent,
                 "label": args.label, "lang": lang},
        "variants": outputs,
        "dimensions": f"{W}x{H}",
        "scope": "Frame extraction/scoring + deterministic render by package; video understanding, reference choice, concept and text are agent/creator judgments supplied as inputs.",
    }
    mpath = base + ".manifest.json"
    json.dump(manifest, open(mpath, "w"), indent=2, ensure_ascii=False)
    print(json.dumps({"outputs": [o["file"] for o in outputs], "manifest": mpath}))

def run_concepts(args):
    """Render genuinely distinct concepts (different hook/frame/composition),
    one manifest for the whole set."""
    specs = json.load(open(args.concepts))
    if not isinstance(specs, list) or not specs:
        raise SystemExit("--concepts file must contain a non-empty JSON list")
    prof = PROFILES["profiles"].get(args.profile or PROFILES["default_profile"], {})
    base, ext = os.path.splitext(args.out)
    lo, hi = STYLES["rules"]["title_words"]
    entries = []
    for i, c in enumerate(specs, 1):
        title = c["title"]
        accent = c.get("accent")
        words = len(title.split())
        if not lo <= words <= hi:
            raise SystemExit(f"concept {i}: title has {words} words; rule requires {lo}-{hi}")
        if accent and accent.upper() not in [w.upper() for w in title.split()]:
            raise SystemExit(f"concept {i}: accent must be one of the title words")
        style = c.get("style") or prof.get("style") or "documentary"
        layout = c.get("layout") or prof.get("layout") or "bottom-left"
        lang = c.get("lang") or prof.get("lang") or (
            "hi" if any(ord(ch) > 0x900 for ch in title) else "en")
        out_path = f"{base}-concept{i}{ext or '.jpg'}"
        im = render(title, accent, style, c.get("label"), lang,
                    c.get("frame"), layout, c.get("frame2"), c.get("subject"))
        im.save(out_path, quality=92)
        mb = os.path.getsize(out_path) / 1e6
        entries.append({
            "file": os.path.abspath(out_path), "style": style, "layout": layout,
            "concept": c.get("concept"), "text": {"title": title, "accent_word": accent,
                                                  "label": c.get("label"), "lang": lang},
            "chosen_frame": ({"file": os.path.basename(c["frame"]),
                              "at_seconds": c.get("frame_time")} if c.get("frame") else None),
            "subject": os.path.basename(c["subject"]) if c.get("subject") else None,
            "reaction_edit": ({"applied": True, "description": c["reaction_edit"]}
                              if c.get("reaction_edit") else {"applied": False}),
            "size_mb": round(mb, 2), "under_2mb": mb < 2})
    manifest = {
        "tool": "thumbnail-generator skill (portable package)",
        "run_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "input_video": video_meta(args.video),
        "profile": args.profile or PROFILES["default_profile"],
        "mode": "distinct-concepts",
        "concepts": entries,
        "dimensions": f"{W}x{H}",
        "scope": "Frame extraction/scoring + deterministic render by package; video understanding, reference choice, concept and text are agent/creator judgments supplied as inputs.",
    }
    mpath = base + ".manifest.json"
    json.dump(manifest, open(mpath, "w"), indent=2, ensure_ascii=False)
    print(json.dumps({"outputs": [e["file"] for e in entries], "manifest": mpath}))


if __name__ == "__main__":
    main()
