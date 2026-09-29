#!/bin/bash
# Двойной клик в Finder: поднимает локальный сервер и открывает дашборд в браузере.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
# ffmpeg-full (с drawtext — имена на общем экране) Homebrew не кладёт в PATH — берём его первым, если он есть
for d in /opt/homebrew/opt/ffmpeg-full/bin /usr/local/opt/ffmpeg-full/bin; do [ -x "$d/ffmpeg" ] && PATH="$d:$PATH"; done
PORT="${PORT:-8765}"
URL="http://127.0.0.1:$PORT"

if curl -s -o /dev/null --max-time 1 "$URL/api/jobs"; then
  echo "Сервер уже запущен: $URL"
  open "$URL"
  exit 0
fi

if ! command -v ffmpeg >/dev/null; then
  echo "Не найден ffmpeg. Установите: brew install ffmpeg"
  read -r -p "Enter — закрыть"
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  # Берём первый реально работающий Python 3.10+ (у Homebrew-овского python3 бывает битый бинарник)
  for p in python3.12 python3.13 python3.11 python3.10 python3; do
    if [ "$(command -v "$p" >/dev/null && "$p" -c 'import sys; print(sys.version_info >= (3, 10))' 2>/dev/null)" = "True" ]; then
      PY="$p"; break
    fi
  done
  if [ -z "$PY" ]; then
    echo "Не найден рабочий Python 3.10+. Установите: brew install python@3.12"
    read -r -p "Enter — закрыть"
    exit 1
  fi
  echo "Создаю окружение ($PY)…"
  "$PY" -m venv .venv || exit 1
fi

if [ ! -f .venv/.deps-ok ] || [ requirements.txt -nt .venv/.deps-ok ]; then
  echo "Ставлю зависимости…"
  .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt && touch .venv/.deps-ok || exit 1
fi

(for _ in $(seq 1 40); do
  curl -s -o /dev/null --max-time 1 "$URL/api/jobs" && { open "$URL"; exit; }
  sleep 0.25
done) &

echo "Дашборд: $URL — не закрывайте это окно, пока идут загрузки."
exec .venv/bin/python -m server.app
