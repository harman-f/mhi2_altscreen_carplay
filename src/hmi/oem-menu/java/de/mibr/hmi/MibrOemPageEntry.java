package de.mibr.hmi;

/**
 * One fail-closed HOME entry for a future *separately owned* OEM settings view.
 * This gate is NOT a real page. Do not attach a bridge until the exact MU1440
 * viewhandler service, app service and foreground navigation seam are proven.
 */
public final class MibrOemPageEntry {
    public static interface NativePage {
        /** Accepted once; the host tracks native queued enter/activate separately. */
        boolean open();
        /** Restore prior HOME focus and dispose owned page resources. */
        void close();
    }
    public static interface ChildBack { boolean backChild(); }
    /** Explicitly approved generic element entry only; caller owns the
     * descriptor/data and must be on OEM UI thread. No synthetic menu row.
     */
    interface LocalSink {
        void localDraft(String id);
        void cancelled(String id);
        void rejected(String id);
    }
    interface TypedChild {
        boolean open(MibrElementSpec spec,MibrElementEngine state,String verifiedText,
                     LocalSink sink);
    }
    private static ChildBack childBack;
    private static TypedChild typedChild;
    private static NativePage page;
    private static boolean opening,opened;
    private MibrOemPageEntry() {}
    public static synchronized boolean bind(NativePage candidate) {
        if(candidate==null || page!=null || opened || opening)return false;
        page=candidate; return true;
    }
    static synchronized void setChildBack(NativePage owner,ChildBack callback){
        if(page!=owner)throw new IllegalStateException("MIBR_CHILD_BACK_NOT_OWNER");
        childBack=callback;
    }
    static synchronized void setTypedChild(NativePage owner,TypedChild callback){
        if(page!=owner)throw new IllegalStateException("MIBR_TYPED_CHILD_NOT_OWNER");
        typedChild=callback;
    }
    static synchronized boolean requestTypedChild(MibrElementSpec spec,MibrElementEngine state,
                       String verifiedText,LocalSink sink){
        return opened && !opening && typedChild!=null &&
            typedChild.open(spec,state,verifiedText,sink);
    }
    public static synchronized boolean requestOpen() {
        if(opened)return true; // Tile and own CIO converge; never reopen.
        if (page == null || opening) return false;
        opening=true;
        try {
            opened=page.open();
            if(!opened)try { page.close(); } catch(Throwable ignored) {}
            return opened;
        } catch(Throwable t) {
            opened=false;
            try { page.close(); } catch(Throwable ignored) {}
            try { System.err.println("MIBR_OEM_PAGE_OPEN_FAILED "+t); } catch(Throwable ignored) {}
            return false;
        } finally { opening=false; }
    }
    public static synchronized boolean isOpen() { return opened; }
    static synchronized void completed(NativePage candidate) {
        if(page==candidate){opened=false;opening=false;}
    }
    public static synchronized void back() {
        if(!opened)return;
        // A native child Back must first return to the owned Ssm, preserving
        // the top-level HOME gate and existing local DRAFTs.
        if(childBack!=null && childBack.backChild())return;
        opened=false;
        if(page!=null)try { page.close(); }
        catch(Throwable t) {
            try { System.err.println("MIBR_OEM_PAGE_CLOSE_FAILED "+t); } catch(Throwable ignored) {}
        }
    }
    public static synchronized void detach() {
        // Detach means leave the entire owner, even when a child is open.
        // Never interpret it as only one nested Back.
        NativePage closing=page;boolean mustClose=opened || opening;
        childBack=null;typedChild=null;page=null;opening=false;opened=false;
        if(mustClose && closing!=null)try{closing.close();}
        catch(Throwable failure){System.err.println("MIBR_OEM_DETACH_CLOSE_FAILED "+failure);}
    }
}