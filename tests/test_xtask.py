"""Сборщик канона: разбор _ctx.md и валидатор на временном мини-проекте."""
import tempfile
import unittest
from pathlib import Path

from tools.canon import SECTIONS, parse_ctx
from tools.render import build_data, render_root


def ctx(body_tasks="- [ ] 🔴 01.10 срочно\n- [ ] без срока", extra=""):
    sections = {s: "-" for s in SECTIONS}
    sections.update({"НАЗНАЧЕНИЕ": "Тест.", "СТАТУС": "в работе", "ЗАДАЧИ": body_tasks,
                     "ПЕЧАТИ": "Ъ — решено", "ОТКРЫТО": "❓ вопрос", "ЖДУНЫ": "⏳ ждём", "ТЕХДОЛГ": "- долг"})
    return "# mod\nСлой: БЭКЕНД\n\n" + "\n".join(f"## {k}\n{v}\n" for k, v in sections.items()) + extra


def project(tmp: Path, ctx_text: str, code_lines=10):
    (tmp / "mod").mkdir()
    (tmp / "mod" / "_ctx.md").write_text(ctx_text)
    (tmp / "mod" / "x.py").write_text("x = 1\n" * code_lines)
    (tmp / "CLAUDE.md").write_text("# Проект\n")
    (tmp / "spec.md").write_text("# spec\n")
    (tmp / "roadmap.md").write_text("1. [готово] Старт — было\n2. [сейчас] Канон — идёт\n")
    (tmp / "arhiv.md").write_text("25.09 · [mod] · сделано\n")


class CanonTest(unittest.TestCase):
    def test_parse_ctx(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "_ctx.md"
            p.write_text(ctx())
            m = parse_ctx(p)
            self.assertEqual((m["layer"], m["status"]), ("БЭКЕНД", "в работе"))
            self.assertEqual(m["tasks"][0], {"red": True, "due": "01.10", "text": "срочно"})
            self.assertEqual(m["tasks"][1]["due"], "")

    def test_green_project(self):
        with tempfile.TemporaryDirectory() as t:
            project(Path(t), ctx())
            data = build_data(Path(t))
            self.assertEqual(data["check"]["errors"], [])
            root = render_root(data)
            self.assertIn("Сейчас: **2. Канон**", root)
            self.assertIn("- 01.10 [mod] срочно", root)

    def test_violations(self):
        with tempfile.TemporaryDirectory() as t:
            project(Path(t), ctx("- [ ] 🔴 без даты\n- [x] закрыто"), code_lines=201)
            errors = "\n".join(build_data(Path(t))["check"]["errors"])
            self.assertIn("🔴-задача без срока", errors)
            self.assertIn("закрытая строка", errors)
            self.assertIn("mod/x.py: 201 строк", errors)

    def test_missing_section(self):
        with tempfile.TemporaryDirectory() as t:
            project(Path(t), ctx().replace("## НЕ ТРОГАТЬ", "## ПРОЧЕЕ"))
            self.assertTrue(any("нет разделов НЕ ТРОГАТЬ" in e for e in build_data(Path(t))["check"]["errors"]))


if __name__ == "__main__":
    unittest.main()
