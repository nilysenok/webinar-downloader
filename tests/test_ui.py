import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

UI = Path(__file__).resolve().parent.parent / "ui"


class Favicon(unittest.TestCase):
    def test_page_links_a_valid_svg_icon(self):
        html = (UI / "index.html").read_text(encoding="utf-8")
        link = re.search(r'<link rel="icon" href="([^"]+)" type="image/svg\+xml">', html)
        self.assertIsNotNone(link, "в <head> нет фавиконки")
        root = ET.parse(UI / link.group(1)).getroot()
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(root.get("viewBox"), "0 0 32 32")


class Icons(unittest.TestCase):
    """Один набор иконок (icons.js): текстовые символы вместо иконок в каждом шрифте разной толщины и высоты."""

    def sources(self):
        return {p.name: p.read_text(encoding="utf-8") for p in [*UI.glob("*.js"), UI / "index.html"] if p.name != "icons.js"}

    def test_no_glyphs_instead_of_icons(self):
        for name, text in self.sources().items():
            for glyph in "▶↓✕›":
                self.assertNotIn(glyph, text, f"{name}: символ «{glyph}» — нужна иконка из icons.js")

    def test_every_used_icon_exists(self):
        known = set(re.findall(r"^  (\w+): '", (UI / "icons.js").read_text(encoding="utf-8"), re.M))
        used = set()
        for text in self.sources().values():
            used |= set(re.findall(r'icon\("(\w+)"', text)) | set(re.findall(r'data-icon="(\w+)"', text))
        self.assertTrue(used, "иконки не найдены — поменялся способ вызова?")
        self.assertLessEqual(used, known, f"нет в icons.js: {used - known}")


if __name__ == "__main__":
    unittest.main()
