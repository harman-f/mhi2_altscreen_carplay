"""Source/ABI contracts complement the executable queued-host tests; not UI proof."""
import hashlib
import json
import re
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
H = P / "java/de/mibr/hmi"
REF = P.parents[2] / "reference/oem-settings-viewhost-mu1440"
OEM = P.parents[2] / "reference/oem-dropdown-mu1440"


def code(name):
    text = (H / (name + ".java")).read_text()
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


class OwnedSsmContract(unittest.TestCase):
    def setUp(self):
        requirements = {
            "test_retained_evidence_is_exact": REF / "manifest.json",
            "test_actual_source_identity_and_native_registration": REF / "javap/de.vw.mib.desktop.internal.ScreenAreaDude.txt",
            "test_exact_loader_name_and_no_global_cache_or_unload": REF / "extended/source/generated/de/vw/mib/smartphoneintegration/sm/SmartPhoneIntegrationActivity.java",
            "test_oem_templates_and_original_clone_lifetime": OEM / "skin1/Ssm_5458.java",
        }
        required = requirements.get(self._testMethodName)
        if required is not None and not required.is_file():
            self.skipTest("requires private MU1440 OEM source/evidence fixture: " + str(required.relative_to(P.parents[2])))

    def test_retained_evidence_is_exact(self):
        for root in (REF, REF / "extended", REF / "queue", REF / "followup"):
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["source_jar_sha256"], "57dc5e9313ef8a59403a17b3a6726f0852f6ac68cc72e42ef2a1ca530aba3ae7")
            for item in manifest["files"]:
                data = (root / item["path"]).read_bytes()
                self.assertEqual(len(data), item["bytes"], item["path"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"], item["path"])

    def test_actual_source_identity_and_native_registration(self):
        binding = code("MibrSsmSourceBinding")
        for operation in ("getScreenAreaNode(\"\")", "node.getViewHandler()", "smart.getView() == owner",
                          "scan.match.getViewHandler()", "source.getView() != owner",
                          'getDeclaredField(name)', 'field.getType() != type', 'nativeEnter.invoke'):
            self.assertIn(operation, binding)
        descriptor = (REF / "javap/de.vw.mib.desktop.internal.ScreenAreaDude.txt").read_text()
        self.assertRegex(descriptor, r"void enterView\(de.vw.mib.desktop.internal.viewhandler.SmartViewHandler\);\s+descriptor: \(Lde/vw/mib/desktop/internal/viewhandler/SmartViewHandler;\)V")
        self.assertNotIn("ServiceManager.viewHandlerFactory", binding)
        self.assertIn('getDeclaredMethod("enterView"', binding)
        queued = (REF / 'queue/source/de/vw/mib/event/internal/dispatcher/ViewEventDispatcherImpl.java').read_text()
        self.assertIn('this.queue.add(this.eventFactory.createInvocationEvent(runnable))', queued)

    def test_exact_loader_name_and_no_global_cache_or_unload(self):
        activity = (REF / "extended/source/generated/de/vw/mib/smartphoneintegration/sm/SmartPhoneIntegrationActivity.java").read_text()
        factory = (REF / "extended/source/generated/de/vw/mib/smartphoneintegration/view/internal/LocalViewHandlerFactoryImpl.java").read_text()
        native = code("MibrSsmNativePage")
        self.assertIn('showView("Ssm_5458", bl, 122)', activity)
        self.assertIn('generated.de.vw.mib.smartphoneintegration.view.internal.', factory)
        self.assertIn('generated.de.vw.mib.smartphoneintegration.view.internal.Ssm_5458', native)
        self.assertIn('lifecycle((AbstractViewHandler)candidate)!=-1', native)
        self.assertIn('source.enter(source.home,own)', native)
        self.assertIn('source.enter(foreground,previous)', native)
        self.assertIn('foreground!=own && foreground!=source.home', native)
        self.assertIn('MAX_CHECKS=50', native)
        self.assertIn('checkTimer.start(', native)
        self.assertIn('token!=epoch || step!=phase', native)
        self.assertNotIn('unloadDataForClass', native)
        self.assertNotIn('own.destroy()', native)
        self.assertNotIn('desktop.enterView(', native)
        self.assertIn('getViewHandler(\n                source.provider,source.home.getShortViewHandlerName(),true)', native)

    def test_oem_templates_and_original_clone_lifetime(self):
        binding = (H / "MibrOemSsmTemplate.java").read_text()
        for skin in ("skin1", "skin2"):
            source = (OEM / skin / "Ssm_5458.java").read_text()
            for target in (24786208,47234883,120460962,53708779,40267630,86648370,
                           76384521,18238209,45796615,37984426,47818560,4894361,
                           101603979,70740890,64398879):
                self.assertIn('(int)' + str(target), source)
                self.assertIn('=' + str(target) + ';', binding)
        rows = code("MibrOwnedSsmRows")
        self.assertIn('handler.createWidgetCloneable(template)', rows)
        self.assertIn('handler.destroyWidgetCloneable(masters[i])', rows)
        self.assertIn('stock.mainList.setListItemTransfer(originalTransfer)', rows)
        self.assertNotIn('new TextArea(', rows)
        self.assertNotIn('new Button(', rows)
        self.assertNotIn('get_font()', rows)  # exact stock native row fonts are retained
        dropdown = code("MibrNativeDropdownEditor")
        self.assertIn('button.get_dropDownRef()!=stock.popup', dropdown)
        self.assertIn('stock.options.setListItemTransfer(originalTransfer)', dropdown)
        self.assertIn('item.set_activatedIndex(model.selectedOption(key))', dropdown)
        self.assertIn('set_lineBreakMode(TextAreaModel.LINEBREAKMODE_CHARACTER)', dropdown)

    def test_local_model_and_outgoing_event_quarantine(self):
        isolated = code("MibrIsolatedSsmServices")
        methods = re.findall(r'public void (createAndSubmit\w+|submitEvent)\([^)]*\)\s*\{([^{}]*)\}', isolated)
        self.assertEqual(len(methods), 15)
        self.assertTrue(all(not body.strip() for _, body in methods))
        self.assertIn('public void invoke(Runnable action) { ui.invoke(action); }', isolated)
        for forbidden in ('resources.getModelDatapool(', 'resources.getListControlCache(',
                          'resources.getDynamicListItemControlManager(', 'appServices.getViewEventDispatcher('):
            self.assertNotIn(forbidden, isolated)
        all_native = '\n'.join(code(n) for n in ('MibrSsmNativePage','MibrSsmSourceBinding',
                          'MibrOwnedSsmRows','MibrIsolatedSsmServices'))
        for forbidden in ('DSI', 'CioDispatcher', 'dispatchCio', 'FileOutputStream', 'Runtime.getRuntime',
                          'NativeAppDisplay', 'org.korho', 'System.setProperty'):
            self.assertNotIn(forbidden, all_native)

    def test_home_and_focus_restored_without_radio_dispatch(self):
        home = code("MibrHomeList")
        self.assertNotIn('stockFactory.createWidgetCloneable(template)', home)
        self.assertIn('item.setCloneData(new Data())', home)
        self.assertIn('MibrOemPageEntry.requestOpen()', home)
        self.assertIn('MibrOemPageEntry.requestOpen()', code("MibrHomeCio"))
        self.assertFalse((H / 'MibrContainer.java').exists())
        native = code("MibrSsmNativePage")
        for token in ('get_selectedIndex()', 'getFocusedIndex()', 'getFirstVisibleIndex()',
                      'set_selectedIndex(homeSelected)', 'setFocusedIndex(homeFocused)', 'snap(homeFirst,0)'):
            self.assertIn(token, native)
        self.assertIn('MibrSsmSourceBinding.lifecycle(handler)', native)
        positions = [native.index(call) for call in ('handler.deactivate()', 'handler.deinit()', 'handler.teardown()', 'handler.destroy()')]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('own.isLinked()', native)


if __name__ == '__main__':
    unittest.main()
