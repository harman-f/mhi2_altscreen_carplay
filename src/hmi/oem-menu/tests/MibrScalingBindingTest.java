package de.mibr.hmi;

/** Synthetic MIBR/3 contract test: CAS stores desired values; stream effect remains UNKNOWN. */
public final class MibrScalingBindingTest {
    static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
    static class Fake extends MibrV3Client {
        String main="AUTO",cluster="AUTO",physical="BASE",mainPhysical="BASE",mainStored="DEFAULT",clusterStored="DEFAULT",physicalStored="DEFAULT",mainPhysicalStored="DEFAULT",mainPending="0",clusterPending="0",physicalPending="0",mainPhysicalPending="0";
        String revision="0";int gets,sets;boolean staleNext,loseNextSet,enabled=true,deferGets;
        String deferredResponse,deferredRid;Listener deferredListener;
        Fake(){super(28743,"/unread/host/fixture");}
        public synchronized boolean send(String rid,String verb,String[] names,String[] values,Listener cb){
            String response;
            if("HELLO".equals(verb))response=MibrV3BindingTest.reply(rid,new String[]{"version","schema","registry_keys","phase"},new String[]{"MIBR/3","2","48","NATIVE_PROFILE_GUARDED"});
            else if("CAPABILITIES".equals(verb))response=MibrV3BindingTest.reply(rid,new String[]{"snapshot","durable_set","test_override","presentation_refresh","reconnect","session_control","phase","scaling"},new String[]{"1","1","0","0","0","0","NATIVE_PROFILE_GUARDED",enabled?"1":"0"});
            else if("SNAPSHOT".equals(verb))response=MibrV3BindingTest.snapshot(rid,"23","30");
            else if("ENGINE_GET".equals(verb)||"ENGINE_SET".equals(verb))response=MibrV3BindingTest.reply(rid,new String[]{"engine","announced","pending"},new String[]{"gas","gas","0"});
            else if("VIEW_GET".equals(verb)||"VIEW_SET".equals(verb))response=MibrV3BindingTest.reply(rid,new String[]{"follow","sport","m0","m1","m4","rs","pos"},new String[]{"0","1","1","0","2","0","0"});
            else if("SCALE_GET".equals(verb)){gets++;response=scaling(rid,values[0]);if(deferGets){deferredResponse=response;deferredRid=rid;deferredListener=cb;return true;}}
            else if("SCALE_SET".equals(verb)){
                sets++;String id=values[0],value=values[1],old=values[2];
                check(rid.equals(values[3]),"request id echoed into SET");
                if(staleNext){staleNext=false;main="85";mainStored="VERIFIED";mainPending="1";revision=next(revision);response="MIBR/3 "+rid+" ERR STALE_REVISION\n";}
                else{
                    check(revision.equals(old),"CAS uses one native revision shared by both display keys");
                    if("scaling.main.zoomFactor".equals(id)){main=value;mainStored="VERIFIED";mainPending="1";}
                    else if("scaling.cluster.zoomFactor".equals(id)){cluster=value;clusterStored="VERIFIED";clusterPending="1";}
                    else if("scaling.cluster.physicalSize".equals(id)){physical=value;physicalStored="VERIFIED";physicalPending="1";}
                    else if("scaling.main.physicalSize".equals(id)){mainPhysical=value;mainPhysicalStored="VERIFIED";mainPhysicalPending="1";}
                    else throw new AssertionError("unknown scale id "+id);
                    revision=next(revision);
                    response=scaling(rid,id);
                    if(loseNextSet){loseNextSet=false;cb.onReply(null,"LOST_REPLY");return true;}
                }
            }else throw new AssertionError("unexpected "+verb);
            cb.onReply(MibrV3Protocol.parse(response,rid),null);return true;
        }
        void completeGet(){Listener listener=deferredListener;String rid=deferredRid,response=deferredResponse;deferredListener=null;deferredRid=deferredResponse=null;if(listener==null)throw new AssertionError("no deferred GET");listener.onReply(MibrV3Protocol.parse(response,rid),null);}
        static String next(String s){return Long.toString(Long.parseLong(s)+1);}
        String scaling(String rid,String id){
            boolean primary="scaling.main.zoomFactor".equals(id),clusterZoom="scaling.cluster.zoomFactor".equals(id),mainSize="scaling.main.physicalSize".equals(id);
            String value=primary?main:clusterZoom?cluster:mainSize?mainPhysical:physical;
            String stored=primary?mainStored:clusterZoom?clusterStored:mainSize?mainPhysicalStored:physicalStored,pending=primary?mainPending:clusterZoom?clusterPending:mainSize?mainPhysicalPending:physicalPending;
            return MibrV3BindingTest.reply(rid,new String[]{"id","desired","advertised","effective","apply","stored","pending","writer","revision","advertised_scope"},new String[]{id,value,"UNKNOWN","UNKNOWN","RECONNECT",stored,pending,enabled?"ENABLED":"DISABLED",revision,"UNKNOWN"});
        }
    }
    static MibrV3Session session(Fake f,MibrPopupEditorModel d){return new MibrV3Session(f,d,new MibrV3Session.Dispatcher(){public void post(Runnable r){r.run();}},new Runnable(){public void run(){}});}
    public static void main(String[] args){
        MibrI18n.forced="en_US";
        Fake fake=new Fake();MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);MibrV3Session s=session(fake,model);s.open();
        check(s.canWrite(),"base settings session remains ready");s.scaleRefresh();
        check(fake.gets==4&&"AUTO".equals(model.current(MibrPopupEditorModel.SCALE_MAIN))&&"AUTO".equals(model.current(MibrPopupEditorModel.SCALE_CLUSTER))&&"BASE".equals(model.current(MibrPopupEditorModel.SCALE_PHYSICAL))&&"BASE".equals(model.current(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL)),"four independent scaling GETs default both physical sizes to BASE");
        check("DEFAULT".equals(MibrScalingState.stored(MibrPopupEditorModel.SCALE_MAIN))&&"0".equals(MibrScalingState.pending(MibrPopupEditorModel.SCALE_MAIN)),"compiled automatic default readback");
        check("UNKNOWN".equals(MibrScalingState.effective(MibrPopupEditorModel.SCALE_MAIN))&&MibrScalingState.status(MibrPopupEditorModel.SCALE_MAIN).indexOf("effect unknown")>=0,"no effective-stream claim");
        check(model.open(MibrPopupEditorModel.SCALE_MAIN)&&model.options(MibrPopupEditorModel.SCALE_MAIN).length==6&&model.selectedOption(MibrPopupEditorModel.SCALE_MAIN)==0,"AUTO is first selectable value");
        fake.deferGets=true;fake.main="85";fake.mainStored="VERIFIED";fake.mainPending="1";fake.revision="1";
        s.scaleRefresh();check(fake.gets==5,"page re-entry starts one fresh main GET");
        s.scaleRefresh();check(fake.gets==5,"duplicate render while four-row refresh is in flight does not send another request");
        fake.completeGet();check(fake.gets==6,"first readback starts exactly one cluster GET");
        s.scaleRefresh();check(fake.gets==6,"duplicate render during cluster GET remains bounded");
        fake.completeGet();check(fake.gets==7,"cluster GET starts physical GET");fake.completeGet();check(fake.gets==8,"physical GET starts main physical GET");fake.completeGet();fake.deferGets=false;
        check("85".equals(model.current(MibrPopupEditorModel.SCALE_MAIN))&&"1".equals(MibrScalingState.revision(MibrPopupEditorModel.SCALE_CLUSTER)),"page re-entry refreshes both independent rows with shared revision");
        check(model.open(MibrPopupEditorModel.SCALE_MAIN)&&model.options(MibrPopupEditorModel.SCALE_MAIN).length==6&&model.selectedOption(MibrPopupEditorModel.SCALE_MAIN)==2,"refreshed current value is selected without changing the option domain");
        check(model.choose(3)&&"100".equals(model.draft(MibrPopupEditorModel.SCALE_MAIN)),"explicit 100 draft is distinct from AUTO");
        s.scaleSet(MibrPopupEditorModel.SCALE_MAIN,model.draft(MibrPopupEditorModel.SCALE_MAIN));model.discardDraft(MibrPopupEditorModel.SCALE_MAIN);
        check(MibrScalingState.writable(MibrPopupEditorModel.SCALE_MAIN),"validated enabled writer readback enables this display dropdown");
        check(fake.sets==1&&"100".equals(model.current(MibrPopupEditorModel.SCALE_MAIN))&&"VERIFIED".equals(MibrScalingState.stored(MibrPopupEditorModel.SCALE_MAIN))&&"1".equals(MibrScalingState.pending(MibrPopupEditorModel.SCALE_MAIN)),"CAS setter stores requested value pending reconnect");
        check(fake.gets==12&&MibrScalingState.revision(MibrPopupEditorModel.SCALE_CLUSTER).equals(fake.revision),"SET completion refreshes all four rows to the global revision");
        check("UNKNOWN".equals(MibrScalingState.advertised(MibrPopupEditorModel.SCALE_MAIN))&&"UNKNOWN".equals(MibrScalingState.effective(MibrPopupEditorModel.SCALE_MAIN)),"stored selection is not AirPlay acceptance");
        check(MibrScalingState.uiMessage(MibrPopupEditorModel.SCALE_MAIN)==null, "healthy value UI has no persistent technical status");
        fake.staleNext=true;s.scaleSet(MibrPopupEditorModel.SCALE_MAIN,"85");
        check(fake.sets==2&&fake.gets==16&&"Value changed; choose again".equals(MibrScalingState.status(MibrPopupEditorModel.SCALE_MAIN)),"stale CAS refreshes the shared scaling state without replay");
        check("Value changed; choose again".equals(MibrScalingState.uiMessage(MibrPopupEditorModel.SCALE_MAIN)), "stale write remains visible in normal UI");
        check(MibrScalingState.writable(MibrPopupEditorModel.SCALE_MAIN),"fresh readback restores enabled writer after stale notice");
        fake.loseNextSet=true;s.scaleSet(MibrPopupEditorModel.SCALE_MAIN,"70");
        check(fake.sets==3&&fake.gets==20&&"70".equals(model.current(MibrPopupEditorModel.SCALE_MAIN))&&"VERIFIED".equals(MibrScalingState.stored(MibrPopupEditorModel.SCALE_MAIN))&&"UNKNOWN".equals(MibrScalingState.effective(MibrPopupEditorModel.SCALE_MAIN)),"lost SET reply reconciles committed value with GET and never replays");
        s.scaleSet(MibrPopupEditorModel.SCALE_CLUSTER,"150");
        check(fake.sets==4&&fake.gets==24&&"150".equals(model.current(MibrPopupEditorModel.SCALE_CLUSTER))&&MibrScalingState.revision(MibrPopupEditorModel.SCALE_MAIN).equals(fake.revision),"switching display uses refreshed shared revision without unnecessary STALE_REVISION");
        check(model.options(MibrPopupEditorModel.SCALE_PHYSICAL).length==4&&
              "BASE".equals(model.options(MibrPopupEditorModel.SCALE_PHYSICAL)[0])&&
              "P50".equals(model.options(MibrPopupEditorModel.SCALE_PHYSICAL)[3]),"physical preset enum");
        s.scaleSet(MibrPopupEditorModel.SCALE_PHYSICAL,"P30");
        check(fake.sets==5&&fake.gets==28&&"P30".equals(model.current(MibrPopupEditorModel.SCALE_PHYSICAL))&&
              "70".equals(model.current(MibrPopupEditorModel.SCALE_MAIN))&&
              "150".equals(model.current(MibrPopupEditorModel.SCALE_CLUSTER)),"physical CAS keeps both zoom values and requests reconnect");
        check(model.options(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL).length==4&&"Original".equals(model.label(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL,"BASE")),"main physical size has BASE label without invented dimensions");
        s.scaleSet(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL,"P50");
        check(fake.sets==6&&fake.gets==32&&"P50".equals(model.current(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL))&&"P30".equals(model.current(MibrPopupEditorModel.SCALE_PHYSICAL))&&"70".equals(model.current(MibrPopupEditorModel.SCALE_MAIN))&&"150".equals(model.current(MibrPopupEditorModel.SCALE_CLUSTER)),"main physical SET is independent of both zooms and VC physical size");
        s.detach();
        Fake noWriter=new Fake();noWriter.enabled=false;MibrPopupEditorModel disabled=new MibrPopupEditorModel();disabled.setAvailable(true);MibrV3Session ro=session(noWriter,disabled);ro.open();ro.scaleRefresh();
        check(!MibrScalingState.writable(MibrPopupEditorModel.SCALE_MAIN),"DISABLED writer readback keeps dropdown unavailable");
        ro.scaleSet(MibrPopupEditorModel.SCALE_MAIN,"70");check(noWriter.sets==0,"no write when broker capability is absent");ro.detach();
        MibrScalingState.reset();
        MibrScalingState.readback(MibrPopupEditorModel.SCALE_CLUSTER,"AUTO","UNKNOWN","UNKNOWN","UNKNOWN","DEFAULT","0","RECONNECT","ENABLED","7");
        check(MibrScalingState.writable(MibrPopupEditorModel.SCALE_CLUSTER),"cluster writer capability is independent");
        MibrScalingState.readback(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL,"P20","P20","UNKNOWN","HISTORICAL","VERIFIED","1","RECONNECT","ENABLED","8");
        check(MibrScalingState.status(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL).indexOf("+20 %")>=0&&MibrScalingState.status(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL).indexOf("mm")<0,"main physical status never invents absolute dimensions");
        MibrScalingState.failed(MibrPopupEditorModel.SCALE_CLUSTER,"read failed");
        check(!MibrScalingState.writable(MibrPopupEditorModel.SCALE_CLUSTER)&&MibrScalingState.revision(MibrPopupEditorModel.SCALE_CLUSTER)==null,"failed readback clears writer and CAS revision");
        check("read failed".equals(MibrScalingState.uiMessage(MibrPopupEditorModel.SCALE_CLUSTER)), "readback failure stays visible");
        boolean invalid=false;try{MibrScalingState.readback(MibrPopupEditorModel.SCALE_CLUSTER,"AUTO","UNKNOWN","100","UNKNOWN","DEFAULT","0","RECONNECT","ENABLED","8");}catch(IllegalArgumentException expected){invalid=true;}
        check(invalid,"effective stream value cannot be inferred from storage or advertised data");
        System.out.println("MIBR_SCALING_BINDING_PASS GET=32 SET=6 four_independent_rows=1 main_physical=P50 stale_no_replay=1 lost_reply_reconciled=1");
    }
}
