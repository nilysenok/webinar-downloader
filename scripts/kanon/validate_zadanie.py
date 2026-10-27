"""Валидатор задания агенту (Ж-004 2.2): десять полей шаблона на месте и заполнены.

Запуск: .venv/bin/python -m scripts.kanon.validate_zadanie <файл>... Код 1 — хоть одно задание не прошло.
Поле 10 «Уверенность» заполняет агент, поэтому перед запуском допускается заглушка.
"""
import re
import sys
from pathlib import Path

FIELDS = ["Blok", "Цель", "Владение", "Запрещено читать", "Входы", "Гейты", "Пять вопросов", "Лимиты", "Формат отчёта",
          "Уверенность"]
QUESTIONS = ["готово", "Чем проверить", "можно трогать", "остановит", "подписывает"]


def sections(text: str) -> dict:
    parts = re.split(r"^## (\d+)\. (.+)$", text, flags=re.M)
    return {parts[i + 1].strip(): parts[i + 2] for i in range(1, len(parts) - 2, 3)}


def filled(body: str) -> bool:
    """Есть содержание и не осталось ни одной заглушки шаблона <…>."""
    text = "\n".join(ln for ln in body.splitlines() if not ln.startswith("#"))
    return bool(text.strip()) and not re.search(r"<[^<>\n]+>", text)


def problems(text: str) -> list:
    s, out = sections(text), []
    for name in FIELDS:
        if name not in s:
            out.append(f"нет поля «{name}»")
        elif name != "Уверенность" and not filled(s[name]):
            out.append(f"поле «{name}» пустое (заглушка шаблона)")
    if "Blok" in s and not re.search(r"Ж-\d{3}", s["Blok"]):
        out.append("в «Blok» нет номера Ж-NNN")
    if "Входы" in s and filled(s["Входы"]) and not re.search(r"sha256 [0-9a-f]{16,64}", s["Входы"]):
        out.append("у входов нет sha256")
    if "Цель" in s and "### План" not in s["Цель"]:
        out.append("в «Цель» нет отдельного «### План»")
    if "Пять вопросов" in s:
        out += [f"нет вопроса «{q}»" for q in QUESTIONS if q not in s["Пять вопросов"]]
    return out


def main(argv) -> int:
    from downloader.osdeps import utf8_console  # внутри: функции модуля импортирует и хук, без downloader
    utf8_console()  # Windows: вывод в cp1252 падал на кириллице (CI 27.10)
    bad = 0
    for f in argv:
        errs = problems(Path(f).read_text(encoding="utf-8"))
        print(f"{f}: " + ("ok" if not errs else "ОТКАЗ — " + "; ".join(errs)))
        bad += bool(errs)
    return 1 if bad or not argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
