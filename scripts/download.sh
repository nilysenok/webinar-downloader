#!/bin/bash
# Длинная загрузка из терминала без дашборда (macOS, Linux). Компьютер не уснёт: об этом заботится сам CLI (osdeps.Awake).
# Пример: scripts/download.sh "https://my.mts-link.ru/j/…/record-new/…" --mode audio --workers 64
cd "$(dirname "$0")/.." || exit 1
exec .venv/bin/python -m downloader.cli "$@"
