package de.mibr.hmi;

import java.util.Vector;

/** Wire grammar and request-ID discipline of the visible-route ACTION. */
public final class MibrV3RouteTest {
    static final String AUTH="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);}
    static void rejects(String name,Runnable op){
        try{op.run();throw new AssertionError("ACCEPTED_"+name);}catch(IllegalArgumentException expected){}
    }
    static MibrV3Protocol.Frame ok(String rid,String payload){
        return MibrV3Protocol.parse("MIBR/3 "+rid+" OK "+payload+"\n",rid);
    }
    static MibrV3Protocol.Frame err(String rid,String code){
        return MibrV3Protocol.parse("MIBR/3 "+rid+" ERR "+code+"\n",rid);
    }
    static String caps(boolean route){
        return "snapshot=1;durable_set=0;test_override=0;presentation_refresh=0;reconnect=0;session_control=0;route_action="+
            (route?"1":"0")+";key40_input=0;zoom_exec_owner=GEN2;phase=NATIVE_READONLY_OFFLINE";
    }
    static String status(String route,String session,String gen){
        String s="ready=READ_ONLY;stored=UNCONFIRMED;durable_generation=UNKNOWN;runtime_correlated=0;connected=UNKNOWN;session=NONE;pending=UNKNOWN;";
        if(route==null)return s+"route_correlated=0;visible_route=UNKNOWN;runtime_observed=0;persistent_safety=UNQUALIFIED";
        return s+"route_correlated=1;visible_route="+route+";route_session="+session+";route_generation="+gen+
            ";runtime_observed=0;persistent_safety=UNQUALIFIED";
    }

    interface Responder {MibrV3Protocol.Frame reply(String verb,String rid,String[] names,String[] values);}
    static final class Fake implements MibrV3Route.Transport {
        final Responder responder;final Vector verbs=new Vector();final Vector lastValues=new Vector();
        int actions;boolean transportError;
        Fake(Responder r){responder=r;}
        public boolean send(String rid,String verb,String[] names,String[] values,MibrV3Client.Listener cb){
            verbs.addElement(verb);lastValues.addElement(values);
            if("ACTION".equals(verb))actions++;
            if(transportError&&"ACTION".equals(verb)){cb.onReply(null,"TRANSPORT_OR_PROTOCOL_UNCONFIRMED");return true;}
            cb.onReply(responder.reply(verb,rid,names,values),null);return true;
        }
    }
    static final class Pump implements MibrV3Route.Later {
        final Vector queue=new Vector();
        public void after(long ms,Runnable r){queue.addElement(r);}
        void run(){while(!queue.isEmpty()){Runnable r=(Runnable)queue.elementAt(0);queue.removeElementAt(0);r.run();}}
    }
    static final MibrV3Route.Dispatcher NOW=new MibrV3Route.Dispatcher(){public void post(Runnable a){a.run();}};

