import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_oem_sources


ACTIVATOR = '''public void start(BundleContext bundleContext) {
        this.bundleContext = bundleContext;
    }
    public void stop(BundleContext bundleContext) {
    }
    throw new NoClassDefFoundError().initCause(classNotFoundException);
    this.factory = new Factory(this.logger, configurationManager, this.dictionary, this.idService);
    this.factory.setScriptWidgetService(this.scriptWidgetCioService);
    this.cioVisualizationService = (CioVisualizationService)object;
'''
WIDGET_FACTORY = '''import de.vw.mib.view.internal.treebuilder.WidgetFactory;
class WidgetFactoryImpl {
    case 55: {
                return new WidgetList();
            }
}
'''


class PrepareOemSourcesTest(unittest.TestCase):
    def test_patches_only_guarded_owned_hooks(self):
        patched_a = prepare_oem_sources.patch_activator(ACTIVATOR)
        patched_w = prepare_oem_sources.patch_widget_factory(WIDGET_FACTORY)
        self.assertIn("MibrHomeCio.activatorStarted()", patched_a)
        self.assertIn("MibrHomeCio.deactivate()", patched_a)
        self.assertIn("new de.mibr.hmi.MibrVisualizationService", patched_a)
        self.assertIn("import de.mibr.hmi.MibrHomeList;", patched_w)
        self.assertIn("return new MibrHomeList();", patched_w)
        self.assertNotIn("return new WidgetList();", patched_w)

    def test_rejects_source_drift_and_double_patch(self):
        with self.assertRaisesRegex(ValueError, "WIDGET_FACTORY_SLOT_55_ANCHOR_COUNT=0"):
            prepare_oem_sources.patch_widget_factory("import de.vw.mib.view.internal.treebuilder.WidgetFactory;\ncase 55: { return null; }")
        patched = prepare_oem_sources.patch_widget_factory(WIDGET_FACTORY)
        with self.assertRaisesRegex(ValueError, "WIDGET_FACTORY_ALREADY_PATCHED"):
            prepare_oem_sources.patch_widget_factory(patched)


if __name__ == "__main__":
    unittest.main()
