"""Скрипты канона (scripts/kanon) на временных файлах."""
import tempfile
import unittest
from pathlib import Path

from scripts.kanon import sverka_blokov


class SverkaTest(unittest.TestCase):
    def test_blocks_without_receipt(self):
        text = ("## Ж-001 · а\nтекст\n\nпринят Ж-001, 16:04 (задним числом)\n\n"
                "## Ж-002 · б\nтекст\n\nпринят Ж-001, 16:05\n\n## Ж-003 · в\nтекст\n\nпринят Ж-003, 16:20\n")
        self.assertEqual(sverka_blokov.bloki(text), [("001", True, True), ("002", False, False), ("003", True, False)])

    def test_exit_code(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "r.md"
            p.write_text("## Ж-001 · а\nпринят Ж-001, 10:00\n", encoding="utf-8")
            self.assertEqual(sverka_blokov.main([str(p)]), 0)
            p.write_text("## Ж-001 · а\nбез квитанции\n", encoding="utf-8")
            self.assertEqual(sverka_blokov.main([str(p)]), 1)


if __name__ == "__main__":
    unittest.main()