    static void protocol(){
        String line=MibrV3Protocol.request("hmi87","ACTION",
            new String[]{"kind","target","expected_route","expected_session","expected_generation","origin","request_id"},
            new String[]{"SET_VISIBLE_ROUTE","DIRECT111","STOCK110","7","9","HMI","hmi87"},AUTH);
        check(line.equals("MIBR/3 hmi87 ACTION kind=SET_VISIBLE_ROUTE;target=DIRECT111;expected_route=STOCK110;"+
            "expected_session=7;expected_generation=9;origin=HMI;request_id=hmi87;auth="+AUTH+"\n"),"exact ACTION frame");
        check(MibrV3Protocol.request("check87","ACTION_STATUS",new String[]{"request_id"},new String[]{"hmi87"},AUTH)
            .equals("MIBR/3 check87 ACTION_STATUS request_id=hmi87;auth="+AUTH+"\n"),"exact ACTION_STATUS frame");
        rejects("TOGGLE",new Runnable(){public void run(){MibrV3Protocol.request("x1","TOGGLE",new String[0],new String[0],AUTH);}});
        check(MibrV3Protocol.routeAction(ok("c1",caps(true))),"route_action=1");
        check(!MibrV3Protocol.routeAction(ok("c2",caps(false))),"route_action=0 is normal, not an error");
        MibrV3Protocol.RouteState s=MibrV3Protocol.routeState(ok("s1",status("STOCK110","7","9")));
        check(s.actionable()&&"DIRECT111".equals(s.opposite()),"actionable with owner proof");
        check(!MibrV3Protocol.routeState(ok("s2",status(null,null,null))).actionable(),"unknown route not actionable");
        rejects("ZERO_SESSION",new Runnable(){public void run(){MibrV3Protocol.routeState(ok("s3",status("STOCK110","0","9")));}});
        rejects("LEADING_ZERO",new Runnable(){public void run(){MibrV3Protocol.routeState(ok("s4",status("STOCK110","7","09")));}});
        rejects("UNKNOWN_ENUM",new Runnable(){public void run(){MibrV3Protocol.routeState(ok("s5",status("OTHER","7","9")));}});
        final MibrV3Protocol.Frame active=ok("h1","kind=SET_VISIBLE_ROUTE;target=DIRECT111;apply=ACTIVE;visible_route=DIRECT111;stored=UNCHANGED;owner_session=7;owner_generation=10");
        check(MibrV3Protocol.actionReceipt(active,"DIRECT111").active,"ACTIVE with owner proof");
        rejects("ACTIVE_NO_PROOF",new Runnable(){public void run(){MibrV3Protocol.actionReceipt(
            ok("h2","kind=SET_VISIBLE_ROUTE;target=DIRECT111;apply=ACTIVE;visible_route=DIRECT111;stored=UNCHANGED"),"DIRECT111");}});
        rejects("PENDING_WITH_VISIBLE",new Runnable(){public void run(){MibrV3Protocol.actionReceipt(
            ok("h3","kind=SET_VISIBLE_ROUTE;target=DIRECT111;apply=PENDING;visible_route=DIRECT111;stored=UNCHANGED"),"DIRECT111");}});
        rejects("WRONG_TARGET",new Runnable(){public void run(){MibrV3Protocol.actionReceipt(active,"STOCK110");}});
        check(!MibrV3Protocol.actionReceipt(ok("h4","kind=SET_VISIBLE_ROUTE;target=DIRECT111;apply=PENDING;visible_route=UNKNOWN;stored=UNCHANGED"),"DIRECT111").active,"PENDING");
        check(MibrV3Protocol.actionStatusReceipt(ok("k1","original_request_id=hmi87;kind=SET_VISIBLE_ROUTE;target=DIRECT111;apply=ACTIVE;receipt_scope=HISTORICAL;stored=UNCHANGED"),"DIRECT111","hmi87").active,"historical ACTIVE");
        rejects("STATUS_OTHER_ID",new Runnable(){public void run(){MibrV3Protocol.actionStatusReceipt(
            ok("k2","original_request_id=other;kind=SET_VISIBLE_ROUTE;target=DIRECT111;apply=ACTIVE;receipt_scope=HISTORICAL;stored=UNCHANGED"),"DIRECT111","hmi87");}});
        // No-write fields only: the ACTION never carries a key or value.
        String[][] f=MibrV3Protocol.routeActionFields(s,"hmi9");
        check(f[0].length==7&&"origin".equals(f[0][5])&&"HMI".equals(f[1][5])&&"hmi9".equals(f[1][6]),"seven fields, HMI origin");
    }

    static MibrV3Route route(Fake t,Pump p){return new MibrV3Route(t,NOW,p,new Runnable(){public void run(){}});}
    static Responder base(final String[] routeBox,final int[] gen,final String[] actionMode,final int[] statusCalls){
        return new Responder(){public MibrV3Protocol.Frame reply(String verb,String rid,String[] n,String[] v){
            if("CAPABILITIES".equals(verb))return ok(rid,caps(true));
            if("STATUS".equals(verb))return ok(rid,status(routeBox[0],"7",""+gen[0]));
            if("ACTION".equals(verb)){
                String target=v[1];
                if("ACTIVE".equals(actionMode[0])){routeBox[0]=target;gen[0]++;
                    return ok(rid,"kind=SET_VISIBLE_ROUTE;target="+target+";apply=ACTIVE;visible_route="+target+";stored=UNCHANGED;owner_session=7;owner_generation="+gen[0]);}
                if("NOT_READY".equals(actionMode[0]))return err(rid,"NOT_READY");
                return ok(rid,"kind=SET_VISIBLE_ROUTE;target="+target+";apply=PENDING;visible_route=UNKNOWN;stored=UNCHANGED");
            }
            if("ACTION_STATUS".equals(verb)){
                statusCalls[0]++;
                if("EVICTED".equals(actionMode[1]))return err(rid,"UNKNOWN_COMMIT");
                String apply=statusCalls[0]>=2&&"LATE".equals(actionMode[1])?"ACTIVE":"PENDING";
                if("ACTIVE".equals(apply)){routeBox[0]="DIRECT111";gen[0]++;}
                return ok(rid,"original_request_id="+v[0]+";kind=SET_VISIBLE_ROUTE;target=DIRECT111;apply="+apply+";receipt_scope=HISTORICAL;stored=UNCHANGED");
            }
            throw new AssertionError("unexpected "+verb);
        }};
    }

