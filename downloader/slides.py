"""Показ файла (презентации) в записи: когда какой слайд был на экране, и картинки слайдов.

Видеопотока у показа файла нет — в журнале записи только события presentation.* с картинкой
текущего слайда (запись 25958812689: 13 событий presentation.update, 22.10). Картинки лежат на
отдельном хосте events-storage.webinar.ru; через VPN владельца он не отвечал — тогда качаем мимо VPN.
"""
import asyncio
import hashlib
from pathlib import Path

import httpx

from .config import TIMEOUT, UA
from .hls import fetch
from .media import _to_file
from .osdeps import direct_addresses
from .tiles import H, W

PROBE = httpx.Timeout(10.0, connect=5.0)  # одна быстрая попытка на путь


def _slide_url(module: str, d) -> str:
    """Картинка слайда из события; пусто — файл закрыт (по флагам/удалению — не проверено на записи)."""
    if not isinstance(d, dict) or module.endswith("delete") or d.get("isDeleted") or d.get("isActive") is False:
        return ""
    ref = d.get("fileReference") if isinstance(d.get("fileReference"), dict) else {}
    slide = ref.get("slide") if isinstance(ref.get("slide"), dict) else {}
    return slide.get("url") or ""


def parse(logs, duration: float):
    """eventLogs → [(с, по, url картинки)]: каждый слайд держится до следующего события показа."""
    shows, cur = [], None
    for e in sorted(logs, key=lambda e: float(e.get("relativeTime") or 0)):
        module = e.get("module") or ""
        if not module.startswith("presentation"):
            continue
        t, url = float(e.get("relativeTime") or 0), _slide_url(module, e.get("data"))
        if cur and url != cur[1]:
            shows.append((cur[0], t, cur[1]))
            cur = None
        if url and not cur:
            cur = (t, url)
    if cur:
        shows.append((cur[0], duration, cur[1]))
    return [s for s in shows if s[1] > s[0]]


async def _one(job, client, url: str, out: Path):
    """Картинка → PNG не больше кадра общего экрана (оригинал бывает 4 МБ; формат — по содержимому)."""
    if out.exists():
        return
    raw = out.with_suffix(".img")  # без «.jpg»: под этим именем у MTS Link бывает PNG
    raw.write_bytes(await fetch(client, url, job))
    vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease"
    await _to_file(job, ["-i", raw, "-frames:v", "1", "-vf", vf], out)
    raw.unlink()


def _client(addr=None):
    transport = httpx.AsyncHTTPTransport(local_address=addr) if addr else None
    return httpx.AsyncClient(headers={"User-Agent": UA}, timeout=TIMEOUT, follow_redirects=True, transport=transport)


async def _route(job, url: str):
    """Клиент, через который хост слайдов отвечает: напрямую, иначе мимо VPN (решение владельца 22.10).

    Никто не ответил с одной попытки — обычный клиент: дальше fetch с повторами, как у сегментов.
    """
    for addr in (None, *await asyncio.to_thread(direct_addresses)):
        client = _client(addr)
        try:
            async with client.stream("GET", url, timeout=PROBE) as r:
                r.raise_for_status()
        except httpx.HTTPError:
            await client.aclose()
            continue
        if addr:
            job.add_log("info", f"Слайды — мимо VPN, с адреса {addr}: через VPN хост слайдов не отвечает")
        return client
    return _client()


async def _download(job, urls, files):
    """Сначала один слайд: хост недоступен — не ждём повторов по каждому."""
    client = await _route(job, urls[0])
    try:
        try:
            await _one(job, client, urls[0], files[urls[0]])
        except RuntimeError as e:
            job.add_log("warn", f"Слайды не скачались ({e}) — на их месте камеры")
            return
        sem = asyncio.Semaphore(4)

        async def one(u):
            async with sem:
                await _one(job, client, u, files[u])

        got = await asyncio.gather(*(one(u) for u in urls[1:]), return_exceptions=True)
    finally:
        await client.aclose()
    for g in got:
        if isinstance(g, BaseException) and not isinstance(g, RuntimeError):
            raise g
        if g:
            job.add_log("warn", f"Слайд не скачался ({g}) — на его месте камеры")


async def load(job, work: Path):
    """[(с, по, путь к PNG)] по job.slides. Не скачалось — общий экран без слайдов, задача не падает."""
    if not job.slides:
        return []
    folder = work / "slides"
    folder.mkdir(parents=True, exist_ok=True)
    urls = list(dict.fromkeys(u for _, _, u in job.slides))
    files = {u: folder / f"{hashlib.sha1(u.encode()).hexdigest()[:12]}.png" for u in urls}
    missing = [u for u in urls if not files[u].exists()]  # перезапуск: готовые картинки сеть не трогают
    if missing:
        await _download(job, missing, files)
    return [(a, b, str(files[u])) for a, b, u in job.slides if files[u].exists()]
