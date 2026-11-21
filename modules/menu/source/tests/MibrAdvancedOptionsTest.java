package de.mibr.hmi;

/** Host-only checks for the owned options; no iPhone/vehicle claims. */
public final class MibrAdvancedOptionsTest {
    private static void ok(boolean value,String message){
        if(!value)throw new AssertionError(message);
    }
    private static MibrV3Protocol.Frame response(String id,String[] k,String[] v){
        return MibrV3Protocol.parse(MibrV3BindingTest.reply(id,k,v),id);
    }
    public static void main(String[] args){
        MibrI18n.forced="de_DE";
        MibrI18n.applyMenuOverride("AUTO");
        MibrI18n.menuLoading();
        ok(!MibrI18n.menuWritable(),"no unconfirmed writers");
        MibrPopupEditorModel choice=new MibrPopupEditorModel();
        choice.setAvailable(true);
        ok(!choice.open(MibrPopupEditorModel.MENU_LANGUAGE),"no unqualified writes");
        MibrV3Protocol.Frame lang=response("l1",
            new String[]{"value","revision","writer","stored","scope","apply"},
            new String[]{"en","4","ENABLED","VERIFIED","MIBR_ONLY","IMMEDIATE"});
        String[] l=MibrV3Protocol.menuLanguage(lang);
        MibrI18n.menuReadback(l[0],l[1],"ENABLED".equals(l[2]));
        ok(MibrI18n.menuWritable()&&!MibrI18n.german(),"confirmed English override");
        String storedGermanStatus="Dienst beschäftigt; Entwurf behalten";
        ok("Service busy; selection retained".equals(MibrI18n.localize(storedGermanStatus)),
           "already-visible status follows runtime English override");
        MibrI18n.applyMenuOverride("de");
        ok("Dienst beschäftigt; Entwurf behalten".equals(MibrI18n.localize(storedGermanStatus)),
           "same stored status follows runtime German override");
        MibrI18n.applyMenuOverride("en");
        MibrI18n.menuFailed(storedGermanStatus);
        ok("Service busy; selection retained".equals(MibrI18n.menuMessage()),
           "language dropdown message follows runtime English override");
        MibrI18n.menuReadback("en","4",true);
        ok("Saved persistently; on the next connection unchanged; stream effect unverified".
           equals(MibrI18n.localize("RECEIPT:RECONNECT:UNCHANGED")),
           "save receipt uses localized labels, not raw activation token");
        String routeStatus=MibrI18n.localize("Nicht umgeschaltet: UNBEKANNT");
        ok("Not switched: Unknown".equals(routeStatus),
           "route fallback status is localized without changing its protocol token: "+routeStatus);
        MibrScalingState.failed(MibrPopupEditorModel.SCALE_MAIN,"Lesestand ungültig");
        ok("Invalid readback".equals(MibrScalingState.uiMessage(MibrPopupEditorModel.SCALE_MAIN)),
           "visible Scaling error follows English override");
        MibrI18n.applyMenuOverride("de");
        ok("Lesestand ungültig".equals(MibrScalingState.uiMessage(MibrPopupEditorModel.SCALE_MAIN)),
           "same Scaling error follows German override");
        MibrI18n.applyMenuOverride("en");
        MibrScalingState.reset();
        ok(choice.open(MibrPopupEditorModel.MENU_LANGUAGE),"confirmed language writer");
        choice.cancel();
        MibrI18n.menuFailed("unavailable");
        ok(!choice.open(MibrPopupEditorModel.MENU_LANGUAGE),"error removes write permission");
        /* r15k: the "Demo GPS position" row (gps.demo) was removed; an old stored menu file that still lists it
         * (valid CRC) must load, with the unknown id skipped and its neighbours intact. */
        try{
            String body="MIBR_MENU/1\ncatalog=2\nbrand=skoda\nname=Old\nadvanced\troot\t-\t\t\ngps.demo\tadvanced\t-\tDemo-GPS-Position\tDemo GPS location\nsd_log\tadvanced\t-\t\t\n";
            byte[] b=body.getBytes("UTF-8");
            MibrMenuLayout layout=MibrMenuLayout.parse((body+"crc32="+MibrMenuLayout.crc32(b,b.length)+"\n").getBytes("UTF-8"));
            ok(layout.skipped==1,"old menu file with removed gps.demo loads, the id is skipped");
        }catch(Exception e){ok(false,"old menu file with removed gps.demo must still load: "+e);}
        MibrI18n.applyMenuOverride("AUTO");MibrI18n.forced=null;
        System.out.println("MIBR_ADVANCED_OPTIONS_HOST_PASS");
    }
}
