# MTS Link Загрузчик

Скачивает запись вебинара MTS Link по ссылке: **звук** всех участников одним MP3 или **видео** — все камеры на одном экране, со звуком. Работает локально на macOS, Windows и Linux: дашборд в браузере или команда в терминале.

![Главный экран](docs/screenshots/01-main.png)

| Вставил ссылку — видно, что за запись | Подробнее — участники на шкале |
|---|---|
| ![](docs/screenshots/02-link.png) | ![](docs/screenshots/03-details.png) |
| **Тёмная тема** | **На телефоне** |
| ![](docs/screenshots/04-dark.png) | ![](docs/screenshots/05-phone.png) |

Только для записей, к которым у вас есть права.

## Установка и запуск

Нужны **ffmpeg** и **Python 3.10+**. Всё остальное скрипт запуска поставит сам: при первом запуске создаст окружение `.venv` и установит зависимости из `requirements.txt`.

### macOS

```bash
brew install ffmpeg-full python@3.12     # Homebrew: https://brew.sh
git clone https://github.com/nilysenok/webinar-downloader.git
```

Запуск — двойной клик по **`start.command`** в Finder (или `./start.command` в Терминале).

Почему `ffmpeg-full`, а не `ffmpeg`: обычный ffmpeg из Homebrew (с версии 8) собран без фильтра подписей, и на общем экране не будет имён участников. Видео соберётся и с ним, просто без имён. `start.command` находит `ffmpeg-full` сам; для работы из терминала добавьте его в PATH: `echo 'export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"' >> ~/.zshrc`.

### Windows 10/11

В PowerShell или командной строке:

```powershell
winget install Gyan.FFmpeg Python.Python.3.12 Git.Git
git clone https://github.com/nilysenok/webinar-downloader.git
```

После `winget` закройте и заново откройте окно, чтобы подхватились новые программы. Запуск — двойной клик по **`start.bat`** в Проводнике. Если Windows спросит про доступ в сеть, достаточно разрешить частные сети: сервер слушает только этот компьютер (`127.0.0.1`).

### Linux (Ubuntu, Debian, Mint; Fedora — через `dnf`)

```bash
sudo apt install ffmpeg python3 python3-venv git fonts-dejavu-core
git clone https://github.com/nilysenok/webinar-downloader.git
cd webinar-downloader && ./start.sh
```

### Дальше одинаково на всех системах

Откроется окно терминала с сервером и дашборд в браузере: <http://127.0.0.1:8765>.

1. Вставьте ссылку на запись вида `https://my.mts-link.ru/j/…/record-new/…` — под полем появится название, длительность и сколько участников и камер.
2. Выберите **Аудио** (MP3) или **Видео** (MP4, все камеры на одном экране).
3. Нажмите **Скачать**. Готовый файл — кнопкой «Смотреть» / «Слушать» или кнопкой папки рядом.

Окно терминала с сервером не закрывайте, пока идут загрузки: закроете — сервер остановится. Пока идёт загрузка, компьютер не уснёт (macOS — `caffeinate`, Windows — системный запрет сна, Linux — `systemd-inhibit`).

Файлы складываются в `downloads/ГГГГ-ММ-ДД_ЧЧММ <название>/`. Промежуточные куски — в `_work/` внутри той же папки; они нужны для докачки после обрыва и удаляются кнопкой «Удалить промежуточные» в «Подробнее».

Поставить окружение вручную, без скрипта запуска:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt       # Windows: .venv\Scripts\pip install -r requirements.txt
.venv/bin/python -m server.app                  # Windows: .venv\Scripts\python -m server.app
```

## Из терминала

В Windows вместо `.venv/bin/python` — `.venv\Scripts\python`.

```bash
# звук одним MP3
.venv/bin/python -m downloader.cli "https://my.mts-link.ru/j/…/record-new/…" --mode audio

# видео: один MP4 «общий экран» со звуком
.venv/bin/python -m downloader.cli "<ссылка>" --mode av

# видео каждой камеры отдельными файлами вместо общего экрана
.venv/bin/python -m downloader.cli "<ссылка>" --mode av --no-gallery
```

Параметры: `--mode audio|av|video`, `--quality best|480`, `--workers 64` (до 256), `--no-gallery`.

Компьютер не уснёт до конца загрузки. На macOS и Linux есть короткая форма — `scripts/download.sh` с теми же параметрами:

```bash
scripts/download.sh "<ссылка>" --mode audio
```

## Обновление

```bash
git pull
```

Затем перезапустите скрипт запуска (`start.command`, `start.bat` или `start.sh`) и обновите страницу. Новые зависимости он доставит сам.

## Если что-то не так

| Что видно | Что сделать |
|---|---|
| В дашборде «Сервер недоступен» | Сервер не запущен — запустите `start.command` / `start.bat` / `start.sh` и не закрывайте его окно |
| «Не найден ffmpeg» | macOS: `brew install ffmpeg` · Windows: `winget install Gyan.FFmpeg` · Linux: `sudo apt install ffmpeg` |
| «Не найден Python 3.10+» | macOS: `brew install python@3.12` · Windows: `winget install Python.Python.3.12` · Linux: `sudo apt install python3 python3-venv` |
| На общем экране нет имён | macOS: `brew install ffmpeg-full` (обычный ffmpeg из Homebrew без подписей) · Linux: нет шрифта с кириллицей — `sudo apt install fonts-dejavu-core` |
| Загрузка оборвалась | «Продолжить» в строке загрузки — докачает с места остановки |
| Интерфейс выглядит странно после обновления | Обновите страницу с Cmd+Shift+R |
| Отдельные видео камер не открываются в плеере | Это VP9 — откройте в браузере или VLC; «общий экран» (H.264) открывается везде |

## webinarip — быстрая версия на Rust

Отдельная открытая программа того же автора: один файл без Python, звук за секунды, видео участников, таймлайн для монтажа. Репозиторий: <https://github.com/nilysenok/webinarip>.

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/nilysenok/webinarip/releases/latest/download/webinarip-installer.sh | sh
webinarip "<ссылка>"            # звук
webinarip "<ссылка>" --video    # видео участников
webinarip serve                 # веб-интерфейс
```

## Распознавание речи (по желанию)

Для экспериментов со стенограммой — отдельное окружение `.venv-asr` и модели Whisper (~2 ГБ в `~/.cache`):

```bash
scripts/asr/setup.sh
```

Для обычной загрузки звука и видео не нужно.

## Разработка

```bash
.venv/bin/python -m unittest discover -s tests   # тесты
.venv/bin/python xtask.py --check                # тесты + проверка документации
.venv/bin/python xtask.py                        # пересобрать ROOT.md и dashboard.html
```

Устройство проекта описано в md-файлах рядом с кодом: `pravila.md` — правила работы, `spec.md` — словарь и лимиты, `<модуль>/_ctx.md` — всё о модуле, `ROOT.md` и `dashboard.html` — сводка (собирается `xtask.py`, руками не правится). Модули: `downloader/` — загрузка и сборка файлов, `server/` — сервер дашборда, `ui/` — интерфейс, `scripts/` — запуск и окружение.

## Автор и лицензия

Nikita Lysenok · [MIT](LICENSE)
