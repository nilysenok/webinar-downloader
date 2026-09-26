"""VAD every track, write a speech-only wav per track and a map back to the recording timeline.

Usage: .venv/bin/python scripts/asr/vad.py     (after scripts/asr/tracks.sh)
Input:  downloads/asr/wav/NN.wav (16 kHz mono) and the FCPXML of the webinarip --multicam run.
Output: downloads/asr/speech/NN.wav + speech/map.json.
"""
import glob
import html
import json
import os
import re
import subprocess
import sys
import wave

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, SILERO  # noqa: E402

PAD, GAP, SR = 0.2, 0.6, 16000  # seconds around speech, silence between pieces, sample rate


def offsets():
    """Track number -> start on the timeline, from the FCPXML (offset − start, 25 fps units)."""
    x = open(glob.glob(f"{ROOT}/*/*.fcpxml")[0], encoding="utf-8").read()
    src = {a: html.unescape(s) for a, s in re.findall(r'<asset id="(a\d+)".*?src="([^"]+)"', x, re.S)}
    clips = re.findall(r'<asset-clip ref="(a\d+)"[^>]*?offset="(-?\d+)/25s"[^>]*?start="(-?\d+)/25s"', x)
    return {os.path.basename(src[r])[:2]: (int(o) - int(s)) / 25 for r, o, s in clips}


def vad(path):
    r = subprocess.run(["whisper-vad-speech-segments", "-vm", SILERO, "-f", path], capture_output=True, text=True)
    return [(float(a) / 100, float(b) / 100) for a, b in re.findall(r"start = ([\d.]+), end = ([\d.]+)", r.stdout)]


def speech_only(path, segs, out):
    """Concatenate speech pieces with short gaps; return [[wav_from, wav_to, source_from], ...]."""
    with wave.open(path) as w:
        pcm = w.readframes(w.getnframes())
    total, parts, m, cur = len(pcm) / 2 / SR, [], [], 0.0
    for s, e in segs:
        s, e = max(0.0, s - PAD), min(total, e + PAD)
        chunk = pcm[int(s * SR) * 2:int(e * SR) * 2]
        m.append([cur, cur + len(chunk) / 2 / SR, s])
        parts += [chunk, bytes(int(GAP * SR) * 2)]
        cur += len(chunk) / 2 / SR + GAP
    with wave.open(out, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR), w.writeframes(b"".join(parts))
    return m


def main():
    sp = f"{ROOT}/speech"
    os.makedirs(sp, exist_ok=True)
    offs, maps, total = offsets(), {}, 0.0
    for p in sorted(glob.glob(f"{ROOT}/wav/*.wav")):
        n, segs = os.path.basename(p)[:2], vad(p)
        if not segs:
            continue
        speech = sum(e - s for s, e in segs)
        maps[n] = {"offset": offs.get(n, 0.0), "map": speech_only(p, segs, f"{sp}/{n}.wav"), "speech": speech}
        total += speech
        print(f"{n} offset {offs.get(n, 0):8.2f}  segments {len(segs):4d}  speech {speech / 60:5.1f} min")
    json.dump(maps, open(f"{sp}/map.json", "w"))
    print(f"total speech {total / 60:.1f} min")


if __name__ == "__main__":
    main()
