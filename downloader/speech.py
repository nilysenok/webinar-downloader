"""Кто когда говорит: громкость дорожки каждого человека по окнам WIN (ffmpeg astats) → окна речи.

Каждая дорожка — один человек, поэтому речь = громкость его дорожки выше порога. Эхо ведущего
в чужих дорожках почти не мешает: двое громче −40 дБ одновременно — 5 мин из 86 (замер 28.09).
"""
import re
from pathlib import Path

from .layout import WIN
from .media import ffmpeg

THRESHOLD = -40.0  # дБ
BRIDGE = 3  # окна: паузу до 1,5 с считаем речью
MIN_TALK = 2  # окна: всплеск короче 1 с — не речь


async def levels(job, audio: Path, start: float, n: int, folder: Path, name: str) -> list:
    """Громкость (дБ) по окнам общей шкалы записи; где дорожки нет — −120."""
    out = [-120.0] * n
    f = folder / f"{name}.lv"
    graph = (f"aformat=channel_layouts=mono,aresample=8000,asetnsamples=n={int(8000 * WIN)}:p=0,"
             "astats=metadata=1:reset=1:measure_perchannel=none:measure_overall=RMS_level,"
             f"ametadata=print:key=lavfi.astats.Overall.RMS_level:file={f.name}")
    await ffmpeg(job, ["-i", audio, "-af", graph, "-f", "null", "-"], cwd=folder)
    pts = None
    for line in f.read_text().splitlines():
        if m := re.search(r"pts_time:([\d.]+)", line):
            pts = float(m[1])
        elif line.startswith("lavfi.astats.Overall.RMS_level=") and pts is not None:
            w = int(round((start + pts) / WIN))
            v = line.split("=", 1)[1]
            if 0 <= w < n and v not in ("-inf", "inf", "nan"):
                out[w] = max(out[w], float(v))
    return out


def _runs(a, value):
    i = 0
    while i < len(a):
        if a[i] == value:
            j = i
            while j < len(a) and a[j] == value:
                j += 1
            yield i, j
            i = j
        else:
            i += 1


def talking(lv) -> list:
    """Окна речи: громче порога, паузы до BRIDGE склеены, всплески короче MIN_TALK выброшены."""
    s = [v > THRESHOLD for v in lv]
    for i, j in list(_runs(s, False)):
        if 0 < i and j < len(s) and j - i < BRIDGE:
            s[i:j] = [True] * (j - i)
    for i, j in list(_runs(s, True)):
        if j - i < MIN_TALK:
            s[i:j] = [False] * (j - i)
    return s
