"""Настоящее видео по init-сегменту, пропуск «видео» без кадров, общий экран (сетка, ffmpeg)."""
import asyncio
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from downloader import Job, gallery, hls, pipeline, tiles
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


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def pixel(path: Path, t: float, x: int, y: int):
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1",
                          "-vf", f"format=rgb24,crop=1:1:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return tuple(out[:3])


def sine(p: Path, seconds: float, talk=None):
    """Звук дорожки: тишина, а в talk=(a, b) — тон громче порога речи."""
    vol = f"volume='between(t,{talk[0]},{talk[1]})':eval=frame" if talk else "volume=0"
    ff("-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-af", vol, "-c:a", "aac", p)


def vp9(p: Path, seconds: float, color: str, size="320x180"):
    ff("-f", "lavfi", "-i", f"color=c={color}:s={size}:r=25:d={seconds}", "-c:v", "libvpx-vp9", "-deadline", "realtime",
       "-movflags", "frag_keyframe+empty_moov", p)


@unittest.skipUnless(shutil.which("ffmpeg"), "нужен ffmpeg")
class RenderTest(unittest.TestCase):
    def test_camera_speaker_and_empty_screen(self):
        """Анна с камерой 0–20 с; никого 20–39; Илья без камеры говорит 40–45 → плитка с именем и рамкой."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "it's 1:2"  # кавычка и двоеточие в пути не ломают граф фильтров
            (d / "_work").mkdir(parents=True)
            vp9(d / "v.mp4", 20, "red")
            ff("-f", "lavfi", "-i", "sine=d=2", "-c:a", "aac", "-movflags", "frag_keyframe+empty_moov", d / "nov.mp4")
            sine(d / "a1.m4a", 20)
            sine(d / "a2.m4a", 60, talk=(40, 45))
            sine(d / "mix.m4a", 60, talk=(40, 45))
            job = Job("u", mode="video", title="t", duration=60.0, folder=str(d))
            tracks = [Track(1, "Анна", 0.0, 20, video=True, height=180), Track(2, "Илья", 0.0, 60, video=True)]
            files = {(1, "v"): d / "v.mp4", (2, "v"): d / "nov.mp4", (1, "a"): d / "a1.m4a", (2, "a"): d / "a2.m4a"}
            asyncio.run(pipeline._mux_all(job, tracks, files, d / "mix.m4a", d, "t"))
            self.assertIn("камера выключена", " ".join(x["msg"] for x in job.log))  # «видео» Ильи без кадров
            self.assertEqual(len(job.outputs), 1, "с общим экраном — один файл, без отдельных видео")
            out = Path(job.outputs[0]["path"])
            self.assertEqual(out.name, "t — общий экран.mp4")
            self.assertEqual(job.mux_done, job.mux_total)
            c = (tiles.W // 2, tiles.H // 2)
            r, g, b = pixel(out, 10, *c)
            self.assertTrue(r > 200 and g < 60 and b < 60, (r, g, b))  # Анна на весь экран
            self.assertLess(max(pixel(out, 30, 20, 20)), 40)  # никого — заставка
            edge = (tiles.GAP // 2 + 2, tiles.H // 2)
            r, g, b = pixel(out, 42, *edge)
            self.assertTrue(g > 150 and r < 120, (r, g, b))  # Илья говорит — зелёная рамка
            self.assertLess(max(pixel(out, 55, *edge)), 60)  # замолчал — рамки нет, плитка осталась
            streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                                      "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.split()
            self.assertEqual(streams[:2], ["video", "audio"])
            self.assertAlmostEqual(float(streams[2]), 60.0, delta=0.2)

    def test_without_gallery_each_video_is_its_own_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            vp9(d / "v1.mp4", 2, "red")
            vp9(d / "v2.mp4", 2, "blue")
            job = Job("u", mode="video", title="t", duration=4.0, folder=str(d), gallery=False)
            tracks = [Track(1, "Анна", 0.0, 2, video=True, height=180), Track(2, "Илья", 2.0, 2, video=True, height=180)]
            files = {(1, "v"): d / "v1.mp4", (2, "v"): d / "v2.mp4"}
            asyncio.run(pipeline._mux_all(job, tracks, files, None, d, "t"))
            names = [Path(o["path"]).name for o in job.outputs]
            self.assertEqual(len(names), 2)
            self.assertNotIn("t — общий экран.mp4", names)
            self.assertEqual(job.mux_done, job.mux_total)

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
            asyncio.run(gallery.render(job, [Track(1, "Анна", 30.0, 6)], {1: d / "v.mp4"}, {}, None, out))
            c = (tiles.W // 2, tiles.H // 2)
            self.assertGreater(pixel(out, 31.0, *c)[0], 200)  # красный 640×360
            self.assertGreater(pixel(out, 33.0, *c)[2], 200)  # синий 320×180
            self.assertGreater(pixel(out, 35.0, *c)[0], 200)  # снова красный, 1280×720
            self.assertLess(max(pixel(out, 10.0, 20, 20)), 60)


if __name__ == "__main__":
    unittest.main()
