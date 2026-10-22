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

    def test_graph_from_file_option_follows_ffmpeg_version(self):
        # граф общего экрана идёт файлом (командная строка Windows — 32 767 символов); ключ сменился в ffmpeg 7
        for banner, want in (("ffmpeg version 6.1.1-3ubuntu5 Copyright", "-filter_complex_script"),
                             ("ffmpeg version 4.4.2-0ubuntu0.22.04.1", "-filter_complex_script"),
                             ("ffmpeg version 7.1.1 Copyright", "-/filter_complex"),
                             ("ffmpeg version n9.0.1", "-/filter_complex"),
                             ("ffmpeg version 8.0-essentials_build-www.gyan.dev", "-/filter_complex"),
                             ("ffmpeg version N-118000-g1a2b3c4d5e", "-/filter_complex"),
                             ("ffmpeg version 2026-09-01-git-1a2b3c4d5e-full_build", "-/filter_complex")):
            osdeps.graph_option.cache_clear()
            with mock.patch.object(osdeps.subprocess, "run", return_value=mock.Mock(stdout=banner + "\nbuilt with …")):
                self.assertEqual(osdeps.graph_option(), [want], banner)
        osdeps.graph_option.cache_clear()

    def test_direct_addresses_only_behind_a_vpn_on_macos(self):
        # хост слайдов через VPN не отвечал — качаем мимо туннеля с адреса основной сети
        def run(route):
            def fake(cmd, **_):
                out = route if cmd[0] == "route" else {"en0": "192.168.1.25\n", "en1": ""}.get(cmd[-1], "")
                return mock.Mock(stdout=out)
            return fake
        with mock.patch.object(osdeps, "_os", return_value="darwin"):
            with mock.patch.object(osdeps.subprocess, "run", run("  interface: utun4\n")):
                self.assertEqual(osdeps.direct_addresses(), ("192.168.1.25",))
            with mock.patch.object(osdeps.subprocess, "run", run("  interface: en0\n")):
                self.assertEqual(osdeps.direct_addresses(), ())  # VPN нет — обходить нечего
        with mock.patch.object(osdeps, "_os", return_value="linux"):
            self.assertEqual(osdeps.direct_addresses(), ())

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
