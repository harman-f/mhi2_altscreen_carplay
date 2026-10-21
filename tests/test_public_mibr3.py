#!/usr/bin/env python3
"""Host regression for the independently published read-only protocol and mailbox."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "experimental" / "mibr3"
sys.path.insert(0, str(SRC))
import api_v3_contract as api


class PublicProtocolTests(unittest.TestCase):
    def test_frame_roundtrip_and_utf8(self):
        original = "maps:/car/instrumentcluster?mode=a;b &view=Ü"
        f = api.request("demo_1", "GET", {"key": original})
        result = api.parse(f)
        self.assertEqual(result["request_id"], "demo_1")
        self.assertEqual(result["fields"]["key"], original)
        self.assertNotIn(original.encode(), f)

    def test_mutation_disabled_in_standalone_readonly_reference(self):
        hello = api.read_only_host(api.request("a", "HELLO"), None, None, None)
        self.assertEqual(api.parse(hello, is_response=True)["fields"]["phase"], "HOST_ONLY_NO_IO")
        blocked = api.read_only_host(api.request("b", "SET", {"key": "maxFPS", "value": "40"}),
                                     None, None, None)
        self.assertEqual(api.parse(blocked, is_response=True)["error"], "POLICY_BLOCKED")

    def test_reject_noncanonical_or_ambiguous_frames(self):
        for raw in (b"MIBR/3 a GET key=%2f\n", b"MIBR/3 a GET key=x;key=y\n",
                    b"MIBR/3 a GET key=x\r\n", b"MIBR/3 a GET key=%ZZ\n",
                    b"MIBR/3 a GET key=x\x00\n"):
            with self.subTest(raw=raw), self.assertRaises(api.FrameError):
                api.parse(raw)
        with self.assertRaises(api.FrameError):
            api.encode_value("\n")

    def test_native_mailbox_host_probe(self):
        with tempfile.TemporaryDirectory(prefix="mibr3-public-") as d:
            exe = str(Path(d) / "mailbox-probe")
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2",
                            str(SRC / "mibr_v3_parity_mailbox.c"),
                            str(SRC / "mibr_v3_parity_mailbox_probe.c"), "-o", exe],
                           check=True)
            output = subprocess.run([exe], check=True, capture_output=True, text=True)
            self.assertIn("PARITY_MAILBOX_ONE_COMMAND_AT_A_TIME_HOST_PASS", output.stdout)


if __name__ == "__main__":
    unittest.main()
