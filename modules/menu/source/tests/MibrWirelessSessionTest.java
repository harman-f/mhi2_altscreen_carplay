package de.mibr.hmi;

/** Host-only tests use an explicit fake backend; production ships no fake wireless owner. */
public final class MibrWirelessSessionTest {
    private static void check(boolean ok,String name){if(!ok)throw new AssertionError(name);}
    private static final class Fake implements MibrWirelessBackend {
        Listener caps;
        long capsGeneration,capsRequest;
        Listener[] statuses=new Listener[16];long[] statusGenerations=new long[16],statusRequests=new long[16];
        Listener[] commands=new Listener[16];long[] commandGeneration=new long[16],requests=new long[16];int[] operations=new int[16];boolean[] targets=new boolean[16];int commandCount;
        boolean accept=true;
        int statusReads;
        public boolean readCapabilities(long g,long r,Listener l){capsGeneration=g;capsRequest=r;caps=l;return accept;}
        public boolean readStatus(long g,long r,Listener l){statusGenerations[statusReads]=g;statusRequests[statusReads]=r;statuses[statusReads]=l;statusReads++;return accept;}
        private boolean command(long g,long r,int op,boolean target,Listener l){int n=commandCount++;commands[n]=l;commandGeneration[n]=g;requests[n]=r;operations[n]=op;targets[n]=target;return accept;}
        public boolean requestEnabled(long g,long r,boolean on,Listener l){return command(g,r,MibrWirelessSession.REQUEST_TOGGLE,on,l);}
        public boolean requestPairing(long g,long r,Listener l){return command(g,r,MibrWirelessSession.REQUEST_PAIRING,false,l);}
        public boolean stop(long g,long r,Listener l){return command(g,r,MibrWirelessSession.REQUEST_STOP,false,l);}
        void capabilities(int mask){caps.onCapabilities(capsGeneration,capsRequest,new Capabilities(ABI,mask,capsGeneration));}
        void status(int index,String state,boolean requested,String pairing){statuses[index].onSnapshot(statusGenerations[index],statusRequests[index],new Snapshot(statusGenerations[index],true,requested,state,pairing));}
        void result(int index,boolean acknowledged,String state,boolean requested,String pairing){
            Listener listener=commands[index];listener.onResult(commandGeneration[index],requests[index],
                new Result(commandGeneration[index],requests[index],operations[index],acknowledged,
                    new Snapshot(commandGeneration[index],true,requested,state,pairing)));
        }
    }
    private static MibrWirelessSession session(Fake fake){
        return new MibrWirelessSession(fake,new MibrWirelessSession.Dispatcher(){public void post(Runnable r){r.run();}},
            new Runnable(){public void run(){}});
    }
    public static void main(String[] args){
        MibrI18n.forced="en_GB";
        MibrWirelessSession absent=new MibrWirelessSession(null,new MibrWirelessSession.Dispatcher(){public void post(Runnable r){r.run();}},new Runnable(){public void run(){}});
        absent.enterPage();
        check(absent.statusLine().toLowerCase().indexOf("unavailable")>=0 && !absent.enabled(MibrWirelessSession.REQUEST_TOGGLE),"missing adapter unavailable");
        check(!absent.perform(MibrWirelessSession.REQUEST_PAIRING) && absent.statusLine().indexOf("confirmed")<0,"missing adapter cannot report pairing success");

        Fake f=new Fake();MibrWirelessSession s=session(f);s.enterPage();
        check(!s.enabled(MibrWirelessSession.REQUEST_TOGGLE),"capability check precedes controls");
        f.caps.onCapabilities(f.capsGeneration+1,f.capsRequest,new MibrWirelessBackend.Capabilities(
            MibrWirelessBackend.ABI,MibrWirelessBackend.CAP_REQUIRED,f.capsGeneration));
        check(!s.available(),"wrong-generation capability envelope is ignored without consuming the request");
        f.capabilities(MibrWirelessBackend.CAP_CONTROL);
        check(!s.available() && f.statusReads==0,"incomplete capability set fails closed");
        s.enterPage();f.capabilities(MibrWirelessBackend.CAP_REQUIRED);
        check(f.statusReads==1 && !s.enabled(MibrWirelessSession.REQUEST_TOGGLE),"full capabilities require status read");
        f.status(0,"OFF",false,"NOT_PAIRED");
        check(s.enabled(MibrWirelessSession.REQUEST_TOGGLE) && s.enabled(MibrWirelessSession.REQUEST_PAIRING),"confirmed OFF enables explicit requests");
        check(s.perform(MibrWirelessSession.REQUEST_TOGGLE)&&f.targets[0],"explicit enable request reaches backend");
        check(s.statusLine().indexOf("requested off")>=0 && s.statusLine().indexOf("ACTIVE")<0,"no optimistic enabled state");
        long wrongGeneration=f.commandGeneration[0]+1;
        f.commands[0].onResult(wrongGeneration,f.requests[0],new MibrWirelessBackend.Result(wrongGeneration,
            f.requests[0],f.operations[0],true,new MibrWirelessBackend.Snapshot(wrongGeneration,true,true,"ACTIVE","NOT_PAIRED")));
        check(s.statusLine().indexOf("Wireless request pending")>=0,"wrong-generation command receipt does not consume pending request");
        f.result(0,true,"ACTIVE",true,"NOT_PAIRED");
        check(s.statusLine().indexOf("requested on")>=0,"matching native acknowledgement updates state");

        check(s.perform(MibrWirelessSession.REQUEST_PAIRING),"pair request sent");
        check(!s.enabled(MibrWirelessSession.REQUEST_TOGGLE),"second command serialized while pairing is pending");
        f.result(1,true,"ACTIVE",true,"REQUESTED");
        check(s.statusLine().indexOf("pairing request pending")>=0 && s.statusLine().indexOf("Pairing confirmed")<0,
              "request ack is not a pairing success");
        check(s.perform(MibrWirelessSession.REQUEST_PAIRING),"pairing request remains explicit");
        f.result(2,false,"ACTIVE",true,"PAIRED");
        check(s.statusLine().indexOf("PAIRED")<0 && s.statusLine().indexOf("Pairing confirmed")<0,"unacknowledged state is not pairing success");
        check(!s.perform(MibrWirelessSession.REQUEST_PAIRING),"untrusted result requires fresh native status");
        check(s.perform(MibrWirelessSession.REFRESH_STATUS),"refresh after untrusted command result");
        int pairRefresh=f.statusReads-1;f.status(pairRefresh,"ACTIVE",true,"REQUESTED");
        check(s.perform(MibrWirelessSession.REQUEST_PAIRING),"pairing can retry after fresh status");
        f.result(3,true,"ACTIVE",true,"PAIRED");
        check(s.statusLine().indexOf("pairing confirmed")>=0,"pairing appears only after matching acknowledged snapshot");

        check(s.perform(MibrWirelessSession.REFRESH_STATUS),"refresh to known OFF before pending enable");
        int offRead=f.statusReads-1;f.status(offRead,"OFF",false,"PAIRED");
        check(s.perform(MibrWirelessSession.REQUEST_TOGGLE)&&f.targets[4],"start enable from OFF");
        int pendingEnable=4;
        check(s.enabled(MibrWirelessSession.REQUEST_STOP) && s.perform(MibrWirelessSession.REQUEST_STOP),"Stop preempts enable even before native state leaves OFF");
        int pendingStop=5;
        f.result(pendingEnable,true,"ACTIVE",false,"PAIRED");
        check(s.statusLine().indexOf("Stop request pending")>=0 && !s.enabled(MibrWirelessSession.REFRESH_STATUS),
              "superseded reply cannot finish the pending Stop");
        check(s.statusLine().indexOf("Stop request pending")>=0,"superseded enable cannot overwrite Stop status");
        f.result(pendingStop,true,"OFF",false,"PAIRED");
        check(s.statusLine().toLowerCase().indexOf("off")>=0 && !s.enabled(MibrWirelessSession.REQUEST_STOP),"Stop requires confirmed OFF snapshot");

        // Same page generation, different request IDs: duplicate older status replies stay stale.
        check(s.perform(MibrWirelessSession.REFRESH_STATUS),"status refresh one");
        int oldReads=f.statusReads-1;
        f.status(oldReads,"OFF",false,"NOT_PAIRED");
        check(s.perform(MibrWirelessSession.REFRESH_STATUS),"status refresh two");
        int newReads=f.statusReads-1;
        f.status(oldReads,"ACTIVE",true,"PAIRED");
        check(s.statusLine().toLowerCase().indexOf("off")>=0,"old same-generation status reply ignored");
        f.status(newReads,"OFF",false,"NOT_PAIRED");
        check(s.statusLine().toLowerCase().indexOf("off")>=0,"current status read accepted");

        check(s.perform(MibrWirelessSession.REFRESH_STATUS),"timeout probe status starts");
        long token=f.statusGenerations[f.statusReads-1]; s.expireAt(token,System.currentTimeMillis()+11000L);
        check(s.statusLine().indexOf("refresh native status")>=0,"withheld callback expires into unknown/fail-closed state");
        s.leavePage();check(!s.enabled(MibrWirelessSession.REFRESH_STATUS),"leaving page closes generation");
        s.detach();s.enterPage();check(!s.available(),"detached menu never reattaches");
        System.out.println("MIBR_WIRELESS_SESSION_PASS fail_closed=1 request_ids=1 duplicate_guard=1 stop_preemption=1 timeout=1");
    }
}
