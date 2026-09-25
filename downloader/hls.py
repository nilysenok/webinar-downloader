"""Сеть и разбор: API записи MTS Link, HLS master/media плейлисты, GET с ретраями."""
import asyncio
import json
import re
from urllib.parse import urljoin

import httpx

from .config import API, RETRIES
from .models import Track


class Cancelled(Exception):
    pass


def session_id(url: str) -> str:
    m = re.search(r"record-new/(\d+)", url or "")
    if "mts-link.ru" not in (url or "") or not m:
        raise ValueError("Нужна ссылка вида https://my.mts-link.ru/j/…/record-new/<id>")
    return m.group(1)


async def fetch(client, url, job=None):
    """GET с ретраями и нарастающей паузой. Проверяет отмену задачи."""
    for attempt in range(1, RETRIES + 1):
        if job and job.cancel:
            raise Cancelled
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.content
        except httpx.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            tail = "/".join(url.rsplit("/", 2)[-2:])
            if attempt == RETRIES or status in (401, 403, 404):
                raise RuntimeError(f"…/{tail}: {type(e).__name__} {status or ''}".strip()) from e
            if job:
                job.retries += 1
                if job.retries <= 50 or job.retries % 50 == 0:  # не заваливаем журнал
                    job.add_log("warn", f"Повтор {attempt}/{RETRIES - 1}: {type(e).__name__} {status or ''} …/{tail}")
            await asyncio.sleep(min(2 ** attempt, 20))


def _names_and_durations(logs):
    nick, dur, screen_confs = {}, {}, set()
    for e in logs:
        d, module = e.get("data"), e.get("module") or ""
        if not isinstance(d, dict):
            continue
        if module.startswith("conference") and isinstance(d.get("user"), dict):
            u = d["user"]
            nick[d.get("id")] = u.get("nickname") or " ".join(filter(None, [u.get("name"), u.get("secondName")]))
        elif module == "mediasession.update":
            dur[d.get("id")] = float(d.get("duration") or 0)
        elif "screensharing" in module.lower():  # эвристика: на записи с экраном не проверена
            conf = d.get("conference") if isinstance(d.get("conference"), dict) else {}
            screen_confs.add(conf.get("id") or d.get("conferenceId") or d.get("id"))
    return nick, dur, screen_confs


def parse_record(rec: dict):
    """Медиасессии записи (с именами, стартом, длительностью) и их HLS-ссылки."""
    logs = rec.get("eventLogs") or []
    nick, dur, screen_confs = _names_and_durations(logs)
    tracks, hls = [], []
    for e in logs:
        d = e.get("data")
        if e.get("module") != "mediasession.add" or not isinstance(d, dict):
            continue
        stream = d.get("stream") or {}
        conf_id = (stream.get("conference") or {}).get("id")
        kind = "screen" if conf_id in screen_confs or "screen" in json.dumps(stream).lower() else "camera"
        tracks.append(Track(id=d["id"], name=nick.get(conf_id) or "Участник", kind=kind,
                            start=float(e.get("relativeTime") or 0), duration=dur.get(d["id"], 0.0)))
        hls.append(d.get("hlsUrl"))
    return tracks, hls


def parse_master(track: Track, base: str, text: str):
    """Заполняет у дорожки ссылку на аудиорендишн и список видеорендишнов."""
    audio = re.search(r"#EXT-X-MEDIA:[^\n]*TYPE=AUDIO[^\n]*", text)
    if audio and (uri := re.search(r'URI="([^"]+)"', audio.group(0))):
        track.audio_uri = urljoin(base, uri.group(1))
        track.has_audio = True
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if not ln.startswith("#EXT-X-STREAM-INF"):
            continue
        res = re.search(r"RESOLUTION=(\d+)x(\d+)", ln)
        bw = re.search(r"BANDWIDTH=(\d+)", ln)
        uri = next((x for x in lines[i + 1:] if x and not x.startswith("#")), None)
        if res and uri:
            track.variants.append({"width": int(res[1]), "height": int(res[2]),
                                   "bandwidth": int(bw[1]) if bw else 0, "uri": urljoin(base, uri)})
    track.variants.sort(key=lambda v: (v["height"], v["bandwidth"]), reverse=True)


def parse_media(url: str, text: str):
    """URL init-сегмента (если есть) и media-сегментов по порядку."""
    parts = []
    init = re.search(r'#EXT-X-MAP:URI="([^"]+)"', text)
    if init:
        parts.append(urljoin(url, init.group(1)))
    parts += [urljoin(url, ln.strip()) for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    return parts


def pick_variant(variants, quality):
    """«best» — лучший; число — лучший не выше этой высоты, иначе самый маленький."""
    if quality == "best" or not str(quality).isdigit():
        return variants[0]
    fit = [v for v in variants if v["height"] <= int(quality)]
    return fit[0] if fit else variants[-1]


async def _get_record(client, sid):
    r = await client.get(API.format(sid))
    if r.status_code in (401, 403):
        raise PermissionError("Запись закрыта: нет доступа (403)")
    if r.status_code == 404:
        raise LookupError("Запись не найдена (404)")
    r.raise_for_status()
    return r.json()


async def analyze(client, url, job=None):
    """Метаданные записи + разбор HLS master-плейлистов каждой медиасессии."""
    sid = session_id(url)
    rec = await _get_record(client, sid)
    tracks, hls = parse_record(rec)
    if not tracks:
        raise RuntimeError("В записи нет медиасессий")

    async def master(h):
        return (await fetch(client, h, job)).decode() if h else ""

    texts = await asyncio.gather(*(master(h) for h in hls), return_exceptions=True)
    for t, h, text in zip(tracks, hls, texts):
        if isinstance(text, Cancelled):
            raise text
        if isinstance(text, Exception):
            if job:
                job.add_log("warn", f"{t.name}: не удалось прочитать плейлист ({text})")
            continue
        parse_master(t, h, text)
    return {"sid": sid, "title": rec.get("name") or sid, "date": (rec.get("createAt") or "")[:10],
            "duration": float(rec.get("duration") or 0), "tracks": tracks}
