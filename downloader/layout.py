"""Раскладка общего экрана во времени: кто в кадре на каждом отрезке и когда он говорит.

В кадре те, у кого сейчас камера, и те, кто говорил за последние HOLD с (появляется за AHEAD с
до начала речи — запись готова, будущее известно). Состав держится не меньше MIN_LEN с.
"""
from dataclasses import dataclass, field

WIN = 0.5  # окно разбора речи, с
HOLD = 20.0
AHEAD = 1.0
MIN_LEN = 10
MAX_TILES = 9


@dataclass
class Segment:
    t0: float
    t1: float
    who: list = field(default_factory=list)  # имена в порядке плиток
    talk: dict = field(default_factory=dict)  # имя → [(a, b)] речь внутри отрезка, с от начала записи


def _visible(duration, cams, talk):
    """[(окно начала, окно конца, множество)] — участки с одинаковым составом по окнам WIN."""
    names = sorted(set(cams) | set(talk))
    hold, ahead = int(HOLD / WIN), int(AHEAD / WIN)
    last = dict.fromkeys(names, -10 ** 9)
    runs = []
    for w in range(int(duration / WIN) + 1):
        for p in names:
            s = talk.get(p, ())
            if w + ahead < len(s) and s[w + ahead]:
                last[p] = w + ahead
        t = w * WIN
        vis = {p for p in names if w - last[p] <= hold or any(a <= t < b for a, b in cams.get(p, ()))}
        if len(vis) > MAX_TILES:  # вылетают те, кто дольше всех молчит
            vis = set(sorted(vis, key=lambda p: last[p], reverse=True)[:MAX_TILES])
        if runs and runs[-1][2] == vis:
            runs[-1][1] = w + 1
        else:
            runs.append([w, w + 1, vis])
    return runs


def _hidden_talk(seg, other, talk):
    """Сколько окон речи потеряем, если отдать отрезок seg составу соседа other."""
    lost = seg[2] - other[2]
    w0, w1 = int(seg[0] / WIN), int(seg[1] / WIN)
    return sum(sum(talk.get(p, ())[w0:w1]) for p in lost)


def _absorb(segs, talk):
    """Короткий отрезок отдаёт своё время соседу (его составу), где меньше спрятанной речи."""
    while len(segs) > 1:
        i = min(range(len(segs)), key=lambda k: segs[k][1] - segs[k][0])
        s = segs[i]
        if s[1] - s[0] >= MIN_LEN:
            break
        near = [j for j in (i - 1, i + 1) if 0 <= j < len(segs)]
        j = min(near, key=lambda k: (_hidden_talk(s, segs[k], talk), -len(s[2] & segs[k][2]), segs[k][1] - segs[k][0]))
        segs[j] = [min(s[0], segs[j][0]), max(s[1], segs[j][1]), segs[j][2]]
        del segs[i]
        k = 0
        while k + 1 < len(segs):  # соседи с одинаковым составом — в один отрезок
            if segs[k][2] == segs[k + 1][2]:
                segs[k:k + 2] = [[segs[k][0], segs[k + 1][1], segs[k][2]]]
            else:
                k += 1
    return segs


def _talk_spans(s, t0, t1):
    """Окна речи → [(a, b)] в секундах внутри [t0, t1)."""
    spans, w = [], int(t0 / WIN)
    while w < min(len(s), int(t1 / WIN) + 1):
        if s[w]:
            a = w
            while w < len(s) and s[w]:
                w += 1
            spans.append((max(a * WIN, t0), min(w * WIN, t1)))
        w += 1
    return [(a, b) for a, b in spans if b > a]


def plan(duration, cams, talk):
    """cams: {имя: [(a, b)]} камера включена; talk: {имя: [bool по окнам WIN]} → [Segment].

    Границы — на целых секундах: 25 кадров/с, отрезки склеиваются без дробных кадров.
    """
    segs = []
    for w0, w1, vis in _visible(duration, cams, talk):
        a, b = round(w0 * WIN), round(w1 * WIN)
        if segs and segs[-1][2] == vis or segs and a == b:
            segs[-1][1] = b
        elif a < b:
            segs.append([a, b, vis])
    segs = _absorb(segs, talk)
    segs[0][0], segs[-1][1] = 0, duration
    order = []
    for _, _, vis in segs:  # постоянный порядок плиток — по первому появлению
        order += sorted(vis - set(order))
    return [Segment(a, b, [p for p in order if p in vis], {p: _talk_spans(talk.get(p, ()), a, b) for p in vis})
            for a, b, vis in segs]
