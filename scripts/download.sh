#!/bin/bash
# Длинная загрузка из терминала без дашборда. Mac не уснёт, пока идёт загрузка (caffeinate -i).
# Пример: scripts/download.sh "https://my.mts-link.ru/j/…/record-new/…" --mode audio --workers 64
cd "$(dirname "$0")/.." || exit 1
exec caffeinate -i .venv/bin/python -m downloader.cli "$@"
