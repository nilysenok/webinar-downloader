"""Разбор init-сегмента fMP4: есть ли в потоке видео и какого размера кадр.

MTS Link пишет в master-плейлисте RESOLUTION=640x480 и у дорожки с выключенной камерой —
внутри такого «видеопотока» только AAC (найдено 28.09, запись ИФР: видео у 1 из 31).
Поэтому верим только init-сегменту: обработчик `vide` в `hdlr` и размер из `tkhd`.
"""


def _boxes(buf: bytes, start: int, end: int):
    """(тип, начало содержимого, конец) для боксов подряд в [start, end)."""
    i = start
    while i + 8 <= end:
        size, kind, head = int.from_bytes(buf[i:i + 4], "big"), buf[i + 4:i + 8], 8
        if size == 1:
            size, head = int.from_bytes(buf[i + 8:i + 16], "big"), 16
        elif size == 0:
            size = end - i
        if size < head or i + size > end:
            return
        yield kind, i + head, i + size
        i += size


def _child(buf: bytes, start: int, end: int, kind: bytes):
    return next(((s, e) for k, s, e in _boxes(buf, start, end) if k == kind), None)


def _track(buf: bytes, s: int, e: int):
    """(обработчик, (ширина, высота)) дорожки `trak`."""
    handler, size = None, None
    if tkhd := _child(buf, s, e, b"tkhd"):
        off = tkhd[0] + (88 if buf[tkhd[0]] == 1 else 76)  # версия 1 — 64-битные времена
        if off + 8 <= tkhd[1]:
            size = (int.from_bytes(buf[off:off + 4], "big") >> 16, int.from_bytes(buf[off + 4:off + 8], "big") >> 16)
    if (mdia := _child(buf, s, e, b"mdia")) and (hdlr := _child(buf, *mdia, b"hdlr")):
        handler = buf[hdlr[0] + 8:hdlr[0] + 12]
    return handler, size


def video_size(init: bytes):
    """(ширина, высота) видеодорожки из init-сегмента; None — видео нет (только звук)."""
    moov = _child(init, 0, len(init), b"moov")
    if not moov:
        return None
    for kind, s, e in _boxes(init, *moov):
        if kind == b"trak":
            handler, size = _track(init, s, e)
            if handler == b"vide" and size and all(size):
                return size
    return None
