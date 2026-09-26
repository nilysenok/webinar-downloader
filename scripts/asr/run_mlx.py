"""Transcribe every speech-only track with mlx-whisper; one process, the model loads once.

Usage: .venv-asr/bin/python scripts/asr/run_mlx.py    (mlx-whisper lives in its own venv: torch is heavy)
Output: downloads/asr/speech/mlx/NN.json
"""
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from common import MLX_MODEL, ROOT  # noqa: E402


def main():
    import mlx_whisper

    sp = f"{ROOT}/speech"
    os.makedirs(f"{sp}/mlx", exist_ok=True)
    t0 = time.time()
    for p in sorted(glob.glob(f"{sp}/*.wav")):
        t = time.time()
        r = mlx_whisper.transcribe(p, path_or_hf_repo=MLX_MODEL, language="ru")
        segs = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in r["segments"]]
        json.dump(segs, open(f"{sp}/mlx/{os.path.basename(p)[:2]}.json", "w"), ensure_ascii=False)
        print(os.path.basename(p), f"{time.time() - t:.1f}s", len(segs), flush=True)
    print(f"total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
