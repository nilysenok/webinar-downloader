"""Score engines against the owner's reference pieces: per-speaker WER and speaker attribution.

Usage: .venv/bin/python scripts/asr/score.py cpp mlx
Reference: downloads/asr/etalon/{A,B,C}.txt (made by etalon.py, corrected by ear).
The hypothesis window is 10 s wider on both sides: engines cut phrases differently.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, WINDOWS, attribution, speaker_wer, words  # noqa: E402


def lines(path):
    return open(path, encoding="utf-8").readlines()


def score(engine):
    hyp_lines = lines(f"{ROOT}/transcript-{engine}.txt")
    total_n = total_e = right = matched = 0
    for k, s in WINDOWS.items():
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
