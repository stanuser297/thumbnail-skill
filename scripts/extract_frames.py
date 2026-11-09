#!/usr/bin/env python3
"""Extract candidate thumbnail frames from a video.

Samples frames at a fixed interval, scores each on sharpness, colorfulness
and brightness, and writes the top candidates plus a JSON report.

Scope note: this is frame selection, not video understanding. It finds
visually strong stills. Choosing the moment that matches the video's message
still needs the agent/creator who knows the video.

Usage: python3 extract_frames.py VIDEO --out DIR [--count 12] [--every 20] [--scenes]
Requires: ffmpeg on PATH, Pillow, numpy.

--scenes: instead of even sampling, take frames at the strongest scene cuts
(detected via ffmpeg scene scores). This shortlists moments where something
changed on screen; it still cannot tell which moment MATTERS - the agent/
creator picks that.
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_brief import scene_cuts

def grab_frames(video, out, every):
    os.makedirs(out, exist_ok=True)
    # one frame every N seconds, scaled down for fast scoring
    pat = os.path.join(out, "f_%04d.jpg")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video,
                    "-vf", f"fps=1/{every},scale=480:-2", "-q:v", "4", pat],
                   check=True)
    return sorted(os.path.join(out, f) for f in os.listdir(out) if f.endswith(".jpg"))

def score(path):
    import numpy as np
    from PIL import Image, ImageFilter
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(float)
    gray = np.asarray(im.convert("L").filter(ImageFilter.FIND_EDGES)).astype(float)
    sharp = float(gray.mean())
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    rg, yb = r - g, 0.5 * (r + g) - b
    colorful = float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))
    bright = float(a.mean())
    # penalize near-black / near-white frames
    pen = 1.0 if 30 < bright < 225 else 0.3
    return {"sharpness": round(sharp, 2), "colorfulness": round(colorful, 2),
            "brightness": round(bright, 1),
            "score": round((0.6 * sharp + 0.4 * colorful) * pen, 2)}

def grab_scene_frames(video, out, thresh=0.25):
    os.makedirs(out, exist_ok=True)
    frames = []
    for i, t in enumerate(scene_cuts(video, thresh)):
        p = os.path.join(out, f"s_{i:04d}.jpg")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video,
                        "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", p],
                       check=True)
        frames.append((p, t))
    return frames

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--every", type=int, default=20, help="seconds between samples")
    ap.add_argument("--scenes", action="store_true",
                    help="sample at strongest scene cuts instead of evenly")
    args = ap.parse_args()
    if args.scenes:
        pairs = grab_scene_frames(args.video, args.out)
        rows = []
        for p, t in pairs:
            s = score(p)
            s["file"] = os.path.basename(p)
            s["at_seconds"] = t
            rows.append(s)
        rows.sort(key=lambda r: -r["score"])
        keep = {r["file"] for r in rows[: args.count]}
        for p, _ in pairs:
            if os.path.basename(p) not in keep:
                os.remove(p)
        report = os.path.join(args.out, "report.json")
        with open(report, "w") as f:
            json.dump(rows[: args.count], f, indent=2)
        print(json.dumps(rows[: args.count], indent=2))
        return
    frames = grab_frames(args.video, args.out, args.every)
    if not frames:
        sys.exit("no frames extracted")
    rows = []
    for p in frames:
        s = score(p)
        s["file"] = os.path.basename(p)
        rows.append(s)
    rows.sort(key=lambda r: -r["score"])
    keep = {r["file"] for r in rows[: args.count]}
    for p in frames:
        if os.path.basename(p) not in keep:
            os.remove(p)
    report = os.path.join(args.out, "report.json")
    with open(report, "w") as f:
        json.dump(rows[: args.count], f, indent=2)
    print(json.dumps(rows[: args.count], indent=2))

if __name__ == "__main__":
    main()
