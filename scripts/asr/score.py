"""Score engines against the owner's reference pieces: per-speaker WER and speaker attribution.

Usage: .venv/bin/python scripts/asr/score.py cpp mlx
Reference: downloads/asr/etalon/{A..G}.txt (etalon2.py: blind draft, chosen by ear).
The hypothesis window is 10 s wider on both sides: engines cut phrases differently.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, attribution, speaker_wer, windows, words  # noqa: E402


def lines(path):
    return open(path, encoding="utf-8").readlines()


def unresolved(path):
    """Draft spots the owner has not chosen yet: «[x / y]» left in the reference."""
    return [ln.strip() for ln in lines(path) if not ln.startswith("#") and re.search(r"\[[^\]]*/[^\]]*\]", ln.split(": ", 1)[-1])]


def score(engine):
    hyp_lines = lines(f"{ROOT}/transcript-{engine}.txt")
    total_n = total_e = right = matched = 0
    left = {k: unresolved(f"{ROOT}/etalon/{k}.txt") for k in windows()}
    if any(left.values()):
        sys.exit("в эталоне остались строки с невыбранными [x / y]: " + ", ".join(f"{k}: {len(v)}" for k, v in left.items() if v))
    for k, s in windows().items():
        ref = words(lines(f"{ROOT}/etalon/{k}.txt"), s, s + 120)
        hyp = words(hyp_lines, s - 10, s + 130)
        n, e = speaker_wer(ref, hyp)
        r, m = attribution(ref, hyp)
        print(f"  {engine} {k}: WER {100 * e / n:.1f}% ({e}/{n}), speaker {r}/{m}")
        total_n, total_e, right, matched = total_n + n, total_e + e, right + r, matched + m
    print(f"{engine}: WER {100 * total_e / total_n:.1f}% on {total_n} words, attribution {100 * right / matched:.1f}%")


if __name__ == "__main__":
    for engine in sys.argv[1:]:
        score(engine)
