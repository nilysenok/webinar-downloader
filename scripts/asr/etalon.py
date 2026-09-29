"""Pick three 2-minute reference pieces with different speaker mixes, cut their audio, write drafts.

Usage: .venv/bin/python scripts/asr/etalon.py [engine=cpp] [--force]
Output: downloads/asr/etalon/{A,B,C}.mp3 + .txt (the draft to correct by ear) + .draft-<engine>.txt.
Pieces used on 26.09 are fixed in common.WINDOWS; this script found them.
"""
import collections
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, fmt, parse  # noqa: E402

LEN, END = 120, 5130


def best(rows, score):
    """Start of the 2-minute window (10 s steps) with the highest score(rows_in_window, start)."""
    top = None
    for s in range(0, END - LEN, 10):
        sc = score([r for r in rows if s <= r[0] < s + LEN], s)
        if top is None or sc > top[0]:
            top = (sc, s)
    return top[1]


def pick(rows):
    """A: the main speaker alone; B: the second speaker; C: the most speakers. No overlaps."""
    tot = collections.Counter()
    for t, n, x in rows:
        tot[n] += len(x.split())
    first, second = [n for n, _ in tot.most_common(2)]
    nwords = lambda r, who: sum(len(x[2].split()) for x in r if x[1] == who)  # noqa: E731
    a = best(rows, lambda r, s: nwords(r, first) - 5 * len({x[1] for x in r}))
    b = best(rows, lambda r, s: nwords(r, second) if abs(s - a) >= LEN else -1)
    c = best(rows, lambda r, s: len({x[1] for x in r}) * 100 + len(r) if min(abs(s - a), abs(s - b)) >= LEN else -1)
    return {"A": a, "B": b, "C": c}


def main(engine):
    path = f"{ROOT}/transcript-{engine}.txt"
    lines = open(path, encoding="utf-8").readlines()
    rows = [p for p in map(parse, lines) if p]
    out, mp3 = f"{ROOT}/etalon", glob.glob(f"{ROOT}/*/*.mp3")[0]
    if os.path.exists(f"{out}/A.txt") and "--force" not in sys.argv:
        sys.exit(f"{out} уже есть — это выверенный эталон; перезапись только с --force")
    os.makedirs(out, exist_ok=True)
    for k, s in pick(rows).items():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", str(LEN), "-i", mp3, "-c", "copy", f"{out}/{k}.mp3"])
        with open(f"{out}/{k}.txt", "w", encoding="utf-8") as f:
            f.write(f"# Кусок {k}: {fmt(s)} — 2 минуты. Исправьте текст и имена прямо здесь, сохраните файл.\n\n")
            f.writelines(line for line, p in zip(lines, map(parse, lines)) if p and s <= p[0] < s + LEN)
        shutil.copy(f"{out}/{k}.txt", f"{out}/{k}.draft-{engine}.txt")
        print(k, fmt(s))


if __name__ == "__main__":
    main(next((a for a in sys.argv[1:] if not a.startswith("--")), "cpp"))
