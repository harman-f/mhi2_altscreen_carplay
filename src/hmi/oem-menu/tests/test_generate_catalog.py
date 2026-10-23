import sys
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[2]
sys.path.insert(0, str(MODULE))
import generate_catalog


class CatalogGenerationTest(unittest.TestCase):
    def test_current_canonical_registry_and_menu_are_compatible(self):
        digest, settings, menu = generate_catalog.load_inputs(
            REPO / "settings/registry.json", MODULE / "menu-definition.json")
        self.assertEqual(len(settings), 48)
        self.assertEqual(len({entry["key"] for entry in settings}), 48)
        self.assertEqual(tuple(menu["native_ui_keys"]), generate_catalog.EXPECTED_NATIVE_UI)
        self.assertEqual(tuple(section["id"] for section in menu["sections"]),
                         ("views", "advanced", "diagnostics"))
        self.assertEqual(menu["sections"][0]["keys"], [])
        self.assertIn('"Ansichten"', generate_catalog.render_menu(menu))
        catalog = generate_catalog.render_catalog(settings, menu)
        self.assertIn('"viewareas.count"', catalog)
        self.assertTrue(digest)


if __name__ == "__main__":
    unittest.main()
