"""Read-only guard on current 48-key apply metadata for the future controller.

This does NOT test durability, runtime effect, a reconnect mechanism or a Unit.
It simply freezes the exact input contract before any product implementation.
"""
import json
import unittest
from collections import Counter
from pathlib import Path

from public_paths import ROOT as APP, OEM_MENU
REGISTRY = APP / "settings/registry.json"
MENU = OEM_MENU / "menu-definition.json"


class ActivationProductPreworkContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.menu = json.loads(MENU.read_text(encoding="utf-8"))
        cls.rows = {r["key"]: r for r in cls.reg["settings"]}

    def test_original_schema_and_exact_apply_counts(self):
        self.assertEqual(self.reg["schema"], 2)
        self.assertEqual(len(self.rows), 48)
        self.assertEqual(len(self.reg["settings"]), len(self.rows))
        self.assertEqual(Counter(r["apply"] for r in self.rows.values()),
                         {"live": 6, "presentation": 7, "session": 3, "reconnect": 29,
                          "unit_reboot": 3})
        self.assertEqual({key for key, row in self.rows.items()
                          if row["apply"] == "unit_reboot"}, {"maxFPS", "keyframe.mode", "keyframe.interval_frames"})

    def test_visible_keys_project_into_three_ui_activation_buckets(self):
        groups = self.menu["sections"]
        visible = list(self.menu["native_ui_keys"])
        self.assertEqual(len(visible), 11)
        self.assertEqual(len(set(visible)), 11)
        self.assertEqual(set(visible) - set(self.rows), set())
        count = Counter(self.rows[k]["apply"] for k in visible)
        self.assertEqual(count, {"presentation": 6, "live": 1, "reconnect": 2,
                                 "session": 1, "unit_reboot": 1})
        self.assertEqual(self.rows["navigation.compass"]["apply"], "presentation")
        self.assertEqual(self.rows["maxFPS"]["apply"], "unit_reboot")
        self.assertEqual(self.rows["sourceVersion"]["apply"], "reconnect")
        self.assertEqual(self.rows["carplay.enabled"]["apply"], "session")

    def test_current_view_and_startup_default_are_not_same_action(self):
        self.assertEqual(self.rows["viewarea.selected"]["apply"], "live")
        self.assertEqual(self.rows["viewareas.initial"]["apply"], "reconnect")
        self.assertNotIn("viewareas.initial",
                         list(self.menu["native_ui_keys"]))

    def test_no_false_boolean_and_maxfps_reboot_classification(self):
        for key in ("navigation.compass", "navigation.ETA", "navigation.speedLimit"):
            self.assertEqual(self.rows[key]["allowed"], ["yes", "no", "user"])
        self.assertTrue(self.rows["legacy.autodirect"]["read_only"])
        self.assertEqual(set(r["apply"] for r in self.rows.values()),
                         {"live", "presentation", "session", "reconnect", "unit_reboot"})
        self.assertEqual(self.rows["maxFPS"]["allowed"], ["20", "25", "30", "40", "60"])


if __name__ == "__main__":
    unittest.main()
