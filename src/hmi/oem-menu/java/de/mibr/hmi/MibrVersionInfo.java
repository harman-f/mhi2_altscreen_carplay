package de.mibr.hmi;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

/** Read-only, Java 1.2-compatible identity view; never claims running bytes match. */
public final class MibrVersionInfo {
    private static final String INSTALLED="/mnt/app/root/mibr-kit/installed-version.properties";
    private MibrVersionInfo(){}
    private static String safe(Properties p,String key){
        String v=p.getProperty(key);
        if(v==null||v.length()==0||v.length()>96)return "?";
        for(int i=0;i<v.length();i++)if(v.charAt(i)<32||v.charAt(i)>126)return "?";
        return v;
    }
    private static String brand(String value){
        if("VW".equals(value))return "VW";
        if("SKODA".equals(value))return "Skoda";
        if("SEAT".equals(value))return "SEAT";
        if("GENERIC".equals(value))return MibrI18n.pick("Generisch","Generic");
        return MibrI18n.pick("Unbekannt","Unknown");
    }
    public static String[] rows(){
        Properties p=new Properties();
        FileInputStream in=null;
        try{
            in=new FileInputStream(INSTALLED);
            p.load(in);
        }catch(IOException e){
            return new String[]{MibrI18n.pick("Versionsdaten nicht installiert","No installed version metadata"),
                MibrI18n.pick("Siehe Build-/Paketmanifest","See build/package manifest")};
        }finally{
            if(in!=null)try{in.close();}catch(IOException ignored){}
        }
        if(!"1".equals(p.getProperty("identity_schema"))||
           !"MIBR-CarPlay".equals(p.getProperty("product")))
            return new String[]{MibrI18n.pick("Versionsdaten ungueltig","Invalid version metadata")};
        return rowsFor(p);
    }
    /** Pure formatter for Java host tests and fail-closed read-only presentation. */
    static String[] rowsFor(Properties p){
        if(!"1".equals(p.getProperty("identity_schema"))||
           !"MIBR-CarPlay".equals(p.getProperty("product")))
            return new String[]{MibrI18n.pick("Versionsdaten ungueltig","Invalid version metadata")};
        String git=safe(p,"source_commit");
        if(git.length()==40||git.length()==64)git=git.substring(0,12);
        String state=safe(p,"identity_stage");
        String status="INSTALLED_VERIFIED".equals(state)
            ? MibrI18n.pick("Installationsbeleg vorhanden (Laufzeit ungeprueft)","Installation receipt present (runtime unverified)")
            : MibrI18n.pick("Nur Build-Metadaten, keine Installation bestaetigt","Build metadata only, installation unconfirmed");
        int count=0;
        try{count=Integer.parseInt(safe(p,"config_count"));}catch(NumberFormatException ignored){}
        if(count<0||count>12)count=0;
        String[] rows=new String[5+count];
        rows[0]=MibrI18n.pick("Version: ","Version: ")+safe(p,"product_version");
        rows[1]=MibrI18n.pick("Marke: ","Brand: ")+brand(safe(p,"target_brand"));
        rows[2]="Target: "+safe(p,"target_profile_id");
        rows[3]="Source: "+git;
        for(int i=0;i<count;i++){
            String prefix="config."+i+".";
            rows[4+i]=safe(p,prefix+"name")+" v"+safe(p,prefix+"schema")+
                      " ["+brand(safe(p,prefix+"brand"))+"]";
        }
        rows[4+count]=status;
        return rows;
    }
}
