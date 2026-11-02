package de.mibr.hmi;
import de.vw.mib.widgets.internal.ServiceManager;

/** Actual Java UI session -> async TCP -> original native TEMP broker host E2E. */
public final class UiWireHarness {
    private static void check(boolean value,String why){if(!value)throw new AssertionError(why);}
    private static int id(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)
            if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        throw new AssertionError("key "+key);
    }
    private static void pumpUntil(MibrControlSession session,String prefix) throws Exception{
        long end=System.currentTimeMillis()+12000;
        while(System.currentTimeMillis()<end){
            Runnable r;
            while((r=ServiceManager.eventDispatcher.poll())!=null)r.run();
            if(session.status().startsWith(prefix))return;
            if(session.status().indexOf("fehlgeschlagen")>=0||
               session.status().indexOf("nicht bestätigt")>=0 ||
               session.status().indexOf("unbestätigt; Entwurf")>=0)
                throw new AssertionError("unexpected "+session.status());
            Thread.sleep(10);
        }
        throw new AssertionError("timeout "+session.status());
    }
    public static void main(String[] args) throws Exception{
        check(args.length==2,"port and token");
        int port=Integer.parseInt(args[0]);
        MibrPopupEditorModel model=new MibrPopupEditorModel();
        model.setAvailable(true);
        final int[] paints={0};
        MibrControlClient client=new MibrControlClient(port,args[1]);
        MibrControlSession session=new MibrControlSession(client,model,new Runnable(){
            public void run(){paints[0]++;}
        });
        session.open();pumpUntil(session,"Bereit");
        check(client.isProductVerified(),"HELLO product handshake");
        int fps=id("maxFPS");
        check(model.current(fps)!=null && model.draft(fps)==null,"initial original native core GET");
        check(model.open(fps)&&model.choose(1)&&"25".equals(model.draft(fps)),"native UI choice local DRAFT");
        check(model.current(fps)!=null&&!model.isTempConfirmed(fps),"local draft not effective");
        session.apply();pumpUntil(session,"TEMP bestätigt:");
        check(model.draft(fps)==null&&"25".equals(model.current(fps))&&model.isTempConfirmed(fps),
              "actual C TCP batch and independent GET confirmed desired/temp");
        check(session.status().indexOf("RECONNECT_REQUIRED")>=0 &&
              session.status().indexOf("Wirkung unbestätigt")>=0,
              "reconnect is required, never APPLIED");
        check(paints[0]>1,"UI repaint callbacks dispatched");
        session.detach();
        // A wrong but correctly formed launch token cannot be promoted by HELLO.
        MibrControlClient bad=new MibrControlClient(port,"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
        MibrControlSession blocked=new MibrControlSession(bad,new MibrPopupEditorModel(),new Runnable(){
            public void run(){}
        });
        blocked.open();pumpUntil(blocked,"Dienst nicht bestätigt");
        check(!bad.isProductVerified(),"auth failure");
        blocked.apply();check(!bad.isProductVerified(),"no mutation after auth failure");
        blocked.detach();
        System.out.println("MIBR_UI_WIRE_TEMP_PASS desired_only_no_effective_ack");
    }
}
