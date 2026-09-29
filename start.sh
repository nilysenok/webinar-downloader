#!/bin/bash
# Linux (и macOS из терминала): поднимает локальный сервер и открывает дашборд в браузере.
# Запуск: ./start.sh   (или двойной клик в файловом менеджере с «запустить в терминале»)
cd "$(dirname "$0")" || exit 1
PORT="${PORT:-8765}"
URL="http://127.0.0.1:$PORT"
open_url() { command -v xdg-open >/dev/null && xdg-open "$1" >/dev/null 2>&1 || open "$1" 2>/dev/null || echo "Откройте $1"; }

if curl -s -o /dev/null --max-time 1 "$URL/api/jobs"; then
  echo "Сервер уже запущен: $URL"
  open_url "$URL"
  exit 0
fi

if ! command -v ffmpeg >/dev/null; then
  echo "Не найден ffmpeg. Установите: sudo apt install ffmpeg   (Fedora: sudo dnf install ffmpeg)"
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  for p in python3.13 python3.12 python3.11 python3.10 python3; do
    if [ "$(command -v "$p" >/dev/null && "$p" -c 'import sys; print(sys.version_info >= (3, 10))' 2>/dev/null)" = "True" ]; then
      PY="$p"; break
    fi
  done
  if [ -z "$PY" ]; then
    echo "Не найден Python 3.10+. Установите: sudo apt install python3 python3-venv"
    exit 1
  fi
  echo "Создаю окружение ($PY)…"
  "$PY" -m venv .venv || { echo "Не создалось окружение. На Debian/Ubuntu: sudo apt install python3-venv"; exit 1; }
fi

if [ ! -f .venv/.deps-ok ] || [ requirements.txt -nt .venv/.deps-ok ]; then
  echo "Ставлю зависимости…"
  .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt && touch .venv/.deps-ok || exit 1
fi

(for _ in $(seq 1 40); do
  curl -s -o /dev/null --max-time 1 "$URL/api/jobs" && { open_url "$URL"; exit; }
  sleep 0.25
done) &

echo "Дашборд: $URL — не закрывайте это окно, пока идут загрузки."
exec .venv/bin/python -m server.app
