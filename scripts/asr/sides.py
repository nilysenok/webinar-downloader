"""Which side the owner took in each «[x / y]» spot of the blind reference, and where they
wrote something of their own (names and terms usually show up there).

Usage: .venv/bin/python scripts/asr/sides.py
Needs: etalon/.key.json with the spots' texts (etalon2.py, 27.09) and the chosen reference.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, fmt, norm, parse  # noqa: E402
from score import unresolved  # noqa: E402


def text(s):
    return " ".join(w for w in map(norm, s.split()) if w and w != "—")


def near(lines, t, span=8):
    """The reference text around `t`, all speakers, normalised."""
    ps = [p for p in map(parse, lines) if p and abs(p[0] - t) <= span]
    return " " + " ".join(text(p[2]) for p in ps) + " "


def side(spot, ref):
    a, b = text(spot["a"]), text(spot["b"])
    has = lambda x: (f" {x} " in ref) if x else None  # noqa: E731
    ha, hb = has(a), has(b)
    if ha and not hb or (ha is None and hb is False):
        return "a"
    if hb and not ha or (hb is None and ha is False):
        return "b"
    return "both" if ha and hb else "own"


def main():
    key = json.load(open(f"{ROOT}/etalon/.key.json"))
    if not all("a" in sp for spots in key["spots"].values() for sp in spots):
        sys.exit("в ключе нет текстов вариантов: пересоберите эталон etalon2.py --force (старый ключ, до 28.09)")
    left = [k for k in key["spots"] if unresolved(f"{ROOT}/etalon/{k}.txt")]
    if left:
        sys.exit("сначала выберите варианты в скобках: " + ", ".join(left))
    names, tally, own = key["engines"], {"a": 0, "b": 0, "both": 0, "own": 0}, []
    for k, spots in key["spots"].items():
        ref = open(f"{ROOT}/etalon/{k}.txt", encoding="utf-8").readlines()
        for sp in spots:
            r = side(sp, near(ref, sp["time"]))
            tally[r] += 1
            if r == "own":
                own.append(f"  {k} {fmt(sp['time'])}  {names['a']}: {sp['a']}  |  {names['b']}: {sp['b']}")
    print(f"выбран {names['a']}: {tally['a']} · выбран {names['b']}: {tally['b']} · своё: {tally['own']} · не различить: {tally['both']}")
    print("\n".join(own))


if __name__ == "__main__":
    main()
