# MTS Link загрузчик

Локальный инструмент: скачать запись вебинара MTS Link (только аудио / видео + аудио / только видео)
через дашборд в браузере или CLI. Проект ведётся по системе КАНОН — `KANON_kak_my_vedem_proekty.md`.

## Начало сессии
Читать по порядку: `pravila.md` → `spec.md` → `ROOT.md` → `_ctx.md` нужного модуля.
Разделы НЕ ТРОГАТЬ и ПЕЧАТИ (`Ъ —`) — запреты. Печать не пересматривается без явной команды владельца.

## Модули
- `downloader/` — БЭКЕНД: API MTS Link, HLS, загрузка сегментов, ffmpeg
- `server/` — БЭКЕНД: FastAPI, фоновые задачи, history.json, caffeinate
- `ui/` — ФРОНТЕНД: интерфейс загрузчика (ES-модули, без сборки)
- `scripts/` — БЭКЕНД: окружение и запуск (start.command, scripts/*.sh, venv)
- `rust-core/`, `rust-cli/`, `rust-server/` — БЭКЕНД, `rust-ui/` — ФРОНТЕНД: канон публичного Rust-проекта
  `../webinarip/` (github nilysenok/webinarip, MIT). Код там, здесь только `_ctx.md`.
  В публичный репо не попадает ничего отсюда; никаких упоминаний ИИ, автор — Nikita Lysenok.

## Команды
- Python только из venv: `.venv/bin/python` (системный `python3` из Homebrew сломан — см. scripts/_ctx.md)
- Сборка канона: `.venv/bin/python xtask.py` → ROOT.md, dashboard.json, dashboard.html
- Валидатор + тесты (CI): `.venv/bin/python xtask.py --check` — должен быть ЗЕЛЁНЫЙ
- Только тесты: `.venv/bin/python -m unittest discover -s tests`
- Дашборд загрузчика: `./start.command` (двойной клик в Finder) → http://127.0.0.1:8765
- Длинная загрузка из терминала: `scripts/download.sh "<ссылка>" --mode audio`
- webinarip: `cd ../webinarip && cargo test --release && cargo build --release` → `target/release/webinarip`

## По ходу
- Одна сессия — один модуль. Сначала план, потом код. Тесты обязательны.
- Файл кода ≤ 200 строк (включая HTML/CSS/JS), функция ≤ ~40. Разрослось — делим.
- Нашёл баг или принял решение — сразу в `_ctx.md` модуля, не «потом».
- Неизвестное — `❓` в ОТКРЫТО, не догадка. Спорный факт — с источником: `(замер 25.09)`.
- `dashboard.html` и `ROOT.md` руками не править — только md + `xtask.py`.
- `ui/index.html` — интерфейс загрузчика; `dashboard.html` в корне — дашборд канона. Не путать.
- Реальная запись для проверок: `https://my.mts-link.ru/j/77749939/25113361522/record-new/24554640907`
  (открытая, 85 мин, 18 медиасессий). Проверочные загрузки — на отдельном порту: `PORT=8799`.

## Конец сессии
1. Обновить `_ctx.md` затронутых модулей.
2. Закрытое — строкой в `arhiv.md` (`ДД.ММ · [модуль] · что`), решения — печатями, вопросы — в ОТКРЫТО.
3. `.venv/bin/python xtask.py`, затем `--check` зелёный.
4. Коммит, рабочая копия чистая. Push в `origin` (публичный GitHub `webinar-downloader` — всё, что в git, видно всем).
