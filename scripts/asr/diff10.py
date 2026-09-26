"""Ten substantive disagreements between two engines across the recording, with 14 s audio clips.

Usage: .venv/bin/python scripts/asr/diff10.py [a=cpp] [b=mlx] [--force]
Output: downloads/asr/diff/NN.mp3 + 10-mest.txt with an empty «прав:» line for the owner.
"""
import difflib
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, fmt, norm, parse  # noqa: E402

FILL = {"ну", "вот", "и", "а", "это", "так", "да", "то", "же", "там", "в", "с", "не"}


def by_speaker(engine):
    out = {}
    for p in map(parse, open(f"{ROOT}/transcript-{engine}.txt", encoding="utf-8")):
        if p:
            out.setdefault(p[1], []).extend((p[0], w, norm(w)) for w in p[2].split())
    return out


def context(ws, lo, hi):
    pre, mid, post = ws[max(lo - 3, 0):lo], ws[lo:hi], ws[hi:hi + 3]
    return " ".join(w[1] for w in pre) + " [" + " ".join(w[1] for w in mid) + "] " + " ".join(w[1] for w in post)


def candidates(a, b):
    """(score, time, speaker, text_a, text_b): score = differing words that are not fillers."""
    out = []
    for sp, x in a.items():
        y = b.get(sp, [])
        ops = difflib.SequenceMatcher(None, [w[2] for w in x], [w[2] for w in y], autojunk=False).get_opcodes()
        for op, i1, i2, j1, j2 in ops:
            diff = {w[2] for w in x[i1:i2]} ^ {w[2] for w in y[j1:j2]}
            if op == "equal" or len(diff - FILL) < 2 or i2 - i1 > 25 or j2 - j1 > 25:
                continue
            t = x[i1][0] if i2 > i1 else x[max(i1 - 1, 0)][0]
            out.append((len(diff - FILL), t, sp, context(x, i1, i2), context(y, j1, j2)))
    return sorted(out, key=lambda c: -c[0])


def main(ea, eb):
    a, b = by_speaker(ea), by_speaker(eb)
    track = {n: f"дорожка {i + 1}" for i, n in enumerate(sorted(a))}
    picked = []
    for c in candidates(a, b):
        if len(picked) < 10 and all(abs(c[1] - p[1]) > 90 for p in picked):
            picked.append(c)
    out, mp3 = f"{ROOT}/diff", glob.glob(f"{ROOT}/*/*.mp3")[0]
    if os.path.exists(f"{out}/10-mest.txt") and "--force" not in sys.argv:
        sys.exit(f"{out}/10-mest.txt уже есть — там могут быть ответы владельца; перезапись только с --force")
    os.makedirs(out, exist_ok=True)
    with open(f"{out}/10-mest.txt", "w") as f:
        for k, (_, t, sp, ta, tb) in enumerate(sorted(picked, key=lambda c: c[1]), 1):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(t - 3, 0)), "-t", "14", "-i", mp3, "-c", "copy", f"{out}/{k:02d}.mp3"])
            block = f"{k:2d}. {fmt(t)}  {track[sp]}  (файл {k:02d}.mp3)\n    {ea}: {ta}\n    {eb}: {tb}\n    прав: \n\n"
            f.write(block)
            print(block, end="")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(*(args[:2] if len(args) > 1 else ("cpp", "mlx")))
