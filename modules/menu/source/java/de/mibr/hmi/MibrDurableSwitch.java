package de.mibr.hmi;

import java.io.File;
import java.io.FileInputStream;

/**
 * A MIBR-owned on/off switch or short value list. The broker owns the only durable file (&lt;verb&gt;_SET, same CAS + atomic
 * scheme as the menu language); the menu row shows the broker readback. Other modules read the same file
 * directly (read only), so a switch works from boot on, also before the menu was ever opened. A missing
 * or damaged file means the default. A new switch is one constant here, one row in the broker's mibr_switch_defs
 * and its menu row.
 */
final class MibrDurableSwitch {
    private static final String[] ON_OFF={"off","on"};
    /** "CarPlay-Navigation": route guidance of the iPhone in the cockpit. */
    static final MibrDurableSwitch CARPLAY_NAV=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-carplay-nav.conf","MIBR_CARPLAY_NAV/1","CARPLAY_NAV","carplay_nav",ON_OFF,"off");
    /** "Diagnostic logs on SD card"; the cockpit supervisor script reads the same file. */
    static final MibrDurableSwitch SD_LOG=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-sd-log.conf","MIBR_SD_LOG/1","SD_LOG","sd_log",ON_OFF,"off");
    /** The line above the cockpit map: distance and target, street only, or nothing. */
    static final MibrDurableSwitch NAV_TEXT=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-nav-line.conf","MIBR_NAV_LINE/1","NAV_LINE","nav_line",
        new String[]{"dist","street","off"},"dist");
    /** The CarPlay map: follow the car, always light, always dark. */
    static final MibrDurableSwitch NAV_NIGHT=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-nav-night.conf","MIBR_NAV_NIGHT/1","NAV_NIGHT","nav_night",
        new String[]{"auto","light","dark"},"auto");
    /** Where the arrows come from; "phone" also works while the stock map is in the cockpit. */
    static final MibrDurableSwitch NAV_SOURCE=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-nav-source.conf","MIBR_NAV_SOURCE/1","NAV_SOURCE","nav_source",
        new String[]{"auto","stock","phone"},"auto");
    /** Side panel arrow, the small symbol in the lane strip at the top, or both. */
    static final MibrDurableSwitch NAV_DISPLAY=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-nav-display.conf","MIBR_NAV_DISPLAY/1","NAV_DISPLAY","nav_display",
        new String[]{"side","top","both"},"side");
    /** Arrival time or remaining travel time at the bottom. */
    static final MibrDurableSwitch NAV_BOTTOM=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-nav-bottom.conf","MIBR_NAV_BOTTOM/1","NAV_BOTTOM","nav_bottom",
        new String[]{"eta","rtt"},"eta");
    /** Side streets drawn into the arrow. */
    static final MibrDurableSwitch NAV_SIDE=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-nav-side.conf","MIBR_NAV_SIDE/1","NAV_SIDE","nav_side",ON_OFF,"on");
    /** Real lane guidance from the phone. */
    static final MibrDurableSwitch NAV_LANES=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-nav-lanes.conf","MIBR_NAV_LANES/1","NAV_LANES","nav_lanes",ON_OFF,"on");
    /** Safe areas as "x,y,w,h"; GEN2 reads the same files when CarPlay connects. */
    static final MibrDurableSwitch SAFE_VOLL=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-safe-voll.conf","MIBR_SAFE_VOLL/1","SAFE_VOLL","safe_voll",null,"0,58,1010,248");
    static final MibrDurableSwitch SAFE_WIDE=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-safe-wide.conf","MIBR_SAFE_WIDE/1","SAFE_WIDE","safe_wide",null,"200,58,590,248");
    static final MibrDurableSwitch SAFE_CENTER=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-safe-center.conf","MIBR_SAFE_CENTER/1","SAFE_CENTER","safe_center",null,"370,58,256,248");
    /** "Permanent" of the expert mode; "until restart" lives in MibrExpert. */
    static final MibrDurableSwitch EXPERT_MODE=new MibrDurableSwitch(
        "/mnt/app/root/altscreen-u2/config/mibr-expert-mode.conf","MIBR_EXPERT_MODE/1","EXPERT_MODE","expert_mode",ON_OFF,"off");
    static final MibrDurableSwitch[] ALL={CARPLAY_NAV,SD_LOG,NAV_TEXT,NAV_NIGHT,NAV_SOURCE,NAV_DISPLAY,NAV_BOTTOM,NAV_SIDE,NAV_LANES,
        SAFE_VOLL,SAFE_WIDE,SAFE_CENTER,EXPERT_MODE};

    final String file,verb,capability;
    private final String magic;
    final String[] values;
    private final String compiledDefault;
    private String defaultValue;
    private String value,revision;
    private boolean writer;
    private String message;
    private long fileStamp=-1L,fileLength=-1L;
    private String fileValue;
    /* Session state of the menu's broker connection. */
    boolean available,asked,setInFlight;

    private MibrDurableSwitch(String file,String magic,String verb,String capability,String[] values,String defaultValue){
        this.file=file;this.magic=magic+"\nrevision=";this.verb=verb;this.capability=capability;
        this.values=values;compiledDefault=defaultValue;this.defaultValue=defaultValue;value=defaultValue;fileValue=defaultValue;
    }

    /** The platform default if the file has a valid one, else the compiled one. */
    final synchronized String defaultValue(){
        String platform=MibrPlatformDefaults.get(capability);
        defaultValue=valid(platform)?platform:compiledDefault;
        return defaultValue;
    }
    boolean valid(String v){
        if(values==null)return MibrSafeArea.parse(v)!=null;
        for(int i=0;i<values.length;i++)if(values[i].equals(v))return true;
        return false;
    }
    synchronized String value(){return value;}
    synchronized String revision(){return revision;}
    synchronized boolean writable(){return writer&&revision!=null;}
    synchronized String message(){return MibrI18n.localize(message);}
    synchronized void loading(){writer=false;revision=null;message=null;}
    synchronized void failed(String why){writer=false;revision=null;message=why;}
    synchronized void saving(){writer=false;message=MibrI18n.pick("Speichern...","Saving...");}
    synchronized void readback(String v,String rev,boolean canWrite){
        if(!valid(v)||rev==null||rev.length()==0)throw new IllegalArgumentException(verb+"_READBACK_INVALID");
        for(int i=0;i<rev.length();i++)
            if(rev.charAt(i)<'0'||rev.charAt(i)>'9')throw new IllegalArgumentException(verb+"_REVISION_INVALID");
        value=v;revision=rev;writer=canWrite;message=null;
        fileStamp=-1L; // readers of the file look again at once
    }

    /** Durable value as the broker wrote it; re-read only when the file changed. */
    synchronized String persistedValue(){
        File f=new File(file);
        long stamp=f.lastModified(),length=f.length();
        if(stamp==fileStamp&&length==fileLength)return fileValue;
        fileStamp=stamp;fileLength=length;fileValue=defaultValue();
        if(stamp==0L||length<=0L||length>=96L)return fileValue;
        FileInputStream in=null;
        try{
            byte[] b=new byte[(int)length];
            in=new FileInputStream(f);
            int n=0,k;
            while(n<b.length&&(k=in.read(b,n,b.length-n))>0)n+=k;
            if(n!=b.length)return fileValue;
            fileValue=parseValue(new String(b,0,n,"US-ASCII"));
        }catch(Throwable t){
            fileValue=defaultValue;
        }finally{
            if(in!=null)try{in.close();}catch(Throwable ignored){}
        }
        return fileValue;
    }
    boolean persistedOn(){return "on".equals(persistedValue());}

    /** Exact canonical file only: "&lt;magic&gt;\nrevision=N\nvalue=X\n"; anything else is the default. */
    String parseValue(String text){
        if(text==null||!text.startsWith(magic))return defaultValue;
        int end=text.indexOf('\n',magic.length());
        if(end<=magic.length())return defaultValue;
        for(int i=magic.length();i<end;i++)if(text.charAt(i)<'0'||text.charAt(i)>'9')return defaultValue;
        String rest=text.substring(end+1);
        if(!rest.startsWith("value=")||!rest.endsWith("\n"))return defaultValue;
        String v=rest.substring(6,rest.length()-1);
        return valid(v)?v:defaultValue;
    }
    boolean parseOn(String text){return "on".equals(parseValue(text));}
}
