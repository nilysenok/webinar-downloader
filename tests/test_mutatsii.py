"""Тесты на мутации: каждый ловит конкретную поломку, которую не видят остальные тесты."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from downloader import Job, job_folder
from downloader import pipeline


class RestartFolderTest(unittest.TestCase):
    """M6: перезапуск задачи продолжает в той же папке — на этом держится докачка."""

    def test_restart_keeps_existing_folder(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(pipeline, "DOWNLOADS", Path(tmp)):
            created = time.mktime((2026, 9, 25, 16, 38, 0, 0, 0, -1))
            folder = Path(tmp) / "2026-09-25_1638 Запись"
            (folder / "_work").mkdir(parents=True)  # первый запуск уже скачал часть сегментов
            job = Job("u", title="Запись", created=created, folder=str(folder))
            self.assertEqual(job_folder(job), folder)
            self.assertEqual(job.folder, str(folder))
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [folder.name])  # без «(2)»

    def test_restart_ignores_new_title(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(pipeline, "DOWNLOADS", Path(tmp)):
            folder = Path(tmp) / "2026-09-25_1638 Старое название"
            folder.mkdir()
            job = Job("u", title="Новое название", created=time.time(), folder=str(folder))
            self.assertEqual(job_folder(job), folder)  # название сменилось — папка та же


if __name__ == "__main__":
    unittest.main()
