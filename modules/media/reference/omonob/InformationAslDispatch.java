package org.omonob.cpmap.information;
import de.vw.mib.asl.framework.internal.framework.ServiceManager;
import de.vw.mib.genericevents.ThreadSwitchingTarget;
import java.lang.reflect.Method;
/** Keep OEM DSI/BAP calls on their owning ASL thread. Five coalesced jobs max. */
public final class InformationAslDispatch {
    private static final String[] METHODS={"sendInitVolley","sendCleanupVolley","sendVcFrame","triggerBapShadows"};
    private static final boolean[] pending=new boolean[5];
    private static final Object[] latest=new Object[5];
    private static Object attachedTarget;
    private static boolean attachedResult;
    private InformationAslDispatch() { }

    /** -1 means already on ASL; 0 means not attached yet; 1 is actual success.
     * The historical AttachWorker keeps its own retry/attached lifecycle. Never
     * return success merely because registration was queued, and never let an
     * old HsmTarget's result satisfy a new target's request.
     */
    public static int attach(Object request) {
        if(request==null)return 0;
        try {
            final ThreadSwitchingTarget target=ServiceManager.aslThreadSwitch;
            if(target==null)return 0;
            if(!target.isThreadChangeNecessary())return -1;
            synchronized(pending) {
                if(attachedTarget==request) {
                    attachedTarget=null;
                    return attachedResult?1:0;
                }
                if(pending[4])return 0;
                attachedTarget=null;latest[4]=request;pending[4]=true;
            }
            try {target.enqueue(new Job(4));}
            catch(Throwable failed){synchronized(pending){pending[4]=false;latest[4]=null;}}
        }catch(Throwable unavailable){ }
        return 0;
    }

    public static boolean defer(final int operation,String context) {
        if(operation<0||operation>=METHODS.length)throw new IllegalArgumentException("Unknown information operation");
        try {
            final ThreadSwitchingTarget target=ServiceManager.aslThreadSwitch;
            if(target==null)return true; // not ready: never call DSI from an arbitrary thread
            if(!target.isThreadChangeNecessary())return false;
            synchronized(pending){latest[operation]=context;if(pending[operation])return true;pending[operation]=true;}
            try {
                target.enqueue(new Job(operation));
            } catch(Throwable failed) {synchronized(pending){pending[operation]=false;}}
            return true;
        } catch(Throwable unavailable) {return true;}
    }

    private static final class Job implements Runnable {
        private final int operation;
        Job(int value){operation=value;}
        public void run() {
            Object value;boolean success=false;
            synchronized(pending) {
                value=latest[operation];latest[operation]=null;
                if(operation!=4)pending[operation]=false;
            }
            try {
                Class type=Class.forName(operation==4?"com.mst2.carplay.bridge.Mst2NowPlayingBridge":"com.mst2.carplay.navi.Mst2CarPlayNaviSinkBridge");
                Class[] signature=operation==4?new Class[]{Class.forName("de.vw.mib.asl.internal.carplay.target.HsmTarget")}:
                    operation==3?new Class[]{Class.forName("java.lang.String")}:new Class[0];
                Object[] arguments=operation>=3?new Object[]{value}:new Object[0];
                Method method=type.getDeclaredMethod(operation==4?"tryAttach":METHODS[operation],signature);
                method.setAccessible(true);
                Object result=method.invoke(null,arguments);
                success=operation==4&&Boolean.TRUE.equals(result);
            }catch(Throwable ignored){ }
            finally {
                if(operation==4)synchronized(pending) {
                    attachedTarget=value;attachedResult=success;pending[4]=false;
                }
            }
        }
    }
}
