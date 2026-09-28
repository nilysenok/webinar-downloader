"""Константы загрузчика: адреса MTS Link, сеть, режимы, раскладка папок."""
from pathlib import Path

import httpx

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
API = "https://my.mts-link.ru/api/eventsessions/{}/record?withoutCuts=false"

ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS = ROOT / "downloads"  # внутри — папка на каждую загрузку: ГГГГ-ММ-ДД_ЧЧММ <название>/
WORK_DIR = "_work"  # промежуточные файлы внутри папки загрузки

# Сервер режет ~11 КБ/с на соединение (замер 25.09), поэтому качаем во много потоков
DEFAULT_WORKERS = 64
MAX_WORKERS = 256
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
RETRIES = 6

MODES = {"audio": "Только аудио", "av": "Видео + аудио", "video": "Только видео"}
ACTIVE = {"queued", "meta", "download", "mix", "mux"}

# Доля общего прогресса, которую занимает каждый этап: (начало, вес)
WEIGHTS = {
    "audio": {"download": (0.02, 0.88), "mix": (0.90, 0.10)},
    "av": {"download": (0.02, 0.73), "mix": (0.75, 0.05), "mux": (0.80, 0.20)},  # mux включает общий экран
    "video": {"download": (0.02, 0.75), "mix": (0.77, 0.03), "mux": (0.80, 0.20)},
}
