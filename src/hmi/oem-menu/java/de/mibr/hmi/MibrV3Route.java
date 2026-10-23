package de.mibr.hmi;

/** Visible-route (STOCK110 / DIRECT111) client state machine for MIBR/3 ACTION.
 * Momentary only: never a stored preference and never SET carplay.enabled. Not bound to any
 * widget; a UI control needs its own owner approval. Callbacks come back through the OEM
 * dispatcher, never block it. One request ID per user attempt: a lost reply, PENDING or
 * NOT_READY is resolved with ACTION_STATUS on the ORIGINAL ID or a fresh STATUS, never by
 * sending a new ACTION. route_action=0 is the normal state of an unqualified unit.
 */
final class MibrV3Route {
    static final int UNAVAILABLE=0,READY=1,BUSY=2,PENDING=3,UNRESOLVED=4;
    static final int MAX_POLLS=10;
    static final long POLL_MS=1000L;
    public static interface Transport {
        boolean send(String rid,String verb,String[] names,String[] values,MibrV3Client.Listener cb);
    }
    public static interface Dispatcher {void post(Runnable action);}
    public static interface Later {void after(long ms,Runnable action);}
    /** Daemon-thread delay; the action is then posted through the OEM dispatcher by the caller. */
    static final Later THREAD_LATER=new Later(){
        public void after(final long ms,final Runnable action){
            Thread t=new Thread(new Runnable(){public void run(){
                try{Thread.sleep(ms);}catch(InterruptedException e){return;}
                action.run();
            }},"MibrV3RoutePoll");
            t.setDaemon(true);t.start();
        }
    };
    private final Transport transport;
    private final Dispatcher dispatcher;
    private final Later later;
    private final Runnable changed;
    private final String prefix="r"+Long.toString(System.currentTimeMillis(),36);
    private int state=UNAVAILABLE,epoch,sequence,polls;
    private boolean attached=true;
    private String visible=MibrV3Protocol.UNKNOWN_ROUTE,pendingRid,pendingTarget,note="Umschalten nicht verfügbar";

    MibrV3Route(Transport t,Dispatcher d,Later l,Runnable changed){
        if(t==null||d==null||l==null||changed==null)throw new IllegalArgumentException("ROUTE_DEPENDENCIES");
        transport=t;dispatcher=d;later=l;this.changed=changed;
    }
    int state(){return state;}
    /** STOCK110, DIRECT111 or UNKNOWN as last freshly observed; never inferred from a receipt. */
    String visible(){return visible;}
    String note(){return note;}
    boolean canSwitch(){return attached&&state==READY;}
    private String id(){return prefix+"_"+(++sequence);}
    private void set(int s,String text){state=s;note=text;if(attached)changed.run();}
    private void relay(final int version,final Runnable action){
        dispatcher.post(new Runnable(){public void run(){if(attached&&epoch==version)action.run();}});
    }

