package de.mibr.hmi;

import de.vw.mib.desktop.internal.common.ServiceManager;
import de.vw.mib.desktop.internal.viewhandler.SmartViewHandler;
import de.vw.mib.timer.Timer;
import de.vw.mib.view.internal.AbstractViewHandler;
import de.vw.mib.viewmanager.internal.ViewHandler;
import de.vw.mib.widgets.View;
import de.vw.mib.widgets.event.ViewChangedListener;
import de.vw.mib.widgets.models.ViewModel;

/** Own native page; original transitions and timers, no global factory/cache. */
final class MibrSsmNativePage implements MibrOwnedSsmPageHost.Driver {
    private static final String SSM_CLASS="generated.de.vw.mib.smartphoneintegration.view.internal.Ssm_5458";
    private static final String OWN_NAME="MibrOwnedSsmPage";
    private static final int MAX_CHECKS=50;
    private static final Runnable IDLE=new Runnable(){public void run(){}};
    private static boolean enabled;
    private static ViewModel latestHome;
    private static MibrHomeList latestList;
    private static MibrSsmNativePage current;
    private MibrOwnedSsmPageHost host;
    private MibrOwnedSsmPageHost.Completion completion;
    private MibrSsmSourceBinding.Binding source;
    private MibrIsolatedSsmServices isolated;
    private AbstractViewHandler handler;
    private SmartViewHandler own;
    private ViewModel ownedView,returnView;
    private MibrOwnedSsmRows rows;
    private Timer checkTimer;
    private boolean cancelled,left,returning,checkScheduled,nativeEntryUncertain;
    private int epoch,phase,checks,homeSelected,homeFocused,homeFirst;
    private final NativeListener listener=new NativeListener(){
        public void viewEntered(View view){
            if(view!=ownedView || cancelled)return;
            try{
                MibrOemSsmTemplate.Binding template=MibrOemSsmTemplate.inspect(ownedView);
                if(template==null || rows!=null)throw new IllegalStateException("MIBR_SSM_TEMPLATE_OR_DOUBLE_INIT");
                MibrV3Client product=MibrV3Bootstrap.devClient();
                rows=new MibrOwnedSsmRows(handler,template,new Runnable(){public void run(){MibrOemPageEntry.back();}},
                    new MibrPopupEditorModel(),null,product==null?MibrControlBootstrap.devClient():null,product);
                rows.open();
                MibrMenuKeyBack.arm();
                probeLater();
            }catch(Throwable failure){completion.failed(String.valueOf(failure));}
        }
        public void viewLeft(View view){
            if(view!=ownedView)return;
            left=true;
            MibrMenuKeyBack.disarm();
            try{if(rows!=null){rows.detach();rows=null;}}
            catch(Throwable failure){System.err.println("MIBR_SSM_LEAVE_CLEANUP_FAILED "+failure);
                completion.failed("MIBR_SSM_CLEANUP_FAILED "+failure);}
            if(!returning)completion.failed("MIBR_SSM_EXTERNAL_PAGE_LEAVE");
            probeLater();
        }
    };
    private final NativeListener returnListener=new NativeListener(){
        public void viewEntered(View view){if(view==returnView)probeLater();}
        public void viewLeft(View view){if(view==returnView)probeLater();}
    };
    private static abstract class NativeListener implements ViewChangedListener {
        public void viewCovered(){} public void viewUncovered(){}
        public void viewInited(View view){} public void viewEntered(View view){} public void viewLeft(View view){}
    }
    private static void later(Runnable action){de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(action);}
    static synchronized void enable(){enabled=true;bindIfReady();}
    static synchronized void captureHome(ViewModel view,MibrHomeList list){latestHome=view;latestList=list;bindIfReady();}
    static synchronized void releaseHome(ViewModel view,MibrHomeList list){
        if(latestHome==view && latestList==list){latestHome=null;latestList=null;}
    }
    private static void bindIfReady(){
        if(!enabled || latestHome==null || latestList==null)return;
        if(current==null || current.host.state()==MibrOwnedSsmPageHost.DETACHED){
            final MibrSsmNativePage page=new MibrSsmNativePage();
            page.host=new MibrOwnedSsmPageHost(page,new MibrOwnedSsmPageHost.Observer(){
                public void closed(){MibrHomeAnimationMirror.ownTransitionEnded();MibrOemPageEntry.completed(page.host);}
            });
            if(MibrOemPageEntry.bind(page.host))current=page;
        }
    }
    static synchronized void disable(){enabled=false;if(current!=null)current.host.detach();}

