"""Кадр общего экрана на одном отрезке: сетка плиток, видео, имена, рамка говорящего.

Пути к подписям — относительные (ffmpeg запускается в папке подписей): в граф не попадает путь
загрузки, где могут быть кавычки и двоеточия.
"""
import math

from .osdeps import filter_path, font

W, H, FPS = 1280, 720, 25
BG, TILE, TALK, GAP = "0x111111", "0x262626", "0x2fd26b", 4


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


def text(textfile: str, size: int, center: bool) -> str:
    """Подпись: снизу слева, если есть видео; крупно по центру — у плитки без камеры и на заставке."""
    if not (f := font()):  # нет шрифта с кириллицей — без подписей, но видео соберётся
        return "null"
    where = "x=(w-tw)/2:y=(h-th)/2" if center else "x=12:y=h-th-12"
    return (f"drawtext=fontfile='{filter_path(f)}':textfile={textfile}:expansion=none:fontsize={size}:fontcolor=white"
            f":box=1:boxcolor=black@0.55:boxborderw={max(6, size // 5)}:{where}")


def _border(spans, t0: float, h: int) -> str:
    """Зелёная рамка, пока человек говорит; время — от начала отрезка."""
    when = "+".join(f"between(t,{a - t0:.2f},{b - t0:.2f})" for a, b in spans)
    return f",drawbox=x=0:y=0:w=iw:h=ih:color={TALK}:t={max(4, h // 90)}:enable='{when}'" if when else ""


def graph(seg, sessions, labels):
    """(входы [(путь, с какой секунды, сколько)], filter_complex) отрезка seg.

    sessions: {имя: [(начало, конец, путь к видео)]} на шкале записи; labels: {имя: файл подписи}.
    """
    t0, dur = seg.t0, seg.t1 - seg.t0
    d = f"{dur:.3f}"
    parts, inputs, last = [f"color=c={BG}:s={W}x{H}:r={FPS}:d={d}[bg]"], [], "bg"
    if not seg.who:
        parts.append(f"[bg]{text('title.txt', 40, True)},format=yuv420p[out]")
        return inputs, ";".join(parts)
    for p, (who, (x, y, w, h)) in enumerate(zip(seg.who, grid(len(seg.who)))):
        cur = f"t{p}"
        parts.append(f"color=c={TILE}:s={w}x{h}:r={FPS}:d={d}[{cur}]")
        seen = False
        for a, b, path in sessions.get(who, ()):
            lo, hi = max(a, t0), min(b, seg.t1)
            if hi - lo < 0.05:
                continue
            k, seen = len(inputs), True
            inputs.append((path, lo - a, hi - lo))
            parts.append(f"[{k}:v]setpts=PTS-STARTPTS+{lo - t0:.3f}/TB,"
                         f"scale={w}:{h}:force_original_aspect_ratio=decrease[v{k}]")
            parts.append(f"[{cur}][v{k}]overlay=x=(W-w)/2:y=(H-h)/2:eof_action=pass[t{p}_{k}]")
            cur = f"t{p}_{k}"
        size = max(12, h // 14) if seen else max(16, h // 7)
        parts.append(f"[{cur}]{text(labels[who], size, not seen)}{_border(seg.talk.get(who, ()), t0, h)}[p{p}]")
        parts.append(f"[{last}][p{p}]overlay=x={x}:y={y}[g{p}]")
        last = f"g{p}"
    parts.append(f"[{last}]format=yuv420p[out]")
    return inputs, ";".join(parts)
