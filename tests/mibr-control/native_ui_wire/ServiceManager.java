package de.vw.mib.widgets.internal;
import java.util.Vector;
/** Host double: callbacks are queued, then run by the test's UI thread. */
public final class ServiceManager {
    public static final Dispatcher eventDispatcher=new Dispatcher();
    public static final class Dispatcher {
        private final Vector tasks=new Vector();
        public synchronized void invoke(Runnable r){tasks.addElement(r);}
        public synchronized Runnable poll(){
            if(tasks.size()==0)return null;
            Runnable r=(Runnable)tasks.elementAt(0);tasks.removeElementAt(0);return r;
        }
    }
}
