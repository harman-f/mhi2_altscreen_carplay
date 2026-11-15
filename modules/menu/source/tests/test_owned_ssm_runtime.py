"""Execute actual native host/binding against authored OEM contract doubles.

Original ROM/J9 native widgets cannot execute in a desktop JVM. The four actual
production host sources are compiled here unchanged; only OEM services/widgets,
the row renderer and isolated resource adapter are doubles. Exact target ABI,
original template IDs and quarantine are checked separately. No vehicle claim.
The timer and staged transition scenarios are authored deterministic doubles;
they verify host reactions and do not execute ScreenAreaDude or native widgets.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
H = P / "java/de/mibr/hmi"
STUBS = {
"de/vw/mib/app/framework/AppDefinition.java": "package de.vw.mib.app.framework; public class AppDefinition {}",
"de/vw/mib/view/internal/ViewHandlerServices.java": "package de.vw.mib.view.internal; public interface ViewHandlerServices {}",
"de/vw/mib/view/internal/ViewHandlerAppServices.java": "package de.vw.mib.view.internal; public interface ViewHandlerAppServices { de.vw.mib.app.framework.AppDefinition getAppDefinition(); }",
"de/vw/mib/timer/Invoker.java": "package de.vw.mib.timer; public interface Invoker { void invoke(Runnable r); }",
"de/vw/mib/timer/Timer.java": "package de.vw.mib.timer; public interface Timer { void start(Runnable r); void stop(); void setRunnable(Runnable r,Invoker i); }",
"de/vw/mib/timer/TimerManager.java": "package de.vw.mib.timer; public interface TimerManager { Timer createTimer(String n,long d,boolean repeat,Runnable r,Invoker i); }",
"de/vw/mib/event/dispatcher/ViewEventDispatcher.java": "package de.vw.mib.event.dispatcher; public interface ViewEventDispatcher extends de.vw.mib.timer.Invoker { void invoke(Runnable r); }",
"de/vw/mib/widgets/internal/ServiceManager.java": "package de.vw.mib.widgets.internal; public class ServiceManager { public static de.vw.mib.event.dispatcher.ViewEventDispatcher eventDispatcher; }",
"de/vw/mib/widgets/event/ViewChangedListener.java": """package de.vw.mib.widgets.event;
import de.vw.mib.widgets.View;
public interface ViewChangedListener {void viewCovered();void viewUncovered();void viewInited(View v);void viewEntered(View v);void viewLeft(View v);}
""",
"de/vw/mib/widgets/models/ViewModel.java": """package de.vw.mib.widgets.models;
import de.vw.mib.widgets.event.ViewChangedListener;
public interface ViewModel {int get_targetId();String get_name();void addViewChangedListener(ViewChangedListener l);void removeViewChangedListener(ViewChangedListener l);void onEnter();void onLeave();}
""",
"de/vw/mib/widgets/View.java": """package de.vw.mib.widgets;
import java.util.ArrayList;import de.vw.mib.widgets.event.ViewChangedListener;import de.vw.mib.widgets.models.ViewModel;
public class View implements ViewModel {
 public final int id;public final String name;private final ArrayList<ViewChangedListener> listeners=new ArrayList<ViewChangedListener>();
 public View(int id,String name){this.id=id;this.name=name;}public int get_targetId(){return id;}public String get_name(){return name;}
 public void addViewChangedListener(ViewChangedListener l){if(!listeners.contains(l))listeners.add(l);}public void removeViewChangedListener(ViewChangedListener l){listeners.remove(l);}
 public void onEnter(){for(ViewChangedListener l:new ArrayList<ViewChangedListener>(listeners))l.viewEntered(this);}
 public void onLeave(){for(ViewChangedListener l:new ArrayList<ViewChangedListener>(listeners))l.viewLeft(this);}
 public int listenerCount(){return listeners.size();}
}
""",
"de/vw/mib/viewmanager/internal/ViewHandler.java": "package de.vw.mib.viewmanager.internal; public interface ViewHandler {de.vw.mib.widgets.models.ViewModel getView();}",
"de/vw/mib/desktop/ViewHandlerProvider.java": "package de.vw.mib.desktop; public interface ViewHandlerProvider {de.vw.mib.viewmanager.internal.ViewHandler getViewHandler(String name);}",
"de/vw/mib/graphics/image/Image.java": "package de.vw.mib.graphics.image; public class Image {}",
"de/vw/mib/skin/SkinImagePool.java": "package de.vw.mib.skin; public class SkinImagePool {public de.vw.mib.graphics.image.Image[] getImageArray(int id){if(id!=686)throw new AssertionError(\"wrong checkbox array\");return new de.vw.mib.graphics.image.Image[18];}}",
"de/vw/mib/skin/SkinClassLoader.java": "package de.vw.mib.skin; public interface SkinClassLoader {de.vw.mib.viewmanager.internal.ViewHandler getViewHandler(String name);}",
"de/vw/mib/view/internal/AbstractViewHandler.java": """package de.vw.mib.view.internal;
import de.vw.mib.widgets.View;import de.mibr.hmi.Trace;
public class AbstractViewHandler implements de.vw.mib.viewmanager.internal.ViewHandler {
 protected ViewHandlerServices services;protected ViewHandlerAppServices appServices;private int lifeCycle=-1;private final View view;
 public AbstractViewHandler(View view){this.view=view;}
 private void step(int from,int to,String label){if(lifeCycle!=from)throw new IllegalStateException("bad lifecycle "+lifeCycle+" "+label);lifeCycle=to;Trace.events.add(view.id+":"+label);}
 public void postConstructor(ViewHandlerServices s,ViewHandlerAppServices a){step(-1,0,"post");services=s;appServices=a;}
 public void clearServices(){services=null;}public View getView(){return view;}public boolean isActivated(){return lifeCycle==4;}
 public void create(){step(0,1,"create");}public void setup(){step(1,2,"setup");if(view.id==24786208 && Trace.failSetup)throw new IllegalStateException("partial native setup");}
 public void init(boolean reset){step(2,3,"init");if(view.id==33077553)Trace.homeInit(view);}
 public void activate(){step(3,4,"activate");}public void deactivate(){step(4,3,"deactivate");}
 public void deinit(){step(3,2,"deinit");if(view.id==33077553)Trace.homeDeinit(view);}
 public void teardown(){step(2,1,"teardown");}public void destroy(){step(1,0,"destroy");Trace.destroyed++;}
}
""",
"de/vw/mib/desktop/internal/viewhandler/SmartViewHandler.java": """package de.vw.mib.desktop.internal.viewhandler;
import de.vw.mib.view.internal.AbstractViewHandler;import de.vw.mib.desktop.ViewHandlerProvider;import de.vw.mib.widgets.models.ViewModel;
public class SmartViewHandler {
 public final AbstractViewHandler handler;private final String name;private final ViewHandlerProvider provider;private int state;private boolean linked;
 public SmartViewHandler(de.vw.mib.viewmanager.internal.ViewHandler h,String name,ViewHandlerProvider p){handler=(AbstractViewHandler)h;this.name=name;provider=p;}
 public ViewModel getView(){return handler.getView();}public AbstractViewHandler getViewHandler(){return handler;}public ViewHandlerProvider getViewHandlerProvider(){return provider;}public String getShortViewHandlerName(){return name;}
 public boolean isLinked(){return linked;}public boolean isActive(){return state==5;}public boolean isInitialized(){return state>=3;}
 public void create(){handler.create();state=1;}public void setup(){if(state<2){handler.setup();state=2;}}
 public void init(){if(state<3){handler.init(false);state=3;}}
 public void link(){if(!linked){linked=true;if(state>=3){getView().onEnter();state=4;}}}
 public void activate(){if(state<3)init();if(state==3||state==4){handler.activate();state=5;}}
 public void deactivate(){if(state==5){handler.deactivate();getView().onLeave();state=3;}}
 public void leave(){if(state==5)deactivate();if(state>=3)handler.deinit();if(state>=2)handler.teardown();state=1;linked=false;}
}
""",
"de/vw/mib/desktop/internal/viewhandler/SmartViewHandlerProvider.java": "package de.vw.mib.desktop.internal.viewhandler; public interface SmartViewHandlerProvider { SmartViewHandler getViewHandler(de.vw.mib.desktop.ViewHandlerProvider p,String n,boolean create); }",
"de/vw/mib/desktop/internal/common/ServiceManager.java": """package de.vw.mib.desktop.internal.common;
public class ServiceManager {public static de.vw.mib.desktop.internal.DesktopManagerImpl desktopManager;public static de.vw.mib.desktop.internal.screenarea.ScreenTree screenAreaTree;public static de.vw.mib.skin.SkinClassLoader skinClassLoader;public static de.vw.mib.desktop.internal.viewhandler.SmartViewHandlerProvider smartViewHandlerProvider;public static de.vw.mib.timer.TimerManager timerManager;}
""",
"de/vw/mib/desktop/internal/screenarea/ScreenAreaNode.java": """package de.vw.mib.desktop.internal.screenarea;
import java.util.ArrayList;import java.util.List;
public class ScreenAreaNode {public final String path;public final ArrayList<ViewNode> views=new ArrayList<ViewNode>();public ScreenAreaNode(String p){path=p;}public List getChildren(){return views;}public String getScreenAreaPath(){return path;}public boolean isActive(){return true;}}
""",
"de/vw/mib/desktop/internal/screenarea/ViewNode.java": """package de.vw.mib.desktop.internal.screenarea;
import java.util.ArrayList;import java.util.List;import de.vw.mib.desktop.internal.viewhandler.SmartViewHandler;
public class ViewNode {public final SmartViewHandler smart;public final ArrayList<ScreenAreaNode> areas=new ArrayList<ScreenAreaNode>();public ViewNode(SmartViewHandler s){smart=s;}public SmartViewHandler getViewHandler(){return smart;}public List getChildren(){return areas;}}
""",
"de/vw/mib/desktop/internal/screenarea/ScreenTree.java": """package de.vw.mib.desktop.internal.screenarea;
import de.vw.mib.desktop.internal.viewhandler.SmartViewHandler;
public class ScreenTree {public final ScreenAreaNode root=new ScreenAreaNode("");public final ScreenAreaNode area=new ScreenAreaNode("ScreenAreaMenu");public ScreenAreaNode getScreenAreaNode(String p){return "".equals(p)?root:"ScreenAreaMenu".equals(p)?area:null;}
 public void registerViewHandler(String p,SmartViewHandler s){area.views.add(new ViewNode(s));}public void unregisterViewHandler(String p,SmartViewHandler s){for(int i=area.views.size()-1;i>=0;i--)if(area.views.get(i).smart==s)area.views.remove(i);}}
