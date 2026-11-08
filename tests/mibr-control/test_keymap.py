"""Steering-wheel key mapping (key.* in platform defaults.conf): parser test and mibr-key40d with a custom file."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from public_paths import NATIVE, ROOT
from test_key40d import line

INC = ROOT / "modules/carplay/source/alt111-settings/include"


@unittest.skipUnless(shutil.which("cc"), "needs a C compiler")
class KeymapHost(unittest.TestCase):
    def test_parser(self):
        with tempfile.TemporaryDirectory(prefix="keymap-") as tmp:
            exe = Path(tmp) / "keymap-test"
            subprocess.run(["cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
                            "-I" + str(INC), str(ROOT / "tests/mibr-control/mibr_keymap_host_test.c"),
                            "-o", str(exe)], check=True, capture_output=True, text=True)
            run = subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("mibr_keymap host PASS", run.stdout)

    def test_key40d_uses_the_file(self):
        with tempfile.TemporaryDirectory(prefix="keymap-") as tmp:
            exe = Path(tmp) / "key40d-test"
            subprocess.run(["cc", "-O2", "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-DKEY40D_TEST",
                            str(NATIVE / "mibr_key40d.c"), str(NATIVE / "mibr_v3_key40.c"),
                            "-o", str(exe)], check=True, capture_output=True, text=True)
            km = Path(tmp) / "defaults.conf"
            km.write_text("safe_wide=1,2,3,4\nkey.menu=16\nzoom.tag=56\nkey.view_step=4/46\n"
                          "key.view_resync_long=4/46\nkey.carplay_switch_long=4/47\n")
            long_ = lambda k: [line(4, k, s, i) for i, s in enumerate((1, 3, 4, 5, 0))]  # noqa: E731

            def run(parts, *extra):
                out = subprocess.run([str(exe), "4096", *extra], input="".join(parts).encode(),
                                     capture_output=True, timeout=10, check=True).stdout.decode()
                return tuple(int(out.split(k + " ")[1].split()[0]) for k in ("STEPS", "RESYNCS", "TOTAL"))
            # default (no file): 4/40 steps+resyncs, 4/44 toggles, 4/46 and 4/47 are inert
            self.assertEqual(run(long_(40) + long_(44) + long_(46) + long_(47)), (1, 1, 1))
            # custom file: the same functions move to 4/46 and 4/47; 4/40 and 4/44 become inert
            self.assertEqual(run(long_(40) + long_(44) + long_(46) + long_(47), str(km)), (1, 1, 1))
            self.assertEqual(run(long_(40) + long_(44), str(km)), (0, 0, 0))
            self.assertEqual(run(long_(46), str(km)), (1, 1, 0))
            self.assertEqual(run(long_(47), str(km)), (0, 0, 1))
            # unreadable file: defaults
            self.assertEqual(run(long_(40) + long_(44), str(Path(tmp) / "none")), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
