"""Regression tests for Money Hunter's HTML smoke-test checks."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from app_maintenance_bot import inspect_markup

class MoneyHunterSmokeTests(unittest.TestCase):
    def test_main_page_navigation_and_assets(self):
        path=ROOT/"money-hunter/index.html"
        findings=inspect_markup(path,path.read_text(encoding="utf-8"))
        codes={item["code"] for item in findings}
        self.assertNotIn("duplicate_html_ids",codes)
        self.assertNotIn("missing_navigation_targets",codes)
        self.assertNotIn("broken_navigation_tabs",codes)
        self.assertNotIn("missing_script_asset",codes)

    def test_duplicate_ids_are_detected(self):
        path=ROOT/"money-hunter/index.html"
        findings=inspect_markup(path,'<main id="home"></main><div id="home"></div>')
        self.assertIn("duplicate_html_ids",{item["code"] for item in findings})

    def test_broken_navigation_is_detected(self):
        path=ROOT/"money-hunter/index.html"
        findings=inspect_markup(path,'<button data-tab="pricing"></button>')
        self.assertIn("broken_navigation_tabs",{item["code"] for item in findings})

if __name__=="__main__":
    unittest.main()
