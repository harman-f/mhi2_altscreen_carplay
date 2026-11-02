"""Static guard for the cross-process GPS menu choice contract.

Catches the common error where only the Java label or the NMEA filter is
changed while the broker's GPS_DEMO_SET, DIO IPC or choice-store rejects it.
This is supplemental to the real host-C/Java tests, not a substitute.
"""
from pathlib import Path
import unittest

from public_paths import ROOT, NATIVE, OEM_MENU
JAVA=OEM_MENU/"java/de/mibr/hmi"
EXTRA=("SCHWALEFELD_DEMO","WINTERBERG_DEMO")
ALL=("OFF","BERLIN_DEMO","HAMBURG_DEMO") + EXTRA


class FiveChoiceContract(unittest.TestCase):
    def test_native_owner_store_broker_and_ui_agree(self):
        files=(
            NATIVE/"mibr_gps_demo.c",
            NATIVE/"mibr_gps_demo_mode.c",
            NATIVE/"mibr_gps_demo_ipc.c",
            NATIVE/"mibr_v3_readonly.c",
            JAVA/"MibrGpsDemoState.java",
            JAVA/"MibrDraftChoiceModel.java",
        )
        for file in files:
            s=file.read_text(encoding="utf-8")
            for mode in EXTRA:
                with self.subTest(file=file.name,mode=mode):
                    self.assertIn('"'+mode+'"',s)

    def test_filter_uses_two_distinct_targets_without_changing_legacy(self):
        source=(NATIVE/"mibr_gps_demo.c").read_text(encoding="utf-8")
        for text in ('{"5231.3235","01324.9731"}',
                     '{"5333.1453","00959.7258"}',
                     '{"5118.4746","00837.8102"}',
                     '{"5111.6490","00831.9856"}'):
            self.assertIn(text,source)
        self.assertNotIn("MIBR_GPS_LOCAL_TWOTOWN_TEST",source)
        self.assertIn("case MIBR_GPS_SCHWALEFELD:point=&schwalefeld;",source)
        self.assertIn("case MIBR_GPS_WINTERBERG:point=&winterberg;",source)

    def test_menu_declares_five_and_no_old_alias_build(self):
        java=(JAVA/"MibrDraftChoiceModel.java").read_text(encoding="utf-8")
        self.assertIn('{"OFF","BERLIN_DEMO","HAMBURG_DEMO","SCHWALEFELD_DEMO","WINTERBERG_DEMO"}',java)
        for label in ("Schwalefeld Ortskern","Winterberg Ortskern"):
            self.assertIn(label,java)


if __name__=="__main__":
    unittest.main()
