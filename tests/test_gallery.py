"""Настоящее видео по init-сегменту, пропуск «видео» без кадров, общий экран (сетка, ffmpeg)."""
import asyncio
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from downloader import Job, gallery, hls, pipeline
from downloader.boxes import video_size
from downloader.models import Track


def box(kind: bytes, payload: bytes = b"") -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + kind + payload


def tkhd(w: int, h: int, version: int = 0) -> bytes:
    times = 8 + 8 + 4 + 4 + 8 if version else 4 + 4 + 4 + 4 + 4
    body = bytes([version, 0, 0, 0]) + bytes(times) + bytes(8 + 8 + 36)
    return box(b"tkhd", body + (w << 16).to_bytes(4, "big") + (h << 16).to_bytes(4, "big"))


def init(handler: bytes, w=640, h=360, version=0) -> bytes:
    hdlr = box(b"hdlr", bytes(8) + handler + bytes(12))
    trak = box(b"trak", tkhd(w, h, version) + box(b"mdia", box(b"mdhd", bytes(24)) + hdlr))
    return box(b"ftyp", b"iso6") + box(b"moov", box(b"mvhd", bytes(100)) + trak)


class BoxesTest(unittest.TestCase):
    def test_video_size_from_tkhd(self):
        self.assertEqual(video_size(init(b"vide", 640, 360)), (640, 360))
        self.assertEqual(video_size(init(b"vide", 320, 180, version=1)), (320, 180))

    def test_audio_only_is_not_video(self):  # так выглядит «640×480» дорожки с выключенной камерой
        self.assertIsNone(video_size(init(b"soun", 0, 0)))
        self.assertIsNone(video_size(b"garbage"))
        self.assertIsNone(video_size(init(b"vide")[:40]))  # обрезанный init — не падаем


class ProbeTest(unittest.TestCase):
    def test_drops_audio_only_variant_and_takes_real_size(self):
        t = Track(1, "x", 0, 1, variants=[
            {"width": 640, "height": 480, "bandwidth": 1_100_000, "uri": "https://h/v/index.m3u8"},
            {"width": 640, "height": 480, "bandwidth": 100_000, "uri": "https://h/a/index.m3u8"}])
        body = {"https://h/v/index.m3u8": b'#EXT-X-MAP:URI="init.m4s"\nseg.m4s\n', "https://h/v/init.m4s": init(b"vide"),
                "https://h/a/index.m3u8": b'#EXT-X-MAP:URI="init.m4s"\nseg.m4s\n', "https://h/a/init.m4s": init(b"soun")}

        async def fake(client, url, job=None):
            return body[url]
        with mock.patch.object(hls, "fetch", fake):
            asyncio.run(hls._probe_video(None, t))
        self.assertEqual([(v["height"], v["bandwidth"]) for v in t.variants], [(360, 1_100_000)])

    def test_gallery_needs_mix_even_in_video_mode(self):
        self.assertEqual(Job("u", mode="video").wants(), (True, True))
        self.assertEqual(Job("u", mode="video", gallery=False).wants(), (False, True))
        self.assertEqual(Job("u", mode="audio").wants(), (True, False))


