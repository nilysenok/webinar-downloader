"""Сведение и склейка через настоящий ffmpeg на синтетических дорожках (~1 с)."""
import asyncio
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from downloader import Job
from downloader.media import concat, mix_audio, mix_filter


def probe_duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def sine(p: Path, seconds: float, freq: int):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}",
                    "-c:a", "aac", str(p)], check=True)


class FilterTest(unittest.TestCase):
    def test_normalize_off_and_offsets(self):
        f = mix_filter([0, 2.5], 10)
        self.assertIn("normalize=0", f)  # Ъ: иначе amix делит громкость на число входов
        self.assertIn("adelay=0:all=1", f)
        self.assertIn("adelay=2500:all=1", f)
        self.assertIn("amix=inputs=2", f)
        self.assertIn("atrim=0:10", f)


@unittest.skipUnless(shutil.which("ffmpeg"), "нужен ffmpeg")
class FfmpegTest(unittest.TestCase):
    def test_mix_overlapping_tracks_to_mp3(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            sine(d / "a.m4a", 2, 440)
            sine(d / "b.m4a", 2, 660)
            job = Job("u", duration=4.0)
            out = d / "mix.mp3"
            asyncio.run(mix_audio(job, [(d / "a.m4a", 0.0), (d / "b.m4a", 2.0)], out))
            self.assertAlmostEqual(probe_duration(out), 4.0, delta=0.15)  # вторая дорожка сдвинута на 2 с
            self.assertFalse(list(d.glob("*.part*")))
            self.assertGreater(job.mix_pos, 0)

    def test_concat_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "0").write_bytes(b"init")
            (d / "1").write_bytes(b"-seg")
            concat([d / "0", d / "1"], d / "out.mp4")
            self.assertEqual((d / "out.mp4").read_bytes(), b"init-seg")


if __name__ == "__main__":
    unittest.main()
