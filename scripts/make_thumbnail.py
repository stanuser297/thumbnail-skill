#!/usr/bin/env python3
"""Render a 1280x720 YouTube thumbnail from a style system + an optional frame.

Layouts:
  bottom-left  one big line, accent word underlined (safe default)
  stack-left   one word per line, accent word on a highlight bar
  center-big   huge centred line, kicker label above (travel/destination)
  split        two frames side by side, BEFORE/AFTER labels, title on a bar

All text geometry uses the font's real ink bounding boxes (getbbox, which
includes side bearings and vertical offsets), never nominal font size, so
highlight bars and underlines hug the actual glyphs. Advances use getlength.
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = json.load(open(os.path.join(ROOT, "styles.json")))
W, H = STYLES["rules"]["size"]


def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def load_font(lang, size):
    name = STYLES["fonts"]["hi_display" if lang == "hi" else "en_display"]
    return ImageFont.truetype(os.path.join(ROOT, "fonts", name), size)


def fit_font(text, lang, max_w, start):
    """Largest size whose ink width fits max_w (never below 24)."""
    size = start
    while size > 24:
        f = load_font(lang, size)
        if f.getbbox(text)[2] <= max_w:
            return f, size
        size -= 4
    return load_font(lang, 24), 24


def fit_font_all(words, lang, max_w, start):
    """Largest size at which EVERY word's ink fits max_w."""
    size = start
    while size > 24:
        f = load_font(lang, size)
        if all(f.getbbox(w)[2] <= max_w for w in words):
            return f, size
        size -= 4
    return load_font(lang, 24), 24


def ink(font, text, x, y):
    """Absolute ink bbox of text drawn at origin (x, y)."""
    b = font.getbbox(text)
    return x + b[0], y + b[1], x + b[2], y + b[3]


def label_font(label, size):
    """Labels follow their own script: Devanagari labels need the hi font."""
    lang = "hi" if any(0x900 <= ord(c) <= 0x97F for c in label) else "en"
    return load_font(lang, size)


def cover(frame, w, h):
    im = Image.open(frame).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)))
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def background(style, frame, layout):
    if frame:
        im = cover(frame, W, H).filter(ImageFilter.GaussianBlur(1))
        # Fade the photo toward the style bg. Text-left layouts (stack-left,
        # bottom-left) darken mostly the LEFT/text side so a subject on the
        # right keeps its brightness; other layouts deepen toward the bottom.
        overlay = Image.new("L", (W, H), 0)
        od = ImageDraw.Draw(overlay)
        if layout in ("stack-left", "bottom-left"):
            for xx in range(W):
                h = 1 - xx / W
                base = 45 + int(190 * h ** 1.2)
                od.line([(xx, 0), (xx, H)], fill=base)
        else:
            for yy in range(H):
                base = 120 + int(115 * (yy / H) ** 1.2)
                od.line([(0, yy), (W, yy)], fill=base)
        tint = Image.new("RGB", (W, H), hx(style["bg"]))
        return Image.composite(tint, im, overlay)
    return Image.new("RGB", (W, H), hx(style["bg"]))


