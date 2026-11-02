package de.mibr.hmi;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;

/**
 * Read-only view of the platform watchdog (/tmp/mibr-watch.state, written by mibr-watch.ksh) for the
 * Diagnose page, plus the marker that tells it the HMI came up.
 */
final class MibrServiceHealth {
    private static final String STATE="/tmp/mibr-watch.state";
    private static final String HMI_UP="/tmp/mibr-hmi-up";
    private MibrServiceHealth(){}

    /** Never affects the HMI start. */
    static void markHmiUp(){
        FileOutputStream out=null;
        try{out=new FileOutputStream(HMI_UP);out.write('1');}
        catch(Throwable ignored){}
        finally{if(out!=null)try{out.close();}catch(Throwable ignored){}}
    }

    static String statusLine(){
        return MibrI18n.pick("Dienste: ","Services: ")+summary(read());
    }

    /** "broker=ok\nkey40d=restarted:1\n" gives "broker ok, key40d restarted:1"; only what is not ok is listed. */
    static String summary(String text){
        if(text==null)return MibrI18n.pick("keine Überwachung","no watchdog");
        StringBuffer out=new StringBuffer();
        int at=0;
        while(at<text.length()){
            int end=text.indexOf('\n',at);
            if(end<0)end=text.length();
            String line=text.substring(at,end);
            at=end+1;
            int eq=line.indexOf('=');
            if(eq<=0||line.endsWith("=ok"))continue;
            if(out.length()>0)out.append(", ");
            out.append(line.substring(0,eq)).append(' ').append(line.substring(eq+1));
        }
        return out.length()==0?"OK":out.toString();
    }

    private static String read(){
        File f=new File(STATE);
        long length=f.length();
        if(length<=0L||length>512L)return null;
        FileInputStream in=null;
        try{
            byte[] b=new byte[(int)length];
            in=new FileInputStream(f);
            int n=0,k;
            while(n<b.length&&(k=in.read(b,n,b.length-n))>0)n+=k;
            return new String(b,0,n,"US-ASCII");
        }catch(Throwable t){
            return null;
        }finally{
            if(in!=null)try{in.close();}catch(Throwable ignored){}
        }
    }
}
