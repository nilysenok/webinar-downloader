"""Сверка блоков владельца: у каждого Ж-NNN в resheniya.md — строка-квитанция «принят Ж-NNN, ЧЧ:ММ» (§6.1, Ж-004 1.2).

Запуск: .venv/bin/python -m scripts.kanon.sverka_blokov [путь к resheniya.md]. Код 1 — есть блоки без квитанции.
"""
import re
import sys
from pathlib import Path

DEFAULT = Path("docs/resheniya/resheniya.md")


def bloki(text: str) -> list:
    """[(номер, есть ли квитанция, задним ли числом)] по порядку блоков."""
    parts = re.split(r"^(?=## Ж-\d{3})", text, flags=re.M)[1:]
    out = []
    for p in parts:
        n = re.match(r"## Ж-(\d{3})", p).group(1)
        r = re.search(rf"^принят Ж-{n}, .*$", p, re.M)
        out.append((n, bool(r), bool(r and "задним числом" in r.group(0))))
    return out


def main(argv) -> int:
    from downloader.osdeps import utf8_console  # внутри: функции модуля импортирует и хук, без downloader
    utf8_console()  # Windows: вывод в cp1252 падал на кириллице (CI 27.10)
    path = Path(argv[0]) if argv else DEFAULT
    if not path.exists():
        print(f"нет файла {path}")
        return 1
    b = bloki(path.read_text(encoding="utf-8"))
    bez = [n for n, ok, _ in b if not ok]
    print(f"блоков: {len(b)}")
    print(f"блоков без квитанции: {len(bez)}" + (f" — Ж-{', Ж-'.join(bez)}" if bez else ""))
    print(f"квитанций задним числом: {sum(z for *_, z in b)}")
    return 1 if bez else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
