package de.mibr.hmi;
import java.util.Properties;

/** No OEM dependencies; version/config brands in a read-only menu. */
public final class MibrVersionInfoTest {
    private static void yes(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static void main(String[] args){
        MibrI18n.forced="de_DE";
        Properties p=new Properties();
        p.setProperty("identity_schema","1");
        p.setProperty("product","MIBR-CarPlay");
        p.setProperty("product_version","1.3.3-rc.1");
        p.setProperty("target_brand","SKODA");
        p.setProperty("target_profile_id","skoda-mu1440-p4526-aid10");
        p.setProperty("source_commit","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
        p.setProperty("identity_stage","SOURCE_ONLY");
        p.setProperty("config_count","2");
        p.setProperty("config.0.name","registry.json");
        p.setProperty("config.0.schema","2");
        p.setProperty("config.0.brand","GENERIC");
        p.setProperty("config.1.name","menu-definition.json");
        p.setProperty("config.1.schema","3");
        p.setProperty("config.1.brand","SKODA");
        String[] rows=MibrVersionInfo.rowsFor(p);
        yes(rows.length==7,"row count");
        yes(rows[0].indexOf("1.3.3-rc.1")>=0,"version");
        yes(rows[1].indexOf("Skoda")>=0,"Skoda brand");
        yes(rows[4].indexOf("Generisch")>=0 && rows[4].indexOf("v2")>=0,"generic config");
        yes(rows[5].indexOf("Skoda")>=0 && rows[5].indexOf("v3")>=0,"brand config");
        yes(rows[6].indexOf("keine Installation")>=0,"source-only is not installed");
        p.setProperty("identity_schema","bad");
        yes(MibrVersionInfo.rowsFor(p).length==1,"invalid metadata rejected");
        System.out.println("MIBR_VERSION_INFO_PASS");
    }
}