""",
"de/vw/mib/desktop/internal/ScreenAreaDude.java": """package de.vw.mib.desktop.internal;
import de.vw.mib.desktop.internal.common.ServiceManager;import de.vw.mib.desktop.internal.viewhandler.SmartViewHandler;import de.mibr.hmi.Trace;
public class ScreenAreaDude {public SmartViewHandler current,pending,pendingOld,delayedOld;
 void enterView(SmartViewHandler next){next.setup();SmartViewHandler old=current;
  if(pending!=null && next.getView().get_targetId()==33077553)cancelPendingEntry();
  ServiceManager.screenAreaTree.registerViewHandler("ScreenAreaMenu",next);
  if(Trace.test.equals("null-foreground-return") && next.getView().get_targetId()==33077553 && old!=null && old.getView().get_targetId()==24786208){current=null;old.leave();ServiceManager.screenAreaTree.unregisterViewHandler("ScreenAreaMenu",old);pending=next;pendingOld=null;next.init();next.link();return;}
  if((Trace.test.equals("async-entry")||Trace.test.equals("timeout-late")) && next.getView().get_targetId()==24786208){pending=next;pendingOld=old;next.init();next.link();return;}
  if(Trace.test.equals("delayed-unlink") && next.getView().get_targetId()==33077553 && old!=null && old.getView().get_targetId()==24786208){current=next;next.init();next.link();next.activate();delayedOld=old;return;}
  current=next;next.init();next.link();if(old!=null && old!=next){old.leave();ServiceManager.screenAreaTree.unregisterViewHandler("ScreenAreaMenu",old);}next.activate();}
 public void finishPendingEntry(){if(pending==null)return;SmartViewHandler next=pending,old=pendingOld;pending=null;pendingOld=null;current=next;if(old!=null){old.leave();ServiceManager.screenAreaTree.unregisterViewHandler("ScreenAreaMenu",old);}next.activate();}
 public void cancelPendingEntry(){if(pending==null)return;SmartViewHandler abandoned=pending;pending=null;pendingOld=null;abandoned.leave();ServiceManager.screenAreaTree.unregisterViewHandler("ScreenAreaMenu",abandoned);}
 public void finishDelayedUnlink(){if(delayedOld==null)return;SmartViewHandler old=delayedOld;delayedOld=null;old.leave();ServiceManager.screenAreaTree.unregisterViewHandler("ScreenAreaMenu",old);}
 public SmartViewHandler getCurrentViewHandler(){return current;}}
