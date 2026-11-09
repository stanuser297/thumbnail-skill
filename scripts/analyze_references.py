#!/usr/bin/env python3
"""Analyze a LOCAL folder of reference thumbnails and print pixel stats.

The reference library stays private: point this at a local folder, it never
uploads or copies anything. Output is a JSON summary per image (brightness,
contrast, dark/light fraction, colourful fraction) plus family aggregates when
a CSV with a 'file' and 'style family' column is passed. Use the result to
choose which layouts/styles to prioritise - grounded in your own references.

Usage:
  python3 analyze_references.py /path/to/reference-folder [--labels sources.csv]
Requires: Pillow, numpy.
"""
import argparse, csv, json, os
import numpy as np
from PIL import Image

def stats(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((320, 320))
    a = np.asarray(im).astype(float)
    lum = a.mean(axis=2)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = np.maximum.reduce([r, g, b]); mn = np.minimum.reduce([r, g, b])
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    return {
        "brightness": round(float(lum.mean()), 1),
        "contrast": round(float(lum.std()), 1),
        "dark_fraction": round(float((lum < 60).mean()), 2),
        "light_fraction": round(float((lum > 200).mean()), 2),
        "colourful_fraction": round(float((sat > 0.35).mean()), 2),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--labels", default=None,
                    help="optional CSV with 'file' and 'style family' columns")
    ap.add_argument("--out", default=None, help="write JSON here instead of stdout only")
    args = ap.parse_args()
    labels = {}
    if args.labels:
        with open(args.labels) as f:
            labels = {r["file"].strip(): r.get("style family", "").strip()
                      for r in csv.DictReader(f) if r.get("file")}
    rows = []
    for name in sorted(os.listdir(args.folder)):
        if not name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        s = stats(os.path.join(args.folder, name))
        s["file"] = name
        if name in labels:
            s["family"] = labels[name]
        rows.append(s)
    families = {}
    for r in rows:
        fam = r.get("family")
        if not fam:
            continue
        families.setdefault(fam, []).append(r)
    summary = {
        "images_analyzed": len(rows),
        "dark_background_share": round(sum(1 for r in rows if r["dark_fraction"] > 0.5) / max(len(rows), 1), 2),
        "families": {k: {"count": len(v),
                         "avg_brightness": round(sum(r["brightness"] for r in v) / len(v), 1),
                         "avg_contrast": round(sum(r["contrast"] for r in v) / len(v), 1)}
                     for k, v in sorted(families.items(), key=lambda kv: -len(kv[1]))},
        "per_image": rows,
    }
    text = json.dumps(summary, indent=2)
    if args.out:
        open(args.out, "w").write(text)
    print(text if not args.out else json.dumps({"out": args.out, "images": len(rows)}))

if __name__ == "__main__":
    main()
