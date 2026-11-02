"""Host-only 4Hz interpolation math; no QNX timer or vendor sender."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
from public_paths import NATIVE

class Gps4HzMath(unittest.TestCase):
    def test_quarter_interval_and_no_send_capability(self):
        source=(NATIVE/"mibr_gps_4hz.c").read_text()
        self.assertNotIn("iap2_gps_data_send",source)
        self.assertNotIn("pthread_create",source)
        self.assertNotIn("nanosleep",source)
        cc=shutil.which("cc")
        self.assertIsNotNone(cc)
        with tempfile.TemporaryDirectory() as d:
            exe=Path(d)/"math"
            proc=subprocess.run([cc,"-std=gnu99","-Wall","-Wextra","-Werror",
                "-I",str(NATIVE),str(NATIVE/"mibr_gps_4hz.c"),
                str(HERE/"mibr_gps_4hz_host_test.c"),"-o",str(exe)],
                capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn("GPS_INTERPOLATION_MATH_ONLY_PASS",run.stdout)

if __name__=="__main__":
    unittest.main()
