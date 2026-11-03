package de.mibr.hmi;

/** No Unit, no native writes: exact Java wire + synthetic service/session contract. */
public final class MibrV3BindingTest {
    static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    static void rejects(String name,Runnable op){
        try{op.run();throw new AssertionError("ACCEPTED_"+name);}
        catch(IllegalArgumentException expected){}
    }
    static String fields(String[] names,String[] values){
        StringBuffer b=new StringBuffer();
        for(int i=0;i<names.length;i++){
            if(i>0)b.append(';');b.append(names[i]).append('=').append(MibrV3Protocol.encode(values[i]));
        }
        return b.toString();
    }
    static String reply(String rid,String[] n,String[] v){return "MIBR/3 "+rid+" OK "+fields(n,v)+"\n";}
    static String caps(String rid,boolean writable){
        return reply(rid,new String[]{"snapshot","durable_set","test_override",
            "presentation_refresh","reconnect","session_control","phase"},
            new String[]{"1",writable?"1":"0","0","0","0","0",
            writable?"NATIVE_PROFILE_GUARDED":"NATIVE_READONLY_OFFLINE"});
    }
    static String snapshot(String rid,String rev,String fps){
        StringBuffer b=new StringBuffer("MIBR/3 ").append(rid).append(" OK row_count=11;revision=")
          .append(rev).append(";stored=UNCONFIRMED;durable_generation=UNKNOWN;runtime_correlated=0")
          .append(";connected=UNKNOWN;session=NONE;session_generation=UNKNOWN;pending=UNKNOWN")
          .append(";phase=NATIVE_PROFILE_GUARDED");
        int j=0;
        // Native scope=ui wire order, written out literally: the r8
        // HMI hides navigation.url but the native service still sends 11 rows.
        String[] section={"carplay.enabled","viewarea.selected","navigation.surface",
            "navigation.ETA","navigation.speedLimit","navigation.compass","navigation.maneuver",
            "navigation.url","preset.id","maxFPS","sourceVersion"};
        {
            for(int i=0;i<section.length;i++){
                String key=section[i],value="1";
                if("maxFPS".equals(key))value=fps;
                else if("navigation.surface".equals(key))value="map";
                else if("navigation.ETA".equals(key)||"navigation.speedLimit".equals(key)||
                        "navigation.compass".equals(key))value="user";
                else if("navigation.maneuver".equals(key))value=maneuver;
                else if("navigation.url".equals(key))value="auto";
                else if("preset.id".equals(key))value="mibr_legacy";
                else if("sourceVersion".equals(key))value="1005.8.1";
                if(OVERRIDE.containsKey(key))value=(String)OVERRIDE.get(key);
                String prefix=";row."+j+".";
                b.append(prefix).append("key=").append(MibrV3Protocol.encode(key));
                b.append(prefix).append("value=").append(MibrV3Protocol.encode(value));
                b.append(prefix).append("source=profile");
                b.append(prefix).append("apply=").append(MibrSettingsCatalog.APPLY[MibrV3Protocol.index(key)]);
                b.append(prefix).append("active=UNKNOWN").append(prefix).append("advertised=UNKNOWN");
                j++;
            }
        }
        return b.append('\n').toString();
    }
    static final java.util.HashMap OVERRIDE=new java.util.HashMap();
    static String maneuver="left";
    static int idx(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        throw new AssertionError(key);
    }
    static class Fake extends MibrV3Client {
        int sets,reads,requests;
        String fps="20",revision="23";
        boolean writable,dropSet;
        Fake(boolean writable){super(28743,"/unread/host/fixture");this.writable=writable;}
        public synchronized boolean send(String rid,String verb,String[] names,String[] values,Listener cb){
            String response;
            if("HELLO".equals(verb))response=reply(rid,new String[]{"version","schema","registry_keys","phase"},
                new String[]{"MIBR/3","2","48",writable?"NATIVE_PROFILE_GUARDED":"NATIVE_READONLY_OFFLINE"});
            else if("CAPABILITIES".equals(verb))response=caps(rid,writable);
            else if("SNAPSHOT".equals(verb)){reads++;response=snapshot(rid,revision,fps);}
            else if("SET".equals(verb)){
                sets++;check(writable,"SET without durable capability");
                if("navigation.maneuver".equals(values[0])){
                    check("top".equals(values[1]),"maneuver gesture payload");maneuver="top";
                }else{
                    check("maxFPS".equals(values[0])&&"60".equals(values[1]),"FPS unit-reboot payload");fps=values[1];
                }
                check(revision.equals(values[2])&&"AUTO".equals(values[3])&&rid.equals(values[4]),"CAS/request id");
                revision=sets==1?"24":"25";
                if(dropSet){cb.onReply(null,"TRANSPORT_OR_PROTOCOL_UNCONFIRMED");return true;}
                String apply="maxFPS".equals(values[0])?"UNIT_REBOOT":"PRESENTATION";
                String stored="maxFPS".equals(values[0])?"PENDING_PERSIST":"VERIFIED";
                response=reply(rid,new String[]{"stored","apply","active","activation","revision","materialized"},
                    new String[]{stored,"PENDING","UNKNOWN",apply,revision,"1"});
            }else if("REQUEST_STATUS".equals(verb)){
                requests++;response="MIBR/3 "+rid+" ERR UNKNOWN_COMMIT\n";
            } else if ("ENGINE_GET".equals(verb) || "ENGINE_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"engine", "announced", "pending"}, new String[]{"gas", "gas", "0"}); else if ("VIEW_GET".equals(verb) || "VIEW_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"follow", "sport", "m0", "m1", "m4", "rs", "pos"}, new String[]{"0", "1", "1", "0", "2", "0", "0"}); else throw new AssertionError(verb);
            cb.onReply(MibrV3Protocol.parse(response,rid),null);return true;
        }
    }
    static MibrV3Session session(MibrV3Client fake,MibrPopupEditorModel model){
        return new MibrV3Session(fake,model,new MibrV3Session.Dispatcher(){
            public void post(Runnable action){action.run();}
        },new Runnable(){public void run(){}});
    }
    static void wire(){
        final String secret="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        String request=MibrV3Protocol.request("r-1","SET",
            new String[]{"key","value","expected_revision","activation","request_id"},
            new String[]{"navigation.compass","user","23","AUTO","r-1"},secret);
        check(request.indexOf("key=navigation.compass;value=user;expected_revision=23;activation=AUTO;request_id=r-1;auth=")>0,"native wire");
        check(request.endsWith(secret+"\n"),"auth last");
        check("%2F".equals(MibrV3Protocol.encode("/")),"canonical percent");
        check("/".equals(MibrV3Protocol.decode("%2F")),"percent decoding");
        check("a%20b".equals(MibrV3Protocol.encode("a b")),"space encoding");
        rejects("escaped-safe",new Runnable(){public void run(){MibrV3Protocol.decode("%61");}});
        rejects("utf8",new Runnable(){public void run(){MibrV3Protocol.decode("%FF");}});
        rejects("bad delimiter",new Runnable(){public void run(){
            MibrV3Protocol.parse("MIBR/3 rid OK row_count=11;;revision=23\n","rid");}});
        rejects("wrong-id",new Runnable(){public void run(){
            MibrV3Protocol.parse("MIBR/3 another OK revision=23\n","rid");}});
        rejects("duplicate",new Runnable(){public void run(){
            MibrV3Protocol.parse("MIBR/3 rid OK revision=23;revision=24\n","rid");}});
        check(MibrV3Protocol.hello(MibrV3Protocol.parse(reply("h",new String[]{"version","schema","registry_keys"},
            new String[]{"MIBR/3","2","48"}),"h")),"HELLO");
        MibrV3Protocol.Snapshot s=MibrV3Protocol.snapshot(MibrV3Protocol.parse(snapshot("s","23","20"),"s"));
        check(s.keys.length==11 && "maxFPS".equals(s.keys[9])&&"20".equals(s.values[9]),"atomic native snapshot");
        check("UNKNOWN".equals(MibrV3Protocol.parse(snapshot("s","23","20"),"s").get("row.9.active")),"no false active");
        MibrV3Protocol.Frame c=MibrV3Protocol.parse(reply("set",new String[]{"stored","apply","active","activation","revision","materialized"},
            new String[]{"VERIFIED","PENDING","UNKNOWN","UNIT_REBOOT","24","1"}),"set");
        check("24".equals(MibrV3Protocol.commit(c,"maxFPS","25").revision),"verified receipt");
        rejects("false-stored",new Runnable(){public void run(){
            MibrV3Protocol.commit(MibrV3Protocol.parse(reply("set",new String[]{"stored","apply","active","activation","revision","materialized"},
                new String[]{"UNCONFIRMED","PENDING","UNKNOWN","UNIT_REBOOT","24","1"}),"set"),"maxFPS","25");}});
    }
    static void lifecycle(){
        // Owner-approved settings include reboot-applied maxFPS.
        final int M=idx("navigation.maneuver"),F=idx("maxFPS");
        maneuver="left";
        MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);
        Fake fake=new Fake(true);MibrV3Session s=session(fake,model);s.open();
        check(s.canWrite() && "left".equals(model.current(M)),"initial atomic snapshot");
        check(model.open(M)&&model.choose(3)&&"top".equals(model.draft(M)),"completed gesture");
        s.commit(M);
        check(fake.sets==1&&fake.reads==2&&model.draft(M)==null&&"top".equals(model.current(M)),"post-commit readback");
        check(!s.status().toLowerCase().contains("aktiviert"),"do not claim applied");
        // No ordinary persistent write for the two runtime actions or unapproved keys.
        model.toggle(1);s.commit(1);
        model.toggle(0);s.commit(0);
        check(model.open(F)&&model.choose(1));s.commit(F);
        check(fake.sets==2&&"60".equals(fake.fps)&&"60".equals(model.current(F))&&model.draft(F)==null,
              "maxFPS is saved and read back; apply waits for Unit reboot");
        s.detach();
        maneuver="left";
        Fake readOnly=new Fake(false);MibrPopupEditorModel local=new MibrPopupEditorModel();
        local.setAvailable(true);MibrV3Session r=session(readOnly,local);r.open();
        check(!r.canWrite()&&local.open(M)&&local.choose(3),"read-only snapshot");
        r.commit(M);check(readOnly.sets==0&&"top".equals(local.draft(M)),"fail closed, draft retained");
        Fake ambiguous=new Fake(true);ambiguous.dropSet=true;maneuver="left";
        MibrPopupEditorModel m=new MibrPopupEditorModel();m.setAvailable(true);
        MibrV3Session uncertain=session(ambiguous,m);uncertain.open();m.open(M);m.choose(3);uncertain.commit(M);
        check(ambiguous.sets==1&&ambiguous.requests==1&&"top".equals(m.draft(M))&&!uncertain.canWrite(),
              "never retry ambiguous SET");
    }
    /** r11: deferred SET replies so a tap can land while a save is in flight. */
    static class Deferred extends MibrV3Client {
        final java.util.Hashtable values=new java.util.Hashtable();
        final java.util.Vector pending=new java.util.Vector();
        int sets,revision=23,stale;
        Deferred(){
            super(28743,"/unread/host/fixture");
            String[] k={"carplay.enabled","viewarea.selected","navigation.surface","navigation.ETA",
                "navigation.speedLimit","navigation.compass","navigation.maneuver","navigation.url",
                "preset.id","maxFPS","sourceVersion"};
            String[] v={"1","1","map","user","user","user","left","auto","mibr_legacy","30","1005.8.1"};
            for(int i=0;i<k.length;i++)values.put(k[i],v[i]);
        }
        String snap(String rid){
            String[] k={"carplay.enabled","viewarea.selected","navigation.surface","navigation.ETA",
                "navigation.speedLimit","navigation.compass","navigation.maneuver","navigation.url",
                "preset.id","maxFPS","sourceVersion"};
            StringBuffer b=new StringBuffer("MIBR/3 ").append(rid).append(" OK row_count=11;revision=")
              .append(revision).append(";stored=UNCONFIRMED;durable_generation=UNKNOWN;runtime_correlated=0")
              .append(";connected=UNKNOWN;session=NONE;session_generation=UNKNOWN;pending=UNKNOWN")
              .append(";phase=NATIVE_PROFILE_GUARDED");
            for(int i=0;i<k.length;i++){
                String prefix=";row."+i+".";
                b.append(prefix).append("key=").append(MibrV3Protocol.encode(k[i]));
                b.append(prefix).append("value=").append(MibrV3Protocol.encode((String)values.get(k[i])));
                b.append(prefix).append("source=profile");
                b.append(prefix).append("apply=").append(MibrSettingsCatalog.APPLY[MibrV3Protocol.index(k[i])]);
                b.append(prefix).append("active=UNKNOWN").append(prefix).append("advertised=UNKNOWN");
            }
            return b.append('\n').toString();
        }
        public synchronized boolean send(String rid,String verb,String[] names,String[] v,Listener cb){
            String response;
            if("HELLO".equals(verb))response=reply(rid,new String[]{"version","schema","registry_keys","phase"},
                new String[]{"MIBR/3","2","48","NATIVE_PROFILE_GUARDED"});
            else if("CAPABILITIES".equals(verb))response=caps(rid,true);
            else if("SNAPSHOT".equals(verb))response=snap(rid);
            else if("SET".equals(verb)){
                sets++;
                check(Integer.toString(revision).equals(v[2]),"SET carries the current revision");
                pending.addElement(new Object[]{rid,v[0],v[1],cb});return true;
            } else if ("ENGINE_GET".equals(verb) || "ENGINE_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"engine", "announced", "pending"}, new String[]{"gas", "gas", "0"}); else if ("VIEW_GET".equals(verb) || "VIEW_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"follow", "sport", "m0", "m1", "m4", "rs", "pos"}, new String[]{"0", "1", "1", "0", "2", "0", "0"}); else throw new AssertionError(verb);
            cb.onReply(MibrV3Protocol.parse(response,rid),null);return true;
        }
        /** Completes the oldest in-flight SET. */
        void release(){
            Object[] p=(Object[])pending.elementAt(0);pending.removeElementAt(0);
            String rid=(String)p[0],key=(String)p[1],value=(String)p[2];
            Listener cb=(Listener)p[3];
            if(stale>0){stale--;revision++;
                cb.onReply(MibrV3Protocol.parse("MIBR/3 "+rid+" ERR STALE_REVISION\n",rid),null);return;}
            values.put(key,value);revision++;
            String activation="viewarea.selected".equals(key)?"LIVE":"PRESENTATION";
            cb.onReply(MibrV3Protocol.parse(reply(rid,new String[]{"stored","apply","active","activation","revision","materialized"},
                new String[]{"VERIFIED","PENDING","UNKNOWN",activation,Integer.toString(revision),"1"}),rid),null);
        }
    }
    static void queue(){
        final int C=idx("navigation.compass"),E=idx("navigation.ETA"),V=idx("viewarea.selected");
        MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);
        Deferred fake=new Deferred();MibrV3Session s=session(fake,model);s.open();
        check(s.canWrite(),"ready");
        check(model.toggle(C)&&"yes".equals(model.draft(C)),"first tap");s.commit(C);
        check(fake.sets==1&&fake.pending.size()==1,"one SET in flight");
        // Second tap on the same row and a tap on another row while the SET is in flight.
        check(model.toggle(C)&&"no".equals(model.draft(C)),"second tap");s.commit(C);
        check(model.toggle(E)&&"yes".equals(model.draft(E)),"other row");s.commit(E);
        check(fake.sets==1,"no parallel SET while one is in flight");
        fake.release();
        check(fake.sets==2&&"yes".equals(model.current(C))&&"no".equals(model.draft(C)),
              "first save confirmed, newer wish kept and sent next");
        fake.release();
        check(fake.sets==3,"queued other row sent next");
        fake.release();
        check(fake.pending.size()==0&&"no".equals(fake.values.get("navigation.compass"))&&
              "yes".equals(fake.values.get("navigation.ETA")),"latest wishes are stored");
        check(model.draft(C)==null&&model.draft(E)==null&&"no".equals(model.current(C))&&s.canWrite(),
              "rows show the saved values, writing stays possible");
        // A stale revision is retried after a fresh read.
        fake.stale=1;
        check(model.toggle(C)&&"yes".equals(model.draft(C)),"tap after stale");s.commit(C);
        fake.release();
        check(fake.sets==5&&fake.pending.size()==1,"stale revision retried once");
        fake.release();
        check("yes".equals(fake.values.get("navigation.compass"))&&model.draft(C)==null&&s.canWrite(),"retry saved");
        // r14: Ansicht (Voll/Wide) is a live TEMP index, saved like the navigation values.
        check(model.open(V),"view dropdown open");model.cancel();
        s.detach();
    }
    /**
     * Physical Scaling increases background reads, but a slow ENGINE_GET must
     * never invalidate core SNAPSHOT/SET or make navigation.ETA/Map unwritable.
     * Hold one admitted request beyond the old 3-second per-request spin limit.
     * The next view GET and a real navigation SET are queued, not retried in
     * parallel; a failing background reply is local to that feature.
     */
    static class SlowBackground extends Fake {
        MibrV3Client.Listener waiting;
        String waitingId;
        String waitingVerb;
        int collided;
        final boolean holdView;
        SlowBackground(){this(false);}
        SlowBackground(boolean holdView){super(true);this.holdView=holdView;}
        public synchronized boolean send(String rid,String verb,String[] names,String[] values,Listener cb){
            if(waiting!=null){collided++;return false;}
            if("ENGINE_GET".equals(verb)||holdView&&"VIEW_GET".equals(verb)){
                waiting=cb;waitingId=rid;waitingVerb=verb;return true;
            }
            return super.send(rid,verb,names,values,cb);
        }
        void finishWithError(){
            Listener callback=waiting;
            if(callback==null)throw new AssertionError("NO_DELAYED_BACKGROUND_GET");
            waiting=null;waitingId=null;waitingVerb=null;
            callback.onReply(null,"TRANSPORT_OR_PROTOCOL_UNCONFIRMED");
        }
    }
    static void slowBackgroundMustNotDisableMenu(){
        final int M=idx("navigation.maneuver");
        maneuver="left";
        MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);
        SlowBackground fake=new SlowBackground();
        MibrV3Session controller=session(fake,model);
        controller.open();
        check(controller.canWrite()&&fake.waiting!=null,"core snapshot ready before auxiliary GET");
        check(model.open(M)&&model.choose(3),"navigation choice accepted while engine reply is delayed");
        controller.commit(M);
        check(fake.sets==0&&fake.collided==0,"SET queued, no competing socket send");
        try{Thread.sleep(3400L);}catch(InterruptedException interrupted){
            throw new AssertionError("SLOW_BACKGROUND_TEST_INTERRUPTED");
        }
        check(fake.collided==0,"background contention must never start parallel requests");
        fake.finishWithError();
        check(fake.sets==1 && fake.reads==2 && controller.canWrite(),
              "failed background GET does not revoke durable core settings");
        check(model.draft(M)==null&&"top".equals(model.current(M)),
              "queued navigation SET completed with matching postcommit snapshot");
        controller.detach();
    }
    static void delayedViewAndDetachEpoch(){
        final int M=idx("navigation.maneuver");maneuver="left";
        MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);
        SlowBackground fake=new SlowBackground(true);MibrV3Session s=session(fake,model);s.open();
        // Drain the engine request first, then hold the subsequent VIEW_GET.
        fake.finishWithError();
        check("VIEW_GET".equals(fake.waitingVerb)&&s.canWrite(),"view GET admitted after engine completion");
        check(model.open(M)&&model.choose(3),"edit while view GET is pending");s.commit(M);
        check(fake.sets==0,"view GET serializes the queued core SET");
        s.detach();fake.finishWithError();
        check(fake.sets==0&&!s.canWrite(),"detached epoch drops late VIEW_GET completion and queued SET");
    }
    static class RefusingEngine extends Fake {
        int refusals;
        RefusingEngine(){super(true);}
        public synchronized boolean send(String rid,String verb,String[] names,String[] values,Listener cb){
            if("ENGINE_GET".equals(verb)){refusals++;return false;}
            return super.send(rid,verb,names,values,cb);
        }
    }
    static void refusalExhaustionIsLocal(){
        RefusingEngine fake=new RefusingEngine();MibrPopupEditorModel model=new MibrPopupEditorModel();
        model.setAvailable(true);MibrV3Session s=session(fake,model);s.open();
        long end=System.currentTimeMillis()+12000L;
        while(fake.refusals<40&&System.currentTimeMillis()<end){try{Thread.sleep(50L);}catch(InterruptedException e){throw new AssertionError(e);}}
        check(fake.refusals==40,"bounded local start refusal retries");
        check(s.canWrite(),"auxiliary refusal exhaustion does not disable core menu");
        s.detach();
    }
    static class FailedScale extends Fake {
        int failedGets;
        FailedScale(){super(true);}
        public synchronized boolean send(String rid,String verb,String[] names,String[] values,Listener cb){
            if("CAPABILITIES".equals(verb)){
                String response=reply(rid,new String[]{"snapshot","durable_set","test_override",
                    "presentation_refresh","reconnect","session_control","phase","scaling"},
                    new String[]{"1","1","0","0","0","0","NATIVE_PROFILE_GUARDED","1"});
                cb.onReply(MibrV3Protocol.parse(response,rid),null);return true;
            }
            if("SCALE_GET".equals(verb)){failedGets++;cb.onReply(null,"SCALE_TIMEOUT");return true;}
            return super.send(rid,verb,names,values,cb);
        }
    }
    static void failedScaleReadIsLocal(){
        final int M=idx("navigation.maneuver");maneuver="left";
        MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);
        FailedScale fake=new FailedScale();MibrV3Session s=session(fake,model);s.scaleRefresh();s.open();
        check(fake.failedGets==4,"each scale row failure is consumed without wedging FIFO");
        check(s.canWrite(),"failed SCALE_GET leaves core settings writable");
        check(model.open(M)&&model.choose(3),"core edit remains available after scale failure");s.commit(M);
        check(fake.sets==1&&s.canWrite(),"core SET still completes after scale GET failures");
        s.detach();
    }
    static void check(boolean b){check(b,"precondition");}
    public static void main(String[] args){wire();lifecycle();queue();slowBackgroundMustNotDisableMenu();delayedViewAndDetachEpoch();refusalExhaustionIsLocal();failedScaleReadIsLocal();System.out.println("MIBR_V3_JAVA_BINDING_HOST_PASS");}
}
