"""Phase C is a bounded host-only CONTRACT model; no production mutator."""
from pathlib import Path
import sys
import unittest

C = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C))
if not (C / "mock_mibr_control.py").is_file() or not (C / "offline_phase_c_contract.py").is_file():
    raise unittest.SkipTest("Research-only phase-C mock model is omitted from the public source tree")
from mock_mibr_control import load_registry, response
from offline_phase_c_contract import PhaseCModel, ContractError


class OfflinePhaseCContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()

    def setUp(self):
        self.m = PhaseCModel(self.registry)

    def tearDown(self):
        self.m.close()

    def test_unknown_never_becomes_false_or_persisted_default(self):
        for key in self.registry:
            state = self.m.get(key)
            self.assertEqual(state["desired"], "UNCONFIRMED")
            self.assertEqual(state["effective"], "UNCONFIRMED")
            self.assertEqual(state["stored"], "UNCONFIRMED")
            self.assertEqual(state["origin"], "HOST_SYNTHETIC_ONLY")
        self.assertEqual(self.m.revision, 0)

    def test_set_ack_simulated_only_with_exact_revision(self):
        p = self.m.set("carplay.enabled", "1", expected_revision=0)
        self.assertFalse(p["vehicle_ack"])
        self.assertFalse(p["written"])
        self.assertEqual(self.m.get("carplay.enabled")["effective"], "UNCONFIRMED")
        with self.assertRaisesRegex(ContractError, "PENDING_ACK"):
            self.m.set("carplay.enabled", "0", expected_revision=0)
        self.assertEqual(self.m.ack(p["token"], accepted=True)["state"], "ACK_HOST_SIMULATED")
        state = self.m.get("carplay.enabled")
        self.assertEqual((state["desired"], state["effective"], state["stored"]),
                         ("1", "1", "UNCONFIRMED"))
        with self.assertRaisesRegex(ContractError, "REVISION_MISMATCH"):
            self.m.set("carplay.enabled", "0", expected_revision=0)
        with self.assertRaisesRegex(ContractError, "STALE_OR_MISSING_ACK"):
            self.m.ack(p["token"], accepted=True)
        with self.assertRaisesRegex(ContractError, "PERSISTENT_POLICY_BLOCKED"):
            self.m.save("carplay.enabled", expected_revision=1)

    def test_rejection_timeout_stale_ack_and_no_default_effective(self):
        rejected = self.m.set("maxFPS", "30", expected_revision=0)
        self.assertEqual(self.m.ack(rejected["token"], accepted=False)["state"],
                         "REJECTED_HOST_SIMULATED")
        self.assertEqual(self.m.get("maxFPS")["effective"], "UNCONFIRMED")
        timed = self.m.set("maxFPS", "40", expected_revision=1)
        self.assertEqual(self.m.timeout(timed["token"])["state"], "TIMEOUT_HOST_SIMULATED")
        with self.assertRaisesRegex(ContractError, "STALE_OR_MISSING_ACK"):
            self.m.ack(timed["token"], accepted=True)
        self.assertEqual(self.m.get("maxFPS")["effective"], "UNCONFIRMED")

    def test_known_domains_bounds_and_unsupported_types_fail_closed(self):
        invalid = [
            ("maxFPS", "35"), ("navigation.compass", "true"),
            ("carplay.enabled", "-1"), ("carplay.enabled", "2"),
            ("viewareas.count", "0"), ("viewarea.0.w", "0"),
            ("keyframe.interval_ms", "99"), ("sourceVersion", "bad"),
            ("display.widthPixels", "1010"), ("display.uuid", "test"),
            ("navigation.url", "https://example.org"), ("presentation.suggested_urls", "a,b"),
            ("unknown.key", "1"), ("maxFPS", "3" * 193),
            ("maxFPS", "30\nRESET"),
        ]
        for key, value in invalid:
            with self.subTest(key=key, value=value[:25]):
                with self.assertRaises(ContractError):
                    self.m.set(key, value, expected_revision=0)
                self.assertEqual(self.m.revision, 0)
        for key, value in (("maxFPS", "25"), ("navigation.compass", "user"),
                           ("viewarea.selected", "0"), ("sourceVersion", "1005.8.1")):
            trial = PhaseCModel(self.registry)
            try:
                self.assertEqual(trial.set(key, value, expected_revision=0)["token"], 1)
            finally:
                trial.close()

    def test_invalid_ack_parameter_does_not_consume_pending_request(self):
        p = self.m.set("carplay.enabled", "1", expected_revision=0)
        for bad in (None, 1, "true"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ContractError, "INVALID_ACK"):
                    self.m.ack(p["token"], accepted=bad)
                self.assertEqual(self.m.revision, 0)
                self.assertEqual(self.m.get("carplay.enabled")["effective"], "UNCONFIRMED")
        self.assertEqual(self.m.ack(p["token"], accepted=True)["state"], "ACK_HOST_SIMULATED")

    def test_save_simulated_explicit_optin_only_volatile_and_requires_ack(self):
        memory = PhaseCModel(self.registry, enable_simulated_save=True)
        try:
            with self.assertRaisesRegex(ContractError, "NO_SIMULATED_ACK"):
                memory.save("carplay.enabled", expected_revision=0)
            p = memory.set("carplay.enabled", "1", expected_revision=0)
            with self.assertRaisesRegex(ContractError, "PENDING_ACK"):
                memory.save("carplay.enabled", expected_revision=0)
            memory.ack(p["token"], accepted=True)
            saved = memory.save("carplay.enabled", expected_revision=1)
            self.assertFalse(saved["vehicle_saved"])
            self.assertEqual(saved["state"], "SAVE_HOST_MEMORY_ONLY")
            self.assertEqual(memory.get("carplay.enabled")["stored"], "1")
        finally:
            memory.close()
        new = PhaseCModel(self.registry, enable_simulated_save=True)
        try:
            self.assertEqual(new.get("carplay.enabled")["stored"], "UNCONFIRMED")
        finally:
            new.close()

    def test_read_only_live_broker_still_blocks_all_mutating_verbs(self):
        for verb in ("SET 0 carplay.enabled 1", "SAVE", "BATCH", "ACTION reboot", "RESET", "DISCARD"):
            self.assertEqual(response(verb, self.registry), "ERROR POLICY_BLOCKED HOST_FIXTURE_READ_ONLY")
        self.assertIn("desired=UNCONFIRMED", response("GET carplay.enabled", self.registry))
        # Simulated ACK must not influence the separate actual read-only fixture.
        p = self.m.set("carplay.enabled", "1", expected_revision=0)
        self.m.ack(p["token"], accepted=True)
        self.assertIn("effective=UNCONFIRMED", response("GET carplay.enabled", self.registry))

    def test_close_zeroizes_and_blocks_late_operations(self):
        p = self.m.set("carplay.enabled", "1", expected_revision=0)
        self.m.close()
        with self.assertRaisesRegex(ContractError, "SESSION_CLOSED"):
            self.m.ack(p["token"], accepted=True)
        with self.assertRaisesRegex(ContractError, "SESSION_CLOSED"):
            self.m.get("carplay.enabled")
        with self.assertRaisesRegex(ContractError, "SESSION_CLOSED"):
            self.m.set("carplay.enabled", "0", expected_revision=0)


if __name__ == "__main__":
    unittest.main()
