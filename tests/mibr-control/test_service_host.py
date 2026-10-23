"""Host-only socket smoke test for the actual MIBR/3 service executable."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

import api_v3_contract as api

SERVICE = os.environ.get("MIBR_V3_NATIVE_HOST_BIN")


@unittest.skipUnless(SERVICE, "build the host service first with tools/build_mibr_control.sh host")
class ServiceHostTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mibr3-host-")
        root = Path(self.tmp.name)
        (root / "temp").mkdir()
        (root / "persistent").mkdir()
        self.secret = root / "service.secret"
        self.secret.write_text("a" * 64 + "\n")
        self.secret.chmod(0o600)
        env = dict(os.environ,
                   ALT111_SETTINGS_TEMP_ROOT=str(root / "temp"),
                   ALT111_SETTINGS_PERSISTENT_ROOT=str(root / "persistent"))
        self.process = subprocess.Popen(
            [SERVICE, "--port", "0", "--secret-file", str(self.secret)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready = self.process.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="), ready)
        self.port = int(ready.split("=", 1)[1])

    def tearDown(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
        self.tmp.cleanup()

    def wire(self, payload):
        with socket.create_connection(("127.0.0.1", self.port), timeout=3) as conn:
            conn.sendall(payload)
            conn.shutdown(socket.SHUT_WR)
            return conn.recv(16384)

    def request(self, rid, op, fields=None, secret="a" * 64):
        frame = api.request(rid, op, fields)
        sep = b";" if fields else b" "
        wire = frame[:-1] + sep + b"auth=" + secret.encode("ascii") + b"\n"
        return api.parse(self.wire(wire), is_response=True)

    def test_loopback_auth_and_runtime_claims_stay_separate(self):
        self.assertEqual(self.request("hello", "HELLO")["fields"]["version"], "MIBR/3")
        self.assertEqual(self.request("bad", "HELLO", secret="b" * 64)["error"], "AUTH_REQUIRED")
        caps = self.request("caps", "CAPABILITIES")["fields"]
        self.assertEqual(caps["route_action"], "0")
        self.assertEqual(caps["key40_input"], "0")
        self.assertEqual(caps["zoom_exec_owner"], "GEN2")
        status = self.request("status", "STATUS")["fields"]
        self.assertEqual(status["stored"], "UNCONFIRMED")
        self.assertEqual(status["runtime_correlated"], "0")
        self.assertEqual(self.request("get", "GET", {"key": "maxFPS"})["fields"]["active"], "UNKNOWN")
        self.assertEqual(self.request("set", "SET", {"key": "maxFPS", "value": "30"})["error"], "POLICY_BLOCKED")


if __name__ == "__main__":
    unittest.main()
