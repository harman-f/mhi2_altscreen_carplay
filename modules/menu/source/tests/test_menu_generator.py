import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[2]
REGISTRY_PATH = REPO / "settings/registry.json"
GENERATOR_PATH = HERE / "generate_catalog.py"
MENU_PATH = HERE / "menu-definition.json"
OUTPUT_PATH = HERE / "java/de/mibr/hmi"

spec = importlib.util.spec_from_file_location("generate_catalog", GENERATOR_PATH)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class MenuGeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="mibr-menu-generator-")
        cls.root = Path(cls.temp.name)
        cls.registry = REGISTRY_PATH

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def menu_copy(self):
        return json.loads(MENU_PATH.read_text(encoding="utf-8"))

    def write_menu(self, menu, path):
        path.write_text(json.dumps(menu, ensure_ascii=True, indent=2) + "\n",
                        encoding="utf-8", newline="\n")

    def run_main(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = generator.main(list(args))
        return result, output.getvalue()

    def test_outputs_are_deterministic_and_menu_definition_matches_source(self):
        out = self.root / "generated"
        args = ("--registry", str(self.registry), "--menu", str(MENU_PATH),
                "--out-dir", str(out))
        self.assertEqual(0, self.run_main(*args)[0])
        catalog = out / "MibrSettingsCatalog.java"
        definition = out / "MibrMenuDefinition.java"
        # This generator retains the legacy registry projection. The current
        # authored RGI menu also has cockpit/safe-area/version pages; never
        # overwrite that production snapshot with the legacy projection.
        authored = (OUTPUT_PATH / "MibrMenuDefinition.java").read_text(encoding="utf-8")
        for group in ("nav_hints", "safe_voll", "safe_wide", "safe_center", "version"):
            self.assertIn('"' + group + '"', authored)
        catalog_text = catalog.read_text(encoding="utf-8")
        self.assertIn('"20|25|30|40|60"', catalog_text)
        self.assertIn('"unit_reboot"', catalog_text)
        first = (catalog.read_bytes(), definition.read_bytes())
        self.assertEqual(0, self.run_main(*args)[0])
        self.assertEqual(first, (catalog.read_bytes(), definition.read_bytes()))

        definition_text = definition.read_text(encoding="utf-8")
        self.assertIn('TITLE_DE="CarPlay-Einstellungen"', definition_text)
        self.assertIn('TITLE_EN="CarPlay settings"', definition_text)
        self.assertIn('GROUP_IDS={\n  "views",\n  "advanced",\n  "diagnostics"', definition_text)
        self.assertIn('ROOT_KEYS={\n  "viewarea.selected",\n  "navigation.surface"', definition_text)
        self.assertIn('{"carplay.enabled", "maxFPS", "sourceVersion"}', definition_text)
        visible = definition_text.split("VISIBLE_KEYS={", 1)[1].split("};", 1)[0]
        native = definition_text.split("NATIVE_UI_KEYS={", 1)[1].split("};", 1)[0]
        self.assertEqual(9, visible.count('"') // 2)
        self.assertEqual(11, native.count('"') // 2)
        self.assertNotIn("navigation.url", visible)
        self.assertNotIn("preset.id", visible)
        self.assertIn('"maxFPS",\n  "sourceVersion"', native)
        self.assertIn('VIRTUAL_PAGE_IDS={\n  "scaling"', definition_text)
        self.assertIn('"Zoomfaktor Hauptdisplay"', definition_text)
        self.assertIn("VIRTUAL_PAGE_NOTICES_DE", definition_text)
        self.assertIn("VIRTUAL_PAGE_NOTICES_EN", definition_text)
        self.assertIn("virtualPageNotice(int page)", definition_text)
        self.assertIn("Changes are sent on the next CarPlay connection.", definition_text)
        self.assertNotIn("scaling.main.zoomFactor", visible)
        self.assertNotIn("scaling.cluster.zoomFactor", native)
        self.assertTrue(all(byte < 128 for byte in definition.read_bytes()))

    def test_check_normalizes_line_endings_and_detects_drift(self):
        out = self.root / "check"
        args = ("--registry", str(self.registry), "--menu", str(MENU_PATH),
                "--out-dir", str(out))
        self.run_main(*args)
        for path in out.glob("*.java"):
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(0, self.run_main("--check", *args)[0])
        path = out / "MibrMenuDefinition.java"
        path.write_text(path.read_text(encoding="utf-8").replace("CarPlay-Einstellungen", "Changed"),
                        encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(SystemExit, "GENERATED_SOURCE_MISMATCH"):
            self.run_main("--check", *args)

    def test_invalid_overlay_mutations_fail_closed(self):
        cases = []

        unknown = self.menu_copy()
        unknown["sections"][1]["keys"][0] = "invented.setting"
        cases.append((unknown, "MENU_UNKNOWN_KEY"))

        duplicate = self.menu_copy()
        duplicate["sections"][1]["keys"].append("carplay.enabled")
        cases.append((duplicate, "MENU_DUPLICATE_KEY"))

        duplicate_group = self.menu_copy()
        duplicate_group["sections"][2]["id"] = "advanced"
        cases.append((duplicate_group, "MENU_GROUP_DUPLICATE_OR_INVALID"))

        missing_visible = self.menu_copy()
        missing_visible["sections"][1]["keys"].pop()
        cases.append((missing_visible, "MENU_VISIBILITY_POLICY_INVALID"))

        hidden_promotion = self.menu_copy()
        hidden_promotion["sections"][1]["keys"].append("navigation.query")
        cases.append((hidden_promotion, "MENU_VISIBILITY_POLICY_INVALID"))

        extra_scaling_row = self.menu_copy()
        extra_scaling_row["virtual_pages"][0]["controls"].append(copy.deepcopy(extra_scaling_row["virtual_pages"][0]["controls"][0]))
        cases.append((extra_scaling_row, "MENU_VIRTUAL_PAGE_POLICY_INVALID"))

        renamed_auto_control = self.menu_copy()
        renamed_auto_control["virtual_pages"][0]["controls"][0]["id"] = "scaling.main.displayScaleMode"
        cases.append((renamed_auto_control, "MENU_VIRTUAL_PAGE_POLICY_INVALID"))

        unauthorized = self.menu_copy()
        unauthorized["defaults"] = {"carplay.enabled": "0"}
        cases.append((unauthorized, "MENU_FIELDS_INVALID"))

        reordered_root = self.menu_copy()
        reordered_root["root"] = list(reversed(reordered_root["root"]))
        cases.append((reordered_root, "MENU_ROOT_POLICY_INVALID"))

        url_visible = self.menu_copy()
        url_visible["sections"][1]["keys"].append("navigation.url")
        cases.append((url_visible, "MENU_VISIBILITY_POLICY_INVALID"))

        native_shrunk = self.menu_copy()
        native_shrunk["native_ui_keys"].remove("navigation.url")
        cases.append((native_shrunk, "MENU_NATIVE_UI_PROJECTION_INVALID"))

        bad_schema = self.menu_copy()
        bad_schema["schema"] = 1.0
        cases.append((bad_schema, "MENU_SCHEMA_INVALID"))
        bad_title = self.menu_copy()
        bad_title["title"]["en"] = "Title\nInjected"
        cases.append((bad_title, "MENU_TITLE_INVALID"))
        bad_label = self.menu_copy()
        bad_label["labels"]["carplay.enabled"]["en"] = "x" * 81
        cases.append((bad_label, "MENU_LABEL_VALUE_INVALID"))

        for index, (menu, error) in enumerate(cases):
            with self.subTest(error=error, index=index):
                path = self.root / ("invalid-" + str(index) + ".json")
                self.write_menu(menu, path)
                with self.assertRaisesRegex(ValueError, error):
                    generator.load_inputs(self.registry, path)

    def test_duplicate_json_fields_are_rejected(self):
        path = self.root / "duplicate-field.json"
        path.write_text(
            '{"schema":1,"schema":1,"target":"MU1440_SSM_5458",'
            '"title":"x","sections":[],"labels":{}}', encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_FIELD"):
            generator.load_inputs(self.registry, path)


if __name__ == "__main__":
    unittest.main()
