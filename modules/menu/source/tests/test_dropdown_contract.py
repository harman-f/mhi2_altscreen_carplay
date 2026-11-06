"""Static ownership/transport guards; not native runtime or screenshot proof."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DropdownContract(unittest.TestCase):
    def test_no_mutating_transport(self):
        for name in ('MibrPopupEditorModel', 'MibrNativeDropdownEditor', 'MibrOemDropdownStyle'):
            source = (ROOT / 'java/de/mibr/hmi' / (name + '.java')).read_text(encoding='utf-8')
            for token in ('MibrControlClient', 'java.net', 'java.io', 'org.dsi', '.save(', '.setEffective(', '.send('):
                self.assertNotIn(token, source)

    def test_native_classes_and_no_clone_pool(self):
        source=(ROOT/'java/de/mibr/hmi/MibrNativeDropdownEditor.java').read_text(encoding='utf-8')
        for token in ('new DropDown()', 'new DropDownButton()', 'new WidgetList()', 'new ListItem()',
                      'new DefaultDropDownButtonController()', 'new DefaultListItemController()',
                      'new DefaultWidgetListController()', 'buttonReleased', 'removeOutEventListener',
                      'LINEBREAKMODE_CHARACTER', 'set_shorten(false)', 'new WidgetModel[values.length]'):
            self.assertIn(token,source)
        self.assertNotIn('setWidgetCloneFactory',source)
        self.assertLess(source.index('openerController.fire_closeDropDown()'), source.index('opener.set_dropDownRef(null)'))
        self.assertLess(source.index('opener.set_dropDownRef(null)'), source.index('popup.deInit()'))

    def test_oem_page_not_a_sgm_overlay(self):
        self.assertFalse((ROOT/'java/de/mibr/hmi/MibrContainer.java').exists())
        factory_path=ROOT/'java/generated/de/vw/mib/global/view/internal/WidgetFactoryImpl.java'
        if not factory_path.is_file():
            self.skipTest("requires private OEM WidgetFactory source used only by the local build")
        factory=factory_path.read_text(encoding='utf-8')
        for token in ('case 11: {\n                return new Container();',
                      'case 13: {\n                return new DropDown();',
                      'case 14: {\n                return new DropDownButton();',
                      'case 55: {\n                return new MibrHomeList();'):
            self.assertIn(token,factory)
        for name in ('MibrHomeList','MibrHomeCio'):
            s=(ROOT/'java/de/mibr/hmi'/(name+'.java')).read_text(encoding='utf-8')
            self.assertIn('MibrOemPageEntry.requestOpen()',s)
            self.assertNotIn('MibrContainer',s)

    def test_exact_oem_colour_literals(self):
        fixtures=ROOT.parents[2]/'reference/oem-dropdown-mu1440'
        if not all((fixtures/('skin%d'%skin)/'SkinLiteralPool.java').is_file() for skin in (1,2)):
            self.skipTest("requires private MU1440 OEM skin source fixtures")
        sources=[(fixtures/('skin%d'%skin)/'SkinLiteralPool.java').read_text(encoding='utf-8') for skin in (1,2)]
        for field in ('COLOR_16', 'COLOR__ARRAY1_10', 'COLOR__ARRAY1_30'):
            lines=[next(line.strip() for line in s.splitlines() if ' '+field+' =' in line) for s in sources]
            self.assertEqual(lines[0],lines[1],field)
        style=(ROOT/'java/de/mibr/hmi/MibrOemDropdownStyle.java').read_text(encoding='utf-8')
        self.assertNotIn('Class.forName',style)
        for value in ('0x4BFFFFFF','-9408400','-14690816'):
            self.assertIn(value,style)
            self.assertIn(value,sources[1])


    def test_skin_id_gate_is_explicit_and_fail_closed(self):
        """Custom skin3 deliberately shares skin1 mapping; skin0 remains blocked."""
        fixture_root = ROOT.parents[2] / 'reference/oem-dropdown-mu1440'
        if not all((fixture_root / ('skin%d'%skin) / 'Ssm_5458.jxe').is_file() for skin in (1,2)):
            self.skipTest("requires private MU1440 OEM skin binaries")
        style = (ROOT / 'java/de/mibr/hmi/MibrOemDropdownStyle.java').read_text(encoding='utf-8')
        editor = (ROOT / 'java/de/mibr/hmi/MibrNativeDropdownEditor.java').read_text(encoding='utf-8')
        self.assertTrue((fixture_root / 'skin1' / 'Ssm_5458.jxe').is_file())
        self.assertTrue((fixture_root / 'skin2' / 'Ssm_5458.jxe').is_file())
        self.assertFalse((fixture_root / 'skin0').exists(), 'unreviewed skin0 must not be inferred')
        self.assertFalse((fixture_root / 'skin3').exists(), 'skin3 reuses skin1; no separate OEM fixture claimed')
        self.assertIn('if (skin != 1 && skin != 2 && skin != 3) return null;', style)
        self.assertIn('skin==2 ? 215 : 213', style)
        for token in ('pool.getImageArray(823)', 'pool.getImageArray(698)',
                      'pool.getImageArray(147)', 'radio.length<14', 'arrow.length<14'):
            self.assertIn(token, style)
        self.assertIn('model.setAvailable(style!=null', editor)
        self.assertIn('if (!model.open(index)) return;', editor)
        # Explicit owner decision: Skin3 uses Skin1 bindings; Skin0 is excluded.
        self.assertNotIn('skin==1 ? 213 : 215', style)


    def test_home_tile_has_own_listitem_without_stock_action_inheritance(self):
        home = (ROOT / 'java/de/mibr/hmi/MibrHomeList.java').read_text(encoding='utf-8')
        self.assertIn('ListItem item = new ListItem();',home)
        self.assertIn('item.setController(new DefaultListItemController())',home)
        self.assertIn('item.setCloneData(new Data())',home)
        self.assertNotIn('stockFactory.createWidgetCloneable(template)',home)
        self.assertNotIn('stockCloneData',home)
        # Stock delegates only handle stock-owned entries, never our own clones.
        own=home.split('public void destroyWidgetCloneable(WidgetCloneable clone) {',1)[1]
        self.assertLess(own.index('return;'),own.index('stockFactory.destroyWidgetCloneable(clone);'))
        self.assertIn('master.setListItemControl(new LocalListItemControl(1));',home)


    def test_exact_stock_ssm_page_template_discovery_is_nonmutating(self):
        contract = (ROOT/'java/de/mibr/hmi/MibrOemSsmTemplate.java').read_text(encoding='utf-8')
        skins = ROOT.parents[2] / 'reference/oem-dropdown-mu1440'
        if not all((skins/skin/'Ssm_5458.java').is_file() for skin in ('skin1','skin2')):
            self.skipTest("requires private MU1440 OEM page source fixtures")
        for skin in ('skin1','skin2'):
            s=(skins/skin/'Ssm_5458.java').read_text(encoding='utf-8')
            self.assertIn('return "SMI_SETUP_MAIN";',s)
            self.assertIn('return 982;',s)
            for token in ('"SelectDevice"', '"ConnectionType"', '(int)24786208'):
                self.assertIn(token,s)
        for token in ('"SMI_SETUP_MAIN"', 'ROOT_TARGET_ID=24786208',
                      'internalViewId()','"SelectDevice"','"ConnectionType"',
                      'unique(view,ROW_PLAIN,ListItem.class,0)',
                      'unique(view,ROW_VALUE,ListItem.class,0)',
                      'uniqueTarget(view,MAIN_LIST_TARGET_ID,WidgetList.class,0)',
                      'uniqueTarget(value,OPENER_TARGET_ID,DropDownButton.class,0)',
                      'uniqueTarget(view,POPUP_TARGET_ID,DropDown.class,0)'):
            self.assertIn(token,contract)
        self.assertNotIn('setChildren(',contract)
        self.assertNotIn('MibrContainer',contract)
        self.assertNotIn('org.korho',contract)


if __name__ == '__main__': unittest.main()
