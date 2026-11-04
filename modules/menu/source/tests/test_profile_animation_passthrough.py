"""Profile-driven home animation table: strict by default, pass-through when a profile accepts it.

Reuses the OEM doubles of the mirror test with a synthetic table; no private
fixture is required.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import profile_stubs
import test_home_animation_mirror as mirror

TEST = r"""package de.mibr.hmi;
import de.vw.mib.view.internal.*;
import de.vw.mib.widgets.models.WidgetModel;
public class PassThroughTest {
 static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
 public static void main(String[] a)throws Exception{
  WidgetAnimator anim=new WidgetAnimator(){
   public void setAnimatableIntValue(WidgetModel w,int t,int what,int v){}
   public void setAnimatableFloatValue(WidgetModel w,int t,int what,float v){}};
  boolean accept=Boolean.getBoolean("mibr.test.passthrough");
  int[][] profileTable={{1,2,3}};
  MibrHomeAnimationMirror m=MibrHomeAnimationMirror.wrap(new AnimationAdapters(profileTable,new CloneData(1,-1),anim),null);
  check((m!=null)==accept,"profile table accepted only when the profile names it");
  int[][] other={{9,9,9}};
  check(MibrHomeAnimationMirror.wrap(new AnimationAdapters(other,new CloneData(1,-1),anim),null)==null,"foreign table fails closed");
  System.out.println("MIBR_PASSTHROUGH_PASS");
 }
}
"""


class ProfileAnimationPassThrough(unittest.TestCase):
    def _run(self, accept):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK required")
        root = Path(tempfile.mkdtemp(prefix="mibr-passthrough-"))
        sources = []
        for rel, text in list(mirror.STUBS.items()) + list(profile_stubs.STUBS.items()):
            p = root / "src" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            sources.append(str(p))
        t = root / "src/de/mibr/hmi/PassThroughTest.java"
        t.write_text(TEST, encoding="utf-8")
        sources += [str(t), str(mirror.H / "MibrHomeAnimationMirror.java")]
        sources += [str(x) for x in profile_stubs.REAL_SOURCES]
        out = root / "classes"
        out.mkdir()
        run = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(out)] + sources,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        run = subprocess.run([java, "-Dmibr.test.passthrough=" + ("true" if accept else "false"),
                              "-cp", str(out), "de.mibr.hmi.PassThroughTest"],
                             capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("MIBR_PASSTHROUGH_PASS", run.stdout)

    def test_strict_profile_rejects_foreign_table(self):
        self._run(False)

    def test_pass_through_profile_accepts_its_table(self):
        self._run(True)


if __name__ == "__main__":
    unittest.main()
