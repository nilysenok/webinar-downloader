"""Engine output -> one transcript on the recording timeline, with hallucination and echo checks.

Usage: .venv/bin/python scripts/asr/merge.py cpp|mlx
Output: downloads/asr/transcript-<engine>.txt, lines '[H:MM:SS] Имя: текст'.
"""
import difflib
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, fmt, to_global  # noqa: E402

HALLU = re.compile(r"продолжение следует|субтитр|корректор|спасибо за просмотр|подпис|DimaTorzok|amara", re.I)


def names():
    """Track number -> participant name, from the file names of webinarip --separate."""
    out = {}
    for f in glob.glob(f"{ROOT}/*/tracks/*.m4a"):
        b = os.path.basename(f)[:-4]
        out[b[:2]] = re.sub(r" [\d-]+$", "", b[3:])
    return out


def load(engine, n):
    sp = f"{ROOT}/speech"
    if engine == "cpp":
        p = f"{sp}/cpp/{n}.wav.json"
        rows = json.load(open(p))["transcription"] if os.path.exists(p) else []
        return [(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"]) for s in rows]
    p = f"{sp}/mlx/{n}.json"
    return [(s["start"], s["end"], s["text"]) for s in json.load(open(p))] if os.path.exists(p) else []


def echo_pairs(rows):
    """Similar phrases on different tracks at the same moment: echo or two people saying the same."""
    out = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:i + 12]:
            if b[2] != a[2] and b[0] < a[1] + 1 and difflib.SequenceMatcher(None, a[3].lower(), b[3].lower()).ratio() > 0.6:
                out.append((a, b))
    return out


def main(engine):
    maps, nm, rows = json.load(open(f"{ROOT}/speech/map.json")), names(), []
    for n, m in maps.items():
        rows += [(to_global(m, s), to_global(m, e), n, t.strip()) for s, e, t in load(engine, n) if t.strip()]
    rows.sort()
    with open(f"{ROOT}/transcript-{engine}.txt", "w") as f:
        f.writelines(f"[{fmt(s)}] {nm.get(n, n)}: {t}\n" for s, _, n, t in rows)
    hallu, echo = [r for r in rows if HALLU.search(r[3])], echo_pairs(rows)
    words = sum(len(r[3].split()) for r in rows)
    print(f"{engine}: {len(rows)} phrases, {words} words, hallucination-like {len(hallu)}, echo pairs {len(echo)}")
    for r in hallu[:10]:
        print("  H", fmt(r[0]), "track", r[2], r[3][:80])
    for a, b in echo[:10]:
        print("  E", fmt(a[0]), "tracks", a[2], b[2])


if __name__ == "__main__":
    main(sys.argv[1])