""",
"de/vw/mib/desktop/internal/DesktopManagerImpl.java": """package de.vw.mib.desktop.internal;
import de.vw.mib.desktop.internal.viewhandler.SmartViewHandler;
public class DesktopManagerImpl {public final ScreenAreaDude area=new ScreenAreaDude();public boolean changing;public boolean isSkinChanging(){return changing;}public SmartViewHandler getDominantViewHandlerOfScreenArea(String path){return area.current;}public ScreenAreaDude getScreenAreaDude(String path){if(!"ScreenAreaMenu".equals(path))throw new AssertionError("wrong area");return area;}}
""",
"de/mibr/hmi/MibrHomeList.java": """package de.mibr.hmi;
public class MibrHomeList {public int selected=2,focused=2,first=1;public int get_selectedIndex(){return selected;}public int getFocusedIndex(){return focused;}public int getFirstVisibleIndex(){return first;}public int get_itemCount(){return 6;}public void set_selectedIndex(int v){if(Trace.failFocus)throw new IllegalStateException("focus restore");selected=v;}public void setFocusedIndex(int v){focused=v;}public void snap(int v,int mode){first=v;}}
""",
"de/mibr/hmi/MibrIsolatedSsmServices.java": """package de.mibr.hmi;
import de.vw.mib.view.internal.*;
class MibrIsolatedSsmServices implements ViewHandlerServices,ViewHandlerAppServices {final de.vw.mib.app.framework.AppDefinition app;MibrIsolatedSsmServices(MibrSsmSourceBinding.Binding source){app=source.appServices.getAppDefinition();}public de.vw.mib.app.framework.AppDefinition getAppDefinition(){return app;}de.vw.mib.skin.SkinImagePool getSkinImagePool(){return new de.vw.mib.skin.SkinImagePool();}void clear(){Trace.clears++;}}
""",
"de/mibr/hmi/MibrHomeAnimationMirror.java": """package de.mibr.hmi;
final class MibrHomeAnimationMirror {static int ended;static void ownTransitionStarted(){}static void ownTransitionEnded(){ended++;}}
""",
"de/mibr/hmi/MibrOemSsmTemplate.java": """package de.mibr.hmi;
class MibrOemSsmTemplate {static class Title {String text;void set_text(String t){text=t;Trace.title=t;Trace.rowsAtTitle=Trace.rows;}}static class Binding {final Title title=new Title();}static Binding inspect(de.vw.mib.widgets.models.ViewModel v){return v!=null && v.get_targetId()==24786208?new Binding():null;}}
""",
"de/mibr/hmi/MibrControlClient.java": "package de.mibr.hmi; class MibrControlClient {}",
"de/vw/mib/asl/api/system/KeyListener.java": "package de.vw.mib.asl.api.system; public interface KeyListener { int KEY_MENU=17; void onReleased(int k); }",
"de/vw/mib/asl/api/system/KeyAdapter.java": "package de.vw.mib.asl.api.system; public class KeyAdapter implements KeyListener { public void onReleased(int k){} }",
"de/vw/mib/asl/api/system/ASLSystemAPI.java": "package de.vw.mib.asl.api.system; public interface ASLSystemAPI { void addKeyListener(int k,KeyListener l); void removeKeyListener(int k,KeyListener l); }",
"de/vw/mib/asl/api/system/ASLSystemFactory.java": "package de.vw.mib.asl.api.system; public class ASLSystemFactory { public static ASLSystemAPI api; public static ASLSystemAPI getSystemApi(){return api;} }",
"de/mibr/hmi/MibrV3Client.java": "package de.mibr.hmi; class MibrV3Client {}",
"de/mibr/hmi/MibrV3Bootstrap.java": "package de.mibr.hmi; class MibrV3Bootstrap {static MibrV3Client devClient(){return null;}}",
"de/mibr/hmi/MibrControlBootstrap.java": "package de.mibr.hmi; class MibrControlBootstrap {static MibrControlClient devClient(){return null;}}",
"de/mibr/hmi/MibrOwnedSsmRows.java": """package de.mibr.hmi;
class MibrOwnedSsmRows {
 boolean attached=true;
 MibrOwnedSsmRows(de.vw.mib.view.internal.AbstractViewHandler h,MibrOemSsmTemplate.Binding b,Runnable back){Trace.rows++;}
 MibrOwnedSsmRows(de.vw.mib.view.internal.AbstractViewHandler h,MibrOemSsmTemplate.Binding b,Runnable back,MibrPopupEditorModel m,MibrCarPlayMenuModel.Snapshot s){Trace.rows++;}
 MibrOwnedSsmRows(de.vw.mib.view.internal.AbstractViewHandler h,MibrOemSsmTemplate.Binding b,Runnable back,MibrPopupEditorModel m,MibrCarPlayMenuModel.Snapshot s,MibrControlClient client){Trace.rows++;}
 MibrOwnedSsmRows(de.vw.mib.view.internal.AbstractViewHandler h,MibrOemSsmTemplate.Binding b,Runnable back,MibrPopupEditorModel m,MibrCarPlayMenuModel.Snapshot s,MibrControlClient client,MibrV3Client v3){Trace.rows++;}
 void open(){Trace.events.add("four-native-categories");}
 MibrCarPlayMenuModel.Snapshot snapshot(){return new MibrCarPlayMenuModel.Snapshot();}
 MibrPopupEditorModel draftOwner(){return new MibrPopupEditorModel();}
 void detach(){if(!attached)throw new AssertionError("double row detach");attached=false;Trace.rowDetach++;}
}
""",
"de/mibr/hmi/MibrCarPlayMenuModel.java": """package de.mibr.hmi;
class MibrCarPlayMenuModel {static final class Snapshot {}}
""",
"de/mibr/hmi/MibrPopupEditorModel.java": """package de.mibr.hmi;
class MibrPopupEditorModel {void detach(){}}
""",
"de/mibr/hmi/MibrElementSpec.java": """package de.mibr.hmi;
class MibrElementSpec {
 static final int BOOLEAN=2,AXIS2=5,SPIN=6,INPUT=7,INFO=8,STATUS=10,PROGRESS=11,SLIDER=4;
 final int kind;final String id="mock";MibrElementSpec(int k){kind=k;}
}
""",
"de/mibr/hmi/MibrElementEngine.java": """package de.mibr.hmi;
class MibrElementEngine {
 final MibrElementSpec spec;
 MibrElementEngine(MibrElementSpec spec){this.spec=spec;}
 MibrElementSpec element(String id){return spec!=null && spec.id.equals(id)?spec:null;}
 String observed(String id){return null;}String draft(String id){return null;}
}
""",
"de/mibr/hmi/Trace.java": """package de.mibr.hmi;
import java.util.*;import de.vw.mib.widgets.*;import de.vw.mib.widgets.models.*;import de.vw.mib.view.internal.*;import de.vw.mib.desktop.*;import de.vw.mib.desktop.internal.*;import de.vw.mib.desktop.internal.common.ServiceManager;import de.vw.mib.desktop.internal.screenarea.*;import de.vw.mib.desktop.internal.viewhandler.*;
public class Trace {
 public static final ArrayList<String> events=new ArrayList<String>();public static final ArrayList<Runnable> queue=new ArrayList<Runnable>();public static final ArrayList<Runnable> timerCallbacks=new ArrayList<Runnable>();public static int rowsAtTitle=-1,destroyed,rows,rowDetach,clears,providerCalls,loads;public static boolean failSetup,failFocus;public static String test,title;public static MibrHomeList homeList;public static ViewModel homeView;public static SmartViewHandler initialHome;public static FakeTimer timer;
 public static final class FakeTimer implements de.vw.mib.timer.Timer {
  private Runnable latest;private de.vw.mib.timer.Invoker invoker;public boolean started;
  FakeTimer(de.vw.mib.timer.Invoker i){invoker=i;}public void start(Runnable r){latest=r;timerCallbacks.add(r);started=true;}
  public void stop(){started=false;}public void setRunnable(Runnable r,de.vw.mib.timer.Invoker i){latest=r;invoker=i;}
  public void fire(){if(started && latest!=null){started=false;invoker.invoke(latest);}}
  public void fireStale(int index){if(index>=0 && index<timerCallbacks.size())invoker.invoke(timerCallbacks.get(index));}
 }
 public static final ViewHandlerServices resources=new ViewHandlerServices(){};public static final ViewHandlerAppServices app=new ViewHandlerAppServices(){public de.vw.mib.app.framework.AppDefinition getAppDefinition(){return new de.vw.mib.app.framework.AppDefinition();}};
 public static final ViewHandlerProvider provider=new ViewHandlerProvider(){public de.vw.mib.viewmanager.internal.ViewHandler getViewHandler(String n){return handler(33077553,"SimpleGridMenu");}};
 public static AbstractViewHandler handler(int id,String name){AbstractViewHandler h=new AbstractViewHandler(new View(id,name));h.postConstructor(resources,app);return h;}
 public static SmartViewHandler home(){SmartViewHandler s=new SmartViewHandler(provider.getViewHandler("Sgm"),"Sgm",provider);s.create();return s;}
 public static void homeInit(ViewModel view){homeView=view;homeList=new MibrHomeList();homeList.selected=0;homeList.focused=0;homeList.first=0;MibrSsmNativePage.captureHome(view,homeList);}
 public static void homeDeinit(ViewModel view){MibrSsmNativePage.releaseHome(view,homeList);}
 public static void drain(){int guard=0;while(!queue.isEmpty()){if(++guard>100)throw new AssertionError("unbounded UI queue");queue.remove(0).run();}}
 public static void check(boolean ok,String msg){if(!ok)throw new AssertionError(msg+" events="+events);}
 public static void main(String[] args)throws Exception {
   MibrI18n.forced="de_DE";final String test=args[0];Trace.test=test;failSetup=test.equals("partial-setup");failFocus=false;ServiceManager.desktopManager=new DesktopManagerImpl();ServiceManager.screenAreaTree=new ScreenTree();
  de.vw.mib.widgets.internal.ServiceManager.eventDispatcher=new de.vw.mib.event.dispatcher.ViewEventDispatcher(){public void invoke(Runnable r){queue.add(r);}};
   ServiceManager.timerManager=test.equals("missing-timer")?null:new de.vw.mib.timer.TimerManager(){public de.vw.mib.timer.Timer createTimer(String n,long d,boolean repeat,Runnable r,de.vw.mib.timer.Invoker invoker){check("MibrSsmTransitionCheck".equals(n)&&d==100L&&!repeat,"one-shot timer contract");timer=new FakeTimer(invoker);return timer;}};
  ServiceManager.smartViewHandlerProvider=new SmartViewHandlerProvider(){public SmartViewHandler getViewHandler(ViewHandlerProvider p,String n,boolean create){check(p==provider && "Sgm".equals(n),"only original HOME uses global cache");providerCalls++;return home();}};
  ServiceManager.skinClassLoader=new de.vw.mib.skin.SkinClassLoader(){public de.vw.mib.viewmanager.internal.ViewHandler getViewHandler(String name){check(name.equals("generated.de.vw.mib.smartphoneintegration.view.internal.Ssm_5458"),"exact load name");loads++;return test.equals("not-fresh")?initialHome.handler:new AbstractViewHandler(new View(test.equals("malformed")?999:24786208,"SMI_SETUP_MAIN"));}};
  SmartViewHandler root=new SmartViewHandler(handler(1,"Screen"),"Screen",provider);root.create();root.setup();root.link();root.init();root.getView().onEnter();root.activate();ViewNode rootNode=new ViewNode(root);rootNode.areas.add(ServiceManager.screenAreaTree.area);ServiceManager.screenAreaTree.root.views.add(rootNode);
  SmartViewHandler original=home();original.setup();original.link();original.init();original.getView().onEnter();original.activate();ServiceManager.screenAreaTree.registerViewHandler("ScreenAreaMenu",original);ServiceManager.desktopManager.area.current=original;
  initialHome=original;if(test.equals("duplicate-home"))ServiceManager.screenAreaTree.registerViewHandler("ScreenAreaMenu",original);
  homeList.selected=2;homeList.focused=2;homeList.first=1;
  if(test.equals("missing-services"))original.handler.clearServices();
  MibrSsmNativePage.enable();check(MibrOemPageEntry.requestOpen(),"entry queued");check(MibrOemPageEntry.requestOpen(),"CIO duplicate coalesced");
  if(test.equals("cancel-pending"))MibrOemPageEntry.back();
  drain();
  if(test.equals("async-entry")){
   check(rows==1 && ServiceManager.desktopManager.area.current==original,"viewEntered precedes activation/foreground during simulated transition");
   check(ServiceManager.desktopManager.area.pending!=null && !ServiceManager.desktopManager.area.pending.isActive(),"owned handler waits in simulated transition");
   check(timer!=null && timer.started,"inactive entry arms bounded check");
   ServiceManager.desktopManager.area.finishPendingEntry();drain();
   check(ServiceManager.desktopManager.area.current.getView().get_targetId()==24786208 && MibrOemPageEntry.isOpen(),"late activation completes entry");
  }
  if(test.equals("timeout-late")){
   check(ServiceManager.desktopManager.area.pending!=null && timer.started,"asynchronous entry is waiting");
   int stale=timerCallbacks.size()-1;
   for(int i=0;i<50;i++){timer.fire();drain();}
   check(ServiceManager.desktopManager.area.pending==null,"timeout recovery cancels unfinished native transition");
   check(!MibrOemPageEntry.isOpen() && destroyed==1,"timeout restores HOME and disposes owned instance");
   ServiceManager.desktopManager.area.finishPendingEntry();timer.fireStale(stale);drain();
   check(ServiceManager.desktopManager.area.current.getView().get_targetId()==33077553 && destroyed==1,"late transition and stale timer are ignored");
  }
  if(test.equals("missing-timer")){
   check(rows==0 && ServiceManager.desktopManager.area.current==original,"missing timer service prevents native entry");
   check(!MibrOemPageEntry.isOpen(),"missing timer recovery closes gate");
  }
  if(test.equals("missing-services")||test.equals("malformed")||test.equals("cancel-pending")||test.equals("partial-setup")||test.equals("not-fresh")||test.equals("duplicate-home")||test.equals("missing-timer")){
    check(ServiceManager.desktopManager.area.current.getView().get_targetId()==33077553,"prepare failure keeps a stock HOME foreground");check(!MibrOemPageEntry.isOpen(),"failed entry cleared");check(rows==0,"no rows on rejected candidate");
   if(test.equals("malformed"))check(events.contains("999:destroy"),"malformed independently created view destroyed");
   if(test.equals("partial-setup"))check(events.contains("24786208:teardown") && events.contains("24786208:destroy"),"partial native prepare reversed in order");
  } else if(!test.equals("timeout-late")) {
   check(loads==1 && rows==1,"one independent Ssm activation");check("CarPlay-Einstellungen".equals(title) && rowsAtTitle==0,"own title set before the entering transition paints");check(ServiceManager.desktopManager.area.current.getView().get_targetId()==24786208,"full native Ssm replaces HOME area");
   if(test.equals("no-foreign-child")){
    // Foreign OEM child pages were removed from the product path: no typed
    // child is registered, a request is refused and the own Ssm stays.
    MibrElementSpec info=new MibrElementSpec(MibrElementSpec.INFO);
    check(!MibrOemPageEntry.requestTypedChild(info,new MibrElementEngine(info),"verified private info",null),
          "typed child refused without registered child host");
    drain();
    check(ServiceManager.desktopManager.area.current.getView().get_targetId()==24786208 &&
          MibrOemPageEntry.isOpen(),"own Ssm remains foreground");
    MibrOemPageEntry.back();drain();
    check(ServiceManager.desktopManager.area.current.getView().get_targetId()==33077553 &&
          !MibrOemPageEntry.isOpen(),"back restores stock HOME");
   } else if(test.equals("external-navigation")){
    SmartViewHandler radio=new SmartViewHandler(handler(77,"StockRadio"),"StockRadio",provider);radio.create();java.lang.reflect.Method m=ScreenAreaDude.class.getDeclaredMethod("enterView",SmartViewHandler.class);m.setAccessible(true);m.invoke(ServiceManager.desktopManager.area,radio);drain();check(ServiceManager.desktopManager.area.current==radio,"foreign stock foreground preserved");check(providerCalls==0,"no forced HOME over foreign owner");
   } else {
    if(test.equals("detach-active")){MibrSsmNativePage.disable();MibrOemPageEntry.detach();}else MibrOemPageEntry.back();
    if(test.equals("null-foreground-return")){
     drain();
     check(ServiceManager.desktopManager.area.current==null && ServiceManager.desktopManager.area.pending!=null,"owned page unlinked while HOME remains pending with no foreground");
     check(timer!=null && timer.started && destroyed==0 && ((View)homeView).listenerCount()==1,"null foreground waits without disposal or removing HOME listener");
     ServiceManager.desktopManager.area.finishPendingEntry();
     check(ServiceManager.desktopManager.area.current.isActive() && timer.started,"HOME activates while bounded return check remains armed");
     timer.fire();drain();
     check(homeList.selected==2 && homeList.focused==2 && homeList.first==1,"timer kick restores HOME focus after activation");
     check(!MibrOemPageEntry.isOpen() && destroyed==1 && rowDetach==1 && ((View)homeView).listenerCount()==0,"successful HOME activation cleans listener and owned handler");
    } else {
    if(test.equals("focus-failure-reopen"))failFocus=true;
     drain();check(ServiceManager.desktopManager.area.current.getView().get_targetId()==33077553,"HOME restored");
     if(!test.equals("delayed-unlink") && !test.equals("focus-failure-reopen"))check(homeList.selected==2 && homeList.focused==2 && homeList.first==1,"HOME selection/focus/scroll restored");
    if(test.equals("delayed-unlink")){
     check(ServiceManager.desktopManager.area.delayedOld!=null && destroyed==0 && rowDetach==0,"HOME entry waits for delayed owned unlink");
     ServiceManager.desktopManager.area.finishDelayedUnlink();drain();
     check(!MibrOemPageEntry.isOpen() && destroyed==1 && rowDetach==1,"delayed unlink completes restoration");
    }
    if(test.equals("focus-failure-reopen")){
     check(!MibrOemPageEntry.isOpen() && ((View)homeView).listenerCount()==0,"focus exception still removes HOME listener");
     failFocus=false;check(MibrOemPageEntry.requestOpen(),"explicit reopen after focus exception");drain();MibrOemPageEntry.back();drain();
     check(!MibrOemPageEntry.isOpen() && rowDetach==2 && destroyed==2,"reopened page cleans up independently");
    }
     if(!test.equals("delayed-unlink") && !test.equals("focus-failure-reopen"))check(providerCalls==1 && events.contains("24786208:destroy") && rowDetach==1,"exact native leave and destroy");
    if(test.equals("reopen")){check(MibrOemPageEntry.requestOpen(),"reopen accepted");drain();check(loads==2 && rows==2,"fresh independent second Ssm");MibrOemPageEntry.back();drain();check(rowDetach==2,"second page cleaned once");}
    }
   }
   check(!MibrOemPageEntry.isOpen(),"entry reset after native return");
  }
  MibrSsmNativePage.disable();MibrOemPageEntry.detach();drain();System.out.println("ACTUAL_NATIVE_HOST_DOUBLE_PASS "+test);
 }
}
""",
}


class NativeRuntimeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="mibr-issue87-runtime-test-"))
        configured = os.environ.get("MIBR_TEST_JAVA_HOME")
        cls.javac = str(Path(configured) / "bin/javac") if configured else shutil.which("javac")
        cls.java = str(Path(configured) / "bin/java") if configured else shutil.which("java")
        if not cls.javac or not cls.java:
            raise RuntimeError("Existing JDK required; set MIBR_TEST_JAVA_HOME (no install/setup is performed)")
        if os.name == "nt" and configured:
            cls.javac += ".exe"
            cls.java += ".exe"
        sources = []
        for relative, body in STUBS.items():
            path = cls.root / "src" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            sources.append(str(path))
        for name in ("MibrSsmNativePage", "MibrSsmSourceBinding", "MibrOwnedSsmPageHost", "MibrOemPageEntry", "MibrMenuKeyBack", "MibrPlatformDefaults", "MibrMenuDefinition", "MibrI18n"):
            sources.append(str(H / (name + ".java")))
        cls.out = cls.root / "classes"
        cls.out.mkdir()
        run = subprocess.run([cls.javac, "-encoding", "UTF-8", "-source", "8", "-target", "8", "-d", str(cls.out)] + sources,
                             capture_output=True, text=True)
        if run.returncode:
            raise AssertionError(run.stdout + run.stderr)

    def test_actual_host_native_contract_scenarios(self):
        for case in ("normal", "reopen", "missing-services", "malformed", "cancel-pending", "external-navigation",
                     "partial-setup", "not-fresh", "duplicate-home", "detach-active", "async-entry",
                     "delayed-unlink", "focus-failure-reopen", "timeout-late", "missing-timer", "null-foreground-return", "no-foreign-child"):
            with self.subTest(case=case):
                run = subprocess.run([self.java, "-cp", str(self.out), "de.mibr.hmi.Trace", case],
                                     capture_output=True, text=True, timeout=20)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertIn("ACTUAL_NATIVE_HOST_DOUBLE_PASS " + case, run.stdout)


if __name__ == "__main__":
    unittest.main()
