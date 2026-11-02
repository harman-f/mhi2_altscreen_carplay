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
    private boolean attached=true,busy,loaded,writable,scalingAvailable,scalingRefreshInFlight,scalingSetInFlight,scalingRefreshPending;
    private int epoch,sequence;
    private boolean languageAvailable,languageAsked,languagePending,languageSetInFlight;
    private boolean gpsAvailable,gpsAsked,gpsSetInFlight;
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
    String status(){return MibrI18n.localize(message);}
    boolean canWrite(){return attached&&loaded&&writable&&!busy;}
    private String id(){return prefix+"_"+(++sequence);}
    private void changed(){if(attached)repaint.run();}
    private void relay(final int version,final Runnable action){
        dispatcher.post(new Runnable(){public void run(){if(attached&&epoch==version)action.run();}});
    }
    /*
     * One serialized FIFO for every MIBR/3 request owned by this menu session.
     * The old issue() spawned a retry thread for *each* concurrent background
     * GET and globally disabled the entire menu after 3 seconds. A new Scaling
     * row could therefore disable ETA, map style and view selection even while
     * CarPlay video continued to stream.
     *
     * Only the OEM UI dispatcher mutates this queue; socket completions return
     * to it before releasing the slot. A refusal to *start* an operation is
     * retried locally and is NEVER interpreted as an ambiguous committed SET.
     */
    private static final int MAX_WIRE_QUEUE=32, MAX_START_RETRIES=40;
    private final java.util.Vector wireQueue=new java.util.Vector();
    private boolean wireBusy,wireDraining,wireRetryScheduled;
    private static final class QueuedCall {
        final String rid,op;
        final String[] fields,values;
        final MibrV3Client.Listener callback;
        final int version;
        int refusals;
        QueuedCall(String r,String o,String[] f,String[] v,MibrV3Client.Listener c,int e){
            rid=r;op=o;fields=f;values=v;callback=c;version=e;
        }
    }
    private void resetWireQueue(){
        wireQueue.removeAllElements();
        wireBusy=false;
        wireRetryScheduled=false;
    }
    private void issue(final String rid,final String op,final String[] fields,final String[] values,
                       final MibrV3Client.Listener cb){
        if(!attached)return;
        if(wireQueue.size()>=MAX_WIRE_QUEUE){
            // One request is rejected; never revoke unrelated menu capabilities.
            cb.onReply(null,"QUEUE_LIMIT_UNSENT");
            return;
        }
        wireQueue.addElement(new QueuedCall(rid,op,fields,values,cb,epoch));
        drainWire();
    }
    private void retryWire(final int version){
        if(wireRetryScheduled)return;
        wireRetryScheduled=true;
        Thread worker=new Thread(new Runnable(){public void run(){
            try{Thread.sleep(150);}catch(InterruptedException ignored){return;}
            relay(version,new Runnable(){public void run(){
                wireRetryScheduled=false;
                drainWire();
            }});
        }},"MibrV3QueueRetry");
        worker.setDaemon(true);
        worker.start();
    }
    private void drainWire(){
        if(wireDraining||wireBusy||!attached)return;
        wireDraining=true;
        try {
            while(!wireBusy && wireQueue.size()>0 && attached){
                final QueuedCall call=(QueuedCall)wireQueue.elementAt(0);
                if(call.version!=epoch){wireQueue.removeElementAt(0);continue;}
                wireBusy=true; // claim before send: host fakes may call back synchronously
                boolean accepted=client.send(call.rid,call.op,call.fields,call.values,
                    new MibrV3Client.Listener(){
                        public void onReply(final MibrV3Protocol.Frame frame,final String error){
                            relay(call.version,new Runnable(){public void run(){
                                if(wireQueue.size()==0 || wireQueue.elementAt(0)!=call)return;
                                wireQueue.removeElementAt(0);
                                wireBusy=false;
                                try {call.callback.onReply(frame,error);}
                                finally {drainWire();}
                            }});
                        }
                    });
                if(accepted){
                    if(wireBusy)return; // asynchronous request is still in flight
                    continue; // synchronous host callback already released the slot
                }
                wireBusy=false;
                if(++call.refusals>=MAX_START_RETRIES){
                    wireQueue.removeElementAt(0);
                    // The operation was never sent: fail only its own callback.
                    call.callback.onReply(null,"TRANSPORT_BUSY_UNSENT");
                    continue;
                }
                retryWire(call.version);
                return;
            }
        }finally{wireDraining=false;}
    }
    private void blocked(String reason){MibrI18n.menuFailed(MibrI18n.pick("Sprachdienst nicht verfügbar","Language service unavailable"));busy=false;loaded=false;writable=false;scalingAvailable=false;scalingRefreshInFlight=false;scalingSetInFlight=false;scalingRefreshPending=false;MibrScalingState.failed(MibrPopupEditorModel.SCALE_MAIN,reason);MibrScalingState.failed(MibrPopupEditorModel.SCALE_CLUSTER,reason);MibrScalingState.failed(MibrPopupEditorModel.SCALE_PHYSICAL,reason);MibrScalingState.failed(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL,reason);message=reason;changed();}
    private static void resetSwitch(MibrDurableSwitch sw){sw.available=false;sw.asked=false;sw.setInFlight=false;sw.loading();}
    void open(){
        if(!attached)return;
        epoch++;resetWireQueue();languageAvailable=false;languageAsked=false;languagePending=false;languageSetInFlight=false;
        for(int i=0;i<MibrDurableSwitch.ALL.length;i++)resetSwitch(MibrDurableSwitch.ALL[i]);
        MibrI18n.menuLoading();MibrGpsDemoState.reset();loaded=false;writable=false;scalingAvailable=false;scalingRefreshInFlight=false;scalingSetInFlight=false;MibrScalingState.reset();busy=true;message="Konfigurationsdienst prüfen";changed();
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
                    scalingAvailable="1".equals(f.get("scaling"));
                    languageAvailable="1".equals(f.get("menu_language"));
                    for(int i=0;i<MibrDurableSwitch.ALL.length;i++)
                        MibrDurableSwitch.ALL[i].available="1".equals(f.get(MibrDurableSwitch.ALL[i].capability));
                    gpsAvailable="1".equals(f.get("gps_demo"));
                    MibrScalingState.reset();
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
        if(scalingRefreshPending)scaleRefresh();
        if(!languageAsked)menuLanguageRefresh();
        for(int i=0;i<MibrDurableSwitch.ALL.length;i++)
            if(!MibrDurableSwitch.ALL[i].asked)switchRefresh(MibrDurableSwitch.ALL[i],MibrPopupEditorModel.keyOf(MibrDurableSwitch.ALL[i]));
        if(!gpsAsked)gpsDemoRefresh();
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
                            if("RECONNECT".equals(receipt.activation)){
                                message=MibrI18n.pick("Gespeichert; wird bei der nächsten CarPlay-Verbindung übertragen",
                                                     "Saved; will be sent on the next CarPlay connection");
                            }else{
                                // r23: "Angezeigt" only after the cockpit (GEN2) confirmed the SHOW.
                                message="Gesendet; warte auf Bestätigung vom Cockpit";
                                confirmShown(version);
                            }
                        }else if("UNIT_REBOOT".equals(receipt.activation))
                            message=MibrI18n.pick("Gespeichert; Unit-Neustart erforderlich",
                                                 "Saved; unit restart required");
                        else
                            message="RECEIPT:"+receipt.activation+":"+receipt.apply;
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
                // Diagnostic status is opportunistic and lower priority than
                // user SET/SNAPSHOT. Never bypass the session's single FIFO.
                relay(version,new Runnable(){public void run(){
                    if(ticket!=confirmTicket||busy||wireBusy||wireQueue.size()>0)return;
                    issue(rid,"SHOW_STATUS",new String[0],new String[0],new MibrV3Client.Listener(){
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
                }});
            }
        }});
        poller.setDaemon(true);
        poller.start();
    }

    /** Read current DIO/iAP2 owner state, not a guessed static UI value. */
    void gpsDemoRefresh(){
        if(!attached||gpsSetInFlight)return;
        if(!loaded)return;
        gpsAsked=true;
        if(!gpsAvailable){
            MibrGpsDemoState.error(MibrI18n.pick("GPS-Demo nicht verfügbar","GPS demo unavailable"));
            changed();return;
        }
        final int version=epoch;
        issue(id(),"GPS_DEMO_GET",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                if(error!=null){
                    MibrGpsDemoState.error(MibrI18n.pick("GPS-Dienst nicht erreichbar","GPS service unavailable"));
                }else try{
                    String[] state=MibrV3Protocol.gpsDemo(f);
                    MibrGpsDemoState.readback(state[0],state[1],state[2],state[3],true);
                    drafts.readback(MibrPopupEditorModel.GPS_DEMO,state[0]);
                }catch(Throwable failure){
                    MibrGpsDemoState.error(MibrI18n.pick("GPS-Rückmeldung ungültig","Invalid GPS state"));
                }
                changed();
            }});}
        });
    }
    /** Mode switch is immediate in the current original iAP2 session.
     *  Never treats an owner's ACK as proof of Apple Maps location rendering. */
    void gpsDemoSet(final String selected){
        final String currentEpoch=MibrGpsDemoState.epoch();
        if(!attached||gpsSetInFlight||!gpsAvailable||!MibrGpsDemoState.writable()||
           !MibrGpsDemoState.valid(selected)||currentEpoch==null)return;
        gpsSetInFlight=true;MibrGpsDemoState.saving();changed();
        final int version=epoch;final String rid=id();
        issue(rid,"GPS_DEMO_SET",new String[]{"value","expected_epoch","request_id"},
            new String[]{selected,currentEpoch,rid},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                gpsSetInFlight=false;
                if(error!=null||f==null||!f.ok()){
                    MibrGpsDemoState.error(MibrI18n.pick("GPS-Umschaltung nicht bestätigt","GPS switch unconfirmed"));
                }else try{
                    String[] state=MibrV3Protocol.gpsDemo(f);
                    if(!selected.equals(state[0])||!currentEpoch.equals(state[1]))
                        throw new IllegalArgumentException("GPS_DEMO_SET_NOT_MATCHED");
                    MibrGpsDemoState.readback(state[0],state[1],state[2],state[3],true);
                    drafts.readback(MibrPopupEditorModel.GPS_DEMO,state[0]);
                }catch(Throwable failure){
                    MibrGpsDemoState.error(MibrI18n.pick("GPS-Rückmeldung ungültig","Invalid GPS response"));
                }
                gpsDemoRefresh();changed();
            }});}
        });
    }

    /** Readback of a durable switch (broker-owned file); key = its row in the popup editor model. */
    void switchRefresh(final MibrDurableSwitch sw,final int key){
        if(!attached||sw.setInFlight||!loaded)return;
        sw.asked=true;
        if(!sw.available){sw.failed(MibrI18n.pick("Dienst nicht verfügbar","Service unavailable"));changed();return;}
        final int version=epoch;
        issue(id(),sw.verb+"_GET",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                if(error!=null)sw.failed(MibrI18n.pick("Nicht lesbar","Unable to read"));
                else try{
                    String[] reply=MibrV3Protocol.durableSwitch(f,sw);
                    sw.readback(reply[0],reply[1],"ENABLED".equals(reply[2]));
                    drafts.readback(key,reply[0]);
                }catch(Throwable failure){sw.failed(MibrI18n.pick("Antwort ungültig","Invalid response"));}
                changed();
            }});}
        });
    }
    void switchSet(final MibrDurableSwitch sw,final int key,final String wanted){
        final String revision=sw.revision();
        if(!attached||sw.setInFlight||!sw.available||!sw.writable()||
           !sw.valid(wanted)||revision==null)return;
        if(wanted.equals(sw.value()))return;
        sw.setInFlight=true;sw.saving();changed();
        final int version=epoch,runtimeSequence=++sequence;
        final String rid=prefix+"_"+sw.capability+"_"+runtimeSequence;
        issue(rid,sw.verb+"_SET",new String[]{"value","expected_revision","request_id"},
            new String[]{wanted,revision,rid},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                sw.setInFlight=false;
                if(error!=null || f==null || !f.ok()){
                    sw.failed(MibrI18n.pick("Speicherung unbestätigt","Save not confirmed"));
                    switchRefresh(sw,key);return;
                }
                try{
                    String[] reply=MibrV3Protocol.durableSwitch(f,sw);
                    if(!wanted.equals(reply[0])||!"VERIFIED".equals(reply[3]))
                        throw new IllegalArgumentException(sw.verb+"_SAVE_UNVERIFIED");
                    sw.readback(reply[0],reply[1],"ENABLED".equals(reply[2]));
                    drafts.readback(key,reply[0]);
                }catch(Throwable bad){
                    sw.failed(MibrI18n.pick("Speicherung unbestätigt","Save not confirmed"));
                }
                switchRefresh(sw,key);changed();
            }});}
        });
    }
    void durableSet(int key,String wanted){
        MibrDurableSwitch sw=MibrPopupEditorModel.durable(key);
        if(MibrPopupEditorModel.isSafe(key)){
            String now=sw.revision()!=null?sw.value():sw.persistedValue();
            switchSet(sw,MibrPopupEditorModel.safeBase(key),
                MibrSafeArea.step(now,sw.defaultValue(),MibrPopupEditorModel.safeField(key),wanted));
        }else switchSet(sw,key,wanted);
    }

    /** Independent MIBR-only menu locale readback; no vehicle language setter. */
    void menuLanguageRefresh(){
        if(!attached||languageSetInFlight)return;
        if(!loaded){languagePending=true;return;}
        languagePending=false;languageAsked=true;
        if(!languageAvailable){MibrI18n.menuFailed(MibrI18n.pick("Sprachdienst nicht verfügbar","Language service unavailable"));changed();return;}
        final int version=epoch;
        issue(id(),"MENU_LANGUAGE_GET",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                if(error!=null)MibrI18n.menuFailed(MibrI18n.pick("Sprachwahl nicht lesbar","Unable to read language"));
                else try{
                    String[] reply=MibrV3Protocol.menuLanguage(f);
                    MibrI18n.menuReadback(reply[0],reply[1],"ENABLED".equals(reply[2]));
                    drafts.readback(MibrPopupEditorModel.MENU_LANGUAGE,reply[0]);
                }catch(Throwable failure){MibrI18n.menuFailed(MibrI18n.pick("Sprachwahl ungültig","Invalid language response"));}
                changed();
            }});}
        });
    }
    void menuLanguageSet(final String wanted){
        if(wanted!=null&&wanted.equals(MibrI18n.menuOverride()))return;
        final String revision=MibrI18n.menuRevision();
        if(!attached||languageSetInFlight||!languageAvailable||!MibrI18n.menuWritable()||
           !MibrI18n.validMenuOverride(wanted)||revision==null)return;
        languageSetInFlight=true;MibrI18n.menuSaving();changed();
        final int version=epoch,runtimeSequence=++sequence;
        final String rid=prefix+"_lang_"+runtimeSequence;
        issue(rid,"MENU_LANGUAGE_SET",new String[]{"value","expected_revision","request_id"},
            new String[]{wanted,revision,rid},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                languageSetInFlight=false;
                if(error!=null || f==null || !f.ok()){
                    MibrI18n.menuFailed(MibrI18n.pick("Speicherung unbestätigt","Save not confirmed"));
                    menuLanguageRefresh();return;
                }
                try{
                    String[] reply=MibrV3Protocol.menuLanguage(f);
                    if(!wanted.equals(reply[0])||!"VERIFIED".equals(reply[3]))
                        throw new IllegalArgumentException("MENU_LANGUAGE_SAVE_UNVERIFIED");
                    MibrI18n.menuReadback(reply[0],reply[1],"ENABLED".equals(reply[2]));
                    drafts.readback(MibrPopupEditorModel.MENU_LANGUAGE,reply[0]);
                }catch(Throwable bad){
                    MibrI18n.menuFailed(MibrI18n.pick("Speicherung unbestätigt","Save not confirmed"));
                }
                menuLanguageRefresh();changed();
            }});}
        });
    }

    /** Read the two independent display preferences. These are requested broker values;
     *  the UI always labels advertised/effective stream effects unknown until observed. */
    void scaleRefresh(){
        if(!attached)return;
        if(scalingRefreshInFlight||scalingSetInFlight)return;
        if(!loaded){scalingRefreshPending=true;return;}
        scalingRefreshPending=false;
        if(!scalingAvailable){
            MibrScalingState.failed(MibrPopupEditorModel.SCALE_MAIN,"Scaling-Dienst nicht freigeschaltet");
            MibrScalingState.failed(MibrPopupEditorModel.SCALE_CLUSTER,"Scaling-Dienst nicht freigeschaltet");
            MibrScalingState.failed(MibrPopupEditorModel.SCALE_PHYSICAL,"Scaling-Dienst nicht freigeschaltet");
            MibrScalingState.failed(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL,"Scaling-Dienst nicht freigeschaltet");
            changed();return;
        }
        scalingRefreshInFlight=true;
        MibrScalingState.beginRefresh();
        scaleGet(MibrPopupEditorModel.SCALE_MAIN);
    }
    private void scaleGet(final int index){
        final String key=MibrScalingState.id(index);final int version=epoch;
        issue(id(),"SCALE_GET",new String[]{"id"},new String[]{key},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                if(error!=null){MibrScalingState.failed(index,"Lesen nicht bestätigt");}
                else try{scaleReadback(index,key,f,false,null);MibrScalingState.staleReadback(index);}catch(Throwable bad){MibrScalingState.failed(index,"Lesestand ungültig");}
                if(index==MibrPopupEditorModel.SCALE_MAIN)scaleGet(MibrPopupEditorModel.SCALE_CLUSTER);
                else if(index==MibrPopupEditorModel.SCALE_CLUSTER)scaleGet(MibrPopupEditorModel.SCALE_PHYSICAL);
                else if(index==MibrPopupEditorModel.SCALE_PHYSICAL)scaleGet(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL);
                else finishScaleRefresh();
                changed();
            }});}
        });
    }
    private void finishScaleRefresh(){
        scalingRefreshInFlight=false;
        MibrScalingState.finishRefresh();
    }
    private void scaleReadback(int index,String key,MibrV3Protocol.Frame f,boolean set,String wanted){
        if(f==null||!f.ok()||!key.equals(f.get("id")))throw new IllegalArgumentException("SCALING_ID_MISMATCH");
        String value=f.get("desired"),advertised=f.get("advertised"),effective=f.get("effective"),scope=f.get("advertised_scope"),apply=f.get("apply"),stored=f.get("stored"),pending=f.get("pending"),writer=f.get("writer"),rev=f.get("revision");
        if(!MibrScalingState.valid(index,value)||set&&!wanted.equals(value)||set&&(!"VERIFIED".equals(stored)||!"1".equals(pending))||
           !("UNKNOWN".equals(advertised)||MibrScalingState.valid(index,advertised))||!("UNKNOWN".equals(scope)||"HISTORICAL".equals(scope))||("UNKNOWN".equals(advertised)!="UNKNOWN".equals(scope))||!"UNKNOWN".equals(effective)||!"RECONNECT".equals(apply)||
           !("DEFAULT".equals(stored)||"VERIFIED".equals(stored)||"UNKNOWN".equals(stored))||
           !("0".equals(pending)||"1".equals(pending))||!("ENABLED".equals(writer)||"DISABLED".equals(writer))||
           !MibrScalingState.revisionValidForProtocol(rev))throw new IllegalArgumentException("SCALING_REPLY_INVALID");
        MibrScalingState.readback(index,value,advertised,effective,scope,stored,pending,apply,writer,rev);
        drafts.readback(index,value,false);
    }
    /** One explicit native SET per selection. A lost reply is reconciled with GET, never replayed. */
    void scaleSet(final int index,final String wanted){
        final String key=MibrScalingState.id(index),old=MibrScalingState.revision(index);
        if(!attached||!scalingAvailable||scalingRefreshInFlight||scalingSetInFlight||!MibrScalingState.writable(index)||key==null||!MibrScalingState.valid(index,wanted)||old==null){
            MibrScalingState.failed(index,"Schreiben nicht freigeschaltet");changed();return;
        }
        scalingSetInFlight=true;
        final int version=epoch;final String rid=id();MibrScalingState.saving(index);changed();
        issue(rid,"SCALE_SET",new String[]{"id","value","expected_revision","request_id"},new String[]{key,wanted,old,rid},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                scalingSetInFlight=false;
                if(error!=null){MibrScalingState.failed(index,"Ergebnis unklar; Lesestand wird abgeglichen");scaleRefresh();changed();return;}
                if(f!=null&&"STALE_REVISION".equals(f.error))MibrScalingState.stale(index);
                try{scaleReadback(index,key,f,true,wanted);}
                catch(Throwable bad){MibrScalingState.failed(index,"Speicherung nicht bestätigt; Lesestand wird abgeglichen");scaleRefresh();changed();return;}
                // The service revision is global to both keys. Refresh both rows after every SET
                // receipt so a later selection on the other display uses the same CAS revision.
                scaleRefresh();
                changed();
            }});}
        });
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
    /** Expertenmodus dropdown: "until restart" is local, only "permanent" reaches the broker. */
    void expertSet(String wish){
        if(!attached||wish==null)return;
        MibrExpert.session("session".equals(wish));
        switchSet(MibrDurableSwitch.EXPERT_MODE,MibrPopupEditorModel.EXPERT_MODE,"on".equals(wish)?"on":"off");
        changed();
    }
    private boolean menuLoading;
    private volatile int menuSkipped;
    /**
     * "Menü laden": check the file on the SD card here, then have the broker's helper store it, then compare the stored
     * bytes. Nothing is replaced for a refused file. The SD read is off the UI thread.
     */
    void menuLoad(){
        if(!attached||menuLoading)return;
        menuLoading=true;
        MibrMenuLayout.message(MibrI18n.pick("lädt…","loading…"));changed();
        final int version=epoch;
        Thread t=new Thread(new Runnable(){public void run(){
            byte[] file=MibrMenuLayout.read(MibrMenuLayout.SD_FILE);
            String refused=null;
            try{menuSkipped=MibrMenuLayout.parse(file).skipped;}
            catch(MibrMenuLayout.Invalid bad){refused=MibrMenuLayout.describe(bad);}
            final String reason=refused;
            final byte[] checked=file;
            relay(version,new Runnable(){public void run(){menuLoadChecked(version,reason,checked);}});
        }},"MibrMenuLoad");
        t.setDaemon(true);t.start();
    }
    private void menuLoadChecked(final int version,String reason,final byte[] checked){
        if(reason!=null){menuDone(reason,false);return;}
        issue(id(),"MENU_LOAD",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){relay(version,new Runnable(){public void run(){
                if(error!=null||f==null||!f.ok()){
                    menuDone(MibrI18n.pick("Speichern fehlgeschlagen","Save failed"),false);
                    return;
                }
                byte[] stored=MibrMenuLayout.read(MibrMenuLayout.STORED);
                boolean same=stored!=null&&stored.length==checked.length;
                for(int i=0;same&&i<stored.length;i++)same=stored[i]==checked[i];
                String done=menuSkipped>0?MibrI18n.pick("geladen, "+menuSkipped+" unbekannt übersprungen","loaded, "+menuSkipped+" unknown skipped"):MibrI18n.pick("geladen","loaded");
                menuDone(same?done:MibrI18n.pick("Speichern unbestätigt","Save not confirmed"),same);
            }});}
        });
    }
    private void menuDone(String text,boolean loaded){
        menuLoading=false;
        MibrMenuLayout.forget();
        MibrMenuLayout.message(text);
        if(loaded)MibrMenuLayout.loaded();
        changed();
    }
    void detach(){
        attached=false;epoch++;menuLoading=false;MibrMenuLayout.message(null);resetWireQueue();busy=false;loaded=false;writable=false;scalingAvailable=false;scalingRefreshInFlight=false;scalingSetInFlight=false;scalingRefreshPending=false;MibrScalingState.reset();
        for(int i=0;i<dirty.length;i++){dirty[i]=false;attempts[i]=0;}
    }
}
