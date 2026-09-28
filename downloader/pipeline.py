"""Конвейер задачи: метаданные → скачивание сегментов → сведение аудио → склейка видео."""
import asyncio
import re
import time
from pathlib import Path

import httpx

from .config import DOWNLOADS, MODES, TIMEOUT, UA
from . import gallery
from .boxes import video_size
from .hls import Cancelled, analyze, fetch, parse_media, pick_variant
from .media import concat, mix_audio, mux_video
from .models import Job


def sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip(" .") or "mts-link"


def hms(sec: float) -> str:
    s = int(sec)
    return f"{s // 3600}-{s % 3600 // 60:02d}-{s % 60:02d}"


def job_folder(job: Job) -> Path:
    """Папка загрузки: downloads/ГГГГ-ММ-ДД_ЧЧММ <название> по моменту загрузки (Ъ, 25.09).

    Повторная загрузка той же записи получает новую папку; перезапуск задачи — ту же (докачка).
    """
    if job.folder:
        return Path(job.folder)
    stamp = time.strftime("%Y-%m-%d_%H%M", time.localtime(job.created))
    base = DOWNLOADS / f"{stamp} {sanitize(job.title)}"
    path, n = base, 2
    while path.exists():
        path, n = base.with_name(f"{base.name} ({n})"), n + 1
    job.folder = str(path)
    return path


async def run(job: Job):
    """Выполняет задачу целиком. Не бросает исключений — итог в job.status / job.error / job.log."""
    try:
        await _run(job)
    except Cancelled:
        job.status = "cancelled"
        job.add_log("warn", "Отменено. Скачанные сегменты сохранены — перезапуск продолжит с места остановки")
    except Exception as e:
        job.status = "error"
        job.error = f"{type(e).__name__}: {e}"
        job.add_log("error", job.error)
    finally:
        job.finished = time.time()


async def _run(job: Job):
    job.status, job.started = "meta", time.time()
    job.add_log("info", f"Старт: {MODES.get(job.mode, job.mode)}, потоков {job.workers}")
    limits = httpx.Limits(max_connections=job.workers, max_keepalive_connections=job.workers)
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=TIMEOUT, limits=limits,
                                 follow_redirects=True) as client:
        tracks = await _prepare(job, client)
        groups = await _download(job, client, tracks)
    files = {}
    for t, kind, paths in groups:
        files[(t.id, kind)] = out = job.work / str(t.id) / f"{kind}.mp4"
        await asyncio.to_thread(concat, paths, out)
    await _assemble(job, tracks, files)
    job.size = sum(o["size"] for o in job.outputs)
    job.status = "done"
    job.add_log("info", f"Готово: {len(job.outputs)} файл(ов), {job.size / 1e6:.0f} МБ → {job.folder}")


async def _prepare(job: Job, client):
    info = await analyze(client, job.url, job)
    job.title, job.rec_date, job.duration = info["title"], info["date"], info["duration"]
    tracks = info["tracks"]
    job_folder(job)
    job.work.mkdir(parents=True, exist_ok=True)
    want_audio, want_video = job.wants()
    if want_video:
        chosen = set(job.streams) or {t.id for t in tracks if t.variants}
        for t in tracks:
            if t.id in chosen and t.variants:
                t.video, t.height = True, pick_variant(t.variants, job.quality)["height"]
        if not any(t.video for t in tracks):
            raise RuntimeError("Не выбран ни один видеопоток")
    if job.mode != "video" and not any(t.has_audio for t in tracks):
        raise RuntimeError("В записи нет аудиодорожек")
    job.tracks = tracks
    job.add_log("info", f"«{job.title}», {job.duration / 60:.1f} мин, медиасессий {len(tracks)}"
                        + (f", видео: {sum(t.video for t in tracks)}" if want_video else ""))
    return tracks


async def _download(job: Job, client, tracks):
    want_audio, _ = job.wants()
    wanted = []  # (дорожка, "a"|"v", url плейлиста)
    for t in tracks:
        if want_audio and t.has_audio:
            wanted.append((t, "a", t.audio_uri))
        if t.video:
            wanted.append((t, "v", pick_variant(t.variants, job.quality)["uri"]))
    playlists = await asyncio.gather(*(fetch(client, u, job) for _, _, u in wanted))
    queue, groups = _plan(job, wanted, playlists)
    job.add_log("info", f"Сегментов: {job.seg_total}, уже на диске: {job.seg_cached}, качать: {queue.qsize()}")
    job.status = "download"
    await _drain(job, client, queue)
    return groups


