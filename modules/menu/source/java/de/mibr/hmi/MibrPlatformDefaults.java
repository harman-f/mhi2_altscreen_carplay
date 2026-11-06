package de.mibr.hmi;

import java.io.File;
import java.io.FileInputStream;

/**
 * Per-platform defaults ("<capability>=<value>" per line), the same file the broker and GEN2 read, so a port
 * to another car changes this file instead of the code. Re-read when the file's mtime or size changes; a missing file gives no values.
 */
final class MibrPlatformDefaults {
    private static final String FILE="/mnt/app/root/mibr/config/platform/defaults.conf";
    /** Test seam; production keeps the constant. */
    static String path=FILE;
    private static String text,textPath;
    private static long textStamp=-1L,textLength=-1L;
    private MibrPlatformDefaults(){}

    /** The raw value for a key, or null. */
    static synchronized String get(String key){
        File f=new File(path);
        long stamp=f.exists()?f.lastModified():-1L,length=f.length();
        /* Racy timestamp: do not trust an mtime within 2 s of now. */
        long age=System.currentTimeMillis()-stamp;
        /* Only a recent past mtime is racy; a unit clock behind the file time keeps the old cache rule. */
        boolean racy=stamp!=-1L&&age>=0L&&age<2000L;
        if(text==null||racy||!path.equals(textPath)||stamp!=textStamp||length!=textLength){
            /* Read while racy: force one more read after the window (-2 never matches). */
            textPath=path;textStamp=racy?-2L:stamp;textLength=length;
            text=read();
        }
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
        File f=new File(path);
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
