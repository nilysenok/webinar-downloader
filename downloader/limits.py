"""Лимит открытых файлов процесса.

macOS даёт всему, что запущено из Finder или Терминала, мягкий лимит 256 (`launchctl limit maxfiles`).
256 потоков загрузки держат 256 сокетов и столько же `.part`-файлов — без подъёма загрузка падает
с `Too many open files` (29.09). Жёсткий лимит — unlimited, мягкий поднимается без прав.
"""
import resource

WANT = 10240  # OPEN_MAX на macOS: выше setrlimit откажет


def raise_open_files(want: int = WANT) -> int:
    """Поднимает мягкий лимит до want (не выше жёсткого) и возвращает итоговый мягкий лимит."""
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target = want if hard == resource.RLIM_INFINITY else min(want, hard)
    if soft == resource.RLIM_INFINITY or soft >= target:
        return soft
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    except (ValueError, OSError):
        return soft
    return target


def enough_for(workers: int) -> int:
    """Сколько файлов нужно задаче: сокет и `.part` на поток плюс запас на ffmpeg и сервер."""
    return 2 * workers + 128
