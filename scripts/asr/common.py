"""Shared pieces of the ASR measurement: paths, transcript lines, word alignment, WER.

Real transcripts are personal data: everything lives in downloads/asr (gitignored).
Models live in ~/.cache, never in the session's temporary folder (it is wiped by macOS updates).
"""
import os
import re

ROOT = os.path.expanduser("~/Desktop/МТС/downloads/asr")
CACHE = os.path.expanduser("~/.cache")
GGML = f"{CACHE}/whisper.cpp/ggml-large-v3-turbo.bin"
SILERO = f"{CACHE}/whisper.cpp/ggml-silero-v5.1.2.bin"
MLX_MODEL = f"{CACHE}/mlx-whisper/whisper-large-v3-turbo"
WINDOWS = {"A": 1300, "B": 4420, "C": 4630}  # reference pieces, 2 min each (26.09)


def windows():
    """Reference pieces: the blind reference's key (27.09, 7 pieces) when it exists."""
    import json
    p = f"{ROOT}/etalon/.key.json"
    return json.load(open(p, encoding="utf-8"))["windows"] if os.path.exists(p) else WINDOWS
LINE = re.compile(r"\[(\d+):(\d+):(\d+)\] ([^:]+): (.*)")


def fmt(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def parse(line):
    """'[0:01:02] Имя: текст' -> (62, 'Имя', 'текст') or None."""
    m = LINE.match(line)
    if not m:
        return None
    return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]), m[4], m[5]


def norm(word):
    return re.sub(r"[^\w]", "", word.lower().replace("ё", "е"))


def words(lines, lo, hi):
    """Words of transcript lines starting in [lo, hi): (time, speaker, normalised word)."""
    out = []
    for line in lines:
        p = parse(line)
        if p and lo <= p[0] < hi:
            out += [(p[0], p[1], w) for w in map(norm, p[2].split()) if w]
    return out


def to_global(entry, t):
    """Time in a speech-only wav -> time on the recording timeline.

    entry = {"offset": track start, "map": [[wav_from, wav_to, source_from], ...]}."""
    for a, b, src in entry["map"]:
        if t <= b + 0.3:
            return entry["offset"] + src + max(0.0, t - a)
    a, _, src = entry["map"][-1]
    return entry["offset"] + src + (t - a)


def align(ref, hyp, free_ends=False):
    """Levenshtein alignment of word tuples by their text: list of (op, i, j), op in = S D I.

    free_ends: hypothesis words before and after the reference cost nothing — the hypothesis
    window is wider, and a repeated word just past the edge must not pull the match outside."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = 0 if free_ends else j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (ref[i - 1][2] != hyp[j - 1][2]))
    end = min(range(m + 1), key=lambda j: (d[n][j], j)) if free_ends else m
    ops, i, j = [("I", None, k) for k in range(m - 1, end - 1, -1)], n, end
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (ref[i - 1][2] != hyp[j - 1][2]):
            ops.append(("=" if ref[i - 1][2] == hyp[j - 1][2] else "S", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif not i:
            ops.append(("I", None, j - 1))
            j -= 1
        elif d[i][j] == d[i - 1][j] + 1:
            ops.append(("D", i - 1, None))
            i -= 1
        else:
            ops.append(("I", None, j - 1))
            j -= 1
    return ops[::-1]


def trim(ops):
    """Drop unmatched words outside the first..last match: the hypothesis window is wider."""
    hits = [k for k, o in enumerate(ops) if o[0] == "="]
    return ops[hits[0]:hits[-1] + 1] if hits else ops


def speaker_wer(ref, hyp):
    """WER per speaker, summed: phrase order between speakers does not count as an error.

    Returns (reference words, errors). A speaker with no match at all counts as deletions."""
    n = e = 0
    for sp in {w[1] for w in ref}:
        rs, hs = [w for w in ref if w[1] == sp], [w for w in hyp if w[1] == sp]
        ops = align(rs, hs, free_ends=True)
        if not any(o[0] == "=" for o in ops):
            n, e = n + len(rs), e + len(rs)
            continue
        ops = trim(ops)
        n += sum(o[1] is not None for o in ops)
        e += sum(o[0] != "=" for o in ops)
    return n, e


def attribution(ref, hyp):
    """Share of matched words whose speaker agrees, over the joint alignment: (right, matched)."""
    same = [o for o in trim(align(ref, hyp, free_ends=True)) if o[0] == "="]
    return sum(ref[i][1] == hyp[j][1] for _, i, j in same), len(same)