    /** CAPABILITIES then STATUS; call after the page's own HELLO. Safe to repeat; ignored while busy/pending. */
    void refresh(){
        if(!attached||state==BUSY||state==PENDING||state==UNRESOLVED)return;
        final int version=++epoch;
        set(BUSY,"Prüfe Umschaltung");
        if(!transport.send(id(),"CAPABILITIES",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    boolean offered=false;
                    try{offered=error==null&&MibrV3Protocol.routeAction(f);}catch(Throwable ignored){}
                    if(!offered){visible=MibrV3Protocol.UNKNOWN_ROUTE;set(UNAVAILABLE,"Umschalten nicht verfügbar");return;}
                    observe(version,false);
                }});
            }
        }))set(UNAVAILABLE,"Dienst beschäftigt");
    }
    private void observe(final int version,final boolean afterAction){
        if(!transport.send(id(),"STATUS",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    MibrV3Protocol.RouteState s=null;
                    try{if(error==null)s=MibrV3Protocol.routeState(f);}catch(Throwable ignored){}
                    if(s==null||!s.actionable()){
                        visible=s==null?MibrV3Protocol.UNKNOWN_ROUTE:s.visible;
                        set(UNAVAILABLE,"Umschalten nicht verfügbar");return;
                    }
                    visible=s.visible;lastObserved=s;
                    set(READY,afterAction?"Umgeschaltet":"Bereit");
                }});
            }
        }))set(UNAVAILABLE,"Dienst beschäftigt");
    }
    private MibrV3Protocol.RouteState lastObserved;

    /** One explicit compare-and-set to the opposite of the freshly observed route, one request ID. */
    void toggle(){
        if(!canSwitch()||lastObserved==null||!lastObserved.actionable())return;
        final MibrV3Protocol.RouteState observed=lastObserved;
        final int version=++epoch;final String rid=id();
        final String[][] f=MibrV3Protocol.routeActionFields(observed,rid);
        final String target=observed.opposite();
        pendingRid=rid;pendingTarget=target;lastObserved=null;
        set(BUSY,"Umschalten");
        if(!transport.send(rid,"ACTION",f[0],f[1],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame r,final String error){
                relay(version,new Runnable(){public void run(){answered(version,r,error);}});
            }
        })){pendingRid=null;pendingTarget=null;set(UNAVAILABLE,"Dienst beschäftigt");}
    }
    private void answered(int version,MibrV3Protocol.Frame r,String error){
        if(error!=null){poll(version,"Antwort verloren; Ergebnis wird geprüft");return;}
        if(r==null||!r.ok()){
            // Proven refusal (stale session, not ready, unsupported ...): nothing is in flight to resolve,
            // except NOT_READY which means another transition may still be pending natively.
            String code=r==null?"UNBEKANNT":r.error;
            pendingRid=null;pendingTarget=null;
            set(UNAVAILABLE,"Nicht umgeschaltet: "+code);return;
        }
        MibrV3Protocol.RouteReceipt rec;
        try{rec=MibrV3Protocol.actionReceipt(r,pendingTarget);}
        catch(Throwable t){poll(version,"Quittung ungültig; Ergebnis wird geprüft");return;}
        if(rec.active){finish(version);return;}
        poll(version,"Umschaltung ausstehend");
    }
    /** PENDING or uncertain: only ever ACTION_STATUS with the original ID, bounded, then a fresh STATUS. */
    private void poll(final int version,String text){
        polls=0;set(PENDING,text);schedule(version);
    }
    private void schedule(final int version){
        later.after(POLL_MS,new Runnable(){public void run(){
            dispatcher.post(new Runnable(){public void run(){
                if(attached&&epoch==version&&state==PENDING)status(version);
            }});
        }});
    }
    private void status(final int version){
        if(!transport.send(id(),"ACTION_STATUS",new String[]{"request_id"},new String[]{pendingRid},new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame r,final String error){
                relay(version,new Runnable(){public void run(){
                    MibrV3Protocol.RouteReceipt rec=null;
                    try{if(error==null&&r!=null&&r.ok())rec=MibrV3Protocol.actionStatusReceipt(r,pendingTarget,pendingRid);}
                    catch(Throwable ignored){}
                    if(rec!=null&&rec.active){finish(version);return;}
                    if(r!=null&&!r.ok()&&("UNKNOWN_COMMIT".equals(r.error)||"FORBIDDEN".equals(r.error))){
                        // Receipt evicted or daemon restarted: no second toggle, re-observe instead.
                        reobserve(version);return;
                    }
                    if(++polls>=MAX_POLLS){
                        set(UNRESOLVED,"Umschaltung unbestätigt; Anzeige neu prüfen");return;
                    }
                    schedule(version);
                }});
            }
        })){
            if(++polls>=MAX_POLLS)set(UNRESOLVED,"Umschaltung unbestätigt; Anzeige neu prüfen");else schedule(version);
        }
    }
    /** Historical ACTIVE is not the present display: refresh CAPABILITIES/STATUS before showing anything. */
    private void finish(int version){
        pendingRid=null;pendingTarget=null;visible=MibrV3Protocol.UNKNOWN_ROUTE;
        state=UNAVAILABLE;epoch++;refreshAfterAction();
    }
    private void reobserve(int version){
        pendingRid=null;pendingTarget=null;visible=MibrV3Protocol.UNKNOWN_ROUTE;
        state=UNAVAILABLE;epoch++;refreshAfterAction();
    }
    private void refreshAfterAction(){
        final int version=++epoch;
        set(BUSY,"Zustand prüfen");
        if(!transport.send(id(),"CAPABILITIES",new String[0],new String[0],new MibrV3Client.Listener(){
            public void onReply(final MibrV3Protocol.Frame f,final String error){
                relay(version,new Runnable(){public void run(){
                    boolean offered=false;
                    try{offered=error==null&&MibrV3Protocol.routeAction(f);}catch(Throwable ignored){}
                    if(!offered){visible=MibrV3Protocol.UNKNOWN_ROUTE;set(UNAVAILABLE,"Umschalten nicht verfügbar");return;}
                    observe(version,true);
                }});
            }
        }))set(UNAVAILABLE,"Dienst beschäftigt");
    }
    /** User asked to look again after UNRESOLVED; still never a new ACTION. */
    void recheck(){
        if(attached&&state==UNRESOLVED&&pendingRid!=null){polls=0;set(PENDING,"Umschaltung wird geprüft");schedule(++epoch);}
    }
    void detach(){attached=false;epoch++;state=UNAVAILABLE;pendingRid=null;pendingTarget=null;lastObserved=null;}
}