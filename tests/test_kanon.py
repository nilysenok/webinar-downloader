"""Скрипты канона (scripts/kanon) на временных файлах."""
import re
import tempfile
import unittest
from pathlib import Path

from scripts.kanon import sverka_blokov, validate_zadanie


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


class ValidateZadanieTest(unittest.TestCase):
    """Ж-004 2.2: задание без любого из полей — отказ; образец — проходит."""
    good = Path("templates/examples/horoshee_zadanie.md").read_text(encoding="utf-8")

    def test_good_example_passes(self):
        self.assertEqual(validate_zadanie.problems(self.good), [])

    def test_each_field_is_required(self):
        for field in validate_zadanie.FIELDS:
            broken = re.sub(rf"^## \d+\. {field}$", "## 0. Убрано", self.good, flags=re.M)
            self.assertTrue(any(field in e for e in validate_zadanie.problems(broken)), field)

    def test_placeholders_hash_and_questions(self):
        self.assertIn("поле «Владение» пустое (заглушка шаблона)",
                      validate_zadanie.problems(self.good.replace("- `tests/test_mutatsii.py` (создать)", "- <путь>")))
        self.assertIn("у входов нет sha256", validate_zadanie.problems(re.sub(r"sha256 [0-9a-f]+", "sha256 ?", self.good)))
        self.assertIn("нет вопроса «подписывает»", validate_zadanie.problems(self.good.replace("подписывает", "решает")))
