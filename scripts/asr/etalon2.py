"""A blind reference: 2-minute pieces whose draft comes from two engines at once. Where they
agree the text is plain; where they differ it reads «[вариант / вариант]» in random order, so
the owner cannot tell the engines apart and picks (or writes) the right words by ear.

Usage: .venv/bin/python scripts/asr/etalon2.py <engine1> <engine2> [--force]
Output: downloads/asr/etalon/{A..G}.txt + .mp3; the old drafts kept as X.v1.txt;
        .key.json says which side was which (for the report only, never shown in the draft).
Pieces: A, B, C as before (26.09) + D (two people at once) + E, F, G (the least heard speakers).
"""
import collections
import difflib
import glob
import json
import os
import random
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, WINDOWS, fmt, norm, parse  # noqa: E402

LEN, END = 120, 5130


def rows(engine):
    return [p for p in map(parse, open(f"{ROOT}/transcript-{engine}.txt", encoding="utf-8")) if p]


def overlap_secs(s):
    """Seconds in [s, s+LEN) where two or more tracks have speech (VAD pieces, speech/map.json)."""
    maps = json.load(open(f"{ROOT}/speech/map.json"))
    on = collections.Counter()
    for m in maps.values():
        for a, b, src in m["map"]:
            t0, t1 = m["offset"] + src, m["offset"] + src + (b - a)
            for k in range(max(int(t0), s), min(int(t1), s + LEN)):
                on[k] += 1
    return sum(1 for k in range(s, s + LEN) if on[k] >= 2)


def far(s, taken):
    return all(abs(s - t) >= LEN for t in taken)


def pick(base):
    """D: most simultaneous speech; E–G: most words of the speakers heard least so far."""
    taken, out = list(WINDOWS.values()), {}
    d = max((s for s in range(0, END - LEN, 10) if far(s, taken)), key=overlap_secs)
    out["D"] = d
    taken.append(d)
    heard = collections.Counter()
    for s in taken:
        for t, n, x in base:
            heard[n] += len(x.split()) if s <= t < s + LEN else 0
    for k in "EFG":
        def score(s):
            w = collections.Counter(n for t, n, x in base if s <= t < s + LEN for _ in x.split())
            return sum(c / (1 + heard[n]) for n, c in w.items())
        s = max((s for s in range(0, END - LEN, 10) if far(s, taken)), key=score)
        out[k], taken = s, taken + [s]
        for t, n, x in base:
            heard[n] += len(x.split()) if s <= t < s + LEN else 0
    return out


def merge(a_rows, b_rows, rnd, key):
    """One speaker's lines from both engines -> draft lines; differences as [x / y]."""
    a = [(t, w) for t, _, x in a_rows for w in x.split()]
    b = [(t, w) for t, _, x in b_rows for w in x.split()]
    ops = difflib.SequenceMatcher(None, [norm(w) for _, w in a], [norm(w) for _, w in b], autojunk=False).get_opcodes()
    out = []  # (time, token)
    for op, i1, i2, j1, j2 in ops:
        if op == "equal":
            out += a[i1:i2]
            continue
        x, y = " ".join(w for _, w in a[i1:i2]) or "—", " ".join(w for _, w in b[j1:j2]) or "—"
        t = a[i1][0] if i2 > i1 else b[j1][0]
        swap = rnd.random() < 0.5
        key.append({"time": t, "first": "b" if swap else "a", "a": x, "b": y})
        out.append((t, f"[{y} / {x}]" if swap else f"[{x} / {y}]"))
    return out


def draft(k, s, ea, eb, rnd, key):
    lines = collections.defaultdict(list)
    ra, rb = rows(ea), rows(eb)
    for sp in sorted({n for t, n, _ in ra + rb if s <= t < s + LEN}):
        pick_rows = lambda r: [x for x in r if x[1] == sp and s <= x[0] < s + LEN]  # noqa: E731
        for t, tok in merge(pick_rows(ra), pick_rows(rb), rnd, key):
            lines[(t, sp)].append(tok)
    body = "".join(f"[{fmt(t)}] {sp}: {' '.join(toks)}\n" for (t, sp), toks in sorted(lines.items()))
    head = (f"# Кусок {k}: {fmt(s)} — 2 минуты. Два черновика сведены в один: где они расходятся, стоит [вариант / вариант].\n"
            "# Оставьте верный вариант без скобок или впишите своё; «—» значит «ничего не сказано». Исправьте и остальное, если слышите иначе.\n\n")
    return head + body


def main(ea, eb):
    out, mp3 = f"{ROOT}/etalon", glob.glob(f"{ROOT}/*/*.mp3")[0]
    if os.path.exists(f"{out}/D.txt") and "--force" not in sys.argv:
        sys.exit(f"{out}/D.txt уже есть — возможно, это выверенный эталон; перезапись только с --force")
    windows = {**WINDOWS, **pick(rows(ea))}
    rnd, key = random.Random(20260927), {}
    for k, s in windows.items():
        if os.path.exists(f"{out}/{k}.txt") and not os.path.exists(f"{out}/{k}.v1.txt"):
            shutil.copy(f"{out}/{k}.txt", f"{out}/{k}.v1.txt")
        key[k] = []
        with open(f"{out}/{k}.txt", "w") as f:
            f.write(draft(k, s, ea, eb, rnd, key[k]))
        if not os.path.exists(f"{out}/{k}.mp3"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", str(LEN), "-i", mp3, "-c", "copy", f"{out}/{k}.mp3"])
        print(k, fmt(s), f"спорных мест {len(key[k])}", f"двое сразу {overlap_secs(s)} с")
    json.dump({"engines": {"a": ea, "b": eb}, "windows": windows, "spots": key}, open(f"{out}/.key.json", "w"), ensure_ascii=False)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(*args[:2])
