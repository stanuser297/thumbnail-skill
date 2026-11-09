#!/usr/bin/env python3
"""Render a 1280x720 (16:9) thumbnail from a style + text + optional frame.

Deterministic renderer: you supply the inputs, it draws the thumbnail.
It does not invent text or claims - the title/accent come from the agent or
creator, and must match the actual video (no clickbait the video can't back).

Usage:
  python3 make_thumbnail.py --title "AI vs ARTISTS?" \
      --accent "ARTISTS?" --style tech --label "THE HONEST ANSWER" \
      --frame frames/f_0007.jpg --out thumb.jpg

  --lang hi renders the title with a Devanagari display font.
  Edit mode: pass --spec spec.json (written next to every output) and only
  the fields you want to change; everything else carries over.
"""
import argparse, json, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = json.load(open(os.path.join(ROOT, "styles.json")))
W, H = STYLES["rules"]["size"]

def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

def load_font(lang, size):
    name = STYLES["fonts"]["hi_display" if lang == "hi" else "en_display"]
    return ImageFont.truetype(os.path.join(ROOT, "fonts", name), size)

def fit_font(text, lang, max_w, start):
    size = start
    while size > 24:
        f = load_font(lang, size)
        if f.getbbox(text)[2] <= max_w:
            return f, size
        size -= 4
    return load_font(lang, 24), 24

def background(style, frame):
    if frame:
        im = Image.open(frame).convert("RGB")
        # cover-crop to 16:9
        s = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)))
        x, y = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(1))
        # dark gradient overlay: darkest bottom-left where text sits
        overlay = Image.new("L", (W, H), 0)
        od = ImageDraw.Draw(overlay)
        for yy in range(H):
            base = int(200 * (yy / H) ** 1.4)
            od.line([(0, yy), (W, yy)], fill=base)
        dark = Image.new("RGB", (W, H), hx(style["bg"]))
        return Image.composite(dark, im, overlay)
    return Image.new("RGB", (W, H), hx(style["bg"]))

def render(title, accent, style_name, label=None, lang="en", frame=None):
    style = STYLES["styles"][style_name]
    im = background(style, frame)
    d = ImageDraw.Draw(im)
    pad = 72
    words = title.split()
    acc = accent.upper() if accent else None
    parts = [(w, "accent" if acc and w.upper() == acc else "text") for w in words]
    line = " ".join(w for w, _ in parts)
    font, size = fit_font(line, lang, W - 2 * pad, 150)
    if size < STYLES["rules"]["min_title_px"]:
        print(f"warning: title size {size}px under mobile-readable minimum; shorten text")
    block_h = size + (70 if label else 0)
    y = (H - block_h) // 2 if not frame else H - block_h - 130
    if label:
        lf = load_font("en", 44)
        d.text((pad, y), label.upper(), font=lf, fill=hx(style["accent"]))
        y += 70
    x = pad
    accent_span = None
    for text, role in parts:
        x0 = x
        d.text((x, y), text, font=font, fill=hx(style[role]))
        x += font.getbbox(text + " ")[2]
        if role == "accent":
            accent_span = (x0, x - font.getbbox(" ")[2])
    # accent underline directly beneath the accent word
    if accent_span:
        d.rectangle([accent_span[0], y + size + 30, accent_span[1], y + size + 42],
                    fill=hx(style["accent"]))
    return im

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="JSON spec from a previous run; flags override it")
    ap.add_argument("--title")
    ap.add_argument("--accent", default=None)
    ap.add_argument("--style", default=None, choices=list(STYLES["styles"]))
    ap.add_argument("--label", default=None)
    ap.add_argument("--lang", default=None, choices=["en", "hi"])
    ap.add_argument("--frame", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    spec = json.load(open(args.spec)) if args.spec else {}
    p = {k: getattr(args, k) if getattr(args, k) is not None else spec.get(k)
         for k in ("title", "accent", "style", "label", "lang", "frame")}
    p["style"] = p["style"] or "documentary"
    p["lang"] = p["lang"] or ("hi" if p["title"] and any(ord(c) > 0x900 for c in p["title"]) else "en")
    if not p["title"]:
        ap.error("--title required (or present in --spec)")
    words = len(p["title"].split())
    lo, hi = STYLES["rules"]["title_words"]
    if not lo <= words <= hi:
        ap.error(f"title has {words} words; the style rule requires {lo}-{hi}")
    out = args.out or spec.get("out") or "thumbnail.jpg"
    im = render(p["title"], p["accent"], p["style"], p["label"], p["lang"], p["frame"])
    im.save(out, quality=92)
    p["out"] = out
    spec_path = os.path.splitext(out)[0] + ".spec.json"
    json.dump(p, open(spec_path, "w"), indent=2)
    mb = os.path.getsize(out) / 1e6
    print(json.dumps({"out": out, "spec": spec_path, "mb": round(mb, 2),
                      "style": p["style"], "lang": p["lang"]}))

if __name__ == "__main__":
    main()
