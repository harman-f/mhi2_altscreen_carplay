package de.mibr.hmi;
public final class MibrControlProtocolTest {
    private static void check(boolean ok,String reason){if(!ok)throw new AssertionError(reason);}
    private static int id(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)
            if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        throw new AssertionError(key);
    }
    public static void main(String[] args){
        String token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        MibrPopupEditorModel drafts=new MibrPopupEditorModel();
        drafts.setAvailable(true);
        check(drafts.open(id("maxFPS"))&&drafts.choose(1),"FPS draft 25");
        check(drafts.open(id("navigation.surface"))&&drafts.choose(1),"surface map draft");
        MibrControlProtocol.Batch batch=MibrControlProtocol.collect(token,"16714623294199880833",drafts);
        check(batch.count()==2 && batch.command.startsWith("TEMPBATCH "+token+" 16714623294199880833 "),"frame");
        check(batch.command.indexOf("navigation.surface=map")>=0 &&
              batch.command.indexOf("maxFPS=25")>=0 && batch.command.length()<=512,"wire values");
        check(MibrControlProtocol.revision("18446744073709551615") &&
              !MibrControlProtocol.revision("18446744073709551616") &&
              !MibrControlProtocol.revision("0"),"revision bounds");
        check("23".equals(MibrControlProtocol.statusRevision(
           "STATUS mode=TEMP_NATIVE revision=23 session=NONE effective=UNCONFIRMED stored=UNCONFIRMED")),"status");
        check(MibrControlProtocol.statusRevision(
           "STATUS mode=HOST_FIXTURE revision=23 session=NONE effective=UNCONFIRMED stored=UNCONFIRMED")==null,"fixture not product");
        check("25".equals(MibrControlProtocol.desiredValue(
           "VALUE key=maxFPS desired=25 source=temp revision=23 effective=UNCONFIRMED session=NONE",
           "maxFPS","23")),"readback");
        check(MibrControlProtocol.desiredValue(
           "VALUE key=maxFPS desired=25 source=temp revision=22 effective=UNCONFIRMED session=NONE",
           "maxFPS","23")==null,"stale revision");
        check(MibrControlProtocol.desiredValue(
           "VALUE key=maxFPS desired=25 source=temp revision=23 effective=25 session=NONE",
           "maxFPS","23")==null,"fake effective");
        MibrControlProtocol.Commit result=MibrControlProtocol.tempResult(
           "RESULT state=RECONNECT_REQUIRED count=2 revision=24 desired=TEMP_READBACK effective=UNCONFIRMED session=NONE",2);
        check(result!=null&&"24".equals(result.revision)&&"RECONNECT_REQUIRED".equals(result.state),"TEMP result");
        check(MibrControlProtocol.tempResult(
           "RESULT state=APPLIED count=2 revision=24 desired=TEMP_READBACK effective=UNCONFIRMED session=NONE",2)==null,"not applied");
        check(MibrControlProtocol.tempResult(
           "RESULT state=QUEUED count=1 revision=24 desired=TEMP_READBACK effective=UNCONFIRMED session=NONE",2)==null,"partial result");
        System.out.println("MIBR_CONTROL_PROTOCOL_PASS");
    }
}
