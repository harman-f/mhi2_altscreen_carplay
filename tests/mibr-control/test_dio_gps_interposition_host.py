"""Linux host integration fixture for the *original sender call*, no Unit I/O.

This proves that a symbol-named wrapper can pass OFF byte-for-byte and change
the payload at the pre-existing iap2_gps_data_send call WITHOUT a second sender.
QNX runtime loader, DIO startup/ownership, phone acceptance remain NOT RUN.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
from public_paths import NATIVE
DIO_TAP = NATIVE / "mibr_gps_dio_tap_experimental.c"


def run(argv, **kwargs):
    result = subprocess.run(argv, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise AssertionError("command failed: %r\nSTDOUT:\n%s\nSTDERR:\n%s" %
                             (argv, result.stdout, result.stderr))
    return result.stdout


def nmea(body):
    x = 0
    for b in body.encode("ascii"):
        x ^= b
    return "$%s*%02X\r\n" % (body, x)


@unittest.skipUnless(DIO_TAP.is_file(), "Research-only experimental DIO tap is omitted from the public source tree")
class OriginalSenderTap(unittest.TestCase):
    def test_off_berlin_hamburg_off_existing_sender_only(self):
        cc = shutil.which(os.environ.get("CC", "cc"))
        if not cc:
            self.skipTest("host compiler missing")
        # This is intentionally a Linux HOST test only.
        with tempfile.TemporaryDirectory(prefix="gps-dio-tap-test-") as name:
            out = Path(name)
            fake = out / "vendor.c"
            fake.write_text(r'''
#include <stdio.h>
#include <stdint.h>
int iap2_gps_data_send(void *handle,const char *nmea){
  printf("VENDOR_CALL handle=%lu nmea=%s", (unsigned long)(uintptr_t)handle,nmea);
  return handle==(void *)(uintptr_t)7?0:-1;
}
''')
            caller = out / "caller.c"
            original = nmea("GPRMC,120000.00,A,5111.0000,N,01122.0000,E,0.0,0.0,261026,,,A")
            caller.write_text(r'''
#include <stdint.h>
#include <stdio.h>
#include <dlfcn.h>
int iap2_gps_data_send(void *, const char *);
typedef int (*choose_fn)(const char *);
int main(void){
  choose_fn choose=(choose_fn)dlsym(RTLD_DEFAULT,"mibr_gps_demo_mode_write");
  const char *msg="''' + original.encode("unicode_escape").decode("ascii").replace('"', '\\"') + r'''";
  if(!choose)return 5;
  if(iap2_gps_data_send((void *)(uintptr_t)7,msg))return 6;
  if(choose("BERLIN_DEMO"))return 7;
  if(iap2_gps_data_send((void *)(uintptr_t)7,msg))return 8;
  if(choose("HAMBURG_DEMO"))return 9;
  if(iap2_gps_data_send((void *)(uintptr_t)7,msg))return 10;
  if(choose("OFF"))return 11;
  if(iap2_gps_data_send((void *)(uintptr_t)7,msg))return 12;
  return 0;
}
''')
            libvendor = out / "libfake_iap2.so"
            tap = out / "libmibr_dio_tap.so"
            exe = out / "caller"
            run([cc, "-std=gnu99", "-fPIC", "-shared", "-Wall", "-Wextra", "-Werror",
                 str(fake), "-o", str(libvendor)])
            run([cc, "-std=gnu99", "-fPIC", "-shared", "-Wall", "-Wextra", "-Werror",
                 "-DMIBR_GPS_HOST_INTERPOSITION_TEST", 
                 '-DMIBR_GPS_DEMO_MODE_FILE="%s"' % (out / "choice"),
                 '-DMIBR_GPS_DEMO_SOCKET="%s"' % (out / "owner.sock"),
                 "-I", str(NATIVE),
                 str(NATIVE / "mibr_gps_dio_tap_experimental.c"),
                 str(NATIVE / "mibr_gps_dio_runtime.c"),
                 str(NATIVE / "mibr_gps_demo_owner.c"),
                 str(NATIVE / "mibr_gps_demo_mode.c"),

                 str(NATIVE / "mibr_gps_demo.c"), "-o", str(tap), "-ldl", "-pthread"])
            run([cc, "-std=gnu99", "-Wall", "-Wextra", "-Werror", str(caller),
                 "-L", str(out), "-lfake_iap2",
                 "-Wl,-rpath," + str(out), "-o", str(exe), "-ldl"])
            env = dict(os.environ, LD_PRELOAD=str(tap))
            text = run([str(exe)], env=env)
            lines = [line for line in text.splitlines() if line.startswith("VENDOR_CALL ")]
            self.assertEqual(len(lines), 4, text)
            self.assertIn("5111.0000,N,01122.0000,E", lines[0])
            self.assertIn("5231.3235,N,01324.9731,E", lines[1])
            self.assertIn("5333.1453,N,00959.7258,E", lines[2])
            self.assertIn("5111.0000,N,01122.0000,E", lines[3])
            self.assertTrue(all("handle=7 " in line for line in lines))


if __name__ == "__main__":
    unittest.main()

