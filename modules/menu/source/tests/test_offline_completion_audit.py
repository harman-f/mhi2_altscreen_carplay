"""Offline-only completion audit against retained bytes, original sources and code.
Never a claim of physical rendering, full Skin3 MCF parity or real backend I/O.
"""
import hashlib
import json
import re
import struct
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
H = P / "java/de/mibr/hmi"
ROOT = P.parents[2]
REFERENCE = ROOT / "reference/oem-system-settings-mu1440"
KNOWLEDGE = ROOT / "knowledge"
ASSETS = ROOT / "design/icon-assets-20261017/generated/native_transparent"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for part in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def png(path):
    raw = path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("NOT_PNG: " + str(path))
    length, = struct.unpack(">I", raw[8:12])
    if raw[12:16] != b"IHDR" or length != 13:
        raise AssertionError("INVALID_IHDR")
    width, height, depth, colour = struct.unpack(">IIBB", raw[16:26])
    return width, height, depth, colour


class OfflineCompletionAudit(unittest.TestCase):
    def setUp(self):
        requirements = {
            "test_real_skin1_skin2_mcf_byte_hashes_not_just_manifest": REFERENCE / "analyst-completion-v1/payload-files.json",
            "test_skin3_is_documented_receipt_not_fake_full_binary_recomparison": KNOWLEDGE / "skin3_evidence/README.md",
            "test_exact_icon_assets_bytes_alpha_dimensions_and_provenance": ASSETS / "IMPORT_RECEIPT.json",
            "test_native_views_exact_target_layout_and_source_event_contract": REFERENCE / "decoded-v1/skin1/Ssd_35BF/cfr/generated/de/vw/mib/systemsetup/view/internal/Ssd_35BF.java",
            "test_check_row_is_stock_ssm_external_apps_template": ROOT / "reference/oem-dropdown-mu1440/skin1/Ssm_5458.java",
            "test_clone_selector_never_arbitrarily_chooses_a_duplicate": REFERENCE / "sound-views-v1/skin1/Tsmv/cfr/generated/de/vw/mib/sound/view/internal/Tsmv.java",
            "test_backend_scope_no_live_write_or_unapproved_release": P / "control/mock_mibr_control.py",
        }
        required = requirements.get(self._testMethodName)
        if required is not None and not required.is_file():
            self.skipTest("requires private MU1440 OEM evidence fixture: " + str(required.relative_to(ROOT)))

    def test_real_skin1_skin2_mcf_byte_hashes_not_just_manifest(self):
        manifest = json.loads((REFERENCE / "analyst-completion-v1/payload-files.json").read_text())
        expected = {x["repository_path"]: x for x in manifest["files"]
                    if x["repository_path"].endswith("/images.mcf")}
        self.assertEqual(len(expected), 2)
        repo = ROOT.parents[1]
        for name, record in expected.items():
            path = repo / name
            with self.subTest(path=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha(path), record["sha256"])
        self.assertEqual(expected[next(x for x in expected if "/skin1/" in x)]["sha256"],
                         "3d0e0498492b68fa8b6529ff23060fe387d349bf8a9a1b404cdd3b1c617bb6e0")

    def test_skin3_is_documented_receipt_not_fake_full_binary_recomparison(self):
        receipt = (KNOWLEDGE / "skin3_evidence/README.md").read_text()
        self.assertIn("0a322d581cb320c60bc6be87e2817fcdf20aa2f2", receipt)
        self.assertIn("41 changed", receipt)
        self.assertIn("2345 image IDs", receipt)
        self.assertIn("NOT prove the actual installed Unit", receipt)
        # No blanket statement that original UI classes are proven equal to
        # Skin3 merely because the image delta is reported as derived from skin1.
        raw = ROOT / "reference/skin3-raw-20261017/README.md"
        self.assertIn("70 actual parts need ONE subsequent upload", raw.read_text())
        self.assertFalse((KNOWLEDGE / "skin3_evidence/skin3_images.mcf").exists())
        self.assertFalse((ROOT / "reference/skin3-raw-20261017/skin3_images.mcf").exists())

    def test_exact_icon_assets_bytes_alpha_dimensions_and_provenance(self):
        own = json.loads((ASSETS / "IMPORT_RECEIPT.json").read_text())["files"]
        source = json.loads((KNOWLEDGE / "EVIDENCE_INDEX.json").read_text())
        self.assertEqual(len(own), 4)
        for name, digest in own.items():
            with self.subTest(asset=name):
                path = ASSETS / name
                self.assertEqual(sha(path), digest)
                self.assertEqual(png(path), (235, 154, 8, 6))
        originals = [x for x in source["selected_image_evidence"] if
                     x["path"].startswith("skin3_evidence/")]
        self.assertEqual(len(originals), 3)
        for record in originals:
            path = KNOWLEDGE / record["path"]
            with self.subTest(asset=record["path"]):
                self.assertEqual(path.stat().st_size, record["size"])
                self.assertEqual(sha(path), record["sha256"])
                self.assertEqual(png(path), (235, 154, 8, 6))
        # MCF record IDs 1834/1835/1847 are NOT image-array 686.
        self.assertNotIn("skin3_images.mcf", own)

    def test_native_views_exact_target_layout_and_source_event_contract(self):
        from test_original_view_port_sources import SOURCES, BACK_TARGETS
        self.assertEqual(len(SOURCES), 8)
        for skin in (1, 2):
            for template, name, view, targets in SOURCES:
                raw = (REFERENCE / template.format(skin=skin)).read_text()
                with self.subTest(skin=skin, view=name):
                    self.assertIn('return "' + name + '";', raw)
                    self.assertIn('return ' + str(view) + ';', raw)
                    for target in targets:
                        self.assertIn("(int)" + str(target), raw)
                    self.assertIn("WidgetInit.init", raw)
            self.assertEqual(len(BACK_TARGETS), 7)
        # The foreign OEM page mount (Sound/Display/...) is archived and no
        # longer part of the package.
        self.assertFalse((H / "MibrOriginalWidgetMount.java").exists())

    def test_j9_build_reads_sources_as_utf8(self):
        # Vehicle 2026-10-19: tile label "CP-Menü" rendered as mojibake because
        # the J9 javac used the platform default encoding.
        build = (P / "toolchain/build_carplay_settings_home.sh").read_text()
        self.assertIn('"$J9_HOME/bin/javac" -encoding UTF-8', build)

    def test_check_row_is_stock_ssm_external_apps_template(self):
        template = (H / "MibrOemSsmTemplate.java").read_text()
        for skin in (1, 2):
            raw = (ROOT / "reference/oem-dropdown-mu1440/skin{}/Ssm_5458.java".format(skin)).read_text()
            init = raw[raw.index("private void initContainerWidgetListExternalAppsCloneData"):]
            init = init[:init.index("registerWidgetPropertyListener")]
            with self.subTest(skin=skin):
                self.assertIn('(String)"ExternalApps"', init)
                self.assertIn("(int)19737792", init)
                self.assertIn("(int)103710118", init)
                self.assertIn("(int)119782300", init)
                # Same state image arrays as the former SystemSetup graft.
                for array in ("getImageArray(147)", "getImageArray(686)", "getImageArray(1365)"):
                    self.assertIn(array, init)
        for value in ('ROW_CHECK="ExternalApps"', "CHECK_TARGET_ID=19737792",
                      "CHECK_BUTTON_TARGET_ID=103710118", "CHECK_TEXT_TARGET_ID=119782300"):
            self.assertIn(value, template)
        rows = (H / "MibrOwnedSsmRows.java").read_text()
        self.assertIn("return stock.check;", rows)
        self.assertNotIn("set_imagesState", rows)
        self.assertNotIn("1139", rows)

    def test_clone_selector_never_arbitrarily_chooses_a_duplicate(self):
        source = (REFERENCE / "sound-views-v1/skin1/Tsmv/cfr/generated/de/vw/mib/sound/view/internal/Tsmv.java").read_text()
        self.assertIn("CloneMaster", source)
        self.assertIn("(int)29388966", source)
        template = (H / "MibrOemSsmTemplate.java").read_text()
        self.assertIn("MIBR_SSM_DUPLICATE_TARGET", template)
        self.assertIn("uniqueTarget(children[i]", template)
        # Fail-closed multi-clone behavior is proven; selection of a specific
        # runtime clone is not established by the static class ID alone.

    def test_original_events_isolated_and_reset_routing_excluded(self):
        isolated = (H / "MibrIsolatedSsmServices.java").read_text()
        for signature in ("createAndSubmitHMIEvent(int id)", "createAndSubmitPointEvent(int id",
                          "createAndSubmitSpellerValueEvent(int id", "submitEvent(HMIEvent event)"):
            self.assertIn(signature, isolated)
        self.assertIn("public void submitEvent(HMIEvent event) { }", isolated)
        rows = (H / "MibrOwnedSsmRows.java").read_text()
        page = (H / "MibrSsmNativePage.java").read_text()
        # Product path: no demo catalogue, no foreign OEM child pages, no
        # TEMP batch action row and no developer status prefixes.
        for forbidden in ("requestTypedChild", "demo.", "MibrGenericCatalog", "actionLabel",
                          "control.apply", "ENTWURF", "SOLL:", "TEMP:", "UNKNOWN", "NUR DEMO",
                          "Pcsartfs2"):
            self.assertNotIn(forbidden, rows)
        for forbidden in ("MibrOriginalPageFactory", "openOriginal", "MibrGenericCatalog", "getImageArray"):
            self.assertNotIn(forbidden, page)

    def test_backend_scope_no_live_write_or_unapproved_release(self):
        client = (H / "MibrControlClient.java").read_text()
        self.assertIn("legacy MIBR/1 fixture and gated native TEMP MIBR/2", client)
        self.assertIn('!verified', client)
        self.assertIn("MibrControlProtocol.HELLO.equals(result)", client)
        self.assertIn("TEMPBATCH ", client)
        self.assertNotIn('start("SET ', client)
        self.assertNotIn('start("SAVE', client)
        broker = (P / "control/mock_mibr_control.py").read_text()
        self.assertIn("HOST_FIXTURE_READ_ONLY", broker)
        self.assertIn('("127.0.0.1", port)', broker)
        package = (P / "release/visual-qa-v4-owned-ssm/make_candidate.py").read_text()
        self.assertIn("CONDITIONAL_VEHICLE_VISUAL_INSTALL", package)
        self.assertIn("PREIMAGE_GATED", package)
        self.assertIn("Do not use a v3/PR82 installer", package)
        self.assertIn("Passing offline CI does not prove exact physical OEM view/rendering", package)
        self.assertIn('"backend_writes": "DISABLED"', package)

    def test_menu_hardkey_uses_stock_asl_key_listener_and_is_disarmed(self):
        key = (H / "MibrMenuKeyBack.java").read_text(encoding="utf-8")
        page = (H / "MibrSsmNativePage.java").read_text(encoding="utf-8")
        build = (P / "toolchain" / "build_carplay_settings_home.sh").read_text(encoding="utf-8")
        self.assertIn("api.addKeyListener(menuKey(), listener)", key)
        self.assertIn("api.removeKeyListener(menuKey(), listener)", key)
        self.assertIn("if (!MibrOemPageEntry.isOpen()) return;", key)
        self.assertIn("eventDispatcher.invoke", key)
        self.assertEqual(page.count("MibrMenuKeyBack.disarm();"), 2)
        self.assertEqual(page.count("MibrMenuKeyBack.arm();"), 1)
        self.assertIn("MibrMenuKeyBack.java", build)


if __name__ == "__main__":
    unittest.main()