class GridTest(unittest.TestCase):
    def test_layouts(self):
        self.assertEqual(gallery.grid(1), [(2, 2, 1276, 716)])  # один — на весь экран
        three = gallery.grid(3)
        self.assertEqual(three[2][0], (gallery.W - three[2][2]) // 2)  # неполный ряд — по центру
        for n in range(1, 20):
            for x, y, w, h in gallery.grid(n):
                self.assertTrue(x >= 0 and y >= 0 and x + w <= gallery.W and y + h <= gallery.H, n)
                self.assertEqual((w % 2, h % 2), (0, 0))

    def test_one_tile_per_person(self):
        ts = [Track(1, "Анна", 9, 1), Track(2, "Илья", 5, 1), Track(3, "Анна", 1, 1), Track(4, "Анна", 2, 1, kind="screen")]
        self.assertEqual([(who, [t.id for t in g]) for who, g in gallery.people(ts)],
                         [("Анна", [3, 1]), ("Анна (экран)", [4]), ("Илья", [2])])


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def pixel(path: Path, t: float, x: int, y: int):
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1",
                          "-vf", f"format=rgb24,crop=1:1:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return tuple(out[:3])


@unittest.skipUnless(shutil.which("ffmpeg"), "нужен ffmpeg")
class RenderTest(unittest.TestCase):
    def test_skips_videoless_stream_and_renders_gallery(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "it's 1:2"  # кавычка и двоеточие в пути не ломают граф фильтров
            (d / "_work").mkdir(parents=True)
            frag = ["-movflags", "frag_keyframe+empty_moov"]
            ff("-f", "lavfi", "-i", "color=c=red:s=320x180:r=25:d=2", "-c:v", "libx264", *frag, d / "v.mp4")
            ff("-f", "lavfi", "-i", "sine=d=2", "-c:a", "aac", *frag, d / "a.mp4")  # «видео» без кадров
            ff("-f", "lavfi", "-i", "sine=d=4", "-c:a", "aac", d / "mix.m4a")
            job = Job("u", mode="video", title="t", duration=4.0, folder=str(d))
            tracks = [Track(1, "Анна", 1.0, 2, video=True, height=180), Track(2, "Илья", 0.0, 2, video=True)]
            files = {(1, "v"): d / "v.mp4", (2, "v"): d / "a.mp4"}
            asyncio.run(pipeline._mux_all(job, tracks, files, d / "mix.m4a", d, "t"))
            self.assertIn("камера выключена", " ".join(x["msg"] for x in job.log))
            self.assertEqual(len(job.outputs), 2)  # видео Анны + общий экран; поток Ильи пропущен
            out = Path(job.outputs[1]["path"])
            self.assertEqual(out.name, "t — общий экран.mp4")
            self.assertEqual(job.mux_done, job.mux_total)
            center = (gallery.W // 2, gallery.H // 2)
            self.assertLess(max(pixel(out, 0.5, *center)), 60)  # до начала камеры — тёмная плитка
            r, g, b = pixel(out, 2.0, *center)
            self.assertTrue(r > 200 and g < 60 and b < 60, (r, g, b))  # камера идёт с 1-й секунды
            streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                                      str(out)], capture_output=True, text=True).stdout.split()
            self.assertEqual(streams, ["video", "audio"])

    def test_frame_size_change_inside_stream(self):
        """MTS Link меняет размер кадра посреди потока; без -reinit_filter 0 граф пересобирался с нуля."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "_work").mkdir()
            for name, color, size in (("1", "red", "640x360"), ("2", "blue", "320x180"), ("3", "red", "1280x720")):
                ff("-f", "lavfi", "-i", f"color=c={color}:s={size}:r=25:d=2", "-c:v", "libvpx-vp9", "-deadline", "realtime",
                   d / f"{name}.webm")
            (d / "list.txt").write_text("".join(f"file '{d / n}.webm'\n" for n in "123"))
            ff("-f", "concat", "-safe", "0", "-i", d / "list.txt", "-c", "copy", "-movflags", "frag_keyframe+empty_moov",
               d / "v.mp4")
            job = Job("u", duration=40.0, folder=str(d))
            out = d / "g.mp4"
            asyncio.run(gallery.render(job, [Track(1, "Анна", 30.0, 6)], {1: d / "v.mp4"}, None, out))
            c = (gallery.W // 2, gallery.H // 2)
            self.assertGreater(pixel(out, 31.0, *c)[0], 200)  # красный 640×360
            self.assertGreater(pixel(out, 33.0, *c)[2], 200)  # синий 320×180
            self.assertGreater(pixel(out, 35.0, *c)[0], 200)  # снова красный, 1280×720
            self.assertLess(max(pixel(out, 10.0, *c)), 60)
            dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                                 capture_output=True, text=True).stdout
            self.assertAlmostEqual(float(dur), 40.0, delta=0.2)


if __name__ == "__main__":
    unittest.main()
