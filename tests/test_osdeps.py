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
