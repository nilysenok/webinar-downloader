"""Кадр общего экрана на одном отрезке: сетка плиток, видео, имена, рамка говорящего, слайд.

Пути к подписям — относительные (ffmpeg запускается в папке подписей): в граф не попадает путь
загрузки, где могут быть кавычки и двоеточия.
"""
import math

from .osdeps import filter_path, font, has_filter

W, H, FPS = 1280, 720, 25
BG, TILE, TALK, GAP = "0x111111", "0x262626", "0x2fd26b", 4
SIDE = 320  # полоса камер справа, пока показывают файл: слайд крупно, как в Zoom


def grid(n: int, box=(0, 0, W, H), cols=0):
    """Плитки 16:9 (x, y, w, h) в рамке box: столбцов ⌈√n⌉, неполный последний ряд — по центру, как в Zoom."""
    bx, by, bw, bh = box
    cols = cols or math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    tw = min(bw // cols, bh // rows * 16 // 9)
    th = tw * 9 // 16
    y0 = by + (bh - rows * th) // 2
    cells = []
    for i in range(n):
        r, c = divmod(i, cols)
        x0 = bx + (bw - min(cols, n - r * cols) * tw) // 2
        cells.append((x0 + c * tw + GAP // 2, y0 + r * th + GAP // 2, (tw - GAP) // 2 * 2, (th - GAP) // 2 * 2))
    return cells


def text(textfile: str, size: int, center: bool) -> str:
    """Подпись: снизу слева, если есть видео; крупно по центру — у плитки без камеры и на заставке."""
    # нет шрифта с кириллицей или ffmpeg собран без drawtext — без подписей, но видео соберётся
    if not (f := font()) or not has_filter("drawtext"):
        return "null"
    where = "x=(w-tw)/2:y=(h-th)/2" if center else "x=12:y=h-th-12"
    return (f"drawtext=fontfile='{filter_path(f)}':textfile={textfile}:expansion=none:fontsize={size}:fontcolor=white"
            f":box=1:boxcolor=black@0.55:boxborderw={max(6, size // 5)}:{where}")


def _any_of(terms: list) -> str:
    """Сумма условий деревом в скобках: ((a+b)+(c+d)), а не цепочкой a+b+c+d.

    FFmpeg с 8.1 не принимает выражение глубже 100, а цепочка из N слагаемых — это глубина N:
    на отрезке, где человек говорил больше 100 раз, сборка падала «Cannot allocate memory» (13.10).
    """
    if len(terms) == 1:
        return terms[0]
    mid = len(terms) // 2
    return f"({_any_of(terms[:mid])}+{_any_of(terms[mid:])})"


def _border(spans, t0: float, h: int) -> str:
    """Зелёная рамка, пока человек говорит; время — от начала отрезка."""
    terms = [f"between(t,{a - t0:.2f},{b - t0:.2f})" for a, b in spans]
    return f",drawbox=x=0:y=0:w=iw:h=ih:color={TALK}:t={max(4, h // 90)}:enable='{_any_of(terms)}'" if terms else ""


def _slide(seg, inputs, parts, d) -> str:
    """Слайд на фоне: на весь кадр или слева от полосы камер. Картинка — 1 кадр/с: overlay держит последний."""
    k, sw = len(inputs), W - SIDE if seg.who else W
    inputs.append((seg.slide, None, float(d)))
    parts.append(f"[{k}:v]scale={sw}:{H}:force_original_aspect_ratio=decrease,setsar=1[s{k}]")
    parts.append(f"[bg][s{k}]overlay=x=({sw}-w)/2:y=({H}-h)/2[sl]")
    return "sl"


def graph(seg, sessions, labels):
    """(входы [(путь, с какой секунды или None у картинки, сколько)], filter_complex) отрезка seg.

    sessions: {имя: [(начало, конец, путь к видео)]} на шкале записи; labels: {имя: файл подписи}.
    """
    t0, dur = seg.t0, seg.t1 - seg.t0
    d = f"{dur:.3f}"
    parts, inputs, last = [f"color=c={BG}:s={W}x{H}:r={FPS}:d={d}[bg]"], [], "bg"
    if not seg.who and not seg.slide:
        parts.append(f"[bg]{text('title.txt', 40, True)},format=yuv420p[out]")
        return inputs, ";".join(parts)
    n, cells = len(seg.who), []
    if seg.slide:
        last = _slide(seg, inputs, parts, d)
        cells = grid(n, (W - SIDE, 0, SIDE, H), math.ceil(n / 4)) if n else []
    elif n:
        cells = grid(n)
    for p, (who, (x, y, w, h)) in enumerate(zip(seg.who, cells)):
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