    static void machine(){
        // route_action=0: the unit's normal state, UNAVAILABLE, never an error or a retry.
        Fake off=new Fake(new Responder(){public MibrV3Protocol.Frame reply(String verb,String rid,String[] n,String[] v){return ok(rid,caps(false));}});
        Pump p=new Pump();MibrV3Route r=route(off,p);r.refresh();
        check(r.state()==MibrV3Route.UNAVAILABLE&&!r.canSwitch()&&off.verbs.size()==1,"route_action=0 stops after CAPABILITIES");
        r.toggle();check(off.actions==0,"no ACTION when unavailable");

        // Immediate ACTIVE: one ACTION, then fresh CAPABILITIES + STATUS before the display changes.
        String[] route={"STOCK110"};int[] gen={9};String[] mode={"ACTIVE","LATE"};int[] sc={0};
        Fake t=new Fake(base(route,gen,mode,sc));p=new Pump();r=route(t,p);r.refresh();
        check(r.canSwitch()&&"STOCK110".equals(r.visible()),"READY with observed route");
        r.toggle();
        check(t.actions==1&&r.state()==MibrV3Route.READY&&"DIRECT111".equals(r.visible()),"ACTIVE then fresh STATUS");
        String[] sent=(String[])t.lastValues.elementAt(t.verbs.indexOf("ACTION"));
        check("DIRECT111".equals(sent[1])&&"STOCK110".equals(sent[2])&&"7".equals(sent[3])&&"9".equals(sent[4]),"compare-and-set fields");
        check(t.verbs.lastElement().equals("STATUS"),"fresh STATUS after ACTIVE");

        // PENDING resolved by ACTION_STATUS on the original ID; never a second ACTION.
        route=new String[]{"STOCK110"};gen=new int[]{9};mode=new String[]{"PENDING","LATE"};sc=new int[]{0};
        t=new Fake(base(route,gen,mode,sc));p=new Pump();r=route(t,p);r.refresh();r.toggle();
        check(r.state()==MibrV3Route.PENDING&&!r.canSwitch(),"PENDING disables repeat clicks");
        r.toggle();check(t.actions==1,"no second ACTION while pending");
        p.run();
        check(t.actions==1&&sc[0]==2&&r.state()==MibrV3Route.READY&&"DIRECT111".equals(r.visible()),"PENDING -> historical ACTIVE -> fresh STATUS");

        // Lost reply: same discipline, evicted receipt -> re-observe, still one ACTION.
        route=new String[]{"STOCK110"};gen=new int[]{9};mode=new String[]{"PENDING","EVICTED"};sc=new int[]{0};
        t=new Fake(base(route,gen,mode,sc));t.transportError=true;p=new Pump();r=route(t,p);r.refresh();r.toggle();
        check(r.state()==MibrV3Route.PENDING,"lost reply is PENDING, not failure");
        p.run();
        check(t.actions==1&&r.state()==MibrV3Route.READY&&"STOCK110".equals(r.visible()),"UNKNOWN_COMMIT re-observes without a new toggle");

        // Never resolves: bounded polling, UNRESOLVED, still one ACTION; refresh ignored.
        route=new String[]{"STOCK110"};gen=new int[]{9};mode=new String[]{"PENDING","NEVER"};sc=new int[]{0};
        t=new Fake(base(route,gen,mode,sc));p=new Pump();r=route(t,p);r.refresh();r.toggle();p.run();
        check(r.state()==MibrV3Route.UNRESOLVED&&sc[0]==MibrV3Route.MAX_POLLS&&t.actions==1,"bounded polling");
        int before=t.verbs.size();r.refresh();check(t.verbs.size()==before,"refresh ignored while unresolved");

        // NOT_READY: refusal, no new request ID, no retry.
        route=new String[]{"STOCK110"};gen=new int[]{9};mode=new String[]{"NOT_READY","NEVER"};sc=new int[]{0};
        t=new Fake(base(route,gen,mode,sc));p=new Pump();r=route(t,p);r.refresh();r.toggle();
        check(t.actions==1&&r.state()==MibrV3Route.UNAVAILABLE&&r.note().indexOf("NOT_READY")>=0,"NOT_READY surfaced, no retry");
        r.toggle();check(t.actions==1,"unavailable after refusal until a fresh observation");

        // Detach silences everything.
        route=new String[]{"STOCK110"};gen=new int[]{9};mode=new String[]{"PENDING","NEVER"};sc=new int[]{0};
        t=new Fake(base(route,gen,mode,sc));p=new Pump();r=route(t,p);r.refresh();r.toggle();r.detach();p.run();
        check(sc[0]==0&&r.state()==MibrV3Route.UNAVAILABLE,"detach stops polling");
    }
    public static void main(String[] a){
        protocol();machine();
        System.out.println("MIBR_V3_ROUTE_PASS");
    }
}
