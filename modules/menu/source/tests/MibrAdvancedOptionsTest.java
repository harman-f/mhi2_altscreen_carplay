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
        MibrGpsDemoState.reset();
        ok(!MibrI18n.menuWritable()&&!MibrGpsDemoState.writable(),"no unconfirmed writers");
        MibrPopupEditorModel choice=new MibrPopupEditorModel();
        choice.setAvailable(true);
        ok(!choice.open(MibrPopupEditorModel.MENU_LANGUAGE) &&
           !choice.open(MibrPopupEditorModel.GPS_DEMO),"no unqualified writes");
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
        MibrGpsDemoState.error("GPS-Demo nicht verfügbar");
        MibrI18n.applyMenuOverride("en");
        ok("GPS demo unavailable".equals(MibrGpsDemoState.message()),
           "visible GPS status follows English override");
        MibrScalingState.reset();
        ok(choice.open(MibrPopupEditorModel.MENU_LANGUAGE),"confirmed language writer");
        choice.cancel();
        MibrV3Protocol.Frame gps=response("g1",
            new String[]{"choice","epoch","active","stationary","owner","effect"},
            new String[]{"OFF","12","0","1","READY","UNVERIFIED_IOS"});
        String[] g=MibrV3Protocol.gpsDemo(gps);
        MibrGpsDemoState.readback(g[0],g[1],g[2],g[3],true);
        ok(MibrGpsDemoState.writable() && choice.open(MibrPopupEditorModel.GPS_DEMO),
           "manual GPS control is selectable");
        choice.cancel();
        MibrGpsDemoState.readback("BERLIN_DEMO","0","1","0",true);
        ok(MibrGpsDemoState.active()&&"BERLIN_DEMO".equals(MibrGpsDemoState.choice()),
           "owner accepted Berlin without an iOS-render claim");
        MibrGpsDemoState.readback("OFF","13","0","0",true);
        ok(!MibrGpsDemoState.active()&&MibrGpsDemoState.writable(),"manual mode has no stationary gate");
        boolean refused=false;
        try{MibrGpsDemoState.readback("OFF","13","1","1",true);}
        catch(IllegalArgumentException expected){refused=true;}
        ok(refused,"reject contradictory active-off response");
        MibrI18n.menuFailed("unavailable");
        ok(!choice.open(MibrPopupEditorModel.MENU_LANGUAGE),"error removes write permission");
        MibrI18n.applyMenuOverride("AUTO");MibrI18n.forced=null;
        System.out.println("MIBR_ADVANCED_OPTIONS_HOST_PASS");
    }
}
