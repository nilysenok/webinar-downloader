"""CLI: .venv/bin/python -m downloader.cli <ссылка record-new> [--mode audio|av|video] [--quality best|480] [--workers 64] [--no-gallery]

Для длинных загрузок — scripts/download.sh (то же самое под caffeinate).
"""
import argparse
import asyncio

from .config import DEFAULT_WORKERS, MODES
from .models import Job
from .pipeline import run


async def _watch(job: Job):
    task = asyncio.create_task(run(job))
    while not task.done():
        d = job.to_dict()
        print(f"\r{job.status:8} {d['progress']:6.1%}  {job.seg_done}/{job.seg_total} сегм.  "
              f"{job.bytes / 1e6:.0f} МБ  {d['speed'] / 1e3:.0f} КБ/с   ", end="", flush=True)
        await asyncio.sleep(1)
    print()


def main():
    ap = argparse.ArgumentParser(description="Скачать запись MTS Link")
    ap.add_argument("url")
    ap.add_argument("--mode", choices=list(MODES), default="audio")
    ap.add_argument("--quality", default="best")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-gallery", action="store_true", help="без общего экрана всех камер")
    a = ap.parse_args()
    job = Job(a.url, mode=a.mode, quality=a.quality, workers=a.workers, gallery=not a.no_gallery)
    asyncio.run(_watch(job))
    for line in job.log:
        if line["level"] != "info":
            print(f"[{line['level']}] {line['msg']}")
    for o in job.outputs:
        print(o["path"])
    if job.status != "done":
        raise SystemExit(job.error or job.status)


if __name__ == "__main__":
    main()
