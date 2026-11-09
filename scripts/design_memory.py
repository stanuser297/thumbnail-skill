#!/usr/bin/env python3
"""Per-channel design memory.

Records each run's design facts (from its manifest) into a per-channel history
file, and warns when a new design repeats the channel's recent pattern. The
goal is avoiding accidental repetition (same layout + same accent style + same
subject use every video), not forcing novelty - repeats are warnings, never
blocks, and deliberate series styling is fine.

History files live OUTSIDE this repo (default ./.thumbnail-history/) because
they are per-creator data.

Usage:
  python3 scripts/design_memory.py --channel NAME --record run.manifest.json
  python3 scripts/design_memory.py --channel NAME --check --style tech --layout stack-left --subject
"""
import argparse, json, os, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = json.load(open(os.path.join(REPO, "styles.json")))
DEFAULT_DIR = ".thumbnail-history"


def hist_path(channel, d):
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{channel}.json")


def load(channel, d):
    p = hist_path(channel, d)
    return json.load(open(p)) if os.path.exists(p) else []


def record(manifest_path, channel, d):
    m = json.load(open(manifest_path))
    hist = load(channel, d)
    entries = m.get("concepts") or m.get("variants") or []
    top_text = m.get("text", {})
    n = 0
    for e in entries:
        text = e.get("text") or top_text
        hist.append({
            "ts": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            "title": text.get("title"),
            "style": e.get("style"),
            "layout": e.get("layout"),
            "subject": bool(e.get("subject")),
            "reaction_edit": (e.get("reaction_edit") or {}).get("applied", False),
        })
        n += 1
    json.dump(hist, open(hist_path(channel, d), "w"), indent=2, ensure_ascii=False)
    return n


def check(channel, style, layout, subject, d, window=8):
    """Warnings count the NEW design together with recent history, so a third
    identical design in a row is caught on the third run."""
    hist = load(channel, d)[-window:]
    warnings = []
    if len(hist) >= 2 and all(h["style"] == style for h in hist[-2:]):
        warnings.append(f"style '{style}' (accent {STYLES['styles'].get(style, {}).get('accent', '?')}) "
                        f"would be 3 thumbnails in a row - consider a different style family")
    if len(hist) >= 2 and all(h["layout"] == layout for h in hist[-2:]):
        warnings.append(f"layout '{layout}' would be 3 thumbnails in a row")
    if subject and sum(1 for h in hist[-3:] if h["subject"]) >= 2:
        warnings.append("cut-out subject on 3 of the last 4 thumbnails - "
                        "a frame-only composition may stand out now")
    return warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--record", default=None, help="manifest JSON to append to history")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--style", default=None, choices=list(STYLES["styles"]))
    ap.add_argument("--layout", default=None)
    ap.add_argument("--subject", action="store_true")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    args = ap.parse_args()
    if args.record:
        print(json.dumps({"recorded": record(args.record, args.channel, args.dir),
                          "history": hist_path(args.channel, args.dir)}))
    if args.check:
        if not args.style or not args.layout:
            ap.error("--check needs --style and --layout")
        print(json.dumps({"warnings": check(args.channel, args.style, args.layout,
                                            args.subject, args.dir)}, indent=2))


if __name__ == "__main__":
    main()
