"""KEY40 route toggle daemon (r21): stream scanner + gesture classifier, host only."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

NATIVE = Path(__file__).resolve().parents[2] / "src" / "native" / "mibr-control"
NL = chr(10)


def line(kbd, key, kst, stamp):
    return "[%012dms] [AslTargetSystemKeyPanelHandling] HK Received: KBD[%d] KEY[%d] KST[%d]" % (
        stamp, kbd, key, kst) + NL


def junk(n):
    # binary noise and unrelated text with the needle prefix but a different shape
    return bytes(range(256)) * n + ("HK Received: KBD[" + NL).encode() + b"HK Rece"


@unittest.skipUnless(shutil.which("cc"), "needs a C compiler")
class Key40dHost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="key40d-")
        cls.binary = Path(cls.tmp.name) / "key40d-test"
        subprocess.run(["cc", "-O2", "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-DKEY40D_TEST",
                        str(NATIVE / "mibr_key40d.c"), str(NATIVE / "mibr_v3_key40.c"),
                        "-o", str(cls.binary)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_stream(self, data, chunk):
        run = subprocess.run([str(self.binary), str(chunk)], input=data, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        return int(run.stdout.decode().strip().split("TOTAL ")[1])

    def stream(self, parts):
        return "".join(parts).encode()

    def wide(self, parts):
        """UTF-16LE like the real DebugSPI text messages."""
        return "".join(parts).encode("utf-16-le")

    def test_utf16le_stream_like_the_car(self):
        press = [line(4, 40, 1, 1), line(4, 40, 3, 2), line(4, 40, 4, 3), line(4, 40, 5, 4), line(4, 40, 0, 5)]
        short = [line(4, 40, 1, 6), line(4, 40, 0, 7)]
        data = self.wide(press + short + press)
        for chunk in (1, 2, 3, 7, 4096):
            self.assertEqual(self.run_stream(data, chunk), 2, chunk)
        self.assertEqual(self.run_stream(self.wide(short), 4096), 0)

    def test_short_press_is_left_to_the_oem(self):
        data = self.stream([line(4, 40, 1, 1000), line(4, 40, 0, 1150)])
        for chunk in (1, 3, 7, 64, 4096):
            self.assertEqual(self.run_stream(data, chunk), 0, chunk)

    def test_long_press_fires_exactly_once(self):
        data = self.stream([line(4, 40, 1, 1000), line(4, 40, 3, 1900), line(4, 40, 4, 2000),
                            line(4, 40, 5, 3000), line(4, 40, 5, 4000), line(4, 40, 0, 5080)])
        for chunk in (1, 2, 5, 17, 64, 4096):
            self.assertEqual(self.run_stream(data, chunk), 1, chunk)

    def test_two_long_presses_and_a_short_between(self):
        press = [line(4, 40, 1, 1), line(4, 40, 3, 2), line(4, 40, 4, 3), line(4, 40, 5, 4), line(4, 40, 0, 5)]
        data = self.stream(press + [line(4, 40, 1, 6), line(4, 40, 0, 7)] + press)
        for chunk in (1, 9, 4096):
            self.assertEqual(self.run_stream(data, chunk), 2, chunk)

    def test_other_keys_and_key41_are_ignored(self):
        data = self.stream([line(4, 41, 1, 1), line(4, 41, 3, 2), line(4, 41, 4, 3), line(4, 41, 0, 4),
                            line(13, 78, 1, 5), line(13, 78, 0, 6)])
        self.assertEqual(self.run_stream(data, 4096), 0)

    def test_noise_does_not_confuse_or_wedge(self):
        press = [line(4, 40, 1, 1), line(4, 40, 3, 2), line(4, 40, 4, 3), line(4, 40, 0, 4)]
        data = junk(40) + self.stream(press) + junk(40) + self.stream(press)
        for chunk in (1, 13, 4096):
            self.assertEqual(self.run_stream(data, chunk), 2, chunk)

    def test_broken_sequence_never_fires(self):
        data = self.stream([line(4, 40, 1, 1), line(4, 40, 4, 2), line(4, 40, 0, 3)])
        self.assertEqual(self.run_stream(data, 4096), 0)


if __name__ == "__main__":
    unittest.main()
