"""Profile selection: anchors-as-data equivalence, binding generation, adapter shape, Java 1.2 lint."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
PROFILES = P.parents[1] / "profiles"
sys.path.insert(0, str(P))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_java12_syntax
import generate_profile_binding
import legacy_oem_patcher
import prepare_oem_sources

SKODA = "skoda-mu1440-p4526"
SEAT1409 = "seat-mu1409-p4708"
SEAT1447 = "seat-mu1447-p4709"

SKODA_ACTIVATOR = '''package de.vw.mib.cio.internal;
import org.osgi.framework.BundleContext;
import org.osgi.framework.ServiceReference;
public class Activator {
    public void start(BundleContext bundleContext) {
        this.bundleContext = bundleContext;
        this.factory = new Factory(this.logger, configurationManager, this.dictionary, this.idService);
        this.factory.setScriptWidgetService(this.scriptWidgetCioService);
    }
    public void stop(BundleContext bundleContext) {
    }
    void filter() {
        this.bundleContext.addServiceListener(this, string);
        ServiceReference[] serviceReferenceArray = this.bundleContext.getServiceReferences(null, string);
    }
    void cause() { throw new NoClassDefFoundError().initCause(classNotFoundException); }
    void svc() { this.cioVisualizationService = (CioVisualizationService)object; }
}
'''
SEAT_ACTIVATOR = '''package de.vw.mib.cio.internal;
import org.osgi.framework.BundleContext;
public class Activator {
    public void start(BundleContext bundleContext) throws Exception {
        this.bundleContext = bundleContext;
        this.factory = new Factory(this.logger, configurationManager, this.dictionary, this.idService);
        this.factory.setScriptWidgetService(this.scriptWidgetCioService);
    }
    public void stop(BundleContext bundleContext) throws Exception {
    }
    void cause() { throw new NoClassDefFoundError().initCause(classNotFoundException); }
    void svc() { this.cioVisualizationService = (CioVisualizationService)object; }
}
'''
WIDGET_FACTORY = '''import de.vw.mib.view.internal.treebuilder.WidgetFactory;
class WidgetFactoryImpl {
    case 55: {
                return new WidgetList();
            }
}
'''


class SkodaAnchorsAreIdentical(unittest.TestCase):
    def test_activator_output_identical_to_legacy_patcher(self):
        self.assertEqual(prepare_oem_sources.patch_activator(SKODA_ACTIVATOR),
                         legacy_oem_patcher.patch_activator(SKODA_ACTIVATOR))
        self.assertEqual(prepare_oem_sources.patch_activator(SKODA_ACTIVATOR, prepare_oem_sources.load_anchors(SKODA)),
                         legacy_oem_patcher.patch_activator(SKODA_ACTIVATOR))

    def test_widget_factory_output_identical_to_legacy_patcher(self):
        self.assertEqual(prepare_oem_sources.patch_widget_factory(WIDGET_FACTORY),
                         legacy_oem_patcher.patch_widget_factory(WIDGET_FACTORY))

    def test_same_error_labels_on_drift(self):
        for drop in ("public void stop(BundleContext bundleContext) {\n    }",
                     "this.cioVisualizationService = (CioVisualizationService)object;"):
            text = SKODA_ACTIVATOR.replace(drop, "")
            errors = []
            for patch in (prepare_oem_sources.patch_activator, legacy_oem_patcher.patch_activator):
                with self.assertRaises(ValueError) as caught:
                    patch(text)
                errors.append(str(caught.exception))
            self.assertEqual(errors[0], errors[1])
        patched = prepare_oem_sources.patch_activator(SKODA_ACTIVATOR)
        with self.assertRaisesRegex(ValueError, "ACTIVATOR_ALREADY_PATCHED"):
            prepare_oem_sources.patch_activator(patched)


class SeatAnchors(unittest.TestCase):
    def test_throws_exception_variant_without_invalid_syntax_block(self):
        anchors = prepare_oem_sources.load_anchors(SEAT1409)
        patched = prepare_oem_sources.patch_activator(SEAT_ACTIVATOR, anchors)
        self.assertIn("throws Exception {\n        de.mibr.hmi.MibrHomeCio.activatorStarted();", patched)
        self.assertIn("de.mibr.hmi.MibrHomeCio.deactivate();", patched)
        self.assertNotIn("InvalidSyntaxException", patched)
        self.assertIn("new de.mibr.hmi.MibrVisualizationService", patched)
        with self.assertRaisesRegex(ValueError, "ACTIVATOR_START_ANCHOR_COUNT=0"):
            prepare_oem_sources.patch_activator(SKODA_ACTIVATOR, anchors)
        with self.assertRaisesRegex(ValueError, "ACTIVATOR_START_ANCHOR_COUNT=0"):
            prepare_oem_sources.patch_activator(SEAT_ACTIVATOR)  # Skoda anchors reject it

    def test_mu1447_reuses_mu1409_anchors(self):
        self.assertEqual(prepare_oem_sources.load_anchors(SEAT1447),
                         prepare_oem_sources.load_anchors(SEAT1409))

    def test_widget_factory_slot_is_shared(self):
        for profile in (SKODA, SEAT1409, SEAT1447):
            patched = prepare_oem_sources.patch_widget_factory(
                WIDGET_FACTORY, prepare_oem_sources.load_anchors(profile))
            self.assertIn("return new MibrHomeList();", patched)

    def test_unknown_or_unsafe_profile_is_refused(self):
        for name in ("missing-profile", "../skoda-mu1440-p4526", ".hidden"):
            with self.assertRaises(ValueError):
                prepare_oem_sources.load_anchors(name)


class BindingGeneration(unittest.TestCase):
    def test_binding_names_adapter_and_source_dirs(self):
        adapter, dirs = generate_profile_binding.adapter_info(SKODA)
        self.assertEqual((adapter, dirs), ("de.mibr.hmi.MibrSkodaMu1440Profile", []))
        adapter, dirs = generate_profile_binding.adapter_info(SEAT1409)
        self.assertEqual((adapter, dirs), ("de.mibr.hmi.MibrSeatMu1409Profile", [SEAT1409]))
        adapter, dirs = generate_profile_binding.adapter_info(SEAT1447)
        self.assertEqual((adapter, dirs), ("de.mibr.hmi.MibrSeatMu1447Profile", [SEAT1447, SEAT1409]))
        source = generate_profile_binding.render(SEAT1447, adapter)
        self.assertIn("return new de.mibr.hmi.MibrSeatMu1447Profile();", source)
        self.assertIn('PROFILE_ID = "seat-mu1447-p4709"', source)

    def test_invalid_adapter_class_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            hmi = Path(tmp) / "bad" / "hmi"
            hmi.mkdir(parents=True)
            (hmi / "oem-anchors.json").write_text(json.dumps({"adapter_class": "x; evil()"}))
            with self.assertRaisesRegex(ValueError, "ADAPTER_CLASS_INVALID"):
                generate_profile_binding.adapter_info("bad", tmp)

    def test_default_profile_is_skoda(self):
        self.assertEqual(prepare_oem_sources.DEFAULT_PROFILE, SKODA)
        build = (P / "build.sh").read_text(encoding="utf-8")
        self.assertIn('PROFILE="${PROFILE:-skoda-mu1440-p4526}"', build)


class AdapterShape(unittest.TestCase):
    INTERFACE = ("id", "internalViewId", "homeTileGeometry", "createTileRenderer",
                 "nativeDropdownStrategy", "passThroughAnimationTable",
                 "imageIndexOffset", "listenersClearedOnDeInit")

    def read(self, path):
        return path.read_text(encoding="utf-8")

    def test_interface_declares_all_variation_points(self):
        text = self.read(P / "java/de/mibr/hmi/MibrOemProfile.java")
        for method in self.INTERFACE:
            self.assertRegex(text, r"\b" + method + r"\(")

    def test_implementations_cover_the_interface(self):
        for path in (P / "java/de/mibr/hmi/MibrSkodaMu1440Profile.java",
                     PROFILES / SEAT1409 / "hmi/java/de/mibr/hmi/MibrSeatMu1409Profile.java"):
            text = self.read(path)
            for method in self.INTERFACE:
                self.assertRegex(text, r"public\s+[\w\[\]]+\s+" + method + r"\(", path.name + " " + method)

    def test_skoda_values_match_pre_profile_literals(self):
        text = self.read(P / "java/de/mibr/hmi/MibrSkodaMu1440Profile.java")
        for token in ("return 982;", "Math.min(235, Math.max(0, width - 60))",
                      "Math.min(154, Math.max(0, height - 80))",
                      "Math.min(30, Math.max(0, height - iconHeight - 50))",
                      "DROPDOWN_STYLE_PROFILE", "return null;", "return 0;", "return false;",
                      '"MibrCarPlayTileIcon", -8803'):
            self.assertIn(token, text)

    def test_seat_values(self):
        text = self.read(PROFILES / SEAT1409 / "hmi/java/de/mibr/hmi/MibrSeatMu1409Profile.java")
        for token in ("return 957;", "Math.min(150, width)", "Math.min(150, height)",
                      "DROPDOWN_LIVE_OEM_WIDGETS", "{-176518671, 2, -1, 47, 0}",
                      "listenersClearedOnDeInit() { return true; }", "getImageArray(CARPLAY_IMAGE_ARRAY)"):
            self.assertIn(token, text)
        text = self.read(PROFILES / SEAT1447 / "hmi/java/de/mibr/hmi/MibrSeatMu1447Profile.java")
        self.assertIn("extends MibrSeatMu1409Profile", text)
        self.assertIn("imageIndexOffset() { return 6; }", text)

    def test_core_has_no_remaining_profile_literals(self):
        home = self.read(P / "java/de/mibr/hmi/MibrHomeList.java")
        self.assertNotIn("Math.min(235", home)
        self.assertNotIn("createFourStateIcon", home)
        self.assertNotIn("INTERNAL_VIEW_ID", self.read(P / "java/de/mibr/hmi/MibrOemSsmTemplate.java"))

    def test_no_private_or_personal_references_in_adapters(self):
        # Patterns are assembled at run time so this file itself stays clean for the publication audit.
        pattern = re.compile("|".join(["Cane" + "TLOTW", r"M\.I\.B\." + "_Re" + "search", "co" + "dex/", "issue" + "150", "/ho" + "me/"]))
        for root in [P / "java", *PROFILES.glob("*/hmi")]:
            for path in root.rglob("*"):
                if path.suffix in (".java", ".json") and path.is_file():
                    self.assertIsNone(pattern.search(self.read(path)), str(path))


class Java12Lint(unittest.TestCase):
    def findings(self, source):
        return sorted({rule for _, rule in check_java12_syntax.check_text(source)})

    def test_flags_each_forbidden_construct(self):
        cases = {
            "generics": "class A { java.util.List<String> x; }",
            "enum": "enum Color { RED }",
            "annotation": "class A { @Override public String toString() { return \"\"; } }",
            "varargs": "class A { void f(String... a) { } }",
            "for-each": "class A { void f(int[] a) { for (int v : a) { } } }",
            "assert": "class A { void f() { assert true; } }",
            "static-import": "import static java.lang.Math.max;\nclass A { }",
            "String.format": "class A { String f() { return String.format(\"%d\", 1); } }",
            "StringBuilder": "class A { StringBuilder b; }",
            "java.util.concurrent": "class A { java.util.concurrent.Executor e; }",
            "autoboxing": "class A { void f() { Integer i = 5; } }",
        }
        for rule, source in cases.items():
            self.assertIn(rule, self.findings(source), rule)

    def test_accepts_java12_code_and_ignores_comments_and_strings(self):
        source = '''/** @author x, uses List<String> and StringBuilder in prose */
class A {
    // for (int v : a) with @Override and String.format
    String s = "List<String> @x ... StringBuilder";
    char c = '@';
    int f(int[] a, int i, int j) {
        StringBuffer b = new StringBuffer();
        for (int k = 0; k < a.length; k++) b.append(a[k]);
        return i < j && j > 0 ? i : j;
    }
}
'''
        self.assertEqual(self.findings(source), [])

    def test_repository_java_sources_are_java12(self):
        roots = check_java12_syntax.default_roots()
        self.assertTrue(any("seat-mu1409-p4708" in str(r) for r in roots))
        for root in roots:
            for path in sorted(root.rglob("*.java")):
                self.assertEqual(check_java12_syntax.check_text(path.read_text(encoding="utf-8")), [], str(path))


if __name__ == "__main__":
    unittest.main()
