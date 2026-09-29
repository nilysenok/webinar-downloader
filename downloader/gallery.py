"""Общий экран, как в Zoom: в кадре те, у кого камера, и те, кто сейчас говорит; говорящий — в зелёной рамке.

Запись режется на отрезки с постоянным составом (layout.py); каждый отрезок — свой ffmpeg
(tiles.py), по PARALLEL сразу; потом склейка без перекодирования и общий звук. Видео
перекодируется (VP9 → H.264, аппаратно на Mac) — склеить сетку без этого нельзя.
"""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from . import layout, speech, tiles
from .media import _to_file, duration

PARALLEL = 3


def label(t) -> str:
    return f"{t.name} (экран)" if t.kind == "screen" else t.name


def codec():
    if sys.platform == "darwin":
        # постоянное качество: говорящая голова 512 кбит/с против 3 Мбит/с на -b:v 3M при той же картинке,
        # пустая плитка ~90 кбит/с (замер 28.09 на ИФР: 2,1 ГБ на 105 мин при 3M)
        return ["-c:v", "h264_videotoolbox", "-q:v", "50"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]


async def _speech(job, tracks, audios, work: Path):
    """{имя: окна речи} по дорожкам людей (у человека может быть несколько сессий — берём громкую)."""
    n, sem, lv = int(job.duration / layout.WIN) + 1, asyncio.Semaphore(8), {}

    async def one(t):
        async with sem:
            return t, await speech.levels(job, audios[t.id], t.start, n, work, str(t.id))

    for t, got in await asyncio.gather(*(one(t) for t in tracks if t.id in audios)):
        lv[label(t)] = [max(a, b) for a, b in zip(lv.get(label(t), got), got)]
    return {p: speech.talking(v) for p, v in lv.items()}


async def _sessions(tracks, videos):
    """{имя: [(начало, конец, путь)]} — когда у человека идёт видео."""
    out = {}
    for t in sorted(tracks, key=lambda t: t.start):
        if t.id in videos:
            out.setdefault(label(t), []).append((t.start, t.start + await duration(videos[t.id]), videos[t.id]))
    return out


async def _segment(job, i, seg, sessions, labels, work: Path, tick):
    """Один отрезок → seg_NNNN_<хеш>.mp4; готовый с тем же графом повторно не собирается (докачка)."""
    inputs, graph = tiles.graph(seg, sessions, labels)
    args = []
    for path, ss, length in inputs:
        # MTS Link меняет размер кадра внутри потока (1280×720 ↔ 640×360 ↔ 320×180). Без -reinit_filter 0
        # ffmpeg на каждую смену пересобирает граф, color начинает с нуля — на ИФР сборка вставала (28.09)
        args += ["-reinit_filter", "0", "-ss", f"{ss:.3f}", "-t", f"{length:.3f}", "-i", path]
    length = seg.t1 - seg.t0
    args += ["-filter_complex", graph, "-map", "[out]", "-an", *codec(), "-r", str(tiles.FPS), "-t", f"{length:.3f}"]
    key = hashlib.sha1(json.dumps([str(a) for a in args]).encode()).hexdigest()[:10]
    out = work / f"seg_{i:04d}_{key}.mp4"
    if not out.exists():
        await _to_file(job, args, out, lambda s: tick(i, min(s, length)), cwd=work)
    tick(i, length)
    return out


async def render(job, tracks, videos: dict, audios: dict, mix: Path | None, out: Path, on_time=None):
    """tracks — все дорожки записи; videos/audios: {id: путь}; mix — общий звук (или None)."""
    work = job.work / "gallery"
    work.mkdir(parents=True, exist_ok=True)
    talk = await _speech(job, tracks, audios, work)
    sessions = await _sessions(tracks, videos)
    segs = layout.plan(job.duration, {p: [(a, b) for a, b, _ in s] for p, s in sessions.items()}, talk)
    names = sorted({p for s in segs for p in s.who})
    labels = {p: f"n{k}.txt" for k, p in enumerate(names)}
    for p, f in labels.items():
        (work / f).write_text(p, encoding="utf-8")
    (work / "title.txt").write_text(job.title or "Запись", encoding="utf-8")
    job.add_log("info", f"Общий экран: отрезков {len(segs)}, в кадре до {max(len(s.who) for s in segs)} человек, "
                        f"с камерой {len(sessions)}, говорили {sum(any(v) for v in talk.values())}")
    done, sem = {}, asyncio.Semaphore(PARALLEL)

    def tick(i, secs):
        done[i] = secs
        if on_time:
            on_time(sum(done.values()))

    async def one(i, seg):
        async with sem:
            return await _segment(job, i, seg, sessions, labels, work, tick)

    parts = await asyncio.gather(*(one(i, s) for i, s in enumerate(segs)))
    (work / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    args = ["-f", "concat", "-safe", "0", "-i", "list.txt"] + (["-i", mix] if mix else [])
    args += ["-map", "0:v"] + (["-map", "1:a:0"] if mix else []) + ["-c", "copy", "-t", f"{job.duration:.3f}",
                                                                    "-movflags", "+faststart"]
    await _to_file(job, args, out, cwd=work)
