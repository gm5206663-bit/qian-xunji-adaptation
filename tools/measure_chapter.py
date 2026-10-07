#!/usr/bin/env python3
"""measure_chapter.py — the measuring tool for Qian Xun Ji Reborn.

Stdlib only. Run:   python3 tools/measure_chapter.py chapters/Chapter_01_The_Night_After.md
                    python3 tools/measure_chapter.py chapters/*.md --receipt

Splits each chapter at its "Footer" heading; measures the PROSE BODY only.

Hard failures (exit 1):
  - any sentence over 60 words          (k01)
  - a banned "the way [clause]" simile  (k01; allowlist below)
  - jargon in prose                     (k02/R17)

Warnings (exit 0):
  - body outside the 2400–3400 band     (k01)

Receipt line (--receipt):
  Ch01: 3503w avg 9.0 median 5 longest 230 (over60 1) dlg 12 (3.4/1k) the-way 0 jargon 0 band OVER

Dialogue lines = paragraphs whose first character is a quote mark; low by
design. Sentence split is punctuation-based with common abbreviations masked;
the longest-sentence report prints offenders so a human judges.
"""
import argparse
import re
import sys

BAND = (2400, 3400)
MAX_SENT = 60

WAY_ALLOW = [
    "all the way", "on the way", "by the way", "the way of", "opens the way",
    "out of the way", "make way", "give way",
]

JARGON = [
    "adaptation talent", "mortal divine", "true divine", "master foundation",
    "master \u00a7", "system window", "status screen", "readout",
    "second mind", "reward engine", "system voice", "the system",
    "level up", "quest", "interface",
]

ABBR = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|St|Ep|No|vs|etc|approx|Ltd)\.", re.I)
DECIMAL = re.compile(r"(\d)\.(\d)")


def split_body(text):
    m = re.search(r"(?m)^\s*#{0,6}\s*Footer\b", text, re.I)
    if m:
        return text[:m.start()]
    m = re.search(r"(?m)^\s*---+ *\n\s*#{1,6}\s*Footer\b", text, re.I)
    if m:
        return text[:m.start()]
    return text


def sentences(body):
    t = ABBR.sub(lambda m: m.group(0).replace(".", "\u00b7"), body)
    t = DECIMAL.sub(lambda m: m.group(1) + "\u00b7" + m.group(2), t)
    parts = re.split(r"(?<=[.!?])\s+", t)
    return [p.strip() for p in parts if p.strip()]


def measure(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    body = split_body(text)
    words = body.split()
    sents = sentences(body)
    lens = [len(s.split()) for s in sents]
    avg = sum(lens) / len(lens) if lens else 0.0
    med = sorted(lens)[len(lens) // 2] if lens else 0
    longest = max(lens) if lens else 0
    long_offenders = [s for s in sents if len(s.split()) > MAX_SENT]

    dlg = 0
    for para in body.split("\n"):
        p = para.strip()
        if p and p[0] in "\"\u201c'\u2018\u300c":
            dlg += 1
    per1k = (dlg / (len(words) / 1000)) if words else 0.0

    low = body.lower()
    way_hits = []
    for m in re.finditer(r"\bthe way\b", low):
        ctx = low[max(0, m.start() - 20):m.end() + 20]
        if not any(a in ctx for a in WAY_ALLOW):
            way_hits.append(ctx.strip())

    jar_hits = [(j, low.count(j)) for j in JARGON if j in low]

    return {
        "file": path, "words": len(words), "sents": len(sents), "avg": avg,
        "median": med, "longest": longest, "over60": long_offenders,
        "dlg": dlg, "per1k": per1k, "way": way_hits, "jargon": jar_hits,
    }


def receipt(r):
    name = r["file"].split("/")[-1][:0] or r["file"].split("/")[-1]
    name = name.replace("Chapter_", "Ch").replace(".md", "")
    band = "OK" if BAND[0] <= r["words"] <= BAND[1] else ("OVER" if r["words"] > BAND[1] else "UNDER")
    return (f"{name}: {r['words']}w avg {r['avg']:.1f} median {r['median']} "
            f"longest {r['longest']} (over60 {len(r['over60'])}) "
            f"dlg {r['dlg']} ({r['per1k']:.1f}/1k) the-way {len(r['way'])} "
            f"jargon {sum(n for _, n in r['jargon'])} band {band}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--receipt", action="store_true",
                    help="print only the one-line receipt per file")
    args = ap.parse_args()

    hard = False
    for f in args.files:
        r = measure(f)
        if args.receipt:
            print(receipt(r))
        else:
            print("=" * 70)
            print(f"FILE   {f}")
            print(receipt(r))
            print(f"       sentences {r['sents']}")
        if r["over60"]:
            hard = True
            if not args.receipt:
                for s in r["over60"]:
                    print(f"  OVER60: {s[:160]}{'...' if len(s) > 160 else ''}")
        if r["way"]:
            hard = True
            if not args.receipt:
                for w in r["way"]:
                    print(f"  THE-WAY: ...{w}...")
        if r["jargon"]:
            hard = True
            if not args.receipt:
                for j, n in r["jargon"]:
                    print(f"  JARGON: '{j}' x{n}")
        if not args.receipt and not (BAND[0] <= r["words"] <= BAND[1]):
            print(f"  BAND: {r['words']}w outside {BAND[0]}-{BAND[1]} (warning)")
    print()
    print("VERDICT:", "FAIL (hard failures above)" if hard else "PASS (warnings only, if any)")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