def _plan(job: Job, wanted, playlists):
    """Раскладывает сегменты по файлам _work/<дорожка>/<a|v>/NNNNN.m4s; уже скачанные — не в очередь."""
    groups, queue = [], asyncio.Queue()
    for (t, kind, url), text in zip(wanted, playlists):
        parts = parse_media(url, text.decode())
        folder = job.work / str(t.id) / kind
        folder.mkdir(parents=True, exist_ok=True)
        paths = [folder / f"{i:05d}.m4s" for i in range(len(parts))]
        groups.append((t, kind, paths))
        t.segments += len(parts)
        job.seg_total += len(parts)
        for u, p in zip(parts, paths):
            if p.exists():
                job.got_segment(t, p.stat().st_size, cached=True)
            else:
                queue.put_nowait((t, u, p))
    return queue, groups


async def _drain(job: Job, client, queue):
    async def worker():
        while not queue.empty():
            t, u, p = queue.get_nowait()
            data = await fetch(client, u, job)
            tmp = p.with_name(p.name + ".part")
            tmp.write_bytes(data)
            tmp.replace(p)  # атомарно: недокачанный сегмент не примется за готовый
            job.got_segment(t, len(data))

    workers = [asyncio.create_task(worker()) for _ in range(min(job.workers, queue.qsize()))]
    try:
        await asyncio.gather(*workers)
    finally:
        for w in workers:
            w.cancel()


async def _assemble(job: Job, tracks, files):
    _, want_video = job.wants()
    folder, base = Path(job.folder), sanitize(job.title)
    mix = None
    inputs = [(files[(t.id, "a")], t.start) for t in tracks if (t.id, "a") in files]
    if inputs:
        job.status = "mix"
        job.add_log("info", f"Сведение {len(inputs)} аудиодорожек")
        mix = folder / f"{base}.mp3" if job.mode == "audio" else job.work / "mix.m4a"
        await mix_audio(job, inputs, mix)
        job.mix_pos = job.duration
        if job.mode == "audio":
            job.outputs.append({"path": str(mix), "size": mix.stat().st_size})
    if want_video:
        await _mux_all(job, tracks, files, mix, folder, base)


def _has_video(path: Path) -> bool:
    with open(path, "rb") as f:
        return video_size(f.read(1 << 16)) is not None  # init в начале склеенного файла


async def _mux_all(job: Job, tracks, files, mix, folder: Path, base: str):
    """Видео каждого по отдельности (без перекодирования), затем общий экран."""
    vids = [t for t in tracks if t.video]
    for t in [t for t in vids if not _has_video(files[(t.id, "v")])]:
        job.add_log("warn", f"{t.name} {hms(t.start)}: в потоке нет видео (камера выключена) — пропущено")
        vids.remove(t)
    job.status, job.mux_total = "mux", len(vids) + (job.gallery and bool(vids))
    own = mix if job.mode == "av" else None  # «Только видео»: отдельные файлы без звука
    for n, t in enumerate(vids, 1):
        out = folder / sanitize(f"{base} — {gallery.label(t)} {hms(t.start)} {t.height}p.mp4")
        job.add_log("info", f"Склейка видео {n}/{len(vids)}: {t.name}")
        await mux_video(job, files[(t.id, "v")], out, own, t.start)
        job.outputs.append({"path": str(out), "size": out.stat().st_size})
        job.mux_done = n
    if job.mux_total > len(vids):
        out = folder / sanitize(f"{base} — общий экран.mp4")
        audios = {t.id: files[(t.id, "a")] for t in tracks if (t.id, "a") in files}
        await gallery.render(job, tracks, {t.id: files[(t.id, "v")] for t in vids}, audios, mix, out,
                             on_time=lambda s: setattr(job, "mux_done", len(vids) + min(s / job.duration, 1)))
        job.outputs.append({"path": str(out), "size": out.stat().st_size})
        job.mux_done = job.mux_total
