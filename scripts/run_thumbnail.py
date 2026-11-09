#!/usr/bin/env python3
"""Run one full thumbnail job and write a run manifest.

The agent workflow in SKILL.md supplies the semantic inputs (concept, frame
choice, reference patterns observed, text). This script executes the render
and records a product-facing manifest: what went in, what was chosen and why,
and what came out. It contains no agent internals - just the run facts.

Usage:
  python3 scripts/run_thumbnail.py --video video.mp4 \
      --title "AI vs ARTISTS?" --accent "ARTISTS?" --style tech \
      --label "THE HONEST ANSWER" --frame frames/cand_330.jpg --frame-time 330 \
      --concept "SAG-AFTRA strike photo = human artists resisting AI" \
      --refs REF1,REF2 --ref-notes "REF1: huge condensed uppercase, dark grade; REF2: 3-word stacked title, accent block" \
      --out thumb.jpg
"""
import argparse, hashlib, json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_thumbnail import render, STYLES, W, H

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
    ap.add_argument("--title", required=True)
    ap.add_argument("--accent", required=True)
    ap.add_argument("--style", required=True, choices=list(STYLES["styles"]))
    ap.add_argument("--label", default=None)
    ap.add_argument("--lang", default=None, choices=["en", "hi"])
    ap.add_argument("--frame", default=None)
    ap.add_argument("--frame-time", type=float, default=None,
                    help="seconds into the video the frame was taken from")
    ap.add_argument("--concept", required=True,
                    help="why this visual + text fits this video")
    ap.add_argument("--refs", default="", help="comma-separated reference IDs inspected")
    ap.add_argument("--ref-notes", default="", help="patterns observed in those references")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    words = len(args.title.split())
    lo, hi = STYLES["rules"]["title_words"]
    if not lo <= words <= hi:
        ap.error(f"title has {words} words; the style rule requires {lo}-{hi}")
    if args.accent.upper() not in [w.upper() for w in args.title.split()]:
        ap.error("accent must be one of the title words, with the same punctuation")
    lang = args.lang or ("hi" if any(ord(c) > 0x900 for c in args.title) else "en")
    im = render(args.title, args.accent, args.style, args.label, lang, args.frame)
    im.save(args.out, quality=92)
    mb = os.path.getsize(args.out) / 1e6

    manifest = {
        "tool": "thumbnail-generator skill (portable package)",
        "run_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "input_video": video_meta(args.video),
        "references_inspected": [r.strip() for r in args.refs.split(",") if r.strip()],
        "reference_patterns": args.ref_notes,
        "concept": args.concept,
        "chosen_frame": ({"file": os.path.basename(args.frame),
                          "at_seconds": args.frame_time} if args.frame else None),
        "text": {"title": args.title, "accent_word": args.accent,
                 "label": args.label, "lang": lang},
        "style": args.style,
        "output": {"file": os.path.abspath(args.out), "size_mb": round(mb, 2),
                   "dimensions": f"{W}x{H}", "under_2mb": mb < 2},
        "scope": "Frame extraction/scoring + deterministic render by package; video understanding, reference choice, concept and text are agent/creator judgments supplied as inputs.",
    }
    mpath = os.path.splitext(args.out)[0] + ".manifest.json"
    json.dump(manifest, open(mpath, "w"), indent=2, ensure_ascii=False)
    print(json.dumps({"out": args.out, "manifest": mpath, "mb": round(mb, 2)}))

if __name__ == "__main__":
    main()
