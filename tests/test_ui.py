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


if __name__ == "__main__":
    unittest.main()
