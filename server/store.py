"""Реестр задач сервера: history.json, запуск в фоне, автосохранение, «не спать» во время загрузок."""
import asyncio
import json
import time
from pathlib import Path

from downloader import ACTIVE, Job, run
from downloader.config import ROOT
from downloader.osdeps import Awake

HISTORY = ROOT / "history.json"

jobs: dict[str, Job] = {}
tasks: dict[str, asyncio.Task] = {}
_sizes: dict[str, tuple[float, int]] = {}
_awake = Awake()


def save():
    data = [j.to_dict() for j in jobs.values()]
    tmp = HISTORY.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(HISTORY)


def load():
    if not HISTORY.exists():
        return
    for d in json.loads(HISTORY.read_text(encoding="utf-8")):
        job = Job.from_dict(d)
        if job.status in ACTIVE:
            job.status = "interrupted"
            job.error = "Сервер был остановлен во время загрузки"
            job.add_log("warn", job.error + " — перезапуск продолжит с места остановки")
        jobs[job.id] = job


def any_active() -> bool:
    return any(j.status in ACTIVE for j in jobs.values())


def keep_awake():
    """Пока идёт хоть одна загрузка, компьютер не уснёт (урок Hustle); как — решает osdeps.Awake по ОС."""
    _awake.start() if any_active() else _awake.stop()


def work_size(job: Job) -> int:
    """Размер _work/ загрузки (кэш 15 с — в ней тысячи сегментов)."""
    if job.status in ACTIVE or not job.work or not job.work.exists():
        return 0
    key = str(job.work)
    cached = _sizes.get(key)
    if cached and time.monotonic() - cached[0] < 15:
        return cached[1]
    size = sum(f.stat().st_size for f in job.work.rglob("*") if f.is_file())
    _sizes[key] = (time.monotonic(), size)
    return size


def forget_size(job: Job):
    _sizes.pop(str(job.work), None)


def launch(job: Job):
    """(Пере)запуск задачи в фоне. Перезапуск идёт в ту же папку — скачанные сегменты не качаются заново."""
    job.reset()
    jobs[job.id] = job

    async def runner():
        await run(job)
        forget_size(job)
        save()
        keep_awake()

    tasks[job.id] = asyncio.create_task(runner())
    keep_awake()
    save()


async def autosave():
    while True:
        await asyncio.sleep(2)
        if any_active():
            await asyncio.to_thread(save)


def shutdown():
    for j in jobs.values():
        if j.status in ACTIVE:
            j.cancel = True
    save()
    _awake.stop()


def outputs_with_state(job: Job) -> dict:
    d = job.to_dict()
    for o in d["outputs"]:
        o["exists"] = Path(o["path"]).exists()
    d["work_size"] = work_size(job)
    return d
