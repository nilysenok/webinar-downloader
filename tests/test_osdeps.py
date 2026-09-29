import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from downloader import osdeps


class OsDeps(unittest.TestCase):
    def test_windows_font_path_is_escaped_for_ffmpeg(self):
        # двоеточие после буквы диска разрывает опцию фильтра — должно быть «C\:/…», слеши прямые
        self.assertEqual(osdeps.filter_path(Path("C:/Windows/Fonts/arial.ttf")), r"C\:/Windows/Fonts/arial.ttf")
        self.assertEqual(osdeps.filter_path(Path("/usr/share/fonts/a'b.ttf")), r"/usr/share/fonts/a'\''b.ttf")

    def test_a_cyrillic_font_is_found_here(self):
        f = osdeps.font()
        self.assertIsNotNone(f, "на этой машине нет шрифта с кириллицей — подписи на общем экране пропадут")
        self.assertTrue(f.is_file())

    def test_filter_check_is_honest(self):
        self.assertTrue(osdeps.has_filter("null"))
        self.assertFalse(osdeps.has_filter("no_such_filter_xyz"))

    def test_no_drawtext_means_no_captions_not_a_crash(self):
        # Homebrew-ffmpeg 8+ собран без drawtext: общий экран должен собираться, просто без имён
        from downloader import tiles
        with mock.patch.object(tiles, "has_filter", return_value=False):
            self.assertEqual(tiles.text("t.txt", 30, True), "null")

    def test_console_survives_a_non_utf8_pipe(self):
        # так было в Windows: вывод в cp1252, первый print с кириллицей ронял сервер
        env = {k: v for k, v in os.environ.items() if k != "PYTHONUTF8"} | {"PYTHONIOENCODING": "cp1252"}
        code = "from downloader.osdeps import utf8_console; utf8_console(); print('Дашборд — готов')"
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env, cwd=Path(__file__).parent.parent)
        self.assertEqual(r.returncode, 0, r.stderr.decode(errors="replace"))
        self.assertIn("Дашборд — готов", r.stdout.decode("utf-8"))

    def test_awake_start_stop_are_idempotent(self):
        a = osdeps.Awake()
        a.start()
        a.start()
        self.assertTrue(a.on)
        a.stop()
        a.stop()
        self.assertFalse(a.on)
        self.assertIsNone(a.proc)


if __name__ == "__main__":
    unittest.main()
