"""Разбор записи и HLS, выбор качества, папки загрузок, прогресс задачи — без сети."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from downloader import Job, job_folder, session_id
from downloader import pipeline
from downloader.hls import parse_master, parse_media, parse_record, pick_variant
from downloader.models import Track

REC = {"name": "Вебинар", "createAt": "2026-09-22T12:22:20+0300", "duration": 100, "eventLogs": [
    {"module": "conference.add", "data": {"id": 1, "user": {"nickname": "Анна"}}},
    {"module": "conference.add", "data": {"id": 2, "user": {"name": "Илья", "secondName": "Сорокин"}}},
    {"module": "mediasession.add", "relativeTime": 5.5,
     "data": {"id": 10, "hlsUrl": "https://h/x/playlist.m3u8", "stream": {"conference": {"id": 1}}}},
    {"module": "mediasession.add", "relativeTime": 30,
     "data": {"id": 11, "hlsUrl": "https://h/y/playlist.m3u8", "stream": {"conference": {"id": 2}}}},
    {"module": "mediasession.update", "data": {"id": 10, "duration": 60}},
    {"module": "userlist.online", "data": []},
]}

MASTER = """#EXTM3U
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="eng",URI="a1/index.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=300000,RESOLUTION=640x480,CODECS="vp09",AUDIO="audio"
v1/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=1280x720,CODECS="vp09",AUDIO="audio"
v2/index.m3u8
"""

MEDIA = """#EXTM3U
#EXT-X-MAP:URI="init/1.m4s"
#EXTINF:14.8,
media/1.m4s
#EXTINF:10.0,
media/2.m4s
#EXT-X-ENDLIST
"""


class ParseTest(unittest.TestCase):
    def test_session_id(self):
        self.assertEqual(session_id("https://my.mts-link.ru/j/1/2/record-new/24554640907"), "24554640907")
        with self.assertRaises(ValueError):
            session_id("https://example.com/record-new/1")

    def test_parse_record(self):
        tracks, hls = parse_record(REC)
        self.assertEqual([t.id for t in tracks], [10, 11])
        self.assertEqual([t.name for t in tracks], ["Анна", "Илья Сорокин"])
        self.assertEqual((tracks[0].start, tracks[0].duration, tracks[1].duration), (5.5, 60.0, 0.0))
        self.assertEqual(hls[1], "https://h/y/playlist.m3u8")

    def test_parse_master(self):
        t = Track(id=1, name="x", start=0, duration=1)
        parse_master(t, "https://h/x/playlist.m3u8", MASTER)
        self.assertTrue(t.has_audio)
        self.assertEqual(t.audio_uri, "https://h/x/a1/index.m3u8")
        self.assertEqual([v["height"] for v in t.variants], [720, 480])  # лучшее первым
        self.assertEqual(t.variants[0]["uri"], "https://h/x/v2/index.m3u8")

    def test_parse_media_init_first(self):
        parts = parse_media("https://h/x/a1/index.m3u8", MEDIA)
        self.assertEqual(parts, ["https://h/x/a1/init/1.m4s", "https://h/x/a1/media/1.m4s", "https://h/x/a1/media/2.m4s"])

    def test_pick_variant(self):
        vs = [{"height": 720}, {"height": 480}, {"height": 240}]
        self.assertEqual(pick_variant(vs, "best")["height"], 720)
        self.assertEqual(pick_variant(vs, "500")["height"], 480)
        self.assertEqual(pick_variant(vs, "100")["height"], 240)


class FolderTest(unittest.TestCase):
    def test_folder_by_download_moment_and_unique(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(pipeline, "DOWNLOADS", Path(tmp)):
            created = time.mktime((2026, 9, 25, 16, 38, 0, 0, 0, -1))
            a = Job("u", title="Запись: 1/2", created=created)
            self.assertEqual(job_folder(a).name, "2026-09-25_1638 Запись_ 1_2")
            job_folder(a).mkdir()
            b = Job("u", title="Запись: 1/2", created=created)  # повторная загрузка в ту же минуту
            self.assertEqual(job_folder(b).name, "2026-09-25_1638 Запись_ 1_2 (2)")
            self.assertEqual(job_folder(a), Path(a.folder))  # перезапуск — та же папка

    def test_work_inside_folder(self):
        j = Job("u", folder="/d/2026-09-25_1638 X")
        self.assertEqual(str(j.work), "/d/2026-09-25_1638 X/_work")


class JobTest(unittest.TestCase):
    def test_progress_by_stage(self):
        j = Job("u", mode="audio", duration=100)
        j.status, j.seg_total, j.seg_done = "download", 10, 5
        self.assertAlmostEqual(j.progress(), 0.02 + 0.88 * 0.5)
        j.status, j.mix_pos = "mix", 50
        self.assertAlmostEqual(j.progress(), 0.90 + 0.10 * 0.5)
        j.status = "done"
        self.assertEqual(j.progress(), 1.0)

    def test_reset_keeps_folder_and_from_dict_ignores_unknown(self):
        j = Job("u", folder="/d/f", seg_done=5, outputs=[{"path": "p", "size": 1}])
        j.reset()
        self.assertEqual((j.folder, j.seg_done, j.outputs, j.status), ("/d/f", 0, [], "queued"))
        d = j.to_dict() | {"work": "legacy", "output": "legacy"}
        self.assertEqual(Job.from_dict(d).folder, "/d/f")

    def test_cached_segments_do_not_count_as_speed(self):
        j = Job("u")
        t = Track(id=1, name="x", start=0, duration=1)
        j.got_segment(t, 100, cached=True)
        self.assertEqual((j.seg_done, j.seg_cached, j._net_bytes), (1, 1, 0))


if __name__ == "__main__":
    unittest.main()
