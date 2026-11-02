"""Offline only: no filesystem writes, sockets, Unit, CarPlay commands or actual SAVE."""
import json
import sys
import unittest
from pathlib import Path

from public_paths import ROOT as APP, OEM_MENU, TESTS
if not (TESTS / "host_prework.py").is_file():
    raise unittest.SkipTest("Research-only host-prework model is omitted from the public source tree")
sys.path.insert(0, str(TESTS))
from host_prework import (ContractError, SnapshotCache, DryRunPlanner,
                          activation_projection, presentation_ack)

REGISTRY = APP / "settings/registry.json"
MENU = OEM_MENU / "menu-definition.json"


class HostPrework(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.menu = json.loads(MENU.read_text(encoding="utf-8"))
        cls.visible = list(cls.menu["native_ui_keys"])
        assert len(cls.visible) == 11
        cls.fixture = {r["key"]: r["default"]["mibr_legacy"] for r in cls.reg["settings"]}

    def setUp(self):
        self.cache = SnapshotCache(self.reg)
        self.vals = dict(self.fixture)

    def core(self, revision=3, persisted=True):
        return {"revision": revision, "values": dict(self.vals),
                "sources": {k: "HOST_FIXTURE" for k in self.vals},
                "persisted_verified": persisted}

    def runtime(self, revision=3, active=None, connected=True,
                session="host-session-A", generation=7):
        return {"desired_revision": revision, "connected": connected,
                "session_id": session, "generation": generation,
                "active_confirmed": True, "active_session_id": session,
                "active_generation": generation,
                "active": dict(self.fixture if active is None else active),
                "advertised": dict(self.fixture)}

    def test_registry_and_snapshot_immutability(self):
        s = self.cache.publish(self.core(), self.runtime())
        self.assertEqual(len(s.values), 48)
        self.assertTrue(s.runtime_correlated and s.active_verified)
        self.assertTrue(s.persisted_verified)
        self.assertIs(self.cache.read(), s)
        with self.assertRaises(TypeError):
            s.values["maxFPS"] = "20"
        self.vals["maxFPS"] = "20"
        self.assertNotEqual(s.values["maxFPS"], "20")

    def test_no_partial_group_or_synthetic_values(self):
        core = self.core()
        del core["values"]["maxFPS"]
        with self.assertRaisesRegex(ContractError, "INCOMPLETE_CANONICAL_GROUP"):
            self.cache.publish(core)
        core = self.core()
        core["values"]["maxFPS"] = None
        with self.assertRaisesRegex(ContractError, "UNOBSERVED_VALUE"):
            self.cache.publish(core)

    def test_runtime_revision_and_generation_stale_fail_closed(self):
        s = self.cache.publish(self.core(), self.runtime(revision=2))
        self.assertFalse(s.runtime_correlated or s.active_verified)
        self.assertEqual(dict(s.active), {})
        wrong = self.runtime()
        wrong["active_generation"] = 6
        s = self.cache.publish(self.core(), wrong)
        self.assertTrue(s.runtime_correlated)
        self.assertFalse(s.active_verified)
        with self.assertRaisesRegex(ContractError, "STALE_CORE_REVISION"):
            self.cache.publish(self.core(revision=2), self.runtime(revision=2))

    def test_cas_idempotence_and_test_override(self):
        s = self.cache.publish(self.core(), self.runtime())
        p = DryRunPlanner(self.reg, self.visible)
        change = p.plan(s, key="navigation.compass", value="yes",
                        expected_revision=3, request_id="gesture-1")
        self.assertEqual(change["state"], "WOULD_REQUIRE_QUALIFIED_NATIVE_COMMIT_NO_IO")
        self.assertEqual(change["durability"], "NOT_ATTEMPTED")
        self.assertEqual(p.plan(s, key="navigation.compass", value="yes",
                        expected_revision=3, request_id="gesture-1")["state"],
                         "SAME_DRY_RUN_REQUEST_NO_IO")
        with self.assertRaisesRegex(ContractError, "IDEMPOTENCY_COLLISION"):
            p.plan(s, key="navigation.compass", value="no",
                   expected_revision=3, request_id="gesture-1")
        with self.assertRaisesRegex(ContractError, "STALE_REVISION"):
            p.plan(s, key="maxFPS", value="20", expected_revision=2, request_id="gesture-2")
        with self.assertRaisesRegex(ContractError, "OVERRIDE_ACTIVE"):
            p.plan(s, key="maxFPS", value="20", expected_revision=3,
                   request_id="gesture-3", overrides=("maxFPS",))

    def test_value_and_hidden_key_guards(self):
        s = self.cache.publish(self.core(), self.runtime())
        p = DryRunPlanner(self.reg, self.visible)
        cases = (("navigation.compass", "maybe", "INVALID_VALUE"),
                 ("maxFPS", "35", "INVALID_VALUE"),
                 ("viewarea.selected", "2", "INTEGER_OUT_OF_RANGE"),
                 ("carplay.enabled", "01", "INVALID_INTEGER"),
                 ("sourceVersion", "9999.9.9", "UNAPPROVED_SOURCE_CANDIDATE"),
                 ("navigation.url", "not-qualified-url", "UNQUALIFIED_RECEIVER_DOMAIN"),
                 ("navigation.query", "1", "KEY_NOT_WRITABLE_IN_MENU"))
        for i, (key, value, reason) in enumerate(cases):
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ContractError, reason):
                p.plan(s, key=key, value=value, expected_revision=3, request_id="bad-"+str(i))

    def test_reconnect_coalesce_revert_and_disconnected(self):
        s = self.cache.publish(self.core(), self.runtime())
        self.assertEqual(activation_projection(s, self.reg)["state"], "ACTIVE_MATCHED")
        self.vals["maxFPS"] = "20"
        s = self.cache.publish(self.core(4), self.runtime(4))
        one = activation_projection(s, self.reg, reconnect_capability=True)
        self.assertEqual(one["pending"], ("maxFPS",))
        self.assertFalse(one["can_reconnect_now"] or one["unit_reboot"])
        self.vals["sourceVersion"] = "950.7.1"
        s = self.cache.publish(self.core(5), self.runtime(5))
        two = activation_projection(s, self.reg)
        self.assertEqual(two["pending"], ("maxFPS", "sourceVersion"))
        self.vals["maxFPS"] = self.fixture["maxFPS"]
        self.vals["sourceVersion"] = self.fixture["sourceVersion"]
        s = self.cache.publish(self.core(6), self.runtime(6))
        self.assertEqual(activation_projection(s, self.reg)["state"], "ACTIVE_MATCHED")
        s = self.cache.publish(self.core(7), self.runtime(7, connected=False))
        self.assertEqual(activation_projection(s, self.reg)["state"], "NEXT_CONNECTION")

    def test_stale_show_completion_never_applied(self):
        self.vals["navigation.compass"] = "yes"
        s = self.cache.publish(self.core(), self.runtime())
        common = dict(request_session="host-session-A", request_generation=7,
                      completion_session="host-session-A", completion_generation=7,
                      completed_successfully=True, key="navigation.compass", observed_active=True)
        self.assertEqual(presentation_ack(s, **common), "APPLY_PENDING")
        self.assertEqual(presentation_ack(s, **dict(common, completion_generation=6)),
                         "STALE_SESSION")
        self.assertEqual(presentation_ack(s, **dict(common, completed_successfully=False)),
                         "APPLY_PENDING")
        live = dict(self.fixture)
        live["navigation.compass"] = "yes"
        s = self.cache.publish(self.core(4), self.runtime(4, active=live))
        self.assertEqual(presentation_ack(s, **common), "ACTIVE")
        self.assertEqual(presentation_ack(s, **dict(common, observed_active=False)),
                         "AWAIT_INDEPENDENT_ACTIVE_READBACK")


if __name__ == "__main__":
    unittest.main()
