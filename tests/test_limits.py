import resource
import unittest

from downloader.config import MAX_WORKERS
from downloader.limits import enough_for, raise_open_files


class OpenFilesLimit(unittest.TestCase):
    def setUp(self):
        self.saved = resource.getrlimit(resource.RLIMIT_NOFILE)

    def tearDown(self):
        resource.setrlimit(resource.RLIMIT_NOFILE, self.saved)

    def test_terminal_limit_is_raised_for_max_workers(self):
        # Как у процесса из Finder/Терминала на macOS: мягкий лимит 256 (29.09: Errno 24 на 256 потоках)
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, self.saved[1]))
        got = raise_open_files()
        self.assertGreaterEqual(got, enough_for(MAX_WORKERS))
        self.assertEqual(resource.getrlimit(resource.RLIMIT_NOFILE)[0], got)

    def test_higher_limit_is_left_alone(self):
        resource.setrlimit(resource.RLIMIT_NOFILE, (4096, self.saved[1]))
        self.assertEqual(raise_open_files(want=1024), 4096)
        self.assertEqual(resource.getrlimit(resource.RLIMIT_NOFILE)[0], 4096)


if __name__ == "__main__":
    unittest.main()
