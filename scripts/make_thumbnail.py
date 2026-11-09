#!/usr/bin/env python3
"""Render a 1280x720 (16:9) thumbnail from a style + text + optional frame(s).

Deterministic renderer: you supply the inputs, it draws the thumbnail.
It does not invent text or claims - the title/accent come from the agent or
creator, and must match the actual video (no clickbait the video can't back).

Layouts (learned from a reference library of real thumbnails):
  bottom-left  text block bottom-left over a darkened frame (default)
  stack-left   one word per line, accent word on a highlight bar
  center-big   huge centred title with a small kicker above (travel style)
  split        before/after: two frames side by side with small labels

Usage:
  python3 make_thumbnail.py --title "AI vs ARTISTS?" \
      --accent "ARTISTS?" --style tech --label "THE HONEST ANSWER" \
      --frame frames/f_0007.jpg --layout stack-left --out thumb.jpg

  --lang hi renders the title with a Devanagari display font.
  Edit mode: pass --spec spec.json (written next to every output) and only
  the fields you want to change; everything else carries over.
  --mobile-preview also writes a 380px-wide preview for a phone-size check.
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

def cover(frame, w, h):
    im = Image.open(frame).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)))
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def background(style, frame):
    if frame:
        im = cover(frame, W, H).filter(ImageFilter.GaussianBlur(1))
        # dark gradient overlay: darkest bottom-left where text sits
        overlay = Image.new("L", (W, H), 0)
        od = ImageDraw.Draw(overlay)
        for yy in range(H):
            base = int(200 * (yy / H) ** 1.4)
            od.line([(0, yy), (W, yy)], fill=base)
        dark = Image.new("RGB", (W, H), hx(style["bg"]))
        return Image.composite(dark, im, overlay)
    return Image.new("RGB", (W, H), hx(style["bg"]))

def split_background(style, frame, frame2):
    half = W // 2
    left = cover(frame, half, H) if frame else Image.new("RGB", (half, H), hx(style["bg"]))
    right = cover(frame2, half, H) if frame2 else Image.new("RGB", (half, H), hx(style["accent"]))
    im = Image.new("RGB", (W, H))
    im.paste(left, (0, 0)); im.paste(right, (half, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([half - 3, 0, half + 3, H], fill=(255, 255, 255))
    return im

def draw_bottom_left(im, title, accent, style, label, lang):
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
    y = H - block_h - 130
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
    if accent_span:
        d.rectangle([accent_span[0], y + size + 30, accent_span[1], y + size + 42],
                    fill=hx(style["accent"]))

def draw_stack_left(im, title, accent, style, label, lang):
    """One word per line on the left; accent word sits on a highlight bar."""
    d = ImageDraw.Draw(im)
    pad = 72
    words = title.split()
    acc = accent.upper() if accent else None
    max_w = (W - 2 * pad) * 3 // 4
    font, size = fit_font(max(words, key=len), lang, max_w, 170)
    line_h = int(size * 1.08)
    block_h = line_h * len(words) + (60 if label else 0)
    y = (H - block_h) // 2
    if label:
        lf = load_font("en", 40)
        d.text((pad, y), label.upper(), font=lf, fill=hx(style["accent"]))
        y += 60
    for w in words:
        is_acc = acc and w.upper() == acc
        bbox = font.getbbox(w)
        if is_acc:
            d.rectangle([pad - 16, y - 8, pad + bbox[2] + 16, y + line_h],
                        fill=hx(style["accent"]))
            d.text((pad, y), w, font=font, fill=hx(style["bg"]))
        else:
            d.text((pad, y), w, font=font, fill=hx(style["text"]))
        y += line_h

def draw_center_big(im, title, accent, style, label, lang):
    """Huge centred title with a small kicker above (travel/destination style)."""
    d = ImageDraw.Draw(im)
    words = title.split()
    acc = accent.upper() if accent else None
    line = " ".join(words)
    font, size = fit_font(line, lang, W - 120, 220)
    bbox = font.getbbox(line)
    y = (H - size) // 2 + 40
    if label:
        lf = load_font("en", 44)
        lw = lf.getbbox(label.upper())[2]
        d.text(((W - lw) // 2, y - 90), label.upper(), font=lf, fill=hx(style["accent"]))
    x = (W - bbox[2]) // 2
    accent_span = None
    for w in words:
        role = "accent" if acc and w.upper() == acc else "text"
        x0 = x
        d.text((x, y), w, font=font, fill=hx(style[role]))
        x += font.getbbox(w + " ")[2]
        if role == "accent":
            accent_span = (x0, x - font.getbbox(" ")[2])
    if accent_span:
        d.rectangle([accent_span[0], y + size + 24, accent_span[1], y + size + 36],
                    fill=hx(style["accent"]))

def draw_split(im, title, accent, style, label, lang):
    """Small caps labels on each half; title on a dark bar at the bottom."""
    d = ImageDraw.Draw(im)
    half = W // 2
    lf = load_font("en", 54)
    for i, lab in enumerate([(label or "BEFORE").upper()] + (["AFTER"] if True else [])):
        lw = lf.getbbox(lab)[2]
        cx = half // 2 if i == 0 else half + half // 2
        d.rectangle([cx - lw // 2 - 24, 36, cx + lw // 2 + 24, 108], fill=hx(style["bg"] if i == 0 else style["accent"]))
        d.text((cx - lw // 2, 52), lab, font=lf, fill=hx(style["text"] if i == 0 else style["bg"]))
    words = title.split()
    acc = accent.upper() if accent else None
    line = " ".join(words)
    font, size = fit_font(line, lang, W - 200, 110)
    d.rectangle([0, H - size - 110, W, H], fill=(0, 0, 0))
    x = (W - font.getbbox(line)[2]) // 2
    y = H - size - 80
    for w in words:
        role = "accent" if acc and w.upper() == acc else "text"
        if role == "accent":
            wb = font.getbbox(w)[2]
            d.rectangle([x - 12, y - 6, x + wb + 12, y + size + 14], fill=hx(style["accent"]))
            d.text((x, y), w, font=font, fill=hx(style["bg"]))
        else:
            d.text((x, y), w, font=font, fill=hx(style["text"]))
        x += font.getbbox(w + " ")[2]

LAYOUTS = {
    "bottom-left": draw_bottom_left,
    "stack-left": draw_stack_left,
    "center-big": draw_center_big,
    "split": draw_split,
}

def render(title, accent, style_name, label=None, lang="en", frame=None,
           layout="bottom-left", frame2=None):
    style = STYLES["styles"][style_name]
    im = split_background(style, frame, frame2) if layout == "split" else background(style, frame)
    LAYOUTS[layout](im, title, accent, style, label, lang)
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
    ap.add_argument("--frame2", default=None, help="second frame for --layout split")
    ap.add_argument("--layout", default=None, choices=list(LAYOUTS))
    ap.add_argument("--mobile-preview", action="store_true",
                    help="also write a 380px-wide preview for phone-size readability check")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    spec = json.load(open(args.spec)) if args.spec else {}
    p = {k: getattr(args, k) if getattr(args, k) is not None else spec.get(k)
         for k in ("title", "accent", "style", "label", "lang", "frame", "frame2", "layout")}
    p["style"] = p["style"] or "documentary"
    p["layout"] = p["layout"] or "bottom-left"
    p["lang"] = p["lang"] or ("hi" if p["title"] and any(ord(c) > 0x900 for c in p["title"]) else "en")
    if not p["title"]:
        ap.error("--title required (or present in --spec)")
    words = len(p["title"].split())
    lo, hi = STYLES["rules"]["title_words"]
    if not lo <= words <= hi:
        ap.error(f"title has {words} words; the style rule requires {lo}-{hi}")
    out = args.out or spec.get("out") or "thumbnail.jpg"
    im = render(p["title"], p["accent"], p["style"], p["label"], p["lang"],
                p["frame"], p["layout"], p["frame2"])
    im.save(out, quality=92)
    p["out"] = out
    spec_path = os.path.splitext(out)[0] + ".spec.json"
    json.dump(p, open(spec_path, "w"), indent=2)
    mb = os.path.getsize(out) / 1e6
    result = {"out": out, "spec": spec_path, "mb": round(mb, 2),
              "style": p["style"], "layout": p["layout"], "lang": p["lang"]}
    if args.mobile_preview:
        small = im.resize((380, 214))
        spath = os.path.splitext(out)[0] + ".mobile.jpg"
        small.save(spath, quality=88)
        result["mobile_preview"] = spath
    print(json.dumps(result))

if __name__ == "__main__":
    main()
