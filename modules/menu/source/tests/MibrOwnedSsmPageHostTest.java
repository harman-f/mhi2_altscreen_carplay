package de.mibr.hmi;

/** Executes the real admission/queued-lifetime owner with an explicit native-port fake. */
public final class MibrOwnedSsmPageHostTest {
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    private static final class Driver implements MibrOwnedSsmPageHost.Driver {
        MibrOwnedSsmPageHost.Completion completion;
        int enters,restores,disposes;boolean foreground,registered,throwEnter,throwRestore,throwDispose;
        public void enter(MibrOwnedSsmPageHost.Completion c){enters++;completion=c;if(throwEnter)throw new IllegalStateException("missing template");}
        void enterDone(){registered=true;foreground=true;completion.entered();}
        public void restore(MibrOwnedSsmPageHost.Completion c){restores++;completion=c;if(throwRestore)throw new IllegalStateException("restore unavailable");}
        void restoreDone(){foreground=false;registered=false;completion.restored();}
        public void dispose(){check(!foreground && !registered,"destroy before native unlink");disposes++;if(throwDispose)throw new IllegalStateException("dispose failure");}
    }
    private static final class Owner implements MibrOwnedSsmPageHost.Observer {
        int closed;MibrOwnedSsmPageHost host;
        public void closed(){closed++;MibrOemPageEntry.completed(host);}
    }
    private static MibrOwnedSsmPageHost host(Driver driver,Owner owner){
        owner.host=new MibrOwnedSsmPageHost(driver,owner);return owner.host;
    }
    private static void openBackReopen(){
        Driver d=new Driver();Owner o=new Owner();MibrOwnedSsmPageHost h=host(d,o);
        MibrOemPageEntry.detach();check(MibrOemPageEntry.bind(h),"bind");
        check(MibrOemPageEntry.requestOpen(),"tile open accepted");
        check(MibrOemPageEntry.requestOpen(),"same CIO converges");check(d.enters==1,"duplicate native activation");
        check(h.state()==MibrOwnedSsmPageHost.OPENING,"native enter not falsely reported active");
        d.enterDone();check(h.state()==MibrOwnedSsmPageHost.ACTIVE,"native activation callback");
        MibrOwnedSsmPageHost.Completion old=d.completion;
        MibrOemPageEntry.back();h.close();check(d.restores==1,"one native Back");
        check(d.disposes==0,"wait for actual native unlink and focus restore");
        check(!h.open(),"no reopen during return");d.restoreDone();
        check(h.state()==MibrOwnedSsmPageHost.HOME && d.disposes==1 && o.closed==1,"stock restored and own instance destroyed");
        check(MibrOemPageEntry.requestOpen(),"reopen");
        old.entered();old.failed("stale failure");old.restored();
        check(h.state()==MibrOwnedSsmPageHost.OPENING && d.restores==1,"stale generation cannot alter new page");
        d.enterDone();MibrOemPageEntry.back();d.restoreDone();MibrOemPageEntry.detach();
    }
    private static void missingBindingAndMalformedPage(){
        Driver d=new Driver();Owner o=new Owner();MibrOwnedSsmPageHost h=host(d,o);
        d.throwEnter=true;check(!h.open(),"missing native binding rejected");
        check(d.restores==1 && d.disposes==0,"failure waits for recovery");d.restoreDone();
        check(h.state()==MibrOwnedSsmPageHost.HOME && d.disposes==1,"failed prepare cleaned");
        d.throwEnter=false;check(h.open(),"retry after complete recovery");
        d.completion.failed("malformed Ssm row");check(d.restores==2,"malformed template restore once");
        d.restoreDone();check(h.state()==MibrOwnedSsmPageHost.HOME,"malformed template safe");
    }
    private static void backBeforeNativeEnterAndDetach(){
        Driver d=new Driver();Owner o=new Owner();MibrOwnedSsmPageHost h=host(d,o);
        check(h.open(),"queued");h.close();d.completion.entered();
        check(h.state()==MibrOwnedSsmPageHost.RETURNING && d.restores==1,"late enter cannot undo Back");
        h.detach();d.restoreDone();
        check(h.state()==MibrOwnedSsmPageHost.DETACHED && !h.open(),"detach survives async return");
        d.completion.restored();check(d.disposes==1,"no double destroy");
    }
    private static void recoveryFaultStopsFurtherMutation(){
        Driver d=new Driver();Owner o=new Owner();MibrOwnedSsmPageHost h=host(d,o);
        h.open();d.enterDone();d.throwRestore=true;h.close();
        check(h.state()==MibrOwnedSsmPageHost.FAULT && !h.open(),"failed restore fails closed");
        check(d.disposes==0 && d.restores==1,"no destroy/second restore under unknown foreground");
        h.close();check(d.restores==1,"fault retained");
        Driver other=new Driver();Owner otherOwner=new Owner();MibrOwnedSsmPageHost next=host(other,otherOwner);
        next.open();other.enterDone();next.close();other.throwDispose=true;other.restoreDone();
        check(next.state()==MibrOwnedSsmPageHost.FAULT && !next.open(),"cleanup failure retained");
    }
    private static void lateRecoveryAndExplicitRetry(){
        Driver d=new Driver();Owner o=new Owner();MibrOwnedSsmPageHost h=host(d,o);
        h.open();d.enterDone();d.throwRestore=true;h.close();
        check(h.state()==MibrOwnedSsmPageHost.FAULT,"restore fault");
        d.restoreDone();
        check(h.state()==MibrOwnedSsmPageHost.HOME && d.disposes==1,"late proven unlink completes cleanup");
        d.throwRestore=false;h.open();d.enterDone();d.throwRestore=true;h.close();
        MibrOwnedSsmPageHost.Completion old=d.completion;
        d.foreground=false;d.registered=false;d.throwRestore=false;
        check(h.open() && d.enters==3,"explicit retry after safe disposal");
        old.restored();old.failed("stale fault");
        check(h.state()==MibrOwnedSsmPageHost.OPENING,"old fault completion cannot close new page");
        d.enterDone();h.close();d.restoreDone();
    }
    public static void main(String[] args){
        openBackReopen();missingBindingAndMalformedPage();backBeforeNativeEnterAndDetach();recoveryFaultStopsFurtherMutation();lateRecoveryAndExplicitRetry();
        System.out.println("OWNED_SSM_HOST_LIFECYCLE_PASS (native port simulated; no vehicle claim)");
    }
}
