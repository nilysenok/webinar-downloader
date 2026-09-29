"""Всё, что зависит от ОС (macOS, Windows, Linux): шрифт подписей, «не спать», показать файл в папке."""
import os
import shutil
import subprocess
import sys
from functools import cache
from pathlib import Path

_WIN_FONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONTS = {  # шрифты с кириллицей, по порядку предпочтения
    "darwin": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial Unicode.ttf"],
    "win32": [str(_WIN_FONTS / "arial.ttf"), str(_WIN_FONTS / "segoeui.ttf")],
    "linux": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
              "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/noto/NotoSans-Regular.ttf"],
}


def _os() -> str:
    return "linux" if sys.platform.startswith("linux") else sys.platform


@cache
def font() -> Path | None:
    """Шрифт для подписей на общем экране; None — подписей не будет, но видео соберётся."""
    for p in FONTS.get(_os(), []):
        if Path(p).is_file():
            return Path(p)
    if shutil.which("fc-match"):  # Linux/BSD: любой шрифт с кириллицей
        out = subprocess.run(["fc-match", "-f", "%{file}", "sans:lang=ru"], capture_output=True, text=True).stdout
        if out and Path(out).is_file():
            return Path(out)
    return None


@cache
def has_filter(name: str) -> bool:
    """Есть ли фильтр в этой сборке ffmpeg. Homebrew-ffmpeg 8+ собран без drawtext (подписи) — нужен ffmpeg-full."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return any(ln.split()[1:2] == [name] for ln in out.splitlines())


def filter_path(p: Path) -> str:
    """Путь для фильтра ffmpeg в одинарных кавычках: прямые слеши, двоеточие диска (C:) экранировано."""
    return p.as_posix().replace("'", r"'\''").replace(":", r"\:")


def utf8_console():
    """Вывод в UTF-8 на любой ОС. В Windows при перенаправленном выводе Python берёт cp1252,
    и первый же print с кириллицей роняет программу (CI 29.09: сервер падал при старте)."""
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")


class Awake:
    """Не даёт компьютеру уснуть, пока идёт загрузка (урок Hustle): start() / stop(), повторные вызовы безопасны."""
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001

    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.on = False

    def start(self):
        if self.on:
            return
        self.on = True
        if _os() == "win32":  # действует на поток, который вызвал; снимается stop() из того же потока
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED)
        elif _os() == "darwin" and shutil.which("caffeinate"):
            # -w: caffeinate завершится вместе с процессом, даже если тот упадёт
            self.proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        elif shutil.which("systemd-inhibit"):
            self.proc = subprocess.Popen(["systemd-inhibit", "--what=sleep:idle", "--who=webinar-downloader",
                                          "--why=Идёт загрузка записи", "--mode=block", "sleep", "infinity"],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if not self.on:
            return
        self.on = False
        if _os() == "win32":
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.proc = None


def reveal(path: Path):
    """Показать файл в файловом менеджере (с выделением, где ОС умеет), папку — открыть."""
    select = path.is_file()
    if _os() == "darwin":
        subprocess.run(["open", "-R", str(path)] if select else ["open", str(path)])
    elif _os() == "win32":
        subprocess.run(f'explorer /select,"{path}"' if select else f'explorer "{path}"')
    else:
        subprocess.run(["xdg-open", str(path.parent if select else path)])
