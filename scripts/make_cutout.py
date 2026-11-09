#!/usr/bin/env python3
"""Cut a subject out of a uniform-background image into an RGBA PNG.

Use when the host has produced (or the creator supplied) a subject shot
against a flat background - chroma green screen, plain white, any solid
colour. The key colour is sampled from the image corners by default, so no
colour picking is needed. Everything runs locally with Pillow + numpy.

  python3 scripts/make_cutout.py subject-on-green.png --out subject.png
  python3 scripts/make_cutout.py photo.jpg --key-color FFFFFF --threshold 60
"""
import argparse

import numpy as np
from PIL import Image, ImageFilter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--key-color", default=None,
                    help="hex like 00FF00; default: sampled from the corners")
    ap.add_argument("--threshold", type=float, default=100.0,
                    help="RGB distance from the key colour treated as background")
    ap.add_argument("--feather", type=float, default=1.5,
                    help="edge soften radius in px")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    im = Image.open(args.image).convert("RGB")
    a = np.asarray(im).astype(np.int16)

    if args.key_color:
        kc = args.key_color.lstrip("#")
        key = np.array([int(kc[i:i + 2], 16) for i in (0, 2, 4)])
    else:
        h, w, _ = a.shape
        corners = np.concatenate([
            a[0:8, 0:8].reshape(-1, 3), a[0:8, w - 8:w].reshape(-1, 3),
            a[h - 8:h, 0:8].reshape(-1, 3), a[h - 8:h, w - 8:w].reshape(-1, 3)])
        key = np.median(corners, axis=0)

    dist = np.sqrt(((a - key) ** 2).sum(axis=2))
    mask = (dist > args.threshold).astype(np.uint8) * 255

    m = Image.fromarray(mask, "L").filter(ImageFilter.MinFilter(3))  # erode fringe
    if args.feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(args.feather))

    # despill: clamp the dominant key channel near the subject edges
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    if key[1] > key[0] and key[1] > key[2]:  # green screen
        spill = (g > r) & (g > b)
        g2 = np.where(spill, np.maximum(r, b), g)
        a = np.stack([r, g2, b], axis=-1)

    out = np.dstack([a.clip(0, 255).astype(np.uint8), np.asarray(m)])
    rgba = Image.fromarray(out, "RGBA")
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    rgba.save(args.out)
    print({"out": args.out, "key_color": [int(x) for x in key],
           "subject_px": [rgba.width, rgba.height]})


if __name__ == "__main__":
    main()
