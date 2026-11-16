"""Keep the editor catalog, generated unit catalog and standard menu in sync."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "modules/menu/source"
SPEC = importlib.util.spec_from_file_location(
    "generate_menu_catalog", SOURCE / "generate_menu_catalog.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class MenuLayoutGenerationTest(unittest.TestCase):
    def test_checked_in_outputs_match_editor_catalog(self):
        with tempfile.TemporaryDirectory(prefix="mibr-menu-layout-") as out:
            generated = Path(out)
            old_standard, old_java = GENERATOR.STANDARD, GENERATOR.JAVA
            try:
                GENERATOR.STANDARD = generated / "standard-menu.txt"
                GENERATOR.JAVA = generated / "MibrMenuCatalog.java"
                GENERATOR.main()
            finally:
                GENERATOR.STANDARD, GENERATOR.JAVA = old_standard, old_java
            for actual, expected in (
                (generated / "standard-menu.txt", old_standard),
                (generated / "MibrMenuCatalog.java", old_java),
            ):
                self.assertEqual(actual.read_text(encoding="utf-8"),
                                 expected.read_text(encoding="utf-8"), str(expected))


if __name__ == "__main__":
    unittest.main()
