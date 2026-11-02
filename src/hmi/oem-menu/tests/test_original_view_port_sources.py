"""Pin both exact MU1440 skin variants for each owned original component port.
Presence of source/target IDs is a SOURCE gate; runtime view activation and
physical rendering remain independently required.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[4]/"reference/oem-system-settings-mu1440"
SOURCES=[
 ("decoded-v1/skin{skin}/Ssd_35BF/cfr/generated/de/vw/mib/systemsetup/view/internal/Ssd_35BF.java",
  "SYSTEM_SETUP_DISPLAY",1096,(100423085,79555142)),
 ("sound-views-v1/skin{skin}/Tsmv/cfr/generated/de/vw/mib/sound/view/internal/Tsmv.java",
  "TONE_SETUP_MAIN_VOLUMES",1144,(85144066,29388966)),
 ("sound-views-v1/skin{skin}/Tssbf/cfr/generated/de/vw/mib/sound/view/internal/Tssbf.java",
  "TONE_SETUP_SOUNDFOCUS_BALANCE_FADER",1145,(88947791,122630135,20623536)),
 ("decoded-v1/skin{skin}/Sst_1067/cfr/generated/de/vw/mib/global/view/internal/Sst_1067.java",
  "SYSTEM_SETUP_TIME",1101,(53572285,80645567,38834395,73085316)),
 ("decoded-v1/skin{skin}/Cws/cfr/generated/de/vw/mib/global/view/internal/Cws.java",
  "CONN_WLAN_SPELLER",94,(39793788,53895592,83431544,39239094)),
 ("decoded-v1/skin{skin}/Ssv/cfr/generated/de/vw/mib/systemsetup/view/internal/Ssv.java",
  "SYSTEM_SETUP_VERSIONS",1105,(89473729,60857356,24923998)),
 ("reset-confirm-views-v1/skin{skin}/Pcsartfs2/cfr/generated/de/vw/mib/appzilla/view/internal/Pcsartfs2.java",
  "PO_CONFIRM_SYSTEM_ALL_RESET_TO_FACTORY_SETTINGS 2",591,(43322150,86851458,40184317)),
 ("decoded-v1/skin{skin}/Wosll/cfr/generated/de/vw/mib/global/view/internal/Wosll.java",
  "WIZARD_ONLINE_SERVICE_LIST_LOADING",1229,(88834565,123262157)),
]


# Native ButtonClose widget index and target, directly from original
# registerOutEvents and WidgetInit.initButton in BOTH retained skins.
BACK_TARGETS=(
 ("decoded-v1","Ssd_35BF","systemsetup",5,126935746),
 ("sound-views-v1","Tsmv","sound",4,126104269),
 ("sound-views-v1","Tssbf","sound",3,111923583),
 ("decoded-v1","Sst_1067","global",5,126935746),
 ("decoded-v1","Cws","global",4,76706307),
 ("decoded-v1","Ssv","systemsetup",5,126935746),
 ("decoded-v1","Wosll","global",8,40573488),
)

class OriginalPortsSource(unittest.TestCase):
    def setUp(self):
        required = ROOT / SOURCES[0][0].format(skin=1)
        if not required.is_file():
            self.skipTest("requires private exact-target OEM view source fixtures")


    def test_all_native_child_back_ids_and_release_routes_both_skins(self):
        for skin in (1,2):
            for family,short,package,index,target in BACK_TARGETS:
                with self.subTest(skin=skin,original=short):
                    source=ROOT/f"{family}/skin{skin}/{short}/cfr/generated/de/vw/mib/{package}/view/internal/{short}.java"
                    raw=source.read_text(encoding="utf-8")
                    start=raw.index("protected void registerOutEvents()")
                    first=raw.index(f"widgetController = this.cd0.widgets[{index}].getController();",start)
                    self.assertIn('setOutEventMapping("released", 1234000729);',
                                  raw[first:first+200])
                    line=next((v for v in raw.splitlines() if
                               f"WidgetInit.initButton((Button)((Button)this.cd0.widgets[{index}])" in v),None)
                    self.assertIsNotNone(line)
                    self.assertIn(f'(int){target}, (TextAreaModel[])',line)

    def test_original_point_speller_and_reset_mapping_stay_quarantined(self):
        sound=(ROOT/"sound-views-v1/context/generated/de/vw/mib/sound/sm/SoundActivity.java").read_text(encoding="utf-8")
        self.assertIn("SoundActivity.evPointGestureParam1()",sound)
        self.assertIn("SoundActivity.evPointGestureParam2()",sound)
        self.assertIn("this.triggerObserver(1073744349, eventGeneric)",sound)
        for skin in (1,2):
            balance=(ROOT/f"sound-views-v1/skin{skin}/Tssbf/cfr/generated/de/vw/mib/sound/view/internal/Tssbf.java").read_text(encoding="utf-8")
            self.assertIn('setOutEventMapping("dragged", 1234004134)',balance)
            self.assertIn('setOutEventMapping("released", 1234004135)',balance)
            volumes=(ROOT/f"sound-views-v1/skin{skin}/Tsmv/cfr/generated/de/vw/mib/sound/view/internal/Tsmv.java").read_text(encoding="utf-8")
            self.assertIn('setOutEventMapping("valueChanged", 1234001532)',volumes)
            clock=(ROOT/f"decoded-v1/skin{skin}/Sst_1067/cfr/generated/de/vw/mib/global/view/internal/Sst_1067.java").read_text(encoding="utf-8")
            self.assertIn('setOutEventMapping("pressed", 1234001447)',clock)
            self.assertIn('setOutEventMapping("pressed", 1234001446)',clock)
            wlan=(ROOT/f"decoded-v1/skin{skin}/Cws/cfr/generated/de/vw/mib/global/view/internal/Cws.java").read_text(encoding="utf-8")
            self.assertIn('setOutEventMapping("okPressed", 1234003880)',wlan)
            self.assertIn("getSpellerData(14573)",wlan)
            reset=(ROOT/f"reset-confirm-views-v1/skin{skin}/Pcsartfs2/cfr/generated/de/vw/mib/appzilla/view/internal/Pcsartfs2.java").read_text(encoding="utf-8")
            self.assertIn('setOutEventMapping("released", 1234001388)',reset)
    def test_source_pinned_display_checkbox_listitem_event_both_skins(self):
        # Native DisplayOffClock is a cloned ListItem, not a synthetic
        # checkbox action. Both original skins own its buttonReleased route.
        for skin in (1, 2):
            p=ROOT/f"decoded-v1/skin{skin}/Ssd_35BF/cfr/generated/de/vw/mib/systemsetup/view/internal/Ssd_35BF.java"
            raw=p.read_text(encoding="utf-8")
            init=raw[raw.index("private void initContainerWidgetListDisplayOffClockCloneData"):
                     raw.index("private void activateContainerWidgetListDisplayOffClockCloneData")]
            self.assertIn("(int)7706535",init)
            self.assertIn("(int)79555142",init)
            event=raw[raw.index("private void activateContainerWidgetListDisplayOffClockCloneData"):
                      raw.index("private void deactivateContainerWidgetListDisplayOffClockCloneData")]
            self.assertIn("widgets[0].getController()",event)
            self.assertIn('setOutEventMapping("buttonReleased", 1234002941)',event)

    def test_exact_origins_skin1_and_skin2(self):
        self.assertEqual(len(SOURCES),8)
        for skin in (1,2):
            for pattern,name,view_id,targets in SOURCES:
                with self.subTest(skin=skin,view=name):
                    source=ROOT/pattern.format(skin=skin)
                    self.assertTrue(source.is_file(),str(source))
                    raw=source.read_text(encoding="utf-8")
                    self.assertRegex(raw,r"public String getName\(\)\s*\{\s*return "+
                                     re.escape('"'+name+'"'))
                    self.assertRegex(raw,r"protected int getInternalViewId\(\)\s*\{\s*return "+
                                     str(view_id)+r";")
                    for target in targets:
                        self.assertIn("(int)"+str(target),raw)
