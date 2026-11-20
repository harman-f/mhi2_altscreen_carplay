package de.mibr.hmi;

/**
 * r15f car 2026-11-19: SAFE_CENTER_SET went out with expected_revision=0 and got STALE_REVISION (the shared profile
 * unit.revision had moved). Host session against a fake broker: page entry re-reads the revision before the first
 * SET, STALE_REVISION re-reads once and re-sends the newest wish, a second stale SET gives up.
 */
public final class MibrSafeRevisionTest {
    private static void check(boolean c,String name){if(!c)throw new AssertionError(name);}

    static final class Broker extends MibrV3Client {
        String rev="0",value="370,58,256,248",lastExpected;int sets,gets;boolean alwaysStale;
        Broker(){super(28743,"/unread/host/fixture");}
        private String state(String rid){
            return MibrV3BindingTest.reply(rid,new String[]{"value","revision","writer","stored","scope","apply"},
                new String[]{value,rev,"ENABLED","VERIFIED","MIBR_ONLY","IMMEDIATE"});
        }
        public synchronized boolean send(String rid,String verb,String[] names,String[] values,Listener cb){
            String r;
            if("HELLO".equals(verb))r=MibrV3BindingTest.reply(rid,new String[]{"version","schema","registry_keys","phase"},
                new String[]{"MIBR/3","2","48","NATIVE_PROFILE_GUARDED"});
            else if("CAPABILITIES".equals(verb))r=MibrV3BindingTest.reply(rid,new String[]{"snapshot","durable_set","test_override",
                "presentation_refresh","reconnect","session_control","phase","safe_center"},
                new String[]{"1","1","0","0","0","0","NATIVE_PROFILE_GUARDED","1"});
            else if("SNAPSHOT".equals(verb))r=MibrV3BindingTest.snapshot(rid,"23","20");
            else if("SAFE_CENTER_GET".equals(verb)){gets++;r=state(rid);}
            else if("SAFE_CENTER_SET".equals(verb)){
                sets++;lastExpected=values[1];
                if(alwaysStale||!rev.equals(values[1]))r="MIBR/3 "+rid+" ERR STALE_REVISION\n";
                else{value=values[0];rev=String.valueOf(Long.parseLong(rev)+1);r=state(rid);}
            }else r="MIBR/3 "+rid+" ERR UNSUPPORTED\n";
            cb.onReply(MibrV3Protocol.parse(r,rid),null);return true;
        }
    }
    private static void idle() throws InterruptedException {Thread.sleep(MibrSafeArea.IDLE_MS+600L);}

    public static void main(String[] args) throws Exception {
        final StringBuffer log=new StringBuffer();
        MibrSafeArea.diag=new MibrSafeArea.Diag(){public void line(String t){synchronized(log){log.append(t).append('\n');}}};
        MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);
        Broker b=new Broker();
        MibrV3Session s=new MibrV3Session(b,model,new MibrV3Session.Dispatcher(){public void post(Runnable r){r.run();}},
            new Runnable(){public void run(){}});
        s.open();
        MibrDurableSwitch sw=MibrDurableSwitch.SAFE_CENTER;
        int key=MibrPopupEditorModel.SAFE_FIRST+10; // Center, left edge
        check(b.gets==1&&"0".equals(sw.revision()),"session start reads revision 0");

        // (1) another writer moved the shared unit.revision; page entry re-reads it before the first SET
        b.rev="5";
        s.safeRefresh(key);
        check(b.gets==2&&"5".equals(sw.revision()),"page entry re-reads the revision");
        s.safeEdge(key,300);
        check(b.sets==0,"debounced");
        idle();
        check(b.sets==1&&"5".equals(b.lastExpected)&&"300,58,326,248".equals(b.value)&&"6".equals(sw.revision()),
              "first SET after entry carries the current revision: "+b.lastExpected+" "+b.value);

        // (2) the revision moves behind our back: STALE -> one re-read -> resend of the newest wish
        b.rev="9";
        s.safeEdge(key,320);
        idle();
        check(b.sets==3&&"9".equals(b.lastExpected)&&"320,58,306,248".equals(b.value),
              "stale SET re-read once and resent with the current revision: sets="+b.sets+" exp="+b.lastExpected);
        check(log.toString().indexOf("MIBR_SAFE_SLIDER_SET_STALE_RETRY SAFE_CENTER")>=0&&
              log.toString().indexOf("MIBR_SAFE_SLIDER_SET_REREAD SAFE_CENTER revision=9")>=0,"retry logged");
        check(MibrSafeArea.due(sw,System.currentTimeMillis()+5000)==null,"nothing left to send");

        // (3) stale again after the re-read: give up, stored value shown, no loop
        b.alwaysStale=true;
        int before=b.sets;
        s.safeEdge(key,340);
        idle();idle();
        check(b.sets==before+2,"exactly one retry: "+(b.sets-before));
        check(sw.wanted==null&&"320,58,306,248".equals(MibrSafeArea.shown(sw)),"gave up: stored value shown");
        check(log.toString().indexOf("MIBR_SAFE_SLIDER_SET_STALE SAFE_CENTER")>=0,"give-up logged");

        // (4) a verified SET of one profile-backed switch moves the shared revision of the others
        MibrDurableSwitch.SAFE_VOLL.readback("0,58,1010,248","3",true);
        MibrDurableSwitch.CARPLAY_NAV.readback("off","4",true);
        MibrDurableSwitch.sharedRevision(MibrDurableSwitch.SAFE_CENTER,"12");
        check("12".equals(MibrDurableSwitch.SAFE_VOLL.revision()),"profile-backed sibling takes the shared revision");
        check("4".equals(MibrDurableSwitch.CARPLAY_NAV.revision()),"own-file switch keeps its own revision");
        s.detach();
        System.out.println("MIBR_SAFE_REVISION_HOST_PASS");
        System.exit(0);
    }
}
