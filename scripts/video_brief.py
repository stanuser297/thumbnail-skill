#!/usr/bin/env python3
"""Build a video brief and check hook evidence against a transcript.

Two jobs:

1. brief: parse a transcript (.srt/.vtt/txt), detect scene cuts with ffmpeg,
   and write a brief JSON the host fills in (main_question, show,
   avoid_implying). Term extraction is plain word frequency - no model.
2. hook evidence: given a proposed hook, show the transcript lines that share
   its content words, and flag absolute claims (dead/khatam/over/...) that
   have no matching word anywhere in the transcript. Overlap is EVIDENCE for
   the host's truthfulness review, not proof - a hook can share words and
   still misrepresent the video.

Usage:
  python3 scripts/video_brief.py --video V [--transcript subs.srt] [--scenes] --out brief.json
  python3 scripts/video_brief.py --brief brief.json --hook "ART KA FUTURE?"
"""
import argparse, json, os, re, subprocess, sys

STOP = set(("the a an and or but of to in on for with is are was were be been it its this that "
            "these those i you he she we they me him her us them my your his their our as at by "
            "from not no yes so if then than too very can could will would should do does did "
            "have has had what when where who why how vs ka ke ki hai hain ho aur ye yeh wo woh "
            "ek bhi se mein par kya nahi").split())
ABSOLUTES = ["dead", "khatam", "over", "never", "end", "killed", "destroyed", "gone", "finished"]


def parse_transcript(path):
    txt = open(path, encoding="utf-8").read()
    lines = []
    if "-->" in txt:
        for block in re.split(r"\n\s*\n", txt):
            m = re.search(r"(\d{1,2}:\d{2}:\d{2}[,.]\d+)\s*-->", block)
            if not m:
                continue
            text = " ".join(l.strip() for l in block.splitlines()
                            if l.strip() and "-->" not in l and not l.strip().isdigit()
                            and not l.startswith("WEBVTT"))
            text = re.sub(r"<[^>]+>", "", text).strip()
            if text:
                lines.append({"t": m.group(1).replace(",", "."), "text": text})
    else:
        lines = [{"t": None, "text": l.strip()} for l in txt.splitlines() if l.strip()]
    return lines


def content_words(text):
    return [w for w in re.findall(r"[a-zA-Z']+", text.lower())
            if len(w) >= 3 and w not in STOP]


def related(a, b):
    """Cheap stemming: exact match, or one word extends the other from a 3+ char stem."""
    return a == b or (min(len(a), len(b)) >= 3 and (a.startswith(b) or b.startswith(a)))


def scene_cuts(video, thresh=0.25):
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", video, "-vf",
         f"scale=160:-2,select='gt(scene,{thresh})',metadata=print", "-f", "null", "-"],
        capture_output=True, text=True)
    return [round(float(m.group(1)), 1)
            for m in re.finditer(r"pts_time:([0-9.]+)", proc.stderr)][:60]


def build(video, transcript_path, want_scenes, out):
    brief = {"video": os.path.basename(video), "main_question": None, "show": [],
             "avoid_implying": [],
             "notes": "host fills main_question/show/avoid_implying after watching; "
                      "terms and cuts are evidence, not understanding"}
    if want_scenes:
        brief["scene_cuts_s"] = scene_cuts(video)
    if transcript_path:
        lines = parse_transcript(transcript_path)
        freq = {}
        for l in lines:
            for w in set(content_words(l["text"])):
                freq[w] = freq.get(w, 0) + 1
        brief["transcript"] = {"file": os.path.basename(transcript_path),
                               "lines": len(lines),
                               "top_terms": [w for w, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:15]]}
        brief["_transcript_path"] = os.path.abspath(transcript_path)
    json.dump(brief, open(out, "w"), indent=2, ensure_ascii=False)
    return brief


def hook_evidence(brief_path, hook):
    brief = json.load(open(brief_path))
    tp = brief.get("_transcript_path")
    if not tp or not os.path.exists(tp):
        return {"hook": hook, "error": "brief has no usable transcript path"}
    lines = parse_transcript(tp)
    hook_words = set(content_words(hook))
    matches = []
    for l in lines:
        lw = set(content_words(l["text"]))
        overlap = sorted({h for h in hook_words for w in lw if related(h, w)})
        if overlap:
            matches.append({"t": l["t"], "text": l["text"], "overlap": overlap})
    matches.sort(key=lambda m: -len(m["overlap"]))
    abs_hits = [a for a in ABSOLUTES if a in hook.lower()]
    unsupported = [a for a in abs_hits
                   if not any(a in l["text"].lower() for l in lines)]
    return {"hook": hook,
            "supporting_lines": matches[:5],
            "absolute_claims_without_transcript_evidence": unsupported,
            "note": "keyword overlap is evidence for review, not proof of truthfulness"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--transcript", default=None)
    ap.add_argument("--scenes", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--brief", default=None)
    ap.add_argument("--hook", default=None)
    args = ap.parse_args()
    if args.hook:
        if not args.brief:
            ap.error("--hook needs --brief")
        print(json.dumps(hook_evidence(args.brief, args.hook), indent=2, ensure_ascii=False))
        return
    if not args.video or not args.out:
        ap.error("brief mode needs --video and --out")
    brief = build(args.video, args.transcript, args.scenes, args.out)
    print(json.dumps(brief, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
