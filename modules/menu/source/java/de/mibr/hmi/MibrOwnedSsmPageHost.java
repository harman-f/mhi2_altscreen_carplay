package de.mibr.hmi;

/** UI-independent owner of one native-page operation, including queued callbacks. */
public final class MibrOwnedSsmPageHost implements MibrOemPageEntry.NativePage {
    public static final int HOME=0,OPENING=1,ACTIVE=2,RETURNING=3,FAULT=4,DETACHED=5;
    public interface Completion {
        void entered();
        void restored();
        void failed(String error);
    }
    public interface Driver {
        void enter(Completion completion) throws Exception;
        void restore(Completion completion) throws Exception;
        void dispose() throws Exception;
    }
    public interface Observer { void closed(); }
    private final Driver driver;
    private final Observer observer;
    private int state=HOME,generation;
    private boolean detached,disposed;
    private String error;
    private Completion operation;

    public MibrOwnedSsmPageHost(Driver driver,Observer observer) {
        if(driver==null || observer==null)throw new IllegalArgumentException("native page dependencies");
        this.driver=driver;this.observer=observer;
    }
    public int state(){return state;}
    public String error(){return error;}
    public boolean open(){
        if(state==OPENING || state==ACTIVE)return true;
        if(state==FAULT && !detached){
            // Explicit user retry only. Driver refuses disposal while linked.
            try{driver.dispose();disposed=true;state=HOME;}
            catch(Throwable failure){error=String.valueOf(failure);return false;}
        }
        if(state!=HOME || detached)return false;
        state=OPENING;disposed=false;error=null;
        final int token=++generation;
        operation=new Completion(){
            public void entered(){if(token==generation && state==OPENING)state=ACTIVE;}
            public void restored(){if(token==generation && (state==RETURNING || state==FAULT))finish();}
            public void failed(String failure){if(token==generation)fail(failure);}
        };
        try{driver.enter(operation);}catch(Throwable failure){fail(String.valueOf(failure));}
        return state==OPENING || state==ACTIVE;
    }
    public void close(){
        if(state==HOME || state==DETACHED || state==RETURNING || state==FAULT)return;
        state=RETURNING;
        try{driver.restore(operation);}catch(Throwable failure){fault(String.valueOf(failure));}
    }
    private void fail(String failure){
        if(state!=OPENING && state!=ACTIVE && state!=RETURNING)return;
        error=failure;
        System.err.println("MIBR_OWNED_SSM_FAILURE "+failure);
        if(state==RETURNING){fault(failure);return;}
        if(state!=OPENING && state!=ACTIVE)return;
        close();
    }
    private void fault(String failure){state=FAULT;error=failure;System.err.println("MIBR_OWNED_SSM_RESTORE_FAULT "+failure);observer.closed();}
    private void finish(){
        try{if(!disposed){driver.dispose();disposed=true;}}
        catch(Throwable failure){fault(String.valueOf(failure));return;}
        state=detached?DETACHED:HOME;observer.closed();
    }
    public void detach(){
        detached=true;
        if(state==HOME){state=DETACHED;observer.closed();}
        else close();
    }
}
