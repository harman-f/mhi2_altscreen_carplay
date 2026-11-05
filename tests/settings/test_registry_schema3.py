"""Host tests for tools/check_registry.py (settings/registry.json schema 3)."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_registry", ROOT / "tools/check_registry.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

C_TEXT = check.C_TABLE.read_text(encoding="utf-8")


def registry():
    return copy.deepcopy(check.load_json(check.REGISTRY))


class RegistrySchema3(unittest.TestCase):
    def errors(self, reg, c_text=C_TEXT):
        return check.validate(reg, c_text)

    def assertFails(self, reg, needle, c_text=C_TEXT):
        errors = self.errors(reg, c_text)
        self.assertTrue(any(needle in e for e in errors), (needle, errors))

    def test_current_registry_is_valid(self):
        self.assertEqual(self.errors(registry()), [])

    def test_thirteen_switches_match_c_table(self):
        reg = registry()
        self.assertEqual(len(reg["switches"]), 13)
        self.assertEqual({s["id"] for s in reg["switches"]},
                         set(check.parse_c_table(C_TEXT)))
        self.assertEqual(reg["switches_pending"], [])

    def test_shared_group_between_keys_is_allowed(self):
        reg = registry()
        counts = {}
        for s in reg["settings"]:
            counts[s["storage_group"]] = counts.get(s["storage_group"], 0) + 1
        self.assertTrue(any(n > 1 for n in counts.values()))
        self.assertEqual(self.errors(reg), [])

    def test_generated_storage_paths_are_current(self):
        data = check.storage_paths(registry())
        self.assertEqual(check.STORAGE_OUT.read_text(encoding="utf-8"), data)

    def test_duplicate_writer_in_group(self):
        reg = registry()
        reg["storage_groups"][0]["writers"] = ["broker", "installer"]
        self.assertFails(reg, "exactly one writer")

    def test_switch_writer_conflicts_with_group_writer(self):
        reg = registry()
        group = {g["id"]: g for g in reg["storage_groups"]}[reg["switches"][0]["storage_group"]]
        group["writer"] = "installer"
        self.assertFails(reg, "differs from group")

    def test_evidence_enum(self):
        reg = registry()
        reg["storage_groups"][0]["evidence"]["format"] = "guess"
        self.assertFails(reg, "evidence needs")
        reg = registry()
        del reg["storage_groups"][0]["evidence"]
        self.assertFails(reg, "evidence needs")

    def test_inferred_does_not_fail(self):
        reg = registry()
        summ = check.evidence_summary(reg)
        self.assertGreater(summ["writer"].get("inferred", 0), 0)
        self.assertEqual(self.errors(reg), [])

    def test_missing_writer(self):
        reg = registry()
        del reg["storage_groups"][0]["writer"]
        self.assertFails(reg, "exactly one writer required")

    def test_shared_current_path(self):
        reg = registry()
        reg["storage_groups"][1]["current_path"] = reg["storage_groups"][0]["current_path"]
        self.assertFails(reg, "share current_path")

    def test_shared_target_path(self):
        reg = registry()
        with_target = [g for g in reg["storage_groups"] if g["target_path"]]
        with_target[1]["target_path"] = with_target[0]["target_path"]
        self.assertFails(reg, "share target_path")

    def test_target_outside_new_root(self):
        reg = registry()
        [g for g in reg["storage_groups"] if g["target_path"]][0]["target_path"] = "/mnt/app/root/other/x.conf"
        self.assertFails(reg, "target_path must be under")

    def test_null_target_requires_tbd(self):
        reg = registry()
        group = [g for g in reg["storage_groups"] if g["target_path"] is None][0]
        del group["target"]
        self.assertFails(reg, "tbd")

    def test_unknown_group_on_setting(self):
        reg = registry()
        reg["settings"][0]["storage_group"] = "no.such_group"
        self.assertFails(reg, "unknown storage_group")

    def test_unknown_group_on_switch(self):
        reg = registry()
        reg["switches"][0]["storage_group"] = "no.such_group"
        self.assertFails(reg, "unknown storage_group")

    def test_duplicate_setting_key_and_switch_id(self):
        reg = registry()
        reg["settings"].append(copy.deepcopy(reg["settings"][0]))
        reg["switches"].append(copy.deepcopy(reg["switches"][0]))
        self.assertFails(reg, "duplicate setting key")
        self.assertFails(reg, "duplicate switch id")

    def test_schema_and_layer_order(self):
        reg = registry()
        reg["schema"] = 2
        self.assertFails(reg, "schema must be 3")
        reg = registry()
        reg["layer_order"][2] = "profile"
        self.assertFails(reg, "layer_order")

    def test_c_table_drift_default(self):
        drifted = C_TEXT.replace('"on|off","off",MIBR_CONFIG_DIR "/features/sd-log.conf"',
                                 '"on|off","on",MIBR_CONFIG_DIR "/features/sd-log.conf"')
        self.assertNotEqual(drifted, C_TEXT)
        self.assertFails(registry(), "drifts from C table", drifted)

    def test_c_table_drift_new_switch(self):
        row = ('    {"MIBR_NEW_ONE/1","on|off","off",MIBR_CONFIG_DIR "/features/new-one.conf",'
               '"NEW_ONE_GET","NEW_ONE_SET","new_one",\n     "H","/tmp/x"},\n')
        drifted = C_TEXT.replace("};\nconst char *mibr_switch_platform_path", row + "};\nconst char *mibr_switch_platform_path")
        self.assertNotEqual(drifted, C_TEXT)
        self.assertFails(registry(), "missing from registry", drifted)

    def test_c_table_drift_path(self):
        drifted = C_TEXT.replace("navigation/nav-line.conf", "navigation/nav-lines.conf")
        self.assertFails(registry(), "drifts from C table", drifted)

    def test_map_target_mismatch_fails(self):
        reg = registry()
        group = next(g for g in reg["storage_groups"] if g["id"] == "features.parity_drive")
        group["target_path"] = "/mnt/app/root/mibr/config/features/parity-drive.conf"
        self.assertFails(reg, "M1 map target")

    def test_tbd_group_that_is_in_the_map_must_take_the_map_target(self):
        reg = registry()
        group = next(g for g in reg["storage_groups"] if g["id"] == "legacy.nav_surface")
        self.assertTrue(group["target_path"].endswith("/config/navigation/mibr-carplay111-nav.surface"))
        group["target_path"] = None
        group["target"] = "tbd"
        self.assertFails(reg, "M1 map target")

    def test_every_map_row_with_a_group_agrees(self):
        reg = registry()
        self.assertEqual(check.check_map(reg, {g["id"]: g for g in reg["storage_groups"]}), [])

    def test_pending_switch_may_be_absent_from_registry_switches(self):
        reg = registry()
        gone = reg["switches"].pop()
        self.assertFails(reg, "missing from registry")
        reg["switches_pending"].append({"id": gone["id"], "reason": "reader/writer lineage to be confirmed"})
        self.assertEqual(self.errors(reg), [])


class PathGate(unittest.TestCase):
    def test_today_tree_passes(self):
        self.assertEqual(check.scan_paths(registry()), [])

    def scan_tree(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, text in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            return check.scan_paths(registry(), root)

    def test_declared_paths_pass(self):
        reg = registry()
        group = reg["storage_groups"][0]["target_path"]
        volatile = reg["volatile_paths"][0]
        offenders = self.scan_tree({
            "modules/a/x.c": '#define P "%s"\n' % group,
            "tools/y.sh": "f=%s\n" % volatile})
        self.assertEqual(offenders, [])

    def test_new_persistent_path_is_an_offender(self):
        offenders = self.scan_tree({
            "modules/a/x.c": '#define P "/mnt/app/root/mibr-brand-new.conf"\n'})
        self.assertEqual([o[0] for o in offenders], ["/mnt/app/root/mibr-brand-new.conf"])

    def test_new_volatile_path_is_an_offender(self):
        offenders = self.scan_tree({"runtime/z.sh": "touch /tmp/mibr-brand-new.flag\n"})
        self.assertEqual([o[0] for o in offenders], ["/tmp/mibr-brand-new.flag"])

    def test_new_file_in_legacy_root_is_an_offender(self):
        offenders = self.scan_tree({
            "modules/a/Y.java": 'String P="/mnt/app/root/altscreen-u2/config/brand-new.conf";\n'})
        self.assertEqual(len(offenders), 1)

    def test_legacy_location_is_an_offender_outside_exempt_dirs(self):
        # M1: a group that has a map target must not be named at its legacy path.
        reg = registry()
        legacy = next(g["current_path"] for g in reg["storage_groups"]
                      if g["id"] == "features.parity_drive")
        offenders = self.scan_tree({"modules/a/x.sh": "ENABLE=%s\n" % legacy})
        self.assertEqual([o[0] for o in offenders], [legacy])

    def test_frozen_legacy_release_line_is_scan_exempt(self):
        reg = registry()
        self.assertTrue(any(e["prefix"] == "deployment/mu1440/" and e["reason"]
                            for e in reg["scan_exempt"]))
        offenders = self.scan_tree({
            "deployment/mu1440/install.sh": "DST=/mnt/app/root/altscreen-u2\n"})
        self.assertEqual(offenders, [])

    def test_new_root_literal_must_be_declared(self):
        offenders = self.scan_tree({
            "modules/a/x.c": '#define P "/mnt/app/root/mibr/config/brand-new.conf"\n'})
        self.assertEqual(len(offenders), 1)

    def test_other_extensions_and_dirs_are_not_scanned(self):
        offenders = self.scan_tree({
            "modules/a/readme.md": "/mnt/app/root/never-scanned\n",
            "docs/x.sh": "/mnt/app/root/outside-scan-dirs\n"})
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
