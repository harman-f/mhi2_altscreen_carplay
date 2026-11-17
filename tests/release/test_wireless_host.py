"""Run the synthetic wireless fixtures as part of the public host audit."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.name == "posix", "wireless host build requires a POSIX host")
class WirelessHostTest(unittest.TestCase):
    def test_wireless_fixtures(self):
        env = os.environ.copy()
        env.update(CC="cc", AR="ar")
        with tempfile.TemporaryDirectory(prefix="mibr-wireless-host-") as out:
            result = subprocess.run(
                ["bash", str(ROOT / "modules/wireless/build/build.sh"), out, "host"],
                cwd=ROOT, env=env, check=True, text=True, capture_output=True,
            )
        self.assertIn("wireless host compile PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
