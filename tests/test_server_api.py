import unittest
from unittest import mock

from fastapi.testclient import TestClient

from server import app as server_app

URL = "https://my.mts-link.ru/j/1/2/record-new/3"


class CreateJob(unittest.TestCase):
    """Форма шлёт только {url, mode}: «Видео» без выбора камер — все камеры записи."""

    def setUp(self):
        launch = mock.patch.object(server_app.store, "launch")
        self.launch = launch.start()
        self.addCleanup(launch.stop)
        self.client = TestClient(server_app.app)  # без with: lifespan не читает history.json

    def test_video_without_streams_is_accepted(self):
        r = self.client.post("/api/jobs", json={"url": URL, "mode": "av"})
        self.assertEqual(r.status_code, 201, r.text)
        job = self.launch.call_args.args[0]
        self.assertEqual((job.mode, job.streams), ("av", []))

    def test_unknown_mode_is_rejected(self):
        r = self.client.post("/api/jobs", json={"url": URL, "mode": "gif"})
        self.assertEqual(r.status_code, 400)
        self.launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
