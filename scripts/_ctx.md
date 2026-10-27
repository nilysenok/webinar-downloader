# scripts
Слой: БЭКЕНД

## НАЗНАЧЕНИЕ
Окружение и запуск: venv, зависимости, двойной клик для дашборда, скрипты длинных прогонов под caffeinate,
сборщик канона и git.

## КОНТРАКТ
- `start.command` ставит `ffmpeg-full` (Homebrew, keg-only, с drawtext) первым в PATH, если он установлен; README для macOS советует `brew install ffmpeg-full`
- запуск: `start.command` (macOS, Finder), `start.bat` (Windows, Проводник; winget-подсказки, UTF-8 через chcp 65001), `start.sh` (Linux и macOS из терминала; apt/dnf-подсказки) — все создают `.venv`, ставят зависимости и открывают дашборд
- `.gitattributes`: `*.bat` — CRLF, `*.sh` / `*.command` — LF; CI `.github/workflows/tests.yml`: тесты на macOS, Windows, Ubuntu + запуск start.bat / start.sh с нуля до ответа дашборда
- `start.command` (корень) — двойной клик в Finder: найти рабочий Python 3.10+, создать `.venv`, поставить `requirements.txt`, поднять сервер, открыть браузер; если сервер уже жив — просто открыть
- `scripts/download.sh <ссылка> [--mode …]` — короткая форма CLI-загрузки (macOS, Linux); «не спать» делает сам CLI (`osdeps.Awake`), `caffeinate` в скрипте убран — в Linux его нет (13.10)
- `scripts/bench.py <ссылка> --secs 60 --workers 64,256 [--http2] [--ip A,B]` — замер скорости сегментов без записи на диск; `--http2` требует `pip install h2` (в requirements нет — HTTP/2 проигрывает)
- `requirements.txt`: fastapi, uvicorn, httpx; внешняя зависимость — `ffmpeg`/`ffprobe` (Homebrew)
- `xtask.py` + `tools/` — сборщик и валидатор канона; `tests/` — unittest
- `scripts/kanon/` — скрипты канона v24 (`python -m scripts.kanon.<имя>`): `sverka_blokov` — блоки владельца без квитанции в `docs/resheniya/resheniya.md` (код 1, если есть); `validate_zadanie <файл>…` — десять полей задания агенту (код 1 при отказе; его же зовёт хук перед запуском агента); вывод — через `utf8_console()` (Windows cp1252, CI 27.10); тесты — `tests/test_kanon.py`
- `scripts/asr/` — замер распознавания речи (этап 9): `setup.sh` (whisper-cpp, `.venv-asr` с mlx-whisper, модели в `~/.cache`) → `tracks.sh <ссылка>` → `vad.py` → `run_cpp.sh` / `run_mlx.py` → `merge.py cpp|mlx` → `score.py cpp mlx`; `etalon.py` и `diff10.py` не перезаписывают выверенное без `--force`; `etalon2.py cpp embC300` — слепой эталон 7×2 мин (27.09): черновик из двух движков, расхождения «[x / y]» в случайном порядке, ключ в `etalon/.key.json`; `score.py` не считает, пока в эталоне есть невыбранные скобки; всё одной строкой — `run_all.sh <ссылка>`
- git: публичный GitHub `nilysenok/webinar-downloader` (origin, push после каждой сессии; старый адрес mts-link-downloader перенаправляется); в git не идут `.venv/`, `downloads/`, `tracks/`, `history.json`

## ИНВАРИАНТЫ
- Python для проекта — только `.venv/bin/python` (3.12); исключение — `.venv-asr/` только для mlx-whisper (тянет torch)
- модели и всё долгоживущее — в `~/.cache`, результаты — в `downloads/`; временная папка сессии — не хранилище
- настоящие стенограммы, звук и эталон — только в `downloads/asr/` (персональные данные); в тестах — только «Спикер N»
- всё, что должно выполниться без человека, — одной строкой в `scripts/*.sh`

## СТАТУС
в работе

## ЗАДАЧИ
- [ ] бэкап `downloads/` на второй носитель (урок Hustle: диск без копии — не диск) — куда? см. ОТКРЫТО

## ТЕХДОЛГ
- клиент Hugging Face (`snapshot_download`) завис на 1,23 из 1,61 ГБ (26.09) — `setup.sh` качает через `curl -C -` с проверкой sha256
- Homebrew `python@3.13` 3.13.7 сломан: бинарник `python3.13` — пустой файл 0 байт, `python3` молча ничего не делает (25.09). Лечится `brew reinstall python@3.13`; проект живёт на 3.12, поэтому не чиним
- `caffeinate -i` не спасает от сна при закрытой крышке — крышку во время длинной загрузки не закрывать
- зависимости в `requirements.txt` без верхних границ: CI ставит свежие версии и может покраснеть без изменений в коде; starlette уже предупреждает, что `TestClient` поверх httpx устарел (13.10, fastapi 0.141 / starlette 1.7)

## ПЕЧАТИ
Ъ — сборщик канона: `python xtask.py`, валидатор `python xtask.py --check` (вместо cargo xtask) (25.09)
Ъ — репозиторий публичный, `nilysenok/webinar-downloader`, MIT, со всей историей: владелец выбрал открыть текущий, зная, что в старых коммитах имена участников, ссылки на записи и прежний файл правил; в текущих файлах имён нет (29.09)
Ъ — в git не попадают записи, расшифровки, история загрузок и имена участников настоящих вебинаров: всё это в `downloads/` и `history.json` (в .gitignore); в тестах и снимках — только вымышленные (29.09)

## ЖДУНЫ
—

## ОТКРЫТО
❓ куда копировать `downloads/` для бэкапа (второй диск / облако) и нужно ли вообще
❓ в `pravila.md` и `spec.md` — ссылка и id настоящей открытой записи (18 участников): репозиторий публичный, скачать её может любой; печать 29.09 говорит про записи и имена, про ссылки в текущих файлах — нет. Оставить или заменить на «ссылка у владельца»? (13.10)
❓ ветки `archive/gallery-toggle-28.09` и `archive/ui-simplify-28.09` есть только в локальной копии: на GitHub одна `main` (`git ls-remote`, 13.10), хотя запись в архиве 29.09 говорит «сохранена в origin». Отправить в публичный репо или оставить локально?

## НЕ ТРОГАТЬ
- `start.command`: перебор `python3.12 → … → python3` с проверкой `print(...)` — голый `python3` на этой машине битый и молчит
- дашборд, поднятый из фонового процесса (не из своего окна Терминала), умирает вместе с ним (29.09: «Failed to fetch» в UI) — поднимать через `open start.command`, свой Терминал; лимит файлов там 256, его поднимает сам загрузчик
