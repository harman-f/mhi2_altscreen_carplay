package de.mibr.hmi;

/** UI-thread state owner for the additive Wireless page. All I/O is delegated to an injected backend. */
public final class MibrWirelessSession {
    public static final int REQUEST_TOGGLE=0, REQUEST_PAIRING=1, REFRESH_STATUS=2, REQUEST_STOP=3;
    private static final int IO_CAPABILITIES=10, IO_STATUS=11, IO_TOGGLE=12, IO_PAIRING=13, IO_STOP=14;
    private static final long TIMEOUT_MS=10000L;
    public interface Dispatcher { void post(Runnable action); }
    private final MibrWirelessBackend backend;
    private final Dispatcher dispatcher;
    private final Runnable changed;
    private long generation, sequence, pendingId, pendingStart;
    private int pendingKind;
    private boolean attached=true, pageVisible, busy, available, capabilitiesKnown;
    private MibrWirelessBackend.Snapshot snapshot;
    private String message;

    public MibrWirelessSession(MibrWirelessBackend backend,Dispatcher dispatcher,Runnable changed) {
        if(dispatcher==null||changed==null)throw new IllegalArgumentException("WIRELESS_DEPENDENCIES");
        this.backend=backend;this.dispatcher=dispatcher;this.changed=changed;
        message=backend==null?pick("Adapter nativ nicht verfügbar","Native adapter unavailable"):pick("Nicht geprüft","Not checked");
    }
    private static String pick(String de,String en){return MibrI18n.pick(de,en);}
    private void notifyChanged(){if(attached)changed.run();}
    private boolean current(long token){return attached&&pageVisible&&generation==token;}
    private void post(final long token,final Runnable action){
        dispatcher.post(new Runnable(){public void run(){if(current(token))action.run();}});
    }
    private long begin(int kind){
        long id=++sequence;pendingId=id;pendingKind=kind;pendingStart=System.currentTimeMillis();busy=true;return id;
    }
    private boolean finish(long token,long request,int kind){
        if(!current(token)||pendingId!=request||pendingKind!=kind)return false;
        pendingId=0;pendingKind=0;pendingStart=0L;busy=false;return true;
    }
    private void failImmediate(long token,long request,int kind,String de,String en){
        if(!finish(token,request,kind))return;
        if(kind==IO_CAPABILITIES){capabilitiesKnown=true;available=false;}
        if(kind==IO_STATUS||kind==IO_TOGGLE||kind==IO_PAIRING||kind==IO_STOP)snapshot=null;
        message=pick(de,en);notifyChanged();
    }
    public void enterPage(){
        if(!attached)return;
        pageVisible=true;generation++;pendingId=0;pendingKind=0;pendingStart=0L;busy=false;
        available=false;capabilitiesKnown=false;snapshot=null;
        message=backend==null?pick("Nicht verfügbar: nativer Adapter fehlt","Unavailable: native adapter missing"):
            pick("Native Fähigkeiten werden geprüft","Checking native capabilities");
        notifyChanged();
        if(backend==null)return;
        final long token=generation,request=begin(IO_CAPABILITIES);
        notifyChanged();
        boolean accepted;
        try{accepted=backend.readCapabilities(token,request,new MibrWirelessBackend.Listener(){
            public void onCapabilities(final long g,final long r,final MibrWirelessBackend.Capabilities c){post(token,new Runnable(){public void run(){
                if(g!=token||r!=request||!finish(token,r,IO_CAPABILITIES))return;
                if(c==null||c.generation!=token||!c.complete()){
                    capabilitiesKnown=true;available=false;message=pick("Native Wireless-Fähigkeiten nicht verfügbar","Native wireless capability unavailable");notifyChanged();return;
                }
                capabilitiesKnown=true;available=true;message=pick("Fähigkeiten bestätigt; Status wird gelesen","Capabilities confirmed; reading status");notifyChanged();readStatus(token);
            }});}
            public void onSnapshot(long g,long r,MibrWirelessBackend.Snapshot s){}
            public void onResult(long g,long r,MibrWirelessBackend.Result v){}
        });}catch(Throwable t){accepted=false;}
        if(!accepted)failImmediate(token,request,IO_CAPABILITIES,"Native Fähigkeitsabfrage nicht verfügbar","Native capability request unavailable");
    }
    private void readStatus(final long token){
        if(!current(token)||backend==null||!available||busy)return;
        final long request=begin(IO_STATUS);message=pick("Native Status wird gelesen","Reading native status");notifyChanged();
        boolean accepted;
        try{accepted=backend.readStatus(token,request,new MibrWirelessBackend.Listener(){
            public void onCapabilities(long g,long r,MibrWirelessBackend.Capabilities c){}
            public void onResult(long g,long r,MibrWirelessBackend.Result v){}
            public void onSnapshot(final long g,final long r,final MibrWirelessBackend.Snapshot s){post(token,new Runnable(){public void run(){
                if(g!=token||r!=request||!finish(token,r,IO_STATUS))return;
                if(s==null||!s.validFor(token)){snapshot=null;message=pick("Native Status nicht bestätigt","Native status unconfirmed");notifyChanged();return;}
                snapshot=s;message=pick("Status bestätigt","Status confirmed");notifyChanged();
            }});}
        });}catch(Throwable t){accepted=false;}
        if(!accepted)failImmediate(token,request,IO_STATUS,"Native Statusabfrage nicht verfügbar","Native status request unavailable");
    }
    /** Called by the page's existing bounded refresh loop; no extra worker or socket is started here. */
    public void checkTimeout(){
        dispatcher.post(new Runnable(){public void run(){
            long token=generation;
            expireAt(token,System.currentTimeMillis());
        }});
    }
    void expireAt(long token,long now){
        if(!current(token)||!busy||pendingId==0)return;
        long elapsed=now-pendingStart;
        /* A backwards wall-clock step or arithmetic overflow fails closed too. */
        if(now>=pendingStart&&elapsed>=0L&&elapsed<TIMEOUT_MS)return;
        int kind=pendingKind;pendingId=0;pendingKind=0;pendingStart=0L;busy=false;
        if(kind==IO_CAPABILITIES){capabilitiesKnown=true;available=false;message=pick("Zeitüberschreitung: Adapter nicht bestätigt","Timeout: adapter not confirmed");}
        else {snapshot=null;message=pick("Zeitüberschreitung: Status erneut prüfen","Timeout: refresh native status");}
        notifyChanged();
    }
    public void leavePage(){if(!pageVisible)return;pageVisible=false;generation++;pendingId=0;pendingKind=0;pendingStart=0L;busy=false;snapshot=null;available=false;}
    public void detach(){attached=false;pageVisible=false;generation++;pendingId=0;pendingKind=0;pendingStart=0L;busy=false;snapshot=null;available=false;}
    public boolean pageVisible(){return pageVisible;}
    public boolean available(){return attached&&pageVisible&&available&&capabilitiesKnown;}
    public boolean enabled(int action){
        if(!available())return false;
        if(action==REFRESH_STATUS)return !busy;
        if(action==REQUEST_STOP&&pendingCommand()&&snapshot!=null&&snapshot.validFor(generation))return true;
        if(busy||snapshot==null||!snapshot.validFor(generation))return false;
        if(action==REQUEST_TOGGLE||action==REQUEST_PAIRING)return true;
        if(action==REQUEST_STOP)return !"OFF".equals(snapshot.state);
        return false;
    }
    private boolean pendingCommand(){return pendingKind==IO_TOGGLE||pendingKind==IO_PAIRING;}
    private String stateLabel(String value){
        if("OFF".equals(value))return pick("aus","off");
        if("IDLE".equals(value))return pick("bereit","idle");
        if("BOOTSTRAP".equals(value))return pick("Start","bootstrap");
        if("VERIFY".equals(value))return pick("Prüfung","verification");
        if("ACTIVE".equals(value))return pick("aktiv","active");
        if("STOPPING".equals(value))return pick("wird beendet","stopping");
        if("FAILED".equals(value))return pick("Fehler","failed");
        return pick("unbekannt","unknown");
    }
    private String pairingLabel(String value){
        if("PAIRED".equals(value))return pick("Pairing bestätigt","pairing confirmed");
        if("REQUESTED".equals(value))return pick("Pairing-Anfrage offen","pairing request pending");
        if("NOT_PAIRED".equals(value))return pick("nicht gekoppelt","not paired");
        return pick("Pairing unbekannt","pairing unknown");
    }
    public String statusLine(){
        if(!attached)return pick("Wireless-Menü geschlossen","Wireless page closed");
        if(!pageVisible)return pick("Status nicht geöffnet","Wireless status not open");
        if(backend==null)return pick("Nicht verfügbar: nativer Adapter fehlt","Unavailable: native adapter missing");
        if(!available)return message;
        if(snapshot==null)return message;
        String confirmed=pick("Nativ bestätigt: ","Native confirmed: ")+stateLabel(snapshot.state)+
            pick("; angefordert ","; requested ")+(snapshot.requestedOn?pick("ein","on"):pick("aus","off"))+"; "+pairingLabel(snapshot.pairing);
        return busy?message+"; "+confirmed:confirmed;
    }
    public String[] rows(){
        boolean on=snapshot!=null&&snapshot.validFor(generation)&&snapshot.requestedOn;
        return new String[]{statusLine(),
            pick("Wireless "+(on?"ausschalten":"einschalten")+" anfordern","Request wireless "+(on?"off":"on")),
            pick("Pairing anfordern","Request pairing"),pick("Status aktualisieren","Refresh status"),pick("Stop anfordern","Request stop")};
    }
    public boolean perform(int action){
        if(!enabled(action))return false;
        if(action==REFRESH_STATUS){readStatus(generation);return true;}
        final long token=generation;
        final int op=action;
        final int kind=action==REQUEST_TOGGLE?IO_TOGGLE:action==REQUEST_PAIRING?IO_PAIRING:IO_STOP;
        /* STOP explicitly supersedes a pending enable/pair command; stale replies cannot reclaim the slot. */
        if(action==REQUEST_STOP&&pendingCommand()){pendingId=0;pendingKind=0;pendingStart=0L;busy=false;}
        final long request=begin(kind);
        final boolean targetOn=action==REQUEST_TOGGLE && !snapshot.requestedOn;
        message=action==REQUEST_PAIRING?pick("Pairing-Anfrage ausstehend","Pairing request pending"):
            action==REQUEST_STOP?pick("Stop-Anfrage ausstehend","Stop request pending"):pick("Wireless-Anfrage ausstehend","Wireless request pending");
        notifyChanged();
        MibrWirelessBackend.Listener listener=new MibrWirelessBackend.Listener(){
            public void onCapabilities(long g,long r,MibrWirelessBackend.Capabilities c){}
            public void onSnapshot(long g,long r,MibrWirelessBackend.Snapshot s){}
            public void onResult(final long g,final long r,final MibrWirelessBackend.Result result){post(token,new Runnable(){public void run(){
                if(g!=token||r!=request||!finish(token,r,kind))return;
                if(result==null||result.generation!=token||result.requestId!=request||result.operation!=op||
                    !result.acknowledged||result.snapshot==null||!result.snapshot.validFor(token)){
                    snapshot=null;message=op==REQUEST_PAIRING?pick("Pairing nicht bestätigt","Pairing not confirmed"):
                        pick("Native Anfrage nicht bestätigt","Native request not confirmed");notifyChanged();return;
                }
                snapshot=result.snapshot;
                if(op==REQUEST_PAIRING){
                    message="PAIRED".equals(snapshot.pairing)?pick("Pairing bestätigt","Pairing confirmed"):
                        pick("Pairing-Anfrage bestätigt; Kopplung offen","Pairing request acknowledged; pairing not confirmed");
                }else if(op==REQUEST_STOP){
                    message="OFF".equals(snapshot.state)?pick("Wireless beendet bestätigt","Wireless stop confirmed"):
                        pick("Wireless-Ende nicht bestätigt","Wireless stop not confirmed");
                }else {
                    message=snapshot.requestedOn==targetOn?pick("Wireless-Anfrage bestätigt","Wireless request acknowledged"):
                        pick("Wireless-Anfragezustand abweichend","Wireless request state mismatch");
                }
                notifyChanged();
            }});}
        };
        boolean accepted=false;
        try{
            if(action==REQUEST_TOGGLE)accepted=backend.requestEnabled(token,request,targetOn,listener);
            else if(action==REQUEST_PAIRING)accepted=backend.requestPairing(token,request,listener);
            else if(action==REQUEST_STOP)accepted=backend.stop(token,request,listener);
        }catch(Throwable t){accepted=false;}
        if(!accepted){failImmediate(token,request,kind,"Native Anfrage vor dem Senden abgelehnt","Native request rejected before send");return false;}
        return true;
    }
}
