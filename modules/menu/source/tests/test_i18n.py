"""Language selection for the generated menu texts: de -> German, everything else -> English."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
H = MODULE / "java/de/mibr/hmi"
ROOT = MODULE.parents[2]

TEST = r"""package de.mibr.hmi;
public class I18nTest {
 static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
 public static void main(String[] a){
  check(!MibrI18n.german(),"no HMI service class: unreadable language falls back to English");
  String[] de={"de_DE","DE","de"},other={"en_GB","cs_CZ","","xx"};
  for(int i=0;i<de.length;i++){MibrI18n.forced=de[i];check(MibrMenuDefinition.title().equals("CarPlay-Einstellungen"),"de "+de[i]);}
  MibrI18n.forced="en_US";check(MibrMenuDefinition.title().equals("CarPlay settings"),"en");
  check(MibrMenuDefinition.groupNames()[0].equals("Views") && MibrMenuDefinition.groupNames()[1].equals("Advanced"),"en group");
  check(MibrSettingsCatalog.label(0).length()>0,"en label");
  MibrI18n.forced="cs_CZ";check(MibrMenuDefinition.title().equals("CarPlay settings"),"cs falls back to en");
  MibrI18n.forced="de_DE";check(MibrSettingsCatalog.label(0).equals(MibrSettingsCatalog.LABELS_DE[0]),"de label");
  check(MibrI18n.validMenuOverride("AUTO") && MibrI18n.validMenuOverride("de") && MibrI18n.validMenuOverride("en"),"three supported menu override values");
  check(!MibrI18n.validMenuOverride("DE") && !MibrI18n.validMenuOverride("") && !MibrI18n.validMenuOverride(null),"invalid override values rejected");
  MibrI18n.forced="de_DE";
  MibrI18n.applyMenuOverride("en");
  check(!MibrI18n.german() && MibrMenuDefinition.title().equals("CarPlay settings"),"English override must win over German car language");
  MibrI18n.forced="en_US";
  MibrI18n.applyMenuOverride("de");
  check(MibrI18n.german() && MibrMenuDefinition.title().equals("CarPlay-Einstellungen"),"German override must win over English car language");
  boolean rejected=false;
  try{MibrI18n.applyMenuOverride("fr");}catch(IllegalArgumentException expected){rejected=true;}
  check(rejected && "de".equals(MibrI18n.menuOverride()),"invalid override preserves selected mode");
  MibrI18n.applyMenuOverride("AUTO");
  check(!MibrI18n.german() && MibrMenuDefinition.title().equals("CarPlay settings"),"AUTO restores current car locale");
  MibrI18n.forced="de_DE";
  check(MibrI18n.german(),"AUTO again follows German car locale");
  MibrI18n.forced=null;
  check(!MibrI18n.german(),"AUTO falls back to English for unreadable car locale");
    check(MibrSettingsCatalog.LABELS_DE.length==MibrSettingsCatalog.LABELS_EN.length,"tables equal");
  for(int i=0;i<MibrSettingsCatalog.LABELS_EN.length;i++)check(MibrSettingsCatalog.LABELS_EN[i].length()>0,"en text "+i);
  System.out.println("MIBR_I18N_PASS");
 }
}
"""

class I18n(unittest.TestCase):
    def test_language_selection(self):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK required")
        root = Path(tempfile.mkdtemp(prefix="mibr-i18n-"))
        generated = root / "generated"
        generated.mkdir()
        generation = subprocess.run([
            "python3", str(MODULE / "generate_catalog.py"),
            "--registry", str(ROOT / "settings/registry.json"),
            "--menu", str(MODULE / "menu-definition.json"),
            "--out-dir", str(generated),
        ], capture_output=True, text=True)
        self.assertEqual(generation.returncode, 0, generation.stdout + generation.stderr)
        t = root / "src/de/mibr/hmi/I18nTest.java"
        t.parent.mkdir(parents=True)
        t.write_text(TEST, encoding="utf-8")
        out = root / "classes"
        out.mkdir()
        srcs = [str(t), str(H / "MibrI18n.java"), str(generated / "MibrMenuDefinition.java"),
                str(generated / "MibrSettingsCatalog.java")]
        r = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(out)] + srcs, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([java, "-cp", str(out), "de.mibr.hmi.I18nTest"], capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("MIBR_I18N_PASS", r.stdout)

if __name__ == "__main__":
    unittest.main()
