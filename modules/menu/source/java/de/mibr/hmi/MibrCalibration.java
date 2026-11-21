package de.mibr.hmi;

import java.io.File;
import java.io.FileOutputStream;

/**
 * "Kalibrierbild": GEN2 shows a looped test-pattern clip while this marker exists; its one-line content is the pattern id (off, grid, black, white, contrast, motion). RAM only; leaving the menu removes it, and
 * GEN2 ignores a marker older than ten minutes.
 */
final class MibrCalibration {
    private MibrCalibration(){}
    /** Test seam. */
    static String marker="/tmp/mibr-calib.enabled";

    /** Pattern ids in menu order; "off" means no marker. */
    static final String[] IDS={"off","grid","black","white","contrast","motion"};
    static final String DEFAULT_ON="grid";

    static boolean on(){return new File(marker).exists();}
    /** Current pattern id: missing marker "off"; "1", empty or unknown content (old toggle) "grid". */
    static String get(){
        File f=new File(marker);
        if(!f.exists())return "off";
        java.io.FileInputStream in=null;
        try{
            in=new java.io.FileInputStream(f);
            byte[] buf=new byte[32];
            int n=in.read(buf);
            String s=n>0?new String(buf,0,n,"ISO-8859-1").trim():"";
            for(int i=1;i<IDS.length;i++)if(IDS[i].equals(s))return IDS[i];
        }catch(Throwable t){
            // unreadable: the marker exists, so show the default pattern
        }finally{
            if(in!=null)try{in.close();}catch(Throwable ignored){}
        }
        return DEFAULT_ON;
    }
    static void set(boolean value){set(value?DEFAULT_ON:"off");}
    static void set(String id){
        File f=new File(marker);
        if(id==null||"off".equals(id)){
            f.delete();
            return;
        }
        boolean known=false;
        for(int i=1;i<IDS.length;i++)if(IDS[i].equals(id))known=true;
        if(!known)id=DEFAULT_ON;
        FileOutputStream out=null;
        try{
            out=new FileOutputStream(f);
            out.write((id+"\n").getBytes("ISO-8859-1"));
        }catch(Throwable t){
            System.err.println("MIBR_CALIBRATION_FAILED "+t);
        }finally{
            if(out!=null)try{out.close();}catch(Throwable ignored){}
        }
    }
}
