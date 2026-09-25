# scripts
Слой: БЭКЕНД

## НАЗНАЧЕНИЕ
Окружение и запуск: venv, зависимости, двойной клик для дашборда, скрипты длинных прогонов под caffeinate,
сборщик канона и git.

## КОНТРАКТ
- `start.command` (корень) — двойной клик в Finder: найти рабочий Python 3.10+, создать `.venv`, поставить `requirements.txt`, поднять сервер, открыть браузер; если сервер уже жив — просто открыть
- `scripts/download.sh <ссылка> [--mode …]` — CLI-загрузка под `caffeinate -i`
- `scripts/bench.py <ссылка> --secs 60 --workers 64,256 [--http2] [--ip A,B]` — замер скорости сегментов без записи на диск; `--http2` требует `pip install h2` (в requirements нет — HTTP/2 проигрывает)
- `requirements.txt`: fastapi, uvicorn, httpx; внешняя зависимость — `ffmpeg`/`ffprobe` (Homebrew)
- `xtask.py` + `tools/` — сборщик и валидатор канона; `tests/` — unittest
- git: приватный GitHub `mts-link-downloader`; в git не идут `.venv/`, `downloads/`, `tracks/`, `history.json`

## ИНВАРИАНТЫ
- Python для проекта — только `.venv/bin/python` (3.12)
- всё, что должно выполниться без человека, — одной строкой в `scripts/*.sh`

## СТАТУС
в работе

## ЗАДАЧИ
- [ ] бэкап `downloads/` на второй носитель (урок Hustle: диск без копии — не диск) — куда? см. ОТКРЫТО

## ТЕХДОЛГ
- Homebrew `python@3.13` 3.13.7 сломан: бинарник `python3.13` — пустой файл 0 байт, `python3` молча ничего не делает (25.09). Лечится `brew reinstall python@3.13`; проект живёт на 3.12, поэтому не чиним
- `caffeinate -i` не спасает от сна при закрытой крышке — крышку во время длинной загрузки не закрывать

## ПЕЧАТИ
Ъ — сборщик канона: `python xtask.py`, валидатор `python xtask.py --check` (вместо cargo xtask) (25.09)
Ъ — репозиторий: приватный GitHub `mts-link-downloader` (25.09)

## ЖДУНЫ
⏳ владелец → `gh auth login` на этой машине (в ~/.config/gh пусто), чтобы создать приватный репо и сделать push, с 25.09

## ОТКРЫТО
❓ куда копировать `downloads/` для бэкапа (второй диск / облако) и нужно ли вообще

## НЕ ТРОГАТЬ
- `start.command`: перебор `python3.12 → … → python3` с проверкой `print(...)` — голый `python3` на этой машине битый и молчит
