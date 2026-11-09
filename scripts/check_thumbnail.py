#!/usr/bin/env python3
"""Automatic quality checks for a rendered thumbnail.

Measurable checks only, all local (Pillow, no model):
- dimensions and file size (YouTube limits)
- phone-size (380px) text contrast in the layout's text zone
- pasted cut-out subject brightness, only when a subject cutout was used:
  reads the KNOWN placement of the pasted PNG via make_thumbnail.subject_geometry.
  This is not a face detector and says nothing about faces inside a
  background frame - frame-based renders still need a human/host look.

What it cannot judge - hook truthfulness, imagery-topic match, style-mood fit,
variety across videos - stays a human/host review step (see SKILL.md). The
checks catch technical defects; they do not certify the design.

Usage:
  python3 scripts/check_thumbnail.py thumb.jpg [--spec thumb.spec.json] [--json]
Exit code 1 when any check FAILs, so it can gate a workflow.
"""
import argparse, json, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_thumbnail import W, H, subject_geometry

# fractional (l, t, r, b) boxes where the layout puts its free text
TEXT_ZONES = {
    "stack-left": (0.0, 0.0, 0.62, 1.0),
    "bottom-left": (0.0, 0.30, 0.75, 1.0),
    "center-big": (0.05, 0.20, 0.95, 0.90),
    "split": (0.0, 0.68, 1.0, 1.0),
}


def _otsu(hist):
    total = sum(hist)
    sum_all = sum(i * h for i, h in enumerate(hist))
    sum_b, w_b, best, thresh = 0.0, 0, -1.0, 127
    for t in range(256):
        w_b += hist[t]
        if w_b == 0 or w_b == total:
            continue
        sum_b += t * hist[t]
        w_f = total - w_b
        m_b, m_f = sum_b / w_b, (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best:
            best, thresh = var, t
    return thresh


def _result(name, status, detail):
    return {"check": name, "status": status, "detail": detail}


def check_dimensions(im):
    ok = im.size == (W, H)
    return _result("dimensions", "pass" if ok else "fail",
                   f"{im.size[0]}x{im.size[1]}, expected {W}x{H}")


def check_file_size(path):
    mb = os.path.getsize(path) / 1e6
    status = "pass" if mb < 1.5 else ("warn" if mb < 2 else "fail")
    return _result("file_size", status, f"{mb:.2f} MB (YouTube limit 2 MB)")


def check_mobile_text_contrast(im, layout):
    """Contrast between the two tone clusters in the text zone at 380px wide.
    Symmetric: works for light-on-dark text and dark-on-bright-bar text."""
    zone = TEXT_ZONES.get(layout)
    if zone is None:
        return _result("mobile_text_contrast", "warn", f"unknown layout '{layout}'")
    small = im.resize((380, round(380 * im.height / im.width)))
    sw, sh = small.size
    box = (round(zone[0] * sw), round(zone[1] * sh), round(zone[2] * sw), round(zone[3] * sh))
    gray = small.crop(box).convert("L")
    hist = gray.histogram()
    total = gray.width * gray.height
    t = _otsu(hist)
    dark_px = sum(hist[: t + 1])
    bright_px = total - dark_px
    m_lo = sum(i * h for i, h in enumerate(hist[: t + 1])) / max(dark_px, 1)
    m_hi = sum(i * h for i, h in enumerate(hist[t + 1:])) / max(bright_px, 1)
    ratio = (m_hi + 5) / (m_lo + 5)
    min_frac = min(dark_px, bright_px) / total
    detail = (f"text zone {zone} at 380px: contrast ratio {ratio:.1f}, "
              f"smaller tone share {min_frac * 100:.1f}%")
    if min_frac < 0.015:
        return _result("mobile_text_contrast", "warn",
                       detail + " - no clear two-tone text found; eyeball the preview")
    # thresholds calibrated against human-inspected renders: approved readable
    # thumbnails land at ratio >= 1.8; a washed-out text zone lands < 0.5
    status = "pass" if ratio >= 1.75 else ("warn" if ratio >= 1.3 else "fail")
    return _result("mobile_text_contrast", status, detail)


def check_subject_brightness(im, subject_path):
    """Mean luminance of the known pasted-cutout region vs the whole image.
    Only meaningful because the renderer placed the cutout at known bounds."""
    if not subject_path or not os.path.exists(subject_path):
        return _result("subject_brightness", "warn", "subject file not found; skipped")
    sw, sh = subject_geometry(subject_path)
    x, y = W - sw - 24, H - sh
    region = im.crop((x, y, x + sw, y + sh)).convert("L")
    hist = region.histogram()
    rp = region.width * region.height
    subj_mean = sum(i * h for i, h in enumerate(hist)) / rp
    full = im.convert("L")
    fhist = full.histogram()
    full_mean = sum(i * h for i, h in enumerate(fhist)) / (im.width * im.height)
    detail = (f"pasted-cutout region mean luminance {subj_mean:.0f}/255 "
              f"(whole image {full_mean:.0f})")
    # guards the real failure mode - subject buried darker than its backdrop.
    # Calibrated against human-inspected renders: an approved bright cutout on
    # a dark graded background lands ~74 vs ~58 (>= 70 absolute passes)
    if subj_mean >= 70 or subj_mean >= 1.05 * full_mean:
        status = "pass"
    elif subj_mean >= 50:
        status = "warn"
    else:
        status = "fail"
    return _result("subject_brightness", status, detail)


def run_checks(image_path, layout=None, subject=None):
    im = Image.open(image_path)
    checks = [check_dimensions(im), check_file_size(image_path)]
    if layout:
        checks.append(check_mobile_text_contrast(im, layout))
    if subject:
        checks.append(check_subject_brightness(im, subject))
    im.close()
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--spec", default=None,
                    help="spec/manifest-style JSON with layout and subject; flags override")
    ap.add_argument("--layout", default=None, choices=list(TEXT_ZONES))
    ap.add_argument("--subject", default=None, help="cutout PNG used in this render, if any")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    spec = json.load(open(args.spec)) if args.spec else {}
    layout = args.layout or spec.get("layout")
    subject = args.subject or spec.get("subject")
    checks = run_checks(args.image, layout, subject)
    worst = "pass"
    for c in checks:
        if c["status"] == "fail":
            worst = "fail"
        elif c["status"] == "warn" and worst == "pass":
            worst = "warn"
    if args.json:
        print(json.dumps({"image": args.image, "overall": worst, "checks": checks}, indent=2))
    else:
        for c in checks:
            print(f"{c['status'].upper():4}  {c['check']}: {c['detail']}")
        print(f"overall: {worst.upper()}")
    sys.exit(1 if worst == "fail" else 0)


if __name__ == "__main__":
    main()
