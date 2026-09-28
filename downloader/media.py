"""Локальная сборка: склейка fMP4-сегментов, сведение аудио и склейка видео через ffmpeg."""
import asyncio
import shutil
from pathlib import Path

from .hls import Cancelled


def concat(paths, out: Path):
    """fMP4: init + сегменты подряд = валидный mp4/m4a (без ffmpeg и без перекодирования)."""
    tmp = out.with_name(out.name + ".tmp")
    with open(tmp, "wb") as f:
        for p in paths:
            with open(p, "rb") as src:
                shutil.copyfileobj(src, f, 1 << 20)
    tmp.replace(out)


async def ffmpeg(job, args, on_time=None, cwd=None):
    """Запуск ffmpeg с отслеживанием прогресса (-progress) и отменой задачи."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-progress", "pipe:1", *map(str, args)]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE, cwd=cwd)
    err = asyncio.create_task(proc.stderr.read())  # читаем сразу: полный канал stderr остановит ffmpeg
    async for line in proc.stdout:
        if job.cancel:
            proc.terminate()
            await proc.wait()
            raise Cancelled
        key, _, val = line.decode().strip().partition("=")
        if on_time and key == "out_time_us" and val.isdigit():
            on_time(int(val) / 1e6)
    if await proc.wait():
        raise RuntimeError("ffmpeg: " + (await err).decode(errors="replace").strip()[-500:])
    await err


async def _to_file(job, args, out: Path, on_time=None, cwd=None):
    """ffmpeg пишет во временный файл; при сбое/отмене он удаляется, при успехе — переименовывается."""
    tmp = out.with_name(f"{out.stem}.part{out.suffix}")
    try:
        await ffmpeg(job, [*args, tmp], on_time, cwd)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(out)


async def duration(path: Path) -> float:
    """Длительность файла по ffprobe; 0, если не прочиталась."""
    proc = await asyncio.create_subprocess_exec("ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                "-of", "csv=p=0", str(path), stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.DEVNULL)
    out, _ = await proc.communicate()
    try:
        return float(out.decode().strip())
    except ValueError:
        return 0.0


def mix_filter(starts, duration):
    """Дорожки звучат одновременно → сводим amix со сдвигом каждой на её relativeTime.

    normalize=0 обязателен: иначе amix делит громкость на число входов и запись тихая.
    """
    parts = [f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(round(s * 1000))}:all=1[a{i}]"
             for i, s in enumerate(starts)]
    trim = f",atrim=0:{duration}" if duration else ""
    parts.append("".join(f"[a{i}]" for i in range(len(starts)))
                 + f"amix=inputs={len(starts)}:duration=longest:normalize=0,alimiter=limit=0.95{trim}[out]")
    return ";".join(parts)


async def mix_audio(job, inputs, out: Path):
    """inputs: [(путь к m4a, старт в секундах)]. mp3 — итог режима «аудио», m4a — для склейки с видео."""
    args = []
    for path, _ in inputs:
        args += ["-i", path]
    codec = ["-c:a", "libmp3lame", "-b:a", "128k"] if out.suffix == ".mp3" else ["-c:a", "aac", "-b:a", "160k"]
    args += ["-filter_complex", mix_filter([s for _, s in inputs], job.duration), "-map", "[out]", *codec]
    await _to_file(job, args, out, on_time=lambda s: setattr(job, "mix_pos", s))


async def mux_video(job, video: Path, out: Path, mix: Path | None = None, start: float = 0.0):
    """Видео копируется без перекодирования; звук — кусок общего микса с момента старта потока."""
    if mix:
        args = ["-i", video, "-ss", f"{start:.3f}", "-i", mix,
                "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-shortest"]
    else:
        args = ["-i", video, "-map", "0:v:0", "-c", "copy"]
    await _to_file(job, [*args, "-movflags", "+faststart"], out)
