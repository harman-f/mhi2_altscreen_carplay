"""Offline OEM-source binding and retired Sgm overlay guard."""
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
H=P/'java/de/mibr/hmi'
class OEMBoundary(unittest.TestCase):
 def test_no_overlay_and_single_admission(self):
  self.assertFalse((H/'MibrContainer.java').exists())
  factory_path=P/'java/generated/de/vw/mib/global/view/internal/WidgetFactoryImpl.java'
  if not factory_path.is_file(): self.skipTest('requires private OEM WidgetFactory source used only by the local build')
  factory=factory_path.read_text()
  self.assertIn('case 11: {\n                return new Container();',factory)
  for n in ('MibrHomeList','MibrHomeCio'):
   s=(H/(n+'.java')).read_text()
   self.assertIn('MibrOemPageEntry.requestOpen()',s)
   self.assertNotIn('MibrContainer',s)
 def test_two_stock_dropdowns_pin_exact_ids(self):
  x=(H/'MibrOemSsmTemplate.java').read_text()
  refs=P.parents[2]/'reference/oem-dropdown-mu1440'
  if not all((refs/skin/'Ssm_5458.java').is_file() for skin in ('skin1','skin2')):
   self.skipTest('requires private MU1440 OEM dropdown sources')
  for skin in ('skin1','skin2'):
   source=(refs/skin/'Ssm_5458.java').read_text()
   for id in (24786208,47234883,120460962,53708779,40267630,86648370,76384521,18238209):
    self.assertIn('(int)'+str(id),source)
    self.assertIn('='+str(id)+';',x)
  self.assertIn('uniqueTarget(view,POPUP_TARGET_ID,DropDown.class,0)',x)
  self.assertNotIn('first(view,DropDown.class',x)
 def test_no_fake_page(self):
  entry=(H/'MibrOemPageEntry.java').read_text()
  self.assertIn('if (page == null || opening) return false;',entry)
  self.assertNotIn('setChildren(',entry)
if __name__=='__main__':unittest.main()
