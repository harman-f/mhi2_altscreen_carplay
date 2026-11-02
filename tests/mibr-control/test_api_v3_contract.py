"""Host-only MIBR/3 contract regression. No Unit, socket, writing or streaming."""
import ast
import json
import sys
import unittest
from pathlib import Path

from public_paths import ROOT as APP, OEM_MENU, TESTS
if not (TESTS / "host_prework.py").is_file():
    raise unittest.SkipTest("Research-only API host-prework model is omitted from the public source tree")
sys.path.insert(0, str(TESTS))
import api_v3_contract as api
from host_prework import SnapshotCache

REGISTRY = APP / "settings/registry.json"
MENU = OEM_MENU / "menu-definition.json"


class ApiV3HostContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.menu = json.loads(MENU.read_text(encoding="utf-8"))
        cls.visible = list(cls.menu["native_ui_keys"])
        cls.values = {r["key"]: r["default"]["mibr_legacy"]
                      for r in cls.registry["settings"]}
        cls.sources = {key: "HOST_FIXTURE" for key in cls.values}

    def snapshot(self, *, runtime=None, persisted=False):
        return SnapshotCache(self.registry).publish({
            "revision": 22, "values": dict(self.values),
            "sources": dict(self.sources), "persisted_verified": persisted,
        }, runtime)

    def test_wire_escapes_utf8_delimiters_and_has_one_frame(self):
        original = "maps:/car/instrumentcluster/map?showCompass=yes&mode=a;b % Ü"
        encoded = api.encode_value(original)
        self.assertNotIn(" ", encoded)
        self.assertIn("%3A", encoded)
        self.assertIn("%3B", encoded)
        self.assertEqual(api.decode_value(encoded), original)
        req = api.request("gesture_72", "SET",
                          {"key": "navigation.url", "value": original,
                           "expected_revision": "22", "activation": "AUTO"})
        parsed = api.parse(req)
        self.assertEqual(parsed["request_id"], "gesture_72")
        self.assertEqual(parsed["fields"]["value"], original)
        self.assertEqual(parsed["kind"], "SET")
        self.assertEqual(api.parse(api.response("gesture_72",
                          {"stored": "VERIFIED", "apply": "PENDING"}),
                          is_response=True)["fields"]["apply"], "PENDING")
        scale = api.parse(api.request("scale_1", "SCALE_SET", {
            "id": "scaling.cluster.zoomFactor", "value": "AUTO",
            "expected_revision": "0", "request_id": "scale_1"}))
        self.assertEqual(scale["kind"], "SCALE_SET")
        self.assertEqual(scale["fields"]["value"], "AUTO")

    def test_invalid_encoding_duplicates_frames_and_versions_fail_closed(self):
        bad = [
            b"MIBR/3 x GET key=bad%0a\n",
            b"MIBR/3 x GET key=bad%0A\n",
            b"MIBR/3 x GET key=bad%ZZ\n",
            b"MIBR/3 x GET key=bad;key=again\n",
            b"MIBR/3 x GET key=bad value=one\n",
            b"MIBR/3 x GET key=bad\r\n",
            b"MIBR/3 x GET key=%FF\n",
            b"MIBR/3 x GET key=bad%\n",
            b"MIBR/3 x GET key=bad\nextra\n",
            b"MIBR/3 x GET key=bad;role=ui;role=shell\n",
            b"MIBR/3 x GET key=bad\n\x00",
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(api.FrameError):
                api.parse(value)
        with self.assertRaisesRegex(api.FrameError, "UNSUPPORTED_VERSION"):
            api.parse(b"MIBR/2 x HELLO\n")
        with self.assertRaises(api.FrameError):
            api.parse(b"MIBR/3 x HELLO " + b"a" * 4096 + b"\n")
        with self.assertRaises(api.FrameError):
            api.request("bad id", "GET", {"key": "maxFPS"})
        with self.assertRaises(api.FrameError):
            api.response("r1", error="MADE_UP_SUCCESS")

    def test_exact_11_and_48_registry_key_projection(self):
        snap = self.snapshot()
        fields = api.snapshot_fields(snap, self.registry, self.visible)
        self.assertEqual(fields["row_count"], "11")
        self.assertEqual(fields["revision"], "22")
        self.assertEqual(fields["stored"], "UNCONFIRMED")
        self.assertEqual(fields["connected"], "UNKNOWN")
        self.assertEqual(fields["row.0.key"], self.visible[0])
        self.assertEqual(fields["row.0.active"], "UNKNOWN")
        out = api.read_only_host(api.request("snap_1", "SNAPSHOT",
                                              {"scope": "ui"}),
                                 snap, self.registry, self.visible)
        parsed = api.parse(out, is_response=True)
        self.assertEqual(parsed["fields"]["row_count"], "11")
        self.assertEqual(parsed["fields"]["phase"], "HOST_ONLY_NO_IO")
        self.assertLessEqual(len(out), api.RESPONSE_MAX)
        all_fields = api.snapshot_fields(snap, self.registry, self.visible,
                                         scope="all", role="shell")
        self.assertEqual(all_fields["row_count"], "48")
        self.assertEqual({all_fields["row.%s.key" % i] for i in range(48)},
                         set(self.values))
        self.assertLessEqual(len(api.response("a", all_fields)), api.RESPONSE_MAX)
        with self.assertRaisesRegex(api.FrameError, "FORBIDDEN"):
            api.snapshot_fields(snap, self.registry, self.visible, scope="all", role="ui")
        denied = api.read_only_host(api.request("snap_2", "SNAPSHOT",
                                                {"scope": "all"}),
                                    snap, self.registry, self.visible)
        self.assertEqual(api.parse(denied, is_response=True)["error"], "FORBIDDEN")

    def test_runtime_is_not_fabricated_from_desired(self):
        snap = self.snapshot(runtime={"desired_revision": 21,
                                      "active_confirmed": True,
                                      "connected": True,
                                      "session_id": "old",
                                      "generation": 1,
                                      "active_session_id": "old",
                                      "active_generation": 1,
                                      "active": dict(self.values)},
                             persisted=True)
        fields = api.snapshot_fields(snap, self.registry, self.visible)
        self.assertEqual(fields["stored"], "VERIFIED")
        self.assertEqual(fields["runtime_correlated"], "0")
        self.assertEqual(fields["connected"], "UNKNOWN")
        self.assertEqual(fields["row.0.active"], "UNKNOWN")
        self.assertEqual(fields["durable_generation"], "UNKNOWN")
        self.assertEqual(fields["pending"], "UNKNOWN")
        rt = {"desired_revision": 22, "connected": True,
              "session_id": "S", "generation": 3, "active_confirmed": True,
              "active_session_id": "S", "active_generation": 3,
              "active": dict(self.values), "advertised": dict(self.values)}
        good = api.snapshot_fields(self.snapshot(runtime=rt), self.registry, self.visible)
        self.assertEqual(good["runtime_correlated"], "1")
        self.assertEqual(good["row.0.active"], self.values[self.visible[0]])
        rt["active_generation"] = 2
        bad = api.snapshot_fields(self.snapshot(runtime=rt), self.registry, self.visible)
        self.assertEqual(bad["row.0.active"], "UNKNOWN")

    def test_host_capabilities_and_mutations_remain_blocked(self):
        snap = self.snapshot()
        for op in ("HELLO", "CAPABILITIES", "STATUS"):
            out = api.read_only_host(api.request("a", op), snap, self.registry, self.visible)
            parsed = api.parse(out, is_response=True)
            self.assertIsNone(parsed["error"])
            self.assertEqual(parsed["fields"]["phase"], "HOST_ONLY_NO_IO")
        for op in ("SET", "BATCH", "RESET", "TEST_SET", "TEST_CLEAR",
                   "TEST_LIST", "ACTIVATE", "REQUEST_STATUS", "GET"):
            out = api.read_only_host(api.request("b", op, {"key": "maxFPS"}),
                                     snap, self.registry, self.visible)
            self.assertEqual(api.parse(out, is_response=True)["error"], "POLICY_BLOCKED")
        out = api.read_only_host(api.request("c", "SNAPSHOT", {"bogus": "1"}),
                                 snap, self.registry, self.visible)
        self.assertEqual(api.parse(out, is_response=True)["error"], "INVALID_REQUEST")

    def test_reference_contains_no_external_io_or_write_primitives(self):
        source = (APP / "control/api_v3_contract.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                modules.extend(n.name.split(".")[0] for n in node.names)
            if isinstance(node, ast.ImportFrom):
                modules.append((node.module or "").split(".")[0])
        self.assertFalse(set(modules) & {"socket", "subprocess", "os", "pathlib",
                                          "ctypes", "sqlite3", "http", "requests"})
        self.assertNotIn("persistent_backup_powerloss_gate", source)
        self.assertNotIn("mount -uw", source)


if __name__ == "__main__":
    unittest.main()
