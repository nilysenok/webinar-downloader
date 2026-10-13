import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from downloader import Job
from server import app as server_app
from server import store

URL = "https://my.mts-link.ru/j/1/2/record-new/3"
HOME = "http://127.0.0.1:8765"


def local(**kw):
    """Клиент, как браузер на этом компьютере. Без with: lifespan не читает history.json."""
    return TestClient(server_app.app, base_url=HOME, **kw)


class CreateJob(unittest.TestCase):
    """Форма шлёт только {url, mode}: «Видео» без выбора камер — все камеры записи."""

    def setUp(self):
        launch = mock.patch.object(server_app.store, "launch")
        self.launch = launch.start()
        self.addCleanup(launch.stop)
        self.client = local()

    def test_video_without_streams_is_accepted(self):
        r = self.client.post("/api/jobs", json={"url": URL, "mode": "av"})
        self.assertEqual(r.status_code, 201, r.text)
        job = self.launch.call_args.args[0]
        self.assertEqual((job.mode, job.streams), ("av", []))

    def test_unknown_mode_is_rejected(self):
        r = self.client.post("/api/jobs", json={"url": URL, "mode": "gif"})
        self.assertEqual(r.status_code, 400)
        self.launch.assert_not_called()


class FreshUi(unittest.TestCase):
    """Старый CSS из кэша + новая разметка = кнопки наезжают: файлы интерфейса браузер сверяет каждый раз."""

    def test_ui_files_are_revalidated(self):
        client = local()
        for path in ("/", "/style.css", "/app.js"):
            r = client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertEqual(r.headers.get("cache-control"), "no-cache", path)
        etag = client.get("/style.css").headers["etag"]
        self.assertEqual(client.get("/style.css", headers={"If-None-Match": etag}).status_code, 304)

    def test_api_is_left_alone(self):
        with mock.patch.object(server_app.store, "jobs", {}):
            r = local().get("/api/jobs")
        self.assertNotEqual(r.headers.get("cache-control"), "no-cache")



class LocalOnly(unittest.TestCase):
    """Сервер слушает 127.0.0.1, но чужой сайт может прийти и туда: подменой DNS или запросом без тела."""

    def setUp(self):
        self.job = Job(URL, status="download")
        jobs = mock.patch.object(server_app.store, "jobs", {self.job.id: self.job})
        jobs.start()
        self.addCleanup(jobs.stop)

    def test_foreign_host_gets_nothing(self):
        r = local().get("/api/jobs", headers={"Host": "evil.example:8765"})
        self.assertEqual(r.status_code, 403)
        self.assertNotIn(self.job.id, r.text)
        for host in ("127.0.0.1:8765", "localhost:8765", "[::1]:8765"):
            self.assertEqual(local().get("/api/jobs", headers={"Host": host}).status_code, 200, host)

    def test_foreign_page_cannot_cancel(self):
        for origin in ("https://evil.example", "null"):
            r = local().post(f"/api/jobs/{self.job.id}/cancel", headers={"Origin": origin})
            self.assertEqual(r.status_code, 403, origin)
        self.assertFalse(self.job.cancel)
        self.assertEqual(local().post(f"/api/jobs/{self.job.id}/cancel", headers={"Origin": HOME}).status_code, 200)
        self.assertTrue(self.job.cancel)

    def test_file_number_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "a.mp3"
            f.write_bytes(b"x")
            self.job.outputs = [{"path": str(f), "size": 1}]
            self.assertEqual(local().get(f"/files/{self.job.id}/0").status_code, 200)
            for n in (-1, 1):  # −1 раньше отдавал последний файл
                self.assertEqual(local().get(f"/files/{self.job.id}/{n}").status_code, 404, n)


class History(unittest.TestCase):
    def test_autosave_thread_and_new_jobs_do_not_collide(self):
        """Автосохранение идёт из потока, запуск задачи — из цикла событий; раньше они делили history.tmp."""
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(store, "HISTORY", Path(tmp) / "history.json"), \
                mock.patch.object(store, "jobs", {}):
            errors, stop = [], threading.Event()

            def autosave():
                while not stop.is_set():
                    try:
                        store.save()
                    except Exception as e:
                        errors.append(e)

            t = threading.Thread(target=autosave)
            t.start()
            try:
                for _ in range(200):
                    job = Job(URL)
                    store.jobs[job.id] = job
                    store.save()
            except Exception as e:
                errors.append(e)
            finally:
                stop.set()
                t.join()
            self.assertEqual(errors, [])
            self.assertEqual(len(json.loads(store.HISTORY.read_text(encoding="utf-8"))), 200)


if __name__ == "__main__":
    unittest.main()
