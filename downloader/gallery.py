"""Общий экран, как галерея Zoom: камеры всех участников сеткой на одном видео с общим звуком.

У каждого человека своя плитка на всю запись: пока его камера идёт — видео, в остальное время —
тёмная плитка с именем. Несколько сессий одного человека (переподключения) — в одной плитке.
Видео перекодируется (VP9 → H.264, аппаратно на Mac) — склеить сетку без этого нельзя.
"""
import math
import sys
from pathlib import Path

from .media import _to_file

W, H, FPS = 1280, 720, 25
BG, TILE, GAP = "0x111111", "0x262626", 4
FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")  # есть кириллица


def label(t) -> str:
    return f"{t.name} (экран)" if t.kind == "screen" else t.name


def people(tracks):
    """[(имя, [дорожки])] в порядке первого появления: одна плитка на человека."""
    groups = {}
    for t in sorted(tracks, key=lambda t: t.start):
        groups.setdefault(label(t), []).append(t)
    return list(groups.items())


def grid(n: int):
    """Плитки 16:9 (x, y, w, h): столбцов ⌈√n⌉, неполный последний ряд — по центру, как в Zoom."""
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    tw = min(W // cols, H // rows * 16 // 9)
    th = tw * 9 // 16
    y0 = (H - rows * th) // 2
    cells = []
    for i in range(n):
        r, c = divmod(i, cols)
        x0 = (W - min(cols, n - r * cols) * tw) // 2
        cells.append((x0 + c * tw + GAP // 2, y0 + r * th + GAP // 2, (tw - GAP) // 2 * 2, (th - GAP) // 2 * 2))
    return cells


def _name(textfile: str, h: int) -> str:
    """Подпись снизу слева. textfile — имя относительно папки подписей (ffmpeg запускается в ней):
    так в граф не попадает путь загрузки, где могут быть кавычки и двоеточия."""
    if not FONT.exists():
        return "null"
    return (f"drawtext=fontfile='{FONT}':textfile={textfile}:expansion=none:fontsize={max(12, h // 14)}"
            f":fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6:x=12:y=h-th-12")


def build(groups, files, duration: float, names: Path):
    """(входы ffmpeg, filter_complex). names — папка для файлов с подписями."""
    inputs, dur = [], f"{duration:.3f}"
    parts, last = [f"color=c={BG}:s={W}x{H}:r={FPS}:d={dur}[bg]"], "bg"
    for p, ((who, ts), (x, y, w, h)) in enumerate(zip(groups, grid(len(groups)))):
        cur = f"t{p}"
        parts.append(f"color=c={TILE}:s={w}x{h}:r={FPS}:d={dur}[{cur}]")
        for t in ts:
            i = len(inputs)
            inputs.append(files[t.id])
            parts.append(f"[{i}:v]setpts=PTS-STARTPTS+{t.start:.3f}/TB,"
                         f"scale={w}:{h}:force_original_aspect_ratio=decrease[v{i}]")
            parts.append(f"[{cur}][v{i}]overlay=x=(W-w)/2:y=(H-h)/2:eof_action=pass[t{p}_{i}]")
            cur = f"t{p}_{i}"
        (names / f"{p}.txt").write_text(who, encoding="utf-8")
        parts.append(f"[{cur}]{_name(f'{p}.txt', h)}[p{p}]")
        parts.append(f"[{last}][p{p}]overlay=x={x}:y={y}[g{p}]")
        last = f"g{p}"
    parts.append(f"[{last}]format=yuv420p[out]")
    return inputs, ";".join(parts)


def codec():
    if sys.platform == "darwin":
        # постоянное качество: говорящая голова 512 кбит/с против 3 Мбит/с на -b:v 3M при той же картинке,
        # пустая плитка ~90 кбит/с (замер 28.09 на ИФР: 2,1 ГБ на 105 мин при 3M)
        return ["-c:v", "h264_videotoolbox", "-q:v", "50"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]


async def render(job, tracks, files, mix: Path | None, out: Path, on_time=None):
    """Собирает общий экран из видео `tracks` (пути в `files`), звук — общий микс `mix`."""
    names = job.work / "gallery"
    names.mkdir(parents=True, exist_ok=True)
    inputs, graph = build(people(tracks), files, job.duration, names)
    # MTS Link меняет размер кадра внутри потока (1280×720 ↔ 640×360 ↔ 320×180). По умолчанию ffmpeg
    # на каждую смену пересобирает граф, источники color начинают с нуля и всё перерисовывается с начала
    # записи — на ИФР к 16-й минуте сборка вставала (28.09). scale сам принимает кадры любого размера.
    args = [a for f in inputs for a in ("-reinit_filter", "0", "-i", f)]
    if mix:
        args += ["-i", mix]
    args += ["-filter_complex", graph, "-map", "[out]"]
    if mix:
        args += ["-map", f"{len(inputs)}:a:0", "-c:a", "copy"]
    args += [*codec(), "-r", str(FPS), "-t", f"{job.duration:.3f}", "-movflags", "+faststart"]
    await _to_file(job, args, out, on_time, cwd=names)
