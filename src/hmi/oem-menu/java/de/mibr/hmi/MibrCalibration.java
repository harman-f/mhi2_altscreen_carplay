package de.mibr.hmi;

import java.io.File;
import java.io.FileOutputStream;

/**
 * "Kalibrierbild": GEN2 shows a looped grid clip while this marker exists. RAM only; leaving the menu removes it, and
 * GEN2 ignores a marker older than ten minutes.
 */
final class MibrCalibration {
    private MibrCalibration(){}
    /** Test seam. */
    static String marker="/tmp/mibr-calib.enabled";

    static boolean on(){return new File(marker).exists();}
    static void set(boolean value){
        File f=new File(marker);
        if(!value){
            f.delete();
            return;
        }
        FileOutputStream out=null;
        try{
            out=new FileOutputStream(f);
            out.write('1');
        }catch(Throwable t){
            System.err.println("MIBR_CALIBRATION_FAILED "+t);
        }finally{
            if(out!=null)try{out.close();}catch(Throwable ignored){}
        }
    }
}
