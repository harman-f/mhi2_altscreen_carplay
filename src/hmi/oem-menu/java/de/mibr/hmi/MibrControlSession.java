package de.mibr.hmi;

/** Single asynchronous HMI client of the canonical TEMP broker; UI thread only. */
final class MibrControlSession {
    private final MibrControlClient client;
    private final MibrPopupEditorModel model;
    private final Runnable repaint;
    private final String[] visible;
    private String revision,message,applyState;
    private boolean busy,connected,attached=true;
    private int epoch;
    private String[] checked;

    MibrControlSession(MibrControlClient client,MibrPopupEditorModel model,Runnable repaint){
        if(model==null||repaint==null)throw new IllegalArgumentException("CONTROL_OWNER");
        this.client=client;this.model=model;this.repaint=repaint;
        visible=new String[MibrMenuDefinition.VISIBLE_KEYS.length];
        for(int n=0;n<visible.length;n++)visible[n]=MibrMenuDefinition.VISIBLE_KEYS[n];
        message=client==null?"Dienst nicht verbunden":"Dienst noch nicht geprüft";
    }
    private void deliver(final int version,final Runnable job){
        de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(new Runnable(){
            public void run(){if(attached && epoch==version)job.run();}
        });
    }
    private void changed(){if(attached)repaint.run();}
    private int keyIndex(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)
            if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        return -1;
    }
    String status(){return message;}
    String actionLabel(){return busy?"Bitte warten":connected?"Temporär übernehmen":"Übernehmen (Dienst offline)";}
    void open(){
        if(!attached || client==null)return;
        connected=false;busy=true;message="Konfigurationsdienst prüfen";changed();
        final int version=epoch;
        if(!client.hello(new MibrControlClient.Listener(){
            public void onReply(final String value){deliver(version,new Runnable(){public void run(){
                if(!MibrControlProtocol.HELLO.equals(value)||!client.isProductVerified()){
                    blocked("Dienst nicht bestätigt");return;
                }
                loadRevision(version);
            }});}
        }))blocked("Dienst beschäftigt");
    }
    private void blocked(String reason){
        connected=false;busy=false;checked=null;message=reason;changed();
    }
    private void loadRevision(final int version){
        if(!client.status(new MibrControlClient.Listener(){
            public void onReply(final String value){deliver(version,new Runnable(){public void run(){
                String r=MibrControlProtocol.statusRevision(value);
                if(r==null){blocked("Status nicht bestätigt");return;}
                revision=r;readInitial(version,0);
            }});}
        }))blocked("Statusabfrage fehlgeschlagen");
    }
    private void readInitial(final int version,final int n){
        if(n>=visible.length){connected=true;busy=false;message="Bereit; Wirkung unbestätigt";changed();return;}
        final String key=visible[n];
        if(!client.get(key,new MibrControlClient.Listener(){
            public void onReply(final String line){deliver(version,new Runnable(){public void run(){
                String value=MibrControlProtocol.desiredValue(line,key,revision);
                int index=keyIndex(key);
                if(value==null||index<0){blocked("Lesestand nicht konsistent");return;}
                model.readback(index,value,MibrControlProtocol.isTempSource(line));
                readInitial(version,n+1);
            }});}
        }))blocked("Leseabfrage fehlgeschlagen");
    }
    void apply(){
        if(!attached)return;
        if(client==null||!connected||busy||revision==null){
            message="Dienst nicht bereit";changed();return;
        }
        final MibrControlProtocol.Batch batch;
        try{batch=client.draftBatch(revision,model);}
        catch(Throwable t){message="Ungültiger Entwurf";changed();return;}
        if(batch==null){message="Kein gültiger Entwurf";changed();return;}
        final int version=epoch;
        busy=true;connected=false;message="TEMP-Übernahme läuft";changed();
        if(!client.tempBatch(batch,new MibrControlClient.Listener(){
            public void onReply(final String line){deliver(version,new Runnable(){public void run(){
                MibrControlProtocol.Commit commit=MibrControlProtocol.tempResult(line,batch.count());
                if(commit==null){blocked("Übernahme unbestätigt; Entwurf behalten");return;}
                revision=commit.revision;applyState=commit.state;checked=new String[batch.count()];
                readApplied(version,batch,0);
            }});}
        }))blocked("TEMP-Transport nicht bereit");
    }
    private void readApplied(final int version,final MibrControlProtocol.Batch batch,final int n){
        if(n>=batch.count()){
            // Do not publish a partial commit in the UI: check all drafts again.
            for(int i=0;i<batch.count();i++){
                int index=keyIndex(batch.keys[i]);
                if(index<0||!batch.values[i].equals(model.draft(index))){
                    blocked("Entwurf während Übernahme verändert");return;
                }
            }
            for(int i=0;i<batch.count();i++)
                model.confirmTemp(keyIndex(batch.keys[i]),checked[i]);
            checked=null;busy=false;connected=true;
            message="TEMP bestätigt: "+applyState+"; Wirkung unbestätigt";changed();return;
        }
        final String key=batch.keys[n],wanted=batch.values[n];
        if(!client.get(key,new MibrControlClient.Listener(){
            public void onReply(final String line){deliver(version,new Runnable(){public void run(){
                String value=MibrControlProtocol.desiredValue(line,key,revision);
                if(value==null||!wanted.equals(value)||!MibrControlProtocol.isTempSource(line)){
                    blocked("TEMP Readback unbestätigt; Entwurf behalten");return;
                }
                checked[n]=value;readApplied(version,batch,n+1);
            }});}
        }))blocked("TEMP Readback fehlgeschlagen");
    }
    void detach(){attached=false;epoch++;busy=false;connected=false;checked=null;}
}