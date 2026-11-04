"""Host double for the long press on the stock SmartPhoneIntegration HOME tile.

Stubs carry only the members MibrOemTileLongPress uses; the controller stub
mirrors DefaultPushButtonController: mode 2 fires longPressed, and the release
after it fires longReleased instead of released.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

if __package__:
    from . import profile_stubs
else:
    import profile_stubs

P = Path(__file__).resolve().parents[1]
H = P / "java/de/mibr/hmi"

STUBS = {
"de/vw/mib/widgets/models/WidgetModel.java": "package de.vw.mib.widgets.models; public interface WidgetModel { Object getController(); }",
"de/vw/mib/widgets/event/OutEventListener.java": """package de.vw.mib.widgets.event;
public interface OutEventListener { void outHMIEventFired(String a); void outIntegerEventFired(String a,int b); void outBooleanEventFired(String a,boolean b);
 void outStringEventFired(String a,String b); void outPointEventFired(String a,int b,int c,int d,int e); void outListItemEventFired(String a,int b,int c,int d,int e,String f,long g);
 void outSpellerEventFired(String a,String b,int c,int d,int e); }""",
"de/vw/mib/widgets/controller/AbstractWidgetController.java": """package de.vw.mib.widgets.controller;
public abstract class AbstractWidgetController { public final java.util.Vector listeners=new java.util.Vector();
 public final void addOutEventListener(de.vw.mib.widgets.event.OutEventListener l){if(!listeners.contains(l))listeners.addElement(l);}
 public final void removeOutEventListener(de.vw.mib.widgets.event.OutEventListener l){listeners.removeElement(l);}
 protected void fire(String e){for(int i=0;i<listeners.size();i++)((de.vw.mib.widgets.event.OutEventListener)listeners.elementAt(i)).outHMIEventFired(e);} }""",
"de/vw/mib/widgets/controller/DefaultPushButtonController.java": """package de.vw.mib.widgets.controller;
public class DefaultPushButtonController extends AbstractWidgetController { public de.vw.mib.widgets.Button b; public boolean longFired;
 public void press(){} public void timerElapsed(){if(b.get_buttonMode()==2){longFired=true;fire("longPressed");}}
 public void release(){if(b.get_buttonMode()==2&&longFired){longFired=false;fire("longReleased");}else fire("released");} }""",
"de/vw/mib/widgets/Button.java": """package de.vw.mib.widgets;
public class Button implements de.vw.mib.widgets.models.WidgetModel { String name; int mode, start; public boolean timerChanged; public Object controller;
 public Button(String n){name=n;} public Object getController(){return controller;} public final String get_name(){return name;}
 public final int get_buttonMode(){return mode;} public final void set_buttonMode(int m){mode=m;timerChanged=true;}
 public final int get_startTimePrimary(){return start;} public final void set_startTimePrimary(int s){start=s;timerChanged=true;}
 public final void setTimerChanged(boolean b){timerChanged=b;} }""",
"de/vw/mib/widgets/ListItem.java": """package de.vw.mib.widgets;
public class ListItem implements de.vw.mib.widgets.models.WidgetModel { String name; public ListItem(String n){name=n;} public Object getController(){return null;} public final String get_name(){return name;} }""",
"de/vw/mib/view/internal/CloneData.java": """package de.vw.mib.view.internal;
public class CloneData { public CloneData next; public final de.vw.mib.widgets.models.WidgetModel[] widgets; public CloneData(de.vw.mib.widgets.models.WidgetModel[] w){widgets=w;} }""",
"de/vw/mib/view/internal/AbstractViewHandler.java": "package de.vw.mib.view.internal; public class AbstractViewHandler {}",
"generated/Sgm.java": """package generated;
public class Sgm extends de.vw.mib.view.internal.AbstractViewHandler { private de.vw.mib.view.internal.CloneData gridMenuPlateWidgetListListItemSmartPhoneIntegrationCloneMaster;
 public void set(de.vw.mib.view.internal.CloneData c){gridMenuPlateWidgetListListItemSmartPhoneIntegrationCloneMaster=c;} }""",
}

TEST = r"""package de.mibr.hmi;
import de.vw.mib.view.internal.*;
import de.vw.mib.widgets.*;
import de.vw.mib.widgets.controller.*;
import de.vw.mib.widgets.models.WidgetModel;
public class LongPressTest {
 static int opened, carplay;
 static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
 static Button tile(generated.Sgm sgm, CloneData[] out){
  Button b=new Button("ButtonSmartPhoneIntegration");final DefaultPushButtonController c=new DefaultPushButtonController();c.b=b;b.controller=c;
  c.addOutEventListener(new de.vw.mib.widgets.event.OutEventListener(){
   public void outHMIEventFired(String e){if("released".equals(e))carplay++;}
   public void outIntegerEventFired(String a,int b){} public void outBooleanEventFired(String a,boolean b){} public void outStringEventFired(String a,String b){}
   public void outPointEventFired(String a,int b,int c,int d,int e){} public void outListItemEventFired(String a,int b,int c,int d,int e,String f,long g){}
   public void outSpellerEventFired(String a,String b,int c,int d,int e){}});
  CloneData cd=new CloneData(new WidgetModel[]{new ListItem("ListItemSmartPhoneIntegration"),b});out[0]=cd;return b;}
 public static void main(String[] a)throws Exception{
  generated.Sgm sgm=new generated.Sgm(); CloneData[] cd=new CloneData[1];
  Button b=tile(sgm,cd); sgm.set(cd[0]);
  Runnable open=new Runnable(){public void run(){opened++;}};
  check(MibrOemTileLongPress.install(new AbstractViewHandler(),open)==null,"no Sgm field: untouched");
  MibrOemTileLongPress lp=MibrOemTileLongPress.install(sgm,open);
  check(lp!=null && b.get_buttonMode()==2 && b.get_startTimePrimary()==MibrOemTileLongPress.LONG_PRESS_MS,"armed mode 2");
  DefaultPushButtonController c=(DefaultPushButtonController)b.controller;
  c.press();c.release();check(carplay==1&&opened==0,"short tap still opens CarPlay only");
  c.press();c.timerElapsed();c.release();check(opened==1&&carplay==1,"long press opens settings, not CarPlay");
  lp.refresh();check(c.listeners.size()==2,"refresh does not double-hook");
  b.set_buttonMode(0);lp.refresh();check(b.get_buttonMode()==2,"re-armed after Sgm re-init");
  boolean rr=Boolean.getBoolean("mibr.test.reregister");
  if(rr){
   int before=opened;c.listeners.removeAllElements();lp.refresh();
   c.press();c.timerElapsed();c.release();check(opened==before+1&&c.listeners.size()==1,"hook re-registered after deInit cleared listeners");
   lp.refresh();check(c.listeners.size()==1,"re-registration is idempotent");
  }
  lp.restore();check(b.get_buttonMode()==0&&b.get_startTimePrimary()==0&&c.listeners.size()==(rr?0:1),"restore puts stock back");
  Button other=new Button("ButtonOther");other.controller=new DefaultPushButtonController();
  sgm.set(new CloneData(new WidgetModel[]{new ListItem("ListItemOther"),other}));
  MibrOemTileLongPress.install(sgm,open);check(other.get_buttonMode()==0,"foreign layout untouched");
  System.out.println("MIBR_OEM_TILE_LONGPRESS_PASS");
 }
}
"""


class OemTileLongPress(unittest.TestCase):
    def test_long_press_opens_settings_short_tap_unchanged(self):
        self._run(False)

    def test_listeners_cleared_profile_reregisters_hook(self):
        self._run(True)

    def _run(self, reregister):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK required")
        root = Path(tempfile.mkdtemp(prefix="mibr-oem-longpress-"))
        sources = []
        for rel, text in list(STUBS.items()) + list(profile_stubs.STUBS.items()):
            p = root / "src" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            sources.append(str(p))
        t = root / "src/de/mibr/hmi/LongPressTest.java"
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(TEST, encoding="utf-8")
        sources += [str(t), str(H / "MibrOemTileLongPress.java")] + [str(x) for x in profile_stubs.REAL_SOURCES]
        out = root / "classes"
        out.mkdir()
        run = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(out)] + sources, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        run = subprocess.run([java, "-Dmibr.test.reregister=" + ("true" if reregister else "false"),
                              "-cp", str(out), "de.mibr.hmi.LongPressTest"], capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("MIBR_OEM_TILE_LONGPRESS_PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
