"""HTTP API дашборда загрузок + раздача ui/. Запуск: ./start.command (или .venv/bin/python -m server.app)."""
import asyncio
import os
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import downloader
from downloader import ACTIVE, DOWNLOADS, MODES, Job
from downloader.config import ROOT, TIMEOUT, UA

from . import store

PORT = int(os.environ.get("PORT", 8765))


@asynccontextmanager
async def lifespan(_):
    store.load()
    saver = asyncio.create_task(store.autosave())
    yield
    saver.cancel()
    store.shutdown()


app = FastAPI(lifespan=lifespan)


class UrlIn(BaseModel):
    url: str


class JobIn(BaseModel):
    url: str
    mode: str = "audio"
    quality: str = "best"
    streams: list[int] = []
    workers: int = downloader.DEFAULT_WORKERS


def get(job_id: str) -> Job:
    if job_id not in store.jobs:
        raise HTTPException(404, "Задача не найдена")
    return store.jobs[job_id]


@app.post("/api/analyze")
async def analyze(body: UrlIn):
    try:
        async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=TIMEOUT, follow_redirects=True) as client:
            info = await downloader.analyze(client, body.url.strip())
    except Exception as e:
        raise HTTPException(400, str(e) or type(e).__name__)
    info["tracks"] = [
        {k: getattr(t, k) for k in ("id", "name", "start", "duration", "kind", "has_audio")}
        | {"variants": [{k: v[k] for k in ("width", "height", "bandwidth")} for v in t.variants]}
        for t in info["tracks"]
    ]
    return info


# async обязательно: launch() создаёт asyncio-задачу, а sync-обработчики FastAPI идут в пуле потоков без event loop
@app.post("/api/jobs", status_code=201)
async def create(body: JobIn):
    try:
        downloader.session_id(body.url.strip())
    except ValueError as e:
        raise HTTPException(400, str(e))
    if body.mode not in MODES:
        raise HTTPException(400, "Неизвестный режим")
    if body.mode != "audio" and not body.streams:
        raise HTTPException(400, "Выберите хотя бы один видеопоток")
    job = Job(body.url.strip(), mode=body.mode, quality=body.quality, streams=body.streams,
              workers=max(1, min(body.workers, downloader.MAX_WORKERS)))
    store.launch(job)
    return job.to_dict()


@app.get("/api/jobs")
def list_jobs():
    ordered = sorted(store.jobs.values(), key=lambda j: j.created, reverse=True)
    return [store.outputs_with_state(j) for j in ordered]


@app.post("/api/jobs/{job_id}/cancel")
def cancel(job_id: str):
    get(job_id).cancel = True
    return {"ok": True}


@app.post("/api/jobs/{job_id}/restart")
async def restart(job_id: str):
    job = get(job_id)
    if job.status in ACTIVE:
        raise HTTPException(409, "Задача уже выполняется")
    job.add_log("info", "— Перезапуск —")
    store.launch(job)
    return job.to_dict()


@app.post("/api/jobs/{job_id}/reveal")
def reveal(job_id: str):
    job = get(job_id)
    existing = [o["path"] for o in job.outputs if Path(o["path"]).exists()]
    if existing:
        subprocess.run(["open", "-R", existing[0]])
    else:
        subprocess.run(["open", job.folder if job.folder and Path(job.folder).exists() else str(DOWNLOADS)])
    return {"ok": True}


@app.post("/api/jobs/{job_id}/clean")
def clean(job_id: str):
    job = get(job_id)
    if job.status in ACTIVE:
        raise HTTPException(409, "Загрузка ещё идёт")
    if job.work and job.work.resolve().is_relative_to(DOWNLOADS.resolve()):
        shutil.rmtree(job.work, ignore_errors=True)
        store.forget_size(job)
        job.add_log("info", "Промежуточные файлы удалены")
        store.save()
    return {"ok": True}


@app.delete("/api/jobs/{job_id}")
def delete(job_id: str):
    job = get(job_id)
    if job.status in ACTIVE:
        raise HTTPException(409, "Сначала отмените загрузку")
    del store.jobs[job_id]
    store.save()
    return {"ok": True}


@app.get("/files/{job_id}/{n}")
def file(job_id: str, n: int, dl: int = 0):
    job = get(job_id)
    if n >= len(job.outputs) or not Path(job.outputs[n]["path"]).exists():
        raise HTTPException(404, "Файл не найден")
    path = Path(job.outputs[n]["path"])
    return FileResponse(path, filename=path.name if dl else None,
                        content_disposition_type="attachment" if dl else "inline")


# Последним: статика ui/ на «/», не перекрывает /api и /files
app.mount("/", StaticFiles(directory=ROOT / "ui", html=True), name="ui")


if __name__ == "__main__":
    print(f"Дашборд: http://127.0.0.1:{PORT}  (Ctrl+C — остановить)")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
