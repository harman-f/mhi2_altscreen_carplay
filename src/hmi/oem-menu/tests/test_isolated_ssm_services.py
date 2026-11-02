"""Focused desktop-JVM regression for the production isolated SSM services.

The ROM API is unavailable here, so this compiles the real MibrIsolatedSsmServices
against small authored interface/resource doubles. It exercises ownership boundaries;
it does not claim to validate OEM implementation behavior or vehicle integration.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
JAVA = P / "java/de/mibr/hmi/MibrIsolatedSsmServices.java"


STUBS = {
    "de/vw/mib/app/appadapter/CellValue.java": "package de.vw.mib.app.appadapter; public class CellValue {}",
    "de/vw/mib/app/framework/AppDefinition.java": "package de.vw.mib.app.framework; public class AppDefinition {}",
    "de/vw/mib/datapool/ModelDatapool.java": """package de.vw.mib.datapool;
import de.vw.mib.graphics.*;import de.vw.mib.graphics.image.Image;import de.vw.mib.properties.values.*;import org.dsi.ifc.global.ResourceLocator;
public interface ModelDatapool {
boolean getBoolean(int i);int getInteger(int i);long getLong(int i);float getFloat(int i);String getString(int i);Object getRawObject(int i);boolean[] getFlagVector(int i);int[] getIntegerArray(int i);int[] getIntegerVector(int i);String[] getStringVector(int i);Image[] getImageVector(int i);Gradient getGradient(int i);Gradient[] getGradientVector(int i);FixFormatterFieldData getFixFormatterFieldData(int i);LabeledIconValue getLabeledIconValue(int i);ResourceLocator getResourceLocator(int i);SpellerData getSpellerData(int i);
void setBoolean(int i,boolean v);void setInteger(int i,int v);void setLong(int i,long v);void setFloat(int i,float v);void setString(int i,String v);void setRawObject(int i,Object v);void setFlagVector(int i,boolean[] v);void setIntegerArray(int i,int[] v);void setIntegerVector(int i,int[] v);void setStringVector(int i,String[] v);void setImageVector(int i,Image[] v);void setGradient(int i,Gradient v);void setGradientVector(int i,Gradient[] v);void setFixFormatterFieldData(int i,FixFormatterFieldData v);void setLabeledIconValue(int i,LabeledIconValue v);void setResourceLocator(int i,ResourceLocator v);void setSpellerData(int i,SpellerData v);
void registerDatapoolUpdate(ModelDatapoolObserver o);void registerObserver(int i,ModelDatapoolObserver o);void registerObserver(int i,ModelDatapoolObserver o,boolean immediate);void unregisterObserver(int i,ModelDatapoolObserver o);
}""",
    "de/vw/mib/datapool/ModelDatapoolObserver.java": "package de.vw.mib.datapool; public interface ModelDatapoolObserver { void datapoolValueChanged(int id); }",
    "de/vw/mib/datapool/DynamicListItemControlManager.java": "package de.vw.mib.datapool; import de.vw.mib.app.appadapter.CellValue; public interface DynamicListItemControlManager { CellValue getCellValue(CellValue v,int l,int r,int c); ExtendedListItemControl getListItemControl(int id); }",
    "de/vw/mib/datapool/ExtendedListItemControl.java": "package de.vw.mib.datapool; public interface ExtendedListItemControl {}",
    "de/vw/mib/datapool/AppAdapterListItemControlManager.java": "package de.vw.mib.datapool; import de.vw.mib.datapool.internal.AppAdapterListItemControl; public interface AppAdapterListItemControlManager { AppAdapterListItemControl getListItemControl(int id); }",
    "de/vw/mib/datapool/internal/AppAdapterListItemControl.java": "package de.vw.mib.datapool.internal; public class AppAdapterListItemControl {}",
    "de/vw/mib/datapool/LocalListItemControl.java": "package de.vw.mib.datapool; public class LocalListItemControl implements ExtendedListItemControl { public final int id; public LocalListItemControl(int i){id=i;} }",
    "de/vw/mib/event/HMIEvent.java": "package de.vw.mib.event; public class HMIEvent {}",
    "de/vw/mib/event/dispatcher/ViewEventDispatcher.java": """package de.vw.mib.event.dispatcher; import de.vw.mib.app.framework.AppDefinition;import de.vw.mib.event.HMIEvent;public interface ViewEventDispatcher {void invoke(Runnable r);void createAndSubmitBooleanValueEvent(int i,boolean v);void createAndSubmitHMIEvent(int i);void createAndSubmitIntegerValueEvent(int i,int v);void createAndSubmitListItemEvent(int i,int a,int b,int c,int d,String s,long l);void createAndSubmitPointEvent(int i,int a,int b,int c,int d);void createAndSubmitSpellerValueEvent(int i,String s,int a,int b,int c);void createAndSubmitStringValueEvent(int i,String s);void createAndSubmitBooleanValueEvent(AppDefinition a,AppDefinition b,int i,boolean v);void createAndSubmitHMIEvent(AppDefinition a,AppDefinition b,int i);void createAndSubmitIntegerValueEvent(AppDefinition a,AppDefinition b,int i,int v);void createAndSubmitListItemEvent(AppDefinition a,AppDefinition b,int i,int w,int x,int y,int z,String s,long l);void createAndSubmitPointEvent(AppDefinition a,AppDefinition b,int i,int w,int x,int y,int z);void createAndSubmitSpellerValueEvent(AppDefinition a,AppDefinition b,int i,String s,int x,int y,int z);void createAndSubmitStringValueEvent(AppDefinition a,AppDefinition b,int i,String s);void submitEvent(HMIEvent e);}""",
    "de/vw/mib/format/FixFormat.java": "package de.vw.mib.format; public class FixFormat {}",
    "de/vw/mib/graphics/Gradient.java": "package de.vw.mib.graphics; public class Gradient {}",
    "de/vw/mib/graphics/image/Image.java": "package de.vw.mib.graphics.image; public class Image {}",
    "de/vw/mib/log4mib/LoggerFactory.java": "package de.vw.mib.log4mib; public class LoggerFactory {}",
    "de/vw/mib/properties/values/FixFormatterFieldData.java": "package de.vw.mib.properties.values; public class FixFormatterFieldData {}",
    "de/vw/mib/properties/values/LabeledIconValue.java": "package de.vw.mib.properties.values; public class LabeledIconValue {}",
    "de/vw/mib/properties/values/SpellerData.java": "package de.vw.mib.properties.values; public class SpellerData {}",
    "de/vw/mib/skin/SkinAnimationPool.java": "package de.vw.mib.skin; public class SkinAnimationPool {}",
    "de/vw/mib/skin/SkinImagePool.java": "package de.vw.mib.skin; public class SkinImagePool {}",
    "de/vw/mib/view/internal/ViewHandlerServices.java": """package de.vw.mib.view.internal;import de.vw.mib.datapool.*;import de.vw.mib.format.FixFormat;import de.vw.mib.log4mib.LoggerFactory;import de.vw.mib.skin.*;import de.vw.mib.view.internal.treebuilder.WidgetTreeBuilder;public interface ViewHandlerServices {FixFormat getFixFormat();GlobalExpressionEvaluator getGlobalExpressionEvaluator();I18nDatapool getI18nDatapool();ListControlCache getListControlCache();DynamicListItemControlManager getDynamicListItemControlManager();LoggerFactory getLoggerFactory();ModelDatapool getModelDatapool();SkinAnimationPool getSkinAnimationPool();SkinImagePool getSkinImagePool();WidgetAnimator getWidgetAnimator();WidgetTreeBuilder getWidgetTreeBuilder();}""",
    "de/vw/mib/view/internal/ViewHandlerAppServices.java": "package de.vw.mib.view.internal;import de.vw.mib.app.framework.AppDefinition;import de.vw.mib.datapool.AppAdapterListItemControlManager;public interface ViewHandlerAppServices {AppDefinition getAppDefinition();AppAdapterListItemControlManager getAppAdapterListItemControlManager();}",
    "de/vw/mib/view/internal/GlobalExpressionEvaluator.java": "package de.vw.mib.view.internal; public class GlobalExpressionEvaluator {}",
    "de/vw/mib/view/internal/I18nDatapool.java": "package de.vw.mib.view.internal; public class I18nDatapool {}",
    "de/vw/mib/view/internal/ListControlCache.java": "package de.vw.mib.view.internal; public class ListControlCache {}",
    "de/vw/mib/view/internal/WidgetAnimator.java": "package de.vw.mib.view.internal; public class WidgetAnimator {}",
    "de/vw/mib/view/internal/treebuilder/WidgetTreeBuilder.java": "package de.vw.mib.view.internal.treebuilder; public class WidgetTreeBuilder {}",
    "de/vw/mib/widgets/internal/ServiceManager.java": "package de.vw.mib.widgets.internal; public class ServiceManager { public static de.vw.mib.event.dispatcher.ViewEventDispatcher eventDispatcher; }",
    "org/dsi/ifc/global/ResourceLocator.java": "package org.dsi.ifc.global; public class ResourceLocator {}",
    "de/mibr/hmi/MibrSsmSourceBinding.java": """package de.mibr.hmi;import de.vw.mib.view.internal.*;public class MibrSsmSourceBinding {static class Binding {final ViewHandlerServices services;final ViewHandlerAppServices appServices;Binding(ViewHandlerServices s,ViewHandlerAppServices a){services=s;appServices=a;}}}""",
}


HARNESS = r'''package de.mibr.hmi;
import de.vw.mib.app.appadapter.CellValue;import de.vw.mib.app.framework.AppDefinition;import de.vw.mib.datapool.*;import de.vw.mib.event.HMIEvent;import de.vw.mib.event.dispatcher.ViewEventDispatcher;import de.vw.mib.view.internal.*;import java.util.*;
public final class Harness {
 static final ArrayList<Runnable> queue=new ArrayList<Runnable>();static int[] submits={0};
 static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
 static final class UI implements ViewEventDispatcher {public void invoke(Runnable r){queue.add(r);}void hit(){submits[0]++;}public void createAndSubmitBooleanValueEvent(int i,boolean v){hit();}public void createAndSubmitHMIEvent(int i){hit();}public void createAndSubmitIntegerValueEvent(int i,int v){hit();}public void createAndSubmitListItemEvent(int i,int a,int b,int c,int d,String s,long l){hit();}public void createAndSubmitPointEvent(int i,int a,int b,int c,int d){hit();}public void createAndSubmitSpellerValueEvent(int i,String s,int a,int b,int c){hit();}public void createAndSubmitStringValueEvent(int i,String s){hit();}public void createAndSubmitBooleanValueEvent(AppDefinition a,AppDefinition b,int i,boolean v){hit();}public void createAndSubmitHMIEvent(AppDefinition a,AppDefinition b,int i){hit();}public void createAndSubmitIntegerValueEvent(AppDefinition a,AppDefinition b,int i,int v){hit();}public void createAndSubmitListItemEvent(AppDefinition a,AppDefinition b,int i,int w,int x,int y,int z,String s,long l){hit();}public void createAndSubmitPointEvent(AppDefinition a,AppDefinition b,int i,int w,int x,int y,int z){hit();}public void createAndSubmitSpellerValueEvent(AppDefinition a,AppDefinition b,int i,String s,int x,int y,int z){hit();}public void createAndSubmitStringValueEvent(AppDefinition a,AppDefinition b,int i,String s){hit();}public void submitEvent(HMIEvent e){hit();}}
 static final class Resources implements ViewHandlerServices,ViewHandlerAppServices {final AppDefinition app=new AppDefinition();public AppDefinition getAppDefinition(){return app;}public de.vw.mib.datapool.AppAdapterListItemControlManager getAppAdapterListItemControlManager(){return null;}public de.vw.mib.format.FixFormat getFixFormat(){return null;}public GlobalExpressionEvaluator getGlobalExpressionEvaluator(){return null;}public I18nDatapool getI18nDatapool(){return null;}public ListControlCache getListControlCache(){return null;}public DynamicListItemControlManager getDynamicListItemControlManager(){return null;}public de.vw.mib.log4mib.LoggerFactory getLoggerFactory(){return null;}public ModelDatapool getModelDatapool(){return null;}public de.vw.mib.skin.SkinAnimationPool getSkinAnimationPool(){return null;}public de.vw.mib.skin.SkinImagePool getSkinImagePool(){return null;}public WidgetAnimator getWidgetAnimator(){return null;}public de.vw.mib.view.internal.treebuilder.WidgetTreeBuilder getWidgetTreeBuilder(){return null;}}
 static MibrIsolatedSsmServices make(Resources r){return new MibrIsolatedSsmServices(new MibrSsmSourceBinding.Binding(r,r));}
 public static void main(String[] args){UI ui=new UI();de.vw.mib.widgets.internal.ServiceManager.eventDispatcher=ui;Resources r=new Resources();MibrIsolatedSsmServices a=make(r),b=make(r);
  ModelDatapool da=a.getModelDatapool(),db=b.getModelDatapool();check(da!=db,"datapools are per instance");check(a.getListControlCache()!=b.getListControlCache(),"list caches are per instance");
  da.setInteger(7,42);check(da.getInteger(7)==42 && db.getInteger(7)==0,"values isolated");final int[] observed={0};ModelDatapoolObserver observer=new ModelDatapoolObserver(){public void datapoolValueChanged(int id){observed[0]++;}};da.registerObserver(9,observer,true);check(observed[0]==1,"immediate observer registration is local callback");da.setInteger(9,5);check(observed[0]==1,"local writes are not forwarded as observer notifications");
  DynamicListItemControlManager la=a.getDynamicListItemControlManager(),lb=b.getDynamicListItemControlManager();Object ca=la.getListItemControl(12),caAgain=la.getListItemControl(12),cb=lb.getListItemControl(12);check(ca==caAgain && ca!=cb,"dynamic list controls cached only within their owner");CellValue cv=new CellValue();check(la.getCellValue(cv,1,2,3)==cv,"cell values pass through");
  ViewEventDispatcher ev=a.getViewEventDispatcher();final int[] ran={0};ev.invoke(new Runnable(){public void run(){ran[0]++;}});check(queue.size()==1 && ran[0]==0 && submits[0]==0,"invoke alone queues work");queue.remove(0).run();check(ran[0]==1,"queued invoke reaches UI dispatcher");
  AppDefinition app=new AppDefinition();ev.createAndSubmitBooleanValueEvent(1,true);ev.createAndSubmitHMIEvent(1);ev.createAndSubmitIntegerValueEvent(1,1);ev.createAndSubmitListItemEvent(1,1,2,3,4,"x",5L);ev.createAndSubmitPointEvent(1,1,2,3,4);ev.createAndSubmitSpellerValueEvent(1,"x",1,2,3);ev.createAndSubmitStringValueEvent(1,"x");ev.createAndSubmitBooleanValueEvent(app,app,1,true);ev.createAndSubmitHMIEvent(app,app,1);ev.createAndSubmitIntegerValueEvent(app,app,1,1);ev.createAndSubmitListItemEvent(app,app,1,1,2,3,4,"x",5L);ev.createAndSubmitPointEvent(app,app,1,1,2,3,4);ev.createAndSubmitSpellerValueEvent(app,app,1,"x",1,2,3);ev.createAndSubmitStringValueEvent(app,app,1,"x");ev.submitEvent(new HMIEvent());check(submits[0]==0 && queue.isEmpty(),"all outgoing dispatcher methods are no-op");
  a.clear();check(da.getInteger(7)==0 && da.getInteger(9)==0,"clear removes this instance's values");check(db.getInteger(7)==0,"clear leaves sibling isolated");da.registerObserver(9,observer,true);check(observed[0]==2,"clear removes observer registrations");check(b.getDynamicListItemControlManager().getListItemControl(12)==cb,"clear does not clear sibling dynamic controls");
  System.out.println("ISOLATED_SSM_SERVICES_PASS");
 }
}'''


class IsolatedSsmServices(unittest.TestCase):
    def test_production_isolation_boundaries(self):
        tmp = Path(tempfile.mkdtemp(prefix="mibr-isolated-ssm-services-"))
        configured = os.environ.get("MIBR_TEST_JAVA_HOME")
        javac = str(Path(configured) / "bin/javac") if configured else shutil.which("javac")
        java = str(Path(configured) / "bin/java") if configured else shutil.which("java")
        if os.name == "nt" and configured:
            javac += ".exe"
            java += ".exe"
        if not javac or not java:
            raise RuntimeError("Existing JDK required; set MIBR_TEST_JAVA_HOME (no installation/setup)")
        sources = []
        for relative, body in STUBS.items():
            path = tmp / "src" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            sources.append(str(path))
        harness = tmp / "src/de/mibr/hmi/Harness.java"
        harness.parent.mkdir(parents=True, exist_ok=True)
        harness.write_text(HARNESS, encoding="utf-8")
        sources.extend([str(harness), str(JAVA)])
        out = tmp / "classes"
        out.mkdir()
        compile_result = subprocess.run([javac, "-encoding", "UTF-8", "-source", "8", "-target", "8", "-d", str(out)] + sources,
                                        capture_output=True, text=True)
        if compile_result.returncode:
            self.fail(compile_result.stdout + compile_result.stderr)
        run = subprocess.run([java, "-cp", str(out), "de.mibr.hmi.Harness"],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("ISOLATED_SSM_SERVICES_PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