    public void enter(MibrOwnedSsmPageHost.Completion completion){
        this.completion=completion;cancelled=false;left=false;returning=false;nativeEntryUncertain=false;
        checks=0;phase++;final int token=++epoch;
        later(new Runnable(){public void run(){if(token==epoch)begin();}});
    }
    private void begin(){
        if(cancelled){probeLater();return;}
        try{
            ViewModel home=latestHome;MibrHomeList list=latestList;
            if(!enabled || home==null || list==null)throw new IllegalStateException("MIBR_SSM_HOME_CAPTURE_MISSING");
            source=MibrSsmSourceBinding.capture(home);
            if(ServiceManager.timerManager==null)throw new IllegalStateException("MIBR_SSM_TIMER_SERVICE_MISSING");
            checkTimer=ServiceManager.timerManager.createTimer("MibrSsmTransitionCheck",100L,false,IDLE,
                de.vw.mib.widgets.internal.ServiceManager.eventDispatcher);
            if(checkTimer==null)throw new IllegalStateException("MIBR_SSM_TIMER_UNAVAILABLE");
            homeSelected=list.get_selectedIndex();homeFocused=list.getFocusedIndex();homeFirst=list.getFirstVisibleIndex();
            isolated=new MibrIsolatedSsmServices(source);
            ViewHandler candidate=source.loader.getViewHandler(SSM_CLASS);
            if(!(candidate instanceof AbstractViewHandler) || candidate==source.handler ||
                    MibrSsmSourceBinding.lifecycle((AbstractViewHandler)candidate)!=-1)
                throw new IllegalStateException("MIBR_SSM_LOADER_DID_NOT_RETURN_FRESH_HANDLER");
            handler=(AbstractViewHandler)candidate;
            handler.postConstructor(isolated,isolated);
            own=new SmartViewHandler(handler,OWN_NAME,null);
            own.create();own.setup();ownedView=handler.getView();
            MibrOemSsmTemplate.Binding first=MibrOemSsmTemplate.inspect(ownedView);
            if(first==null)throw new IllegalStateException("MIBR_SSM_TEMPLATE_MISMATCH");
            // The entering transition paints before viewEntered: never show the template's SmartLink title.
            first.title.set_text(MibrMenuDefinition.title());
            ownedView.addViewChangedListener(listener);
            nativeEntryUncertain=true;source.enter(source.home,own);nativeEntryUncertain=false;
            probeLater();
        }catch(Throwable failure){completion.failed(String.valueOf(failure));}
    }
    public void restore(MibrOwnedSsmPageHost.Completion completion){
        this.completion=completion;cancelled=true;returning=true;phase++;checks=0;stopCheck();
        final int token=epoch;
        later(new Runnable(){public void run(){if(token==epoch)returnHome();}});
    }
    private void returnHome(){
        try{
            if(own==null || source==null){probeLater();return;}
            SmartViewHandler foreground=source.desktop.getDominantViewHandlerOfScreenArea(source.path);
            if(foreground!=own && foreground!=source.home){probeLater();return;}
            // The original HOME may still be foreground during an entering animation.
            // Entering HOME again aborts that owned transition using the native path.
            SmartViewHandler previous=ServiceManager.smartViewHandlerProvider.getViewHandler(
                source.provider,source.home.getShortViewHandlerName(),true);
            if(previous==null || previous==own)throw new IllegalStateException("MIBR_SSM_HOME_RESTORE_UNAVAILABLE");
            previous.setup();returnView=previous.getView();
            if(returnView==null || returnView.get_targetId()!=33077553)
                throw new IllegalStateException("MIBR_SSM_HOME_RESTORE_IDENTITY");
            returnView.addViewChangedListener(returnListener);
            nativeEntryUncertain=true;source.enter(foreground,previous);nativeEntryUncertain=false;
            probeLater();
        }catch(Throwable failure){removeReturnListener();completion.failed(String.valueOf(failure));}
    }
    private void probeLater(){
        final int token=epoch,step=phase;
        later(new Runnable(){public void run(){if(token==epoch && step==phase)probe();}});
    }
    private void probe(){
        if(completion==null)return;
        try{
            SmartViewHandler foreground=source==null?null:source.desktop.getDominantViewHandlerOfScreenArea(source.path);
            if(returning){
                // A temporary empty area is not proof of HOME or foreign OEM
                // ownership. Keep the return listener until a real page exists.
                if(own!=null && foreground==null){armCheck();return;}
                if(own==null || !own.isLinked() && foreground!=own){
                    if(returnView!=null){
                        if(foreground!=null && foreground.getView()==returnView){
                            if(!foreground.isActive()){armCheck();return;}
                            restoreFocus();
                        }
                        removeReturnListener();
                    }
                    stopCheck();completion.restored();return;
                }
            }else if(own!=null && own.isLinked() && own.isActive() && foreground==own){
                stopCheck();completion.entered();return;
            }
            armCheck();
        }catch(Throwable failure){stopCheck();removeReturnListener();completion.failed(String.valueOf(failure));}
    }
    private void restoreFocus(){
        try{
            if(latestHome!=returnView || latestList==null)throw new IllegalStateException("HOME list capture missing");
            int count=latestList.get_itemCount();
            if(homeSelected>=0 && homeSelected<count)latestList.set_selectedIndex(homeSelected);
            if(homeFocused>=0 && homeFocused<count)latestList.setFocusedIndex(homeFocused);
            if(homeFirst>=0 && homeFirst<count)latestList.snap(homeFirst,0);
        }catch(Throwable failure){System.err.println("MIBR_SSM_HOME_FOCUS_RESTORE_FAILED "+failure);}
    }
    private void armCheck(){
        if(checkScheduled)return;
        if(checks>=MAX_CHECKS || checkTimer==null){
            stopCheck();removeReturnListener();
            completion.failed(returning?"MIBR_SSM_RETURN_TIMEOUT":"MIBR_SSM_ACTIVATION_TIMEOUT");return;
        }
        final int token=epoch,step=phase;checkScheduled=true;
        checkTimer.start(new Runnable(){public void run(){
            if(token!=epoch || step!=phase)return;
            checkScheduled=false;checks++;probe();
        }});
    }
    private void stopCheck(){
        checkScheduled=false;
        if(checkTimer!=null){checkTimer.stop();checkTimer.setRunnable(IDLE,
            de.vw.mib.widgets.internal.ServiceManager.eventDispatcher);}
    }
    private void removeReturnListener(){
        ViewModel view=returnView;returnView=null;
        if(view!=null)try{view.removeViewChangedListener(returnListener);}
        catch(Throwable failure){System.err.println("MIBR_SSM_HOME_LISTENER_REMOVE_FAILED "+failure);}
    }
    public void dispose() throws Exception {
        if(nativeEntryUncertain)throw new IllegalStateException("MIBR_SSM_NATIVE_ENTRY_UNCERTAIN");
        if(own!=null && own.isLinked())throw new IllegalStateException("MIBR_SSM_DISPOSE_WHILE_LINKED");
        if(own!=null && source!=null)source.unregisterDetached(own);
        stopCheck();removeReturnListener();
        if(ownedView!=null)ownedView.removeViewChangedListener(listener);
        MibrMenuKeyBack.disarm();
        if(rows!=null){rows.detach();rows=null;}
        if(handler!=null){
            int state=MibrSsmSourceBinding.lifecycle(handler);
            if(state==4){handler.deactivate();state=3;}
            if(state==3){if(!left && ownedView!=null)ownedView.onLeave();handler.deinit();state=2;}
            if(state==2){handler.teardown();state=1;}
            if(state==1)handler.destroy();
            // Never call SmartViewHandler.destroy/unloadDataForClass on shared Ssm.
        }
        if(isolated!=null)isolated.clear();
        epoch++;handler=null;own=null;source=null;ownedView=null;isolated=null;completion=null;checkTimer=null;
    }
}