def split_background(style, frame, frame2):
    half = W // 2
    left = cover(frame, half, H) if frame else Image.new("RGB", (half, H), hx(style["bg"]))
    right = cover(frame2, half, H) if frame2 else Image.new("RGB", (half, H), hx(style["accent"]))
    im = Image.new("RGB", (W, H))
    im.paste(left, (0, 0))
    im.paste(right, (half, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([half - 3, 0, half + 3, H], fill=(255, 255, 255))
    return im


def stroke_kw(im, style, size, framed):
    """Dark/light outline behind free text so it survives busy photos."""
    if not framed:
        return {}
    return {"stroke_width": max(2, size // 36), "stroke_fill": hx(style["bg"])}


def paste_subject(im, subject_path, side="right"):
    """Composite a cut-out subject (RGBA PNG) with outline + drop shadow.
    Returns the width the subject occupies, so text can avoid it."""
    subj = Image.open(subject_path).convert("RGBA")
    scale = (H * 0.92) / subj.height
    if subj.width * scale > W * 0.5:
        scale = (W * 0.5) / subj.width
    subj = subj.resize((round(subj.width * scale), round(subj.height * scale)))
    sw, sh = subj.size
    x = W - sw - 24 if side == "right" else 24
    y = H - sh
    alpha = subj.split()[3]
    # soft drop shadow
    sh_mask = alpha.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(16))
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", subj.size, (0, 0, 0, 150)), (x + 10, y + 12), sh_mask)
    # white pop outline
    ol_mask = alpha.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(1.5))
    outline = Image.new("RGBA", im.size, (0, 0, 0, 0))
    outline.paste(Image.new("RGBA", subj.size, (255, 255, 255, 235)), (x, y), ol_mask)
    base = im.convert("RGBA")
    base = Image.alpha_composite(base, shadow)
    base = Image.alpha_composite(base, outline)
    base.paste(subj, (x, y), subj)
    out = base.convert("RGB")
    im.paste(out, (0, 0))
    return sw + 24


def draw_bottom_left(im, title, accent, style, label, lang, framed, text_w=None):
    d = ImageDraw.Draw(im)
    pad = 72
    words = title.split()
    acc = accent.upper() if accent else None
    parts = [(w, "accent" if acc and w.upper() == acc else "text") for w in words]
    line = " ".join(w for w, _ in parts)
    font, size = fit_font(line, lang, text_w or (W - 2 * pad), 150)
    if size < STYLES["rules"]["min_title_px"]:
        print(f"warning: title size {size}px under mobile-readable minimum; shorten text")
    block_h = size + (70 if label else 0)
    y = H - block_h - 130
    if label:
        lf = label_font(label, 44)
        d.text((pad, y), label.upper(), font=lf, fill=hx(style["accent"]))
        y += 70
    sk = stroke_kw(im, style, size, framed)
    x = pad
    accent_span = None
    for text, role in parts:
        x0 = x
        d.text((x, y), text, font=font, fill=hx(style[role]), **sk)
        x += font.getlength(text + " ")
        if role == "accent":
            accent_span = (x0, x - font.getlength(" "))
    if accent_span:
        # underline hangs below the accent word's real ink bottom
        _, _, ax1, abot = ink(font, [t for t, r in parts if r == "accent"][0],
                              accent_span[0], y)
        uy = abot + int(size * 0.14)
        d.rectangle([accent_span[0], uy, ax1, uy + max(8, size // 12)],
                    fill=hx(style["accent"]))


def draw_stack_left(im, title, accent, style, label, lang, framed, text_w=None):
    """One word per line on the left; accent word sits on a highlight bar."""
    d = ImageDraw.Draw(im)
    pad = 72
    words = title.split()
    acc = accent.upper() if accent else None
    max_w = text_w or ((W - 2 * pad) * 3 // 4)
    # fit by width, then shrink until the whole stack also fits vertically
    size = 170
    while True:
        font, size = fit_font_all(words, lang, max_w, size)
        boxes = {w: font.getbbox(w) for w in words}
        ink_h = max(b[3] - b[1] for b in boxes.values())
        step = int(ink_h * 1.22)  # real line pitch from ink, descenders included
        block_h = step * (len(words) - 1) + ink_h + (64 if label else 0)
        if block_h <= H - 110 or size <= 24:
            break
        size -= 8
    y = (H - block_h) // 2
    if label:
        lf = label_font(label, 40)
        d.text((pad, y), label.upper(), font=lf, fill=hx(style["accent"]))
        y += 64
    hp, vp = int(size * 0.10), int(size * 0.07)
    sk = stroke_kw(im, style, size, framed)
    for w in words:
        b = boxes[w]
        ix0, iy0, ix1, iy1 = pad + b[0], y + b[1], pad + b[2], y + b[3]
        if acc and w.upper() == acc:
            # bar hugs the actual glyph ink, padding on all four sides
            d.rectangle([ix0 - hp, iy0 - vp, ix1 + hp, iy1 + vp],
                        fill=hx(style["accent"]))
            d.text((pad, y), w, font=font, fill=hx(style["bg"]))
        else:
            d.text((pad, y), w, font=font, fill=hx(style["text"]), **sk)
        y += step


def draw_center_big(im, title, accent, style, label, lang, framed, text_w=None):
    """Huge centred title with a small kicker above (travel/destination style)."""
    d = ImageDraw.Draw(im)
    words = title.split()
    acc = accent.upper() if accent else None
    line = " ".join(words)
    font, size = fit_font(line, lang, W - 120, 220)
    bx0, by0, bx1, by1 = font.getbbox(line)
    line_w = bx1 - bx0
    y = (H - (by1 - by0)) // 2 - by0 + 40  # origin so ink lands centred
    if label:
        lf = label_font(label, 44)
        lw = lf.getbbox(label.upper())[2]
        d.text(((W - lw) // 2, y + by0 - 90), label.upper(), font=lf,
               fill=hx(style["accent"]))
    sk = stroke_kw(im, style, size, framed)
    x = (W - line_w) // 2 - bx0
    accent_span = None
    for w in words:
        role = "accent" if acc and w.upper() == acc else "text"
        x0 = x
        d.text((x, y), w, font=font, fill=hx(style[role]), **sk)
        x += font.getlength(w + " ")
        if role == "accent":
            accent_span = (x0, x - font.getlength(" "))
    if accent_span:
        aw = [w for w in words if acc and w.upper() == acc][0]
        _, _, ax1, abot = ink(font, aw, accent_span[0], y)
        uy = abot + int(size * 0.14)
        d.rectangle([accent_span[0], uy, ax1, uy + max(8, size // 12)],
                    fill=hx(style["accent"]))


def draw_split(im, title, accent, style, label, lang, framed, text_w=None):
    """Small caps labels on each half; title on a dark bar at the bottom."""
    d = ImageDraw.Draw(im)
    half = W // 2
    labels = [(label or "BEFORE").upper(), "AFTER"]
    for i, lab in enumerate(labels):
        lf = label_font(lab, 54)
        lb = lf.getbbox(lab)
        lw, lh = lb[2] - lb[0], lb[3] - lb[1]
        cx = half // 2 if i == 0 else half + half // 2
        fill = hx(style["bg"]) if i == 0 else hx(style["accent"])
        fg = hx(style["text"]) if i == 0 else hx(style["bg"])
        d.rectangle([cx - lw // 2 - 24, 36, cx + lw // 2 + 24, 36 + lh + 32],
                    fill=fill)
        d.text((cx - lw // 2 - lb[0], 36 + 16 - lb[1]), lab, font=lf, fill=fg)
    words = title.split()
    acc = accent.upper() if accent else None
    line = " ".join(words)
    font, size = fit_font(line, lang, W - 200, 110)
    bx0, by0, bx1, by1 = font.getbbox(line)
    ink_h = by1 - by0
    bar_top = H - ink_h - 90
    d.rectangle([0, bar_top, W, H], fill=(0, 0, 0))
    y = bar_top + 45 - by0  # origin so ink is vertically centred in the bar
    x = (W - (bx1 - bx0)) // 2 - bx0
    for w in words:
        role = "accent" if acc and w.upper() == acc else "text"
        if role == "accent":
            ix0, iy0, ix1, iy1 = ink(font, w, x, y)
            hp, vp = int(size * 0.10), int(size * 0.07)
            d.rectangle([ix0 - hp, iy0 - vp, ix1 + hp, iy1 + vp],
                        fill=hx(style["accent"]))
            d.text((x, y), w, font=font, fill=hx(style["bg"]))
        else:
            d.text((x, y), w, font=font, fill=hx(style["text"]))
        x += font.getlength(w + " ")


LAYOUTS = {
    "bottom-left": draw_bottom_left,
    "stack-left": draw_stack_left,
    "center-big": draw_center_big,
    "split": draw_split,
}


def render(title, accent, style_name, label=None, lang="en", frame=None,
           layout="bottom-left", frame2=None, subject=None):
    style = STYLES["styles"][style_name]
    if subject and layout not in ("stack-left", "bottom-left"):
        raise SystemExit("--subject works with stack-left and bottom-left only")
    if subject:
        # backdrop: blurred + vertical tint when a frame exists, else solid bg
        if frame:
            im = background(style, frame, "center-big")
        else:
            im = Image.new("RGB", (W, H), hx(style["bg"]))
        subj_w = paste_subject(im, subject, side="right")
        text_w = W - subj_w - 2 * 72
        LAYOUTS[layout](im, title, accent, style, label, lang, bool(frame), text_w)
        return im
    im = split_background(style, frame, frame2) if layout == "split" else background(style, frame, layout)
    LAYOUTS[layout](im, title, accent, style, label, lang, bool(frame))
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
    ap.add_argument("--subject", default=None,
                    help="RGBA cut-out PNG (from make_cutout.py) composited on the right with outline")
    ap.add_argument("--layout", default=None, choices=list(LAYOUTS))
    ap.add_argument("--mobile-preview", action="store_true",
                    help="also write a 380px-wide preview for phone-size readability check")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    spec = json.load(open(args.spec)) if args.spec else {}
    p = {k: getattr(args, k) if getattr(args, k) is not None else spec.get(k)
         for k in ("title", "accent", "style", "label", "lang", "frame", "frame2", "layout", "subject")}
    p["style"] = p["style"] or "documentary"
    p["layout"] = p["layout"] or "bottom-left"
    p["lang"] = p["lang"] or ("hi" if p["title"] and any(ord(c) > 0x900 for c in p["title"]) else "en")
    if not p["title"]:
        ap.error("--title required (or present in --spec)")
    words = len(p["title"].split())
    lo, hi = STYLES["rules"]["title_words"]
    if not lo <= words <= hi:
        ap.error(f"title has {words} words; the style rule requires {lo}-{hi}")
    if p["accent"] and p["accent"].upper() not in [w.upper() for w in p["title"].split()]:
        ap.error(f"accent word '{p['accent']}' is not in the title; pick an exact title word")
    out = args.out or spec.get("out") or "thumbnail.jpg"
    im = render(p["title"], p["accent"], p["style"], p["label"], p["lang"],
                p["frame"], p["layout"], p["frame2"], p.get("subject"))
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
