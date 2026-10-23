package de.mibr.hmi;

/** OEM UI-thread controller binding: completed gesture -> one durable MIBR/3 SET.
 * No TEMP writes, speculative display ACK, automatic reconnect or Unit restart.
 * All transport callbacks are returned through the supplied OEM dispatcher.
 */
final class MibrV3Session {
    public static interface Dispatcher {void post(Runnable action);}
    private final MibrV3Client client;
    private final MibrPopupEditorModel drafts;
    private final Dispatcher dispatcher;
    private final Runnable repaint;
    private String revision,message="Konfigurationsdienst nicht geprüft",lastRid;
    private boolean attached=true,busy,loaded,writable;
    private int epoch,sequence;
    // r11: per-key save queue. A tap while another SET is in flight is kept and
    // sent afterwards (latest wish wins); it is never silently dropped.
    private final boolean[] dirty=new boolean[MibrSettingsCatalog.KEYS.length];
    private final int[] attempts=new int[MibrSettingsCatalog.KEYS.length];
    private String failure;
    private final String prefix="h"+Long.toString(System.currentTimeMillis(),36);
    MibrV3Session(MibrV3Client client,MibrPopupEditorModel model,Dispatcher dispatch,Runnable repaint){
        if(client==null||model==null||dispatch==null||repaint==null)throw new IllegalArgumentException("V3_DEPENDENCIES");
        this.client=client;this.drafts=model;this.dispatcher=dispatch;this.repaint=repaint;
    }
    String status(){return message;}
    boolean canWrite(){return attached&&loaded&&writable&&!busy;}
    private String id(){return prefix+"_"+(++sequence);}
    private void changed(){if(attached)repaint.run();}
    private void relay(final int version,final Runnable action){
        dispatcher.post(new Runnable(){public void run(){if(attached&&epoch==version)action.run();}});
    }
    /** The client carries one request at a time; the SHOW_STATUS poller can briefly hold it.
     *  A busy client is retried for up to 3 s instead of locking the menu. */
    private void issue(final String rid,final String op,final String[] fields,final String[] values,
                       final MibrV3Client.Listener cb){
        if(client.send(rid,op,fields,values,cb))return;
        final int version=epoch;
        Thread retry=new Thread(new Runnable(){public void run(){
            for(int n=0;n<20;n++){
                try{Thread.sleep(150);}catch(InterruptedException e){return;}
                if(!attached||epoch!=version)return;
                if(client.send(rid,op,fields,values,cb))return;
            }
            relay(version,new Runnable(){public void run(){blocked("Dienst beschäftigt; Entwurf behalten");}});
        }});
        retry.setDaemon(true);
        retry.start();
    }
    private void blocked(String reason){busy=false;loaded=false;writable=false;message=reason;changed();}
    void open(){
        if(!attached)return;
        epoch++;loaded=false;writable=false;busy=true;message="Konfigurationsdienst prüfen";changed();
        final int version=epoch;final String request=id();
        issue(request,"HELLO",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    if(error!=null||!MibrV3Protocol.hello(f)){blocked("MIBR/3 nicht bestätigt");return;}
                    capabilities(version);
                }});
            }
        });
    }
    private void capabilities(final int version){
        issue(id(),"CAPABILITIES",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    if(error!=null||!MibrV3Protocol.capabilities(f)){blocked("Fähigkeiten unbestätigt");return;}
                    writable=MibrV3Protocol.durable(f);
                    read(version,null,null,null);
                }});
            }
        });
    }
    private void publish(MibrV3Protocol.Snapshot snap){
        for(int i=0;i<11;i++){
            int index=MibrV3Protocol.index(snap.keys[i]);
            drafts.readback(index,snap.values[i],"temp".equals(snap.sources[i]));
        }
        revision=snap.revision;loaded=true;busy=false;
        // A queued wish that the read-back already shows is done.
        for(int i=0;i<dirty.length;i++){
            String wish=drafts.draft(i);
            if(dirty[i]&&(wish==null||wish.equals(drafts.current(i)))){
                if(wish!=null)drafts.confirmPersistent(i,wish);
                dirty[i]=false;attempts[i]=0;
            }
        }
        message=failure!=null?failure:writable?"Bereit; Speicherung möglich, Stream-Wirkung unbestätigt":
            "Nur Lesen: dauerhafte Speicherung nicht freigeschaltet";
        failure=null;
        changed();
        engineRefresh();
        viewRefresh();
    }
    /** On SET, publish only one complete matching post-commit original-core revision. */
    private void read(final int version,final String committedKey,final String wanted,
                      final MibrV3Protocol.Commit receipt){
        issue(id(),"SNAPSHOT",new String[]{"scope"},new String[]{"ui"},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    final MibrV3Protocol.Snapshot snap;
                    try {
                        if(error!=null)throw new IllegalArgumentException("transport");
                        snap=MibrV3Protocol.snapshot(f);
                        if(receipt!=null){
                            if(!receipt.revision.equals(snap.revision))
                                throw new IllegalArgumentException("post-commit revision differs");
                            boolean match=false;
                            for(int i=0;i<11;i++)if(committedKey.equals(snap.keys[i])&&wanted.equals(snap.values[i]))match=true;
                            if(!match)throw new IllegalArgumentException("post-commit value differs");
                        }
                    }catch(Throwable t){
                        blocked(receipt==null?"Konsistenter Lesestand fehlt":
                            "Speicherung bestätigt; Nachlesung unklar, vor weiteren Änderungen neu laden");
                        return;
                    }
                    publish(snap);
                    if(receipt!=null){
                        // publish() confirmed the draft if it still equals the saved value;
                        // a newer tap keeps its key queued and is sent by pump().
                        if("RUNTIME_ONLY".equals(receipt.stored))
                            message="0".equals(wanted)?"CarPlay im Cockpit pausiert (bis Neustart)":
                                                       "CarPlay im Cockpit wieder aktiv";
                        else if("PENDING_PERSIST".equals(receipt.stored)){
                            // r23: "Angezeigt" only after the cockpit (GEN2) confirmed the SHOW.
                            message="Gesendet; warte auf Bestätigung vom Cockpit";
                            confirmShown(version);
                        }else
                            message="Dauerhaft gespeichert; "+receipt.activation+
                                ("UNCHANGED".equals(receipt.apply)?" unverändert":" Aktivierung ausstehend")+
                                "; Stream-Wirkung unbestätigt";
                        changed();
                    }
                    pump();
                }});
            }
        });
    }
    void commit(int index){
        if(!attached)return;
        if(!MibrPopupEditorModel.visible(index)||MibrSettingsCatalog.READ_ONLY[index]){
            message="Speichern nicht verfügbar; Entwurf behalten";changed();return;
        }
        final String key=MibrSettingsCatalog.KEYS[index];
        // carplay.enabled requires a reviewed owner session transition/confirmation
        // (native session_control=0).
        // r23: carplay.enabled is the runtime pause (broker answers stored=RUNTIME_ONLY).
        // Only the approved navigation presentation keys and the Wide/Voll view.
        if(!MibrPopupEditorModel.saveAllowed(index)){
            message="Speichern für diese Einstellung noch nicht freigegeben";changed();return;
        }
        if(drafts.draft(index)==null){message="Kein neuer Wert";changed();return;}
        dirty[index]=true;attempts[index]=0;
        if(loaded&&!writable){
            message="Nur Lesen: dauerhafte Speicherung nicht freigeschaltet";changed();return;
        }
        if(!canWrite()){message="Speichern wartet: "+key;changed();return;}
        pump();
    }
    /** Sends the next queued wish, one SET at a time. */
    private void pump(){
        if(!attached||!canWrite()||revision==null)return;
        for(int i=0;i<dirty.length;i++){
            if(!dirty[i])continue;
            String wanted=drafts.draft(i);
            if(wanted==null||wanted.equals(drafts.current(i))){
                if(wanted!=null)drafts.confirmPersistent(i,wanted);
                dirty[i]=false;continue;
            }
            String[] options=drafts.options(i);boolean permitted=false;
            for(int o=0;o<options.length;o++)if(wanted.equals(options[o]))permitted=true;
            if(!permitted){
                drafts.discardDraft(i);dirty[i]=false;
                message="Wert nicht freigegeben";changed();continue;
            }
            send(i,wanted);return;
        }
    }
    private void send(final int index,final String wanted){
        final String key=MibrSettingsCatalog.KEYS[index];
        confirmTicket++; // a new SET ends the previous cockpit confirmation poll
        busy=true;loaded=false;message="Dauerhaft speichern: "+key;changed();
        final int version=epoch;final String rid=id();lastRid=rid;
        issue(rid,"SET",new String[]{"key","value","expected_revision","activation","request_id"},
            new String[]{key,wanted,revision,"AUTO",rid},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    if(error!=null){
                        // The native service may have committed before the socket failed.
                        // Resolve the ORIGINAL request ID; never blindly replay SET.
                        reconcile(version,rid,key,wanted);return;
                    }
                    if(f==null||!f.ok()){
                        String reason=f==null?"UNCONFIRMED":f.error;
                        // A stale revision is retried after a fresh read; anything else
                        // drops the wish so the row shows the saved value again.
                        if(!"STALE_REVISION".equals(reason)||++attempts[index]>2){
                            drafts.discardDraft(index);dirty[index]=false;attempts[index]=0;
                        }
                        failure="Nicht gespeichert: "+reason;
                        read(version,null,null,null);
                        return;
                    }
                    final MibrV3Protocol.Commit receipt;
                    try{receipt=MibrV3Protocol.commit(f,key,wanted);}
                    catch(Throwable t){blocked("Speicherquittung ungültig; Zustand unklar");return;}
                    if("0".equals(receipt.materialized)){
                        blocked("Dauerhaft gespeichert; TEMP-Materialisierung ausstehend, neu laden");
                        return;
                    }
                    read(version,key,wanted,receipt);
                }});
            }
        });
    }
    private void reconcile(final int version,final String rid,final String key,final String wanted){
        issue(id(),"REQUEST_STATUS",new String[]{"request_id"},new String[]{rid},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    if(error!=null||f==null||!f.ok()||
                       !rid.equals(f.get("original_request_id"))||
                       !"VERIFIED".equals(f.get("stored"))){
                        blocked("SET-Ergebnis unklar; nicht erneut senden, Zustand neu prüfen");
                        return;
                    }
                    if(!"1".equals(f.get("materialized"))){
                        blocked("Dauerhaft gespeichert; Materialisierung ausstehend, neu laden");return;
                    }
                    // REQUEST_STATUS has no revision; never fabricate one or ACK.
                    // A fresh SNAPSHOT supplies it and confirms the queued wish.
                    read(version,null,null,null);
                }});
            }
        });
    }
    /** Polls SHOW_STATUS until GEN2 reports the completed SHOW (or gives up); the text claims
     *  "im Cockpit" only for SHOWN. Never blocks the OEM thread, never touches a running SET. */
    private volatile int confirmTicket;
    private void confirmShown(final int version){
        final int ticket=++confirmTicket;
        Thread poller=new Thread(new Runnable(){public void run(){
            for(int n=0;n<18;n++){
                try{Thread.sleep(700);}catch(InterruptedException e){return;}
                if(!attached||epoch!=version||ticket!=confirmTicket)return;
                if(busy)continue;
                final String rid=prefix+"_c"+ticket+"_"+n;
                boolean sent=client.send(rid,"SHOW_STATUS",new String[0],new String[0],new MibrV3Client.Listener(){
                    public void onReply(final MibrV3Protocol.Frame f,final String error){
                        relay(version,new Runnable(){public void run(){
                            if(ticket!=confirmTicket||busy)return;
                            String state=error!=null?"UNKNOWN":MibrV3Protocol.showState(f);
                            String text=null;
                            if("SHOWN".equals(state))text="Im Cockpit bestätigt; wird in Kürze dauerhaft gesichert";
                            else if("FAILED".equals(state))text="Cockpit hat die Anzeige nicht bestätigt (Fehler)";
                            else if("NO_SESSION".equals(state))text="Gespeichert; wird bei der nächsten CarPlay-Verbindung angezeigt";
                            else if("TIMEOUT".equals(state))text="Keine Bestätigung vom Cockpit; Wert ist gesetzt";
                            if(text!=null){confirmTicket++;message=text;changed();}
                        }});
                    }
                });
                if(!sent)continue;
            }
        }});
        poller.setDaemon(true);
        poller.start();
    }
    /** r46: read the engine type once per menu session (after the settings read-back). */
    private boolean engineAsked;
    void engineRefresh(){
        if(!attached||engineAsked)return;
        engineAsked=true;
        engineCall("ENGINE_GET",null);
    }
    /** The engine type chosen in the dropdown "Motorart". One request at a time. */
    void engineSet(String value){
        if(!attached||MibrEngineState.busy()||MibrEngineState.index(value)<0)return;
        engineCall("ENGINE_SET",value);
    }
    private void engineCall(final String op,String value){
        final int version=epoch;
        MibrEngineState.busy(true);changed();
        issue(id(),op,value==null?new String[0]:new String[]{"value"},value==null?new String[0]:new String[]{value},
              new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    String[] e=error!=null?null:MibrV3Protocol.engine(f);
                    if(e==null)MibrEngineState.failed(true);
                    else MibrEngineState.confirmed(e[0],e[1],e[2]);
                    changed();
                }});
            }
        });
    }
    /** r55: read the view follow state once per menu session. */
    private boolean viewAsked;
    void viewRefresh(){
        if(!attached||viewAsked)return;
        viewAsked=true;
        viewCall("VIEW_GET",null,null);
    }
    /** One row of "Bildbereich folgt Cockpit-Ansicht" changed in a dropdown (name = wire name of the row). */
    void viewSet(String name,String value){
        if(!attached||MibrViewState.busy()||MibrViewState.rowOf(name)<0||value==null||value.length()!=1)return;
        viewCall("VIEW_SET",name,value);
    }
    private void viewCall(final String op,String name,String value){
        final int version=epoch;
        MibrViewState.busy(true);changed();
        issue(id(),op,name==null?new String[0]:new String[]{"name","value"},
              name==null?new String[0]:new String[]{name,value},
              new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    String[] v=error!=null?null:MibrV3Protocol.view(f);
                    if(v==null)MibrViewState.failed(true);
                    else MibrViewState.confirmed(v);
                    changed();
                }});
            }
        });
    }
    void detach(){
        attached=false;epoch++;busy=false;loaded=false;writable=false;
        for(int i=0;i<dirty.length;i++){dirty[i]=false;attempts[i]=0;}
    }
}
