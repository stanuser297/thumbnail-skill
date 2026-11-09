#!/usr/bin/env python3
"""Rank a creator's private reference library against a video's topic/mood.

The matcher is dumb keyword overlap over reference_tags.json. The TAGS are the
smart part: they come from a host vision-language pass over the creator's
PRIVATE reference folder (the host looks at each reference and records its
topics, mood and composition - the same host-capability pattern this package
already uses for reaction edits and cutout shots). This repo ships the matcher
and the tag schema only - never the reference images and never the creator's
real tags file, both of which stay private and local.

Tag schema (reference_tags.json, kept outside the repo):
  {
    "T001": {"topics": ["podcast", "money"], "mood": ["dramatic"],
             "composition": "cutout-left", "notes": "huge condensed stack, red bar"}
  }

Usage:
  python3 scripts/match_references.py --tags /path/to/reference_tags.json \
      --topic "technology,explainer,ai" --mood "dramatic" [--top 5]
"""
import argparse, json, os, sys


def load_tags(path):
    tags = json.load(open(path))
    if not isinstance(tags, dict):
        sys.exit("tags file must be a JSON object keyed by reference ID")
    return tags


def match(tags, topics, moods, top):
    ranked = []
    for rid, t in tags.items():
        if not isinstance(t, dict) or rid.startswith("_"):
            continue
        t_topics = {x.lower() for x in t.get("topics", [])}
        t_moods = {x.lower() for x in t.get("mood", [])}
        topic_hits = sorted(topics & t_topics)
        mood_hits = sorted(moods & t_moods)
        score = 2 * len(topic_hits) + len(mood_hits)
        if score:
            ranked.append({"ref": rid, "score": score,
                           "topic_hits": topic_hits, "mood_hits": mood_hits,
                           "composition": t.get("composition"),
                           "notes": t.get("notes")})
    ranked.sort(key=lambda r: -r["score"])
    return ranked[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", required=True, help="reference_tags.json (private, outside the repo)")
    ap.add_argument("--topic", default="", help="comma-separated topic terms")
    ap.add_argument("--mood", default="", help="comma-separated mood terms")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    topics = {t.strip().lower() for t in args.topic.split(",") if t.strip()}
    moods = {m.strip().lower() for m in args.mood.split(",") if m.strip()}
    ranked = match(load_tags(args.tags), topics, moods, args.top)
    print(json.dumps({"matches": ranked,
                      "note": "tag-overlap shortlist; the host still views the references "
                              "before borrowing composition"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
