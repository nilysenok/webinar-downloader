"""Живая раскладка общего экрана и разбор речи — без ffmpeg."""
import unittest

from downloader import layout, speech, tiles

W = layout.WIN


def talk_between(duration, *spans):
    """Окна речи: True внутри (a, b) секунд."""
    return [any(a <= w * W < b for a, b in spans) for w in range(int(duration / W) + 1)]


def who(segs):
    return [(s.t0, s.t1, s.who) for s in segs]


class LayoutTest(unittest.TestCase):
    def test_camera_then_speaker_without_camera(self):
        segs = layout.plan(120, {"Анна": [(0, 40)]}, {"Илья": talk_between(120, (70, 75))})
        # Илья появляется за 1 с до речи и держится 20 с после; между ними — никого
        self.assertEqual(who(segs), [(0, 40, ["Анна"]), (40, 69, []), (69, 95, ["Илья"]), (95, 120, [])])
        self.assertEqual(segs[2].talk["Илья"], [(70.0, 75.0)])

    def test_short_flicker_is_absorbed(self):
        segs = layout.plan(100, {"Анна": [(0, 100)], "Боря": [(50, 52)]}, {})
        self.assertEqual(who(segs), [(0, 100, ["Анна"])])  # камера на 2 с — не повод перестраивать экран

    def test_short_gap_keeps_speaker_visible(self):
        # состав меняется на 5 с между двумя репликами — отрезок уходит соседу, где не прячем речь
        segs = layout.plan(200, {"Анна": [(0, 200)]}, {"Илья": talk_between(200, (30, 40), (66, 70))})
        self.assertTrue(all(s.t1 - s.t0 >= layout.MIN_LEN for s in segs))
        at = next(s for s in segs if s.t0 <= 64 < s.t1)
        self.assertIn("Илья", at.who)

    def test_stable_order_and_cap(self):
        cams = {f"П{k:02d}": [(0, 100)] for k in range(12)}
        talks = {"П11": talk_between(100, (10, 90))}
        segs = layout.plan(100, cams, talks)
        self.assertTrue(all(len(s.who) <= layout.MAX_TILES for s in segs))
        self.assertTrue(all("П11" in s.who for s in segs if s.t0 >= 9))  # говорящего не выкидываем
        order = [p for s in segs for p in s.who]
        self.assertEqual([p for p in order if p in segs[-1].who][:len(segs[-1].who)], segs[-1].who)

    def test_segments_cover_record_on_whole_seconds(self):
        segs = layout.plan(95.6, {"Анна": [(3.2, 60.7)]}, {"Илья": talk_between(95.6, (80.3, 81))})
        self.assertEqual((segs[0].t0, segs[-1].t1), (0, 95.6))
        for a, b in zip(segs, segs[1:]):
            self.assertEqual(a.t1, b.t0)
            self.assertEqual(a.t1, int(a.t1))


class SpeechTest(unittest.TestCase):
    def test_talking_bridges_pauses_and_drops_blips(self):
        lv = [-60] * 4 + [-30] * 4 + [-60] * 2 + [-30] * 4 + [-60] * 6 + [-30] + [-60] * 4
        s = speech.talking(lv)
        self.assertEqual(s[4:14], [True] * 10)  # пауза 1 с внутри реплики склеена
        self.assertFalse(any(s[14:]))  # одиночный всплеск 0,5 с — не речь


def depth(e: str) -> int:
    """Глубина дерева выражения, как её считает FFmpeg: функция — 1, каждое «+» — на 1 глубже своих слагаемых."""
    pos = 0

    def term():
        nonlocal pos
        if e[pos] == "(":
            pos += 1
            d = total()
            pos += 1  # «)»
            return d
        pos = e.index(")", pos) + 1  # between(t,a,b)
        return 1

    def total():
        nonlocal pos
        d = term()
        while pos < len(e) and e[pos] == "+":
            pos += 1
            d = max(d, term()) + 1
        return d

    return total()


class BorderTest(unittest.TestCase):
    def test_hundreds_of_speech_spans_stay_within_ffmpeg_depth(self):
        spans = [(i * 15.0, i * 15.0 + 9.5) for i in range(700)]  # лектор на записи в три часа
        expr = tiles._border(spans, 0, 240).split("enable='")[1].rstrip("'")
        self.assertEqual(expr.count("between("), 700)
        self.assertLessEqual(depth(expr), 20)  # предел FFmpeg с 8.1 — 100
        self.assertEqual(depth("+".join(["between(t,0,1)"] * 101)), 101)  # цепочка, как было: уже за пределом
        self.assertEqual(tiles._border([], 0, 240), "")


class GridTest(unittest.TestCase):
    def test_layouts(self):
        self.assertEqual(tiles.grid(1), [(2, 2, 1276, 716)])  # один — на весь экран
        three = tiles.grid(3)
        self.assertEqual(three[2][0], (tiles.W - three[2][2]) // 2)  # неполный ряд — по центру
        for n in range(1, 10):
            for x, y, w, h in tiles.grid(n):
                self.assertTrue(x >= 0 and y >= 0 and x + w <= tiles.W and y + h <= tiles.H, n)
                self.assertEqual((w % 2, h % 2), (0, 0))


if __name__ == "__main__":
    unittest.main()
