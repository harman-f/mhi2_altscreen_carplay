"""Host-only regression. Never connects to a vehicle."""
import socket
import sys
import threading
import unittest
from public_paths import TESTS

sys.path.insert(0, str(TESTS))
if not (TESTS / "mock_mibr_control.py").is_file():
    raise unittest.SkipTest("Research-only native-broker mock is omitted from the public source tree")
import mock_mibr_control as fixture


class BrokerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = fixture.load_registry()
        cls.server = fixture.Server(cls.registry, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def ask(self, payload):
        with socket.create_connection(("127.0.0.1", self.server.server_address[1]), timeout=2) as s:
            s.settimeout(2)
            s.sendall(payload)
            return s.makefile("rb").readline(769).decode("ascii").strip()

    def test_all_48_registry_keys_have_no_fabricated_values(self):
        self.assertEqual(len(self.registry), 48)
        self.assertIn("mode=HOST_FIXTURE", self.ask(b"HELLO MIBR/1\n"))
        self.assertIn("count=48", self.ask(b"SNAPSHOT\n"))
        for key, spec in self.registry.items():
            reply = self.ask(("GET " + key + "\n").encode("ascii"))
            self.assertTrue(reply.startswith("VALUE key=" + key + " "), key)
            self.assertIn("type=" + spec["type"], reply)
            self.assertIn("apply=" + spec["apply"], reply)
            self.assertIn("desired=UNCONFIRMED", reply)
            self.assertIn("effective=UNCONFIRMED", reply)
            self.assertIn("source=NONE", reply)
            self.assertIn("session=NONE", reply)
        self.assertIn("read_only=1", self.ask(b"GET display.uuid\n"))

    def test_compass_and_disallowed_requests(self):
        self.assertIn("allowed=yes,no,user", self.ask(b"GET navigation.compass\n"))
        self.assertEqual(self.ask(b"GET unknown.key\n"), "ERROR INVALID_KEY")
        for cmd in (b"SET 0 carplay.enabled 1\n", b"BATCH\n", b"SAVE\n",
                    b"ACTION reboot\n", b"RESET\n", b"DISCARD\n"):
            self.assertEqual(self.ask(cmd), "ERROR POLICY_BLOCKED HOST_FIXTURE_READ_ONLY")

    def test_bounded_frames_and_unrecognized_commands(self):
        self.assertEqual(self.ask(b"X" * 300 + b"\n"), "ERROR OVERSIZE")
        self.assertEqual(self.ask(b"GET \xff\n"), "ERROR INVALID_ENCODING")
        self.assertEqual(self.ask(b"GET\n"), "ERROR INVALID_REQUEST")
        self.assertEqual(self.ask(b"HELLO MIBR/2\n"), "ERROR INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
