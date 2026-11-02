package de.mibr.hmi;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.Properties;
import java.util.Vector;

/** Read-only, Java 1.2-compatible identity view; never claims running bytes match. */
public final class MibrVersionInfo {
    private static final String INSTALLED="/mnt/app/root/mibr-kit/installed-version.properties";
    /** r60: one line per functional package, written by the installer (write-components-manifest.ksh). */
    private static final String COMPONENTS="/mnt/app/root/mibr-kit/components.manifest";
    private static final String[][] NAMES={
        {"menu-jar","Men\u00fc (JAR)","Menu (JAR)"},
        {"broker","Broker","Broker"},
        {"supervisor","Cockpit-Supervisor","Cockpit supervisor"},
        {"gen2-main","Video-Hook (Haupt)","Video hook (main)"},
        {"gen2-lower","Video-Hook (Kopie)","Video hook (copy)"},
        {"parity-session","Cockpit-Ausgabe","Cockpit output"},
        {"alt111-settings","Einstellungsdienst","Settings helper"},
        {"key40d","Lenkradtasten","Steering keys"},
        {"rgi-ipod","CarPlay-Navi (iAP2)","CarPlay nav (iAP2)"},
        {"rgi-helper","CarPlay-Navi (Dienst)","CarPlay nav (service)"},
        {"rgi-wrapper","CarPlay-Navi (Start)","CarPlay nav (launcher)"},
        {"menu-icon","Men\u00fc-Icon","Menu icon"},
    };
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
        String[] packages=componentRows(COMPONENTS);
        String[] kit=kitRows();
        if(packages==null)return kit;
        String[] all=new String[packages.length+kit.length];
        System.arraycopy(packages,0,all,0,packages.length);
        for(int i=0;i<kit.length;i++)all[packages.length+i]=(i==0?MibrI18n.pick("Kit-Basis: ","Kit base: "):"")+kit[i];
        return all;
    }
    private static String name(String id){
        for(int i=0;i<NAMES.length;i++)if(NAMES[i][0].equals(id))return MibrI18n.pick(NAMES[i][1],NAMES[i][2]);
        return id;
    }
    private static boolean printable(String v){
        if(v.length()==0||v.length()>200)return false;
        for(int i=0;i<v.length();i++)if(v.charAt(i)<32||v.charAt(i)>126)return false;
        return true;
    }
    /** Splits on '|' without String.split (Java 1.2 class library). */
    static String[] fields(String line){
        Vector out=new Vector();
        int start=0;
        for(int i=0;i<=line.length();i++){
            if(i==line.length()||line.charAt(i)=='|'){out.addElement(line.substring(start,i));start=i+1;}
        }
        String[] f=new String[out.size()];
        out.copyInto(f);
        return f;
    }
    /** Package rows from the components manifest with a live file check; null if absent or invalid. */
    static String[] componentRows(String path){
        Vector lines=new Vector();
        BufferedReader in=null;
        try{
            in=new BufferedReader(new InputStreamReader(new FileInputStream(path),"US-ASCII"));
            String line=in.readLine();
            if(!"MIBR_COMPONENTS/1".equals(line))return null;
            boolean end=false;
            while((line=in.readLine())!=null&&lines.size()<40){
                if("end=1".equals(line)){end=true;break;}
                if(!printable(line))return null;
                lines.addElement(line);
            }
            if(!end)return null;
        }catch(IOException e){
            return null;
        }finally{
            if(in!=null)try{in.close();}catch(IOException ignored){}
        }
        Vector rows=new Vector();
        for(int i=0;i<lines.size();i++){
            String[] f=fields((String)lines.elementAt(i));
            if(f.length!=5)return null;
            if("product".equals(f[0])){rows.insertElementAt(MibrI18n.pick("Paket: ","Package: ")+f[1],0);continue;}
            rows.addElement(name(f[0])+"  "+f[1]+"  "+(f[2].length()>=8?f[2].substring(0,8):"-")+"  "+state(f[3],f[4]));
        }
        String[] r=new String[rows.size()];
        rows.copyInto(r);
        return r;
    }
    /** OK when the file is there with the installed size; a full hash check needs the installer's sha256sum. */
    static String state(String size,String path){
        File f=new File(path);
        if(!f.isFile())return MibrI18n.pick("FEHLT","MISSING");
        if("-".equals(size))return MibrI18n.pick("NEU","NEW");
        try{
            if(Long.parseLong(size)!=f.length())return MibrI18n.pick("GE\u00c4NDERT","CHANGED");
        }catch(NumberFormatException e){
            return "?";
        }
        return "OK";
    }
    private static String[] kitRows(){
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
