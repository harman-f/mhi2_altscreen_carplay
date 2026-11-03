package de.mibr.hmi;

import java.io.File;
import java.io.FileInputStream;

/**
 * Per-platform defaults ("<capability>=<value>" per line), the same file the broker and GEN2 read, so a port
 * to another car changes this file instead of the code. Read once; a missing file gives no values.
 */
final class MibrPlatformDefaults {
    private static final String FILE="/mnt/app/root/altscreen-u2/config/mibr-platform-defaults.conf";
    private static String text;
    private MibrPlatformDefaults(){}

    /** The raw value for a key, or null. */
    static synchronized String get(String key){
        if(text==null)text=read();
        return lookup(text,key);
    }

    static String lookup(String content,String key){
        String prefix=key+"=";
        int at=0;
        while(at<content.length()){
            int end=content.indexOf('\n',at);
            if(end<0)end=content.length();
            if(content.startsWith(prefix,at))return content.substring(at+prefix.length(),end);
            at=end+1;
        }
        return null;
    }

    private static String read(){
        File f=new File(FILE);
        long length=f.length();
        if(length<=0L||length>4096L)return "";
        FileInputStream in=null;
        try{
            byte[] b=new byte[(int)length];
            in=new FileInputStream(f);
            int n=0,k;
            while(n<b.length&&(k=in.read(b,n,b.length-n))>0)n+=k;
            return new String(b,0,n,"US-ASCII");
        }catch(Throwable t){
            return "";
        }finally{
            if(in!=null)try{in.close();}catch(Throwable ignored){}
        }
    }
}
