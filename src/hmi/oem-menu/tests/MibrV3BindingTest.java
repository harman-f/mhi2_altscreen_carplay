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
        // Native scope=ui wire order (Issue #103), written out literally: the r8
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
                check("navigation.maneuver".equals(values[0])&&"top".equals(values[1]),"gesture payload");
                check(revision.equals(values[2])&&"AUTO".equals(values[3])&&rid.equals(values[4]),"CAS/request id");
                maneuver="top";revision="24";
                if(dropSet){cb.onReply(null,"TRANSPORT_OR_PROTOCOL_UNCONFIRMED");return true;}
                response=reply(rid,new String[]{"stored","apply","active","activation","revision","materialized"},
                    new String[]{"VERIFIED","PENDING","UNKNOWN","PRESENTATION",revision,"1"});
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
            new String[]{"VERIFIED","PENDING","UNKNOWN","RECONNECT","24","1"}),"set");
        check("24".equals(MibrV3Protocol.commit(c,"maxFPS","25").revision),"verified receipt");
        rejects("false-stored",new Runnable(){public void run(){
            MibrV3Protocol.commit(MibrV3Protocol.parse(reply("set",new String[]{"stored","apply","active","activation","revision","materialized"},
                new String[]{"UNCONFIRMED","PENDING","UNKNOWN","RECONNECT","24","1"}),"set"),"maxFPS","25");}});
    }
    static void lifecycle(){
        // r10: only the navigation presentation keys are saved (+ applied live).
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
        check(fake.sets==1,"runtime actions and maxFPS must not be SET in r10");
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
    static void check(boolean b){check(b,"precondition");}
    public static void main(String[] args){wire();lifecycle();queue();System.out.println("MIBR_V3_JAVA_BINDING_HOST_PASS");}
}
