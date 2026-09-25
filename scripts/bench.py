"""Замер скорости загрузки аудиосегментов MTS Link. Ничего не пишет на диск, код загрузчика не трогает.

    .venv/bin/python scripts/bench.py <ссылка record-new> [--secs 60] [--workers 64,128] [--http2] [--ip A,B]

Байты считаются по мере прихода (стрим), поэтому недокачанные к концу окна запросы тоже учтены.
Каждый прогон берёт свой кусок перемешанного списка сегментов, чтобы не мерить кэш CDN.
"""
import argparse
import asyncio
import json
import random
import resource
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx  # noqa: E402

from downloader.config import TIMEOUT, UA  # noqa: E402
from downloader.hls import analyze, fetch, parse_media  # noqa: E402


async def segment_urls(url):
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=TIMEOUT) as c:
        info = await analyze(c, url)
        tracks = [t for t in info["tracks"] if t.has_audio]
        pls = await asyncio.gather(*(fetch(c, t.audio_uri) for t in tracks))
    urls = [u for t, pl in zip(tracks, pls) for u in parse_media(t.audio_uri, pl.decode())[1:]]  # без init
    random.Random(42).shuffle(urls)
    return urls


def make_clients(workers, http2, ips):
    limits = httpx.Limits(max_connections=workers, max_keepalive_connections=workers)
    if not ips:
        return [httpx.AsyncClient(headers={"User-Agent": UA}, timeout=TIMEOUT, limits=limits, http2=http2)]
    per = httpx.Limits(max_connections=max(1, workers // len(ips)), max_keepalive_connections=max(1, workers // len(ips)))
    return [httpx.AsyncClient(headers={"User-Agent": UA}, timeout=TIMEOUT, limits=per, http2=http2) for _ in ips]


def request_args(url, ip):
    """Запрос на конкретный IP с правильными Host и SNI (сертификат проверяется по имени хоста)."""
    if not ip:
        return url, {}, {}
    host = urlsplit(url).hostname
    return url.replace(f"//{host}", f"//{ip}", 1), {"Host": host}, {"sni_hostname": host}


async def run(urls, workers, secs, http2=False, ips=None):
    st = {"bytes": 0, "ok": 0, "err": 0, "codes": Counter(), "lat": []}
    clients = make_clients(workers, http2, ips)
    queue = iter(urls)

    async def worker(i):
        client, ip = clients[i % len(clients)], (ips[i % len(ips)] if ips else None)
        for u in queue:
            target, headers, ext = request_args(u, ip)
            t0 = time.monotonic()
            try:
                async with client.stream("GET", target, headers=headers, extensions=ext) as r:
                    st["codes"][r.status_code] += 1
                    async for chunk in r.aiter_bytes():
                        st["bytes"] += len(chunk)
                    if r.status_code == 200:
                        st["ok"] += 1
                        st["lat"].append(time.monotonic() - t0)
                    else:
                        st["err"] += 1
            except Exception as e:  # замер: считаем, не падаем
                st["err"] += 1
                st["codes"][type(e).__name__] += 1

    ru0, t0 = resource.getrusage(resource.RUSAGE_SELF), time.monotonic()
    tasks = [asyncio.create_task(worker(i)) for i in range(workers)]
    await asyncio.sleep(secs)
    got, wall = st["bytes"], time.monotonic() - t0
    ru1 = resource.getrusage(resource.RUSAGE_SELF)
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    for c in clients:
        await c.aclose()
    return summary(st, got, wall, ru0, ru1, workers, http2, ips)


def summary(st, got, wall, ru0, ru1, workers, http2, ips):
    lat = sorted(st["lat"]) or [0]
    done = st["ok"] + st["err"]
    return {
        "workers": workers, "http": "2" if http2 else "1.1", "ips": len(ips or []) or 1,
        "MB/s": round(got / wall / 1e6, 2), "ok": st["ok"], "err": st["err"],
        "err%": round(100 * st["err"] / done, 1) if done else 0.0, "429": st["codes"].get(429, 0),
        "codes": dict(st["codes"]), "p50_s": round(lat[len(lat) // 2], 1), "p90_s": round(lat[int(len(lat) * .9)], 1),
        "cpu%": round(100 * ((ru1.ru_utime + ru1.ru_stime) - (ru0.ru_utime + ru0.ru_stime)) / wall, 1),
        "rss_MB": round(ru1.ru_maxrss / 1e6, 0),  # macOS: байты
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--secs", type=int, default=60)
    ap.add_argument("--workers", default="64")
    ap.add_argument("--http2", action="store_true")
    ap.add_argument("--ip", default="")
    ap.add_argument("--offset", type=int, default=0, help="с какого сегмента перемешанного списка начинать")
    a = ap.parse_args()
    urls = await segment_urls(a.url)
    ips = [x for x in a.ip.split(",") if x]
    offset = a.offset
    for w in [int(x) for x in a.workers.split(",")]:
        chunk = urls[offset:] + urls[:offset]
        res = await run(chunk, w, a.secs, a.http2, ips)
        offset = (offset + res["ok"] + res["err"] + w) % len(urls)  # следующий прогон — свежие сегменты
        print(json.dumps(res, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
