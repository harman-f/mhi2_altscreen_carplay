"""Host double for the pass-through Sgm animation mirror on the owned CP tile.

The 72-row access table is read from the retained decoded MU1440 Sgm source,
so a changed table is caught here and fails closed on the unit.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import profile_stubs

P = Path(__file__).resolve().parents[1]
H = P / "java/de/mibr/hmi"
SGM = (P.parents[2] / "reference/viewhandler-sgm-decoded/evidence-r2/cfr/Sgm/generated/de/vw/mib/"
       "simplegridmenu/view/internal/Sgm.java")

STUBS = {
"de/vw/mib/widgets/models/WidgetModel.java": "package de.vw.mib.widgets.models; public interface WidgetModel {}",
"de/vw/mib/view/internal/CloneData.java": """package de.vw.mib.view.internal;
public class CloneData { public static final int ROOT_MASTER_ID=-1; public CloneData next; public final de.vw.mib.widgets.models.WidgetModel[] widgets; public final int masterId;
 public CloneData(int n,int m){widgets=new de.vw.mib.widgets.models.WidgetModel[n];masterId=m;}}""",
"de/vw/mib/view/internal/WidgetAnimator.java": """package de.vw.mib.view.internal;
public interface WidgetAnimator { void setAnimatableIntValue(de.vw.mib.widgets.models.WidgetModel w,int t,int what,int v); void setAnimatableFloatValue(de.vw.mib.widgets.models.WidgetModel w,int t,int what,float v); }""",
"de/vw/mib/view/internal/AnimationAdapters.java": """package de.vw.mib.view.internal;
public class AnimationAdapters {
 private final int[][] data; private final de.vw.mib.widgets.models.WidgetModel[] widgets; private final WidgetAnimator widgetAnimator;
 public static int stockInt;
 public AnimationAdapters(int[][] d,CloneData c,WidgetAnimator a){data=d;widgets=c.widgets;widgetAnimator=a;}
 public boolean getAnimBooleanValue(int n,int m){return false;} public void setAnimBooleanValue(int n,int m,boolean b){}
 public int getAnimIntValue(int n,int m){return 0;} public float getAnimFloatValue(int n,int m){return 0f;}
 public void setAnimIntValue(int n,int m,int v){stockInt++;} public void setAnimFloatValue(int n,int m,float v){}
}""",
"de/vw/mib/view/internal/AbstractViewHandler.java": """package de.vw.mib.view.internal;
public class AbstractViewHandler { protected AnimationAdapters animationAdapters; }""",
}

TEST = r"""package de.mibr.hmi;
import de.vw.mib.view.internal.*;
import de.vw.mib.widgets.models.WidgetModel;
public class MirrorTest {
 static int last=-999,writes;
 static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
 static int id(int[][] t,int idx,int what){for(int i=0;i<t.length;i++)if(t[i][1]==idx&&t[i][4]==what)return t[i][0];throw new AssertionError("row");}
 public static void main(String[] a)throws Exception{
  int[][] table=TABLE;
  WidgetAnimator anim=new WidgetAnimator(){
   public void setAnimatableIntValue(WidgetModel w,int t,int what,int v){if(w!=null){last=v;writes++;}}
   public void setAnimatableFloatValue(WidgetModel w,int t,int what,float v){}};
  final WidgetModel tile=new WidgetModel(){};
  AnimationAdapters stock=new AnimationAdapters(table,new CloneData(1,-1),anim);
  AbstractViewHandler sgm=new AbstractViewHandler(){};
  java.lang.reflect.Field f=AbstractViewHandler.class.getDeclaredField("animationAdapters");f.setAccessible(true);f.set(sgm,stock);
  MibrHomeAnimationMirror m=MibrHomeAnimationMirror.install(sgm,new MibrHomeAnimationMirror.Targets(){public WidgetModel[] ownedTiles(){return new WidgetModel[]{tile};}});
  check(m!=null && f.get(sgm)==m,"installed on exact table");
  // Foreign transition: Settings zooms (z=-50), Tuner/Sound recede (z=200/210): ours gets the median receding value.
  m.setAnimIntValue(id(table,5,16),0,200);m.setAnimIntValue(id(table,18,16),0,210);
  check(writes==0,"no mirror before all three donors are known");
  m.setAnimIntValue(id(table,22,16),0,-50);
  check(last==200,"median follows receding tiles, not the zooming Settings tile");
  check(AnimationAdapters.stockInt==3,"every write reaches the stock adapter");
  m.setAnimIntValue(id(table,13,16),0,-80);
  check(last==200,"SmartPhoneIntegration ignored outside own transition");
  // Own transition: ours follows the SmartPhoneIntegration (Ssm_5458 page) tile.
  MibrHomeAnimationMirror.ownTransitionStarted();
  m.setAnimIntValue(id(table,5,16),0,300);check(last==200,"receding donors ignored during own transition");
  m.setAnimIntValue(id(table,13,16),0,-90);check(last==-90,"own transition mirrors the SmartPhoneIntegration track");
  MibrHomeAnimationMirror.ownTransitionEnded();
  m.setAnimIntValue(id(table,13,16),0,-10);check(last==-10,"return animation still mirrored while settling");
  m.restore(sgm);check(f.get(sgm)==stock,"restore puts the stock adapter back");
  int[][] bad=new int[72][];System.arraycopy(table,0,bad,0,72);
  check(MibrHomeAnimationMirror.wrap(new AnimationAdapters(bad,new CloneData(1,-1),anim),null)==null,"changed table fails closed");
  System.out.println("MIBR_HOME_ANIMATION_MIRROR_PASS");
 }
}
"""


class HomeAnimationMirror(unittest.TestCase):
    def test_mirror_follows_oem_tracks(self):
        if not SGM.is_file():
            self.skipTest("requires private decoded MU1440 Sgm source fixture")
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK required")
        body = SGM.read_text(encoding="utf-8")
        m = re.search(r"getAnimationAdapters\(WidgetAnimator widgetAnimator\) \{\s*int\[\]\[\] nArrayArray = new int\[\]\[\](\{.*?\});", body, re.S)
        self.assertIsNotNone(m)
        table = m.group(1)
        self.assertEqual(table.count("{") - 1, 73)
        root = Path(tempfile.mkdtemp(prefix="mibr-anim-mirror-"))
        sources = []
        for rel, text in list(STUBS.items()) + list(profile_stubs.STUBS.items()):
            p = root / "src" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            sources.append(str(p))
        t = root / "src/de/mibr/hmi/MirrorTest.java"
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(TEST.replace("TABLE", "new int[][]" + table), encoding="utf-8")
        sources += [str(t), str(H / "MibrHomeAnimationMirror.java")] + [str(x) for x in profile_stubs.REAL_SOURCES]
        out = root / "classes"
        out.mkdir()
        run = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(out)] + sources, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        run = subprocess.run([java, "-cp", str(out), "de.mibr.hmi.MirrorTest"], capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("MIBR_HOME_ANIMATION_MIRROR_PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
