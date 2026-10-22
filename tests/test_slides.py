"""Показ файла: слайды из журнала записи, нарезка отрезков, слайд в кадре общего экрана."""
import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from downloader import Job, gallery, hls, layout, slides, tiles
from downloader.models import Track
from tests.test_gallery import ff, pixel, vp9
from tests.test_layout import talk_between


def show(t, url, module="presentation.update", **flags):
    return {"module": module, "relativeTime": t,
            "data": {"isActive": True, "fileReference": {"slide": {"url": url}}} | flags}


class ParseTest(unittest.TestCase):
    def test_slides_until_next_event_or_close(self):
        logs = [show(30, "u2"), show(10.4, "u1"), {"module": "userlist.online", "relativeTime": 12, "data": {}},
                show(31, "u2"), show(50, "u2", isActive=False), show(70, "u1")]
        self.assertEqual(slides.parse(logs, 100), [(10.4, 30, "u1"), (30, 50, "u2"), (70, 100, "u1")])

    def test_no_presentation(self):
        self.assertEqual(slides.parse([{"module": "conference.add", "relativeTime": 1, "data": {}}], 60), [])


class SplitTest(unittest.TestCase):
    def test_segments_cut_at_slide_changes(self):
        segs = layout.plan(100, {"Анна": [(0, 100)]}, {"Анна": talk_between(100, (25, 35))})
        cut = layout.with_slides(segs, [(10.4, 30, "a.png"), (30, 50, "b.png")])
        self.assertEqual([(s.t0, s.t1, s.slide) for s in cut], [(0, 10, ""), (10, 30, "a.png"), (30, 50, "b.png"),
                                                                (50, 100, "")])
        self.assertEqual(cut[1].talk["Анна"], [(25.0, 30)])
        self.assertEqual(cut[2].talk["Анна"], [(30, 35.0)])
        self.assertEqual(cut[3].who, ["Анна"])


@unittest.skipUnless(shutil.which("ffmpeg"), "нужен ффмпег")
class RenderTest(unittest.TestCase):
    def render(self, reachable):
        """Анна с камерой 0–20 с, слайд 10–30 с; запись 30 с → кадры в 5, 15 и 25 с.

        reachable(addr) — отвечает ли хост слайдов с этого адреса (None — напрямую, «10.0.0.5» — мимо VPN).
        """
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "_work").mkdir()
            vp9(d / "v.mp4", 20, "red")
            ff("-f", "lavfi", "-i", "color=c=blue:s=1600x900", "-frames:v", "1", d / "slide.png")
            body = (d / "slide.png").read_bytes()  # PNG под именем .jpg — как у MTS Link
            job = Job("u", duration=30.0, folder=str(d), slides=[(10.2, 30, "https://h/s1.jpg")])
            out = d / "g.mp4"
            def client(addr=None):
                def answer(req):
                    if not reachable(addr):
                        raise httpx.ConnectTimeout("timed out", request=req)
                    return httpx.Response(200, content=body)
                return httpx.AsyncClient(transport=httpx.MockTransport(answer))

            with mock.patch.object(slides, "_client", client), mock.patch.object(hls, "RETRIES", 1), \
                    mock.patch.object(slides, "direct_addresses", lambda: ("10.0.0.5",)):
                asyncio.run(gallery.render(job, [Track(1, "Анна", 0.0, 20)], {1: d / "v.mp4"}, {}, None, out))
            return job, [pixel(out, t, x, y) for t, x, y in
                         ((5, tiles.W // 2, tiles.H // 2), (15, (tiles.W - tiles.SIDE) // 2, tiles.H // 2),
                          (15, tiles.W - tiles.SIDE // 2, tiles.H // 2), (25, tiles.W // 2, tiles.H // 2))]

    def test_slide_large_cameras_on_the_side(self):
        job, (cam, slide, side, alone) = self.render(lambda addr: True)
        self.assertNotIn("мимо VPN", " ".join(x["msg"] for x in job.log))
        self.assertGreater(cam[0], 200)  # до слайда — Анна на весь кадр
        self.assertGreater(slide[2], 200)  # слайд слева
        self.assertGreater(side[0], 200)  # Анна в полосе справа
        self.assertGreater(alone[2], 200)  # камеры нет — слайд на весь кадр

    def test_slides_past_vpn_when_direct_route_hangs(self):
        job, (_, slide, _, _) = self.render(lambda addr: addr == "10.0.0.5")
        self.assertIn("мимо VPN, с адреса 10.0.0.5", " ".join(x["msg"] for x in job.log))
        self.assertGreater(slide[2], 200)

    def test_unreachable_slides_keep_cameras(self):
        job, (_, mid, _, alone) = self.render(lambda addr: False)
        self.assertIn("Слайды не скачались", " ".join(x["msg"] for x in job.log))
        self.assertGreater(mid[0], 200)  # слайда нет — Анна по-прежнему на весь кадр
        self.assertLess(max(alone), 60)  # никого — заставка


if __name__ == "__main__":
    unittest.main()
