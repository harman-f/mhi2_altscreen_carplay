package de.mibr.hmi;

import java.io.File;
import java.io.FileInputStream;
import java.util.zip.CRC32;

/**
 * Read-only view of the shared view profile MIBR_NAV_VIEW_PROFILES/3. The broker is the only writer
 * on the unit; the HTML configurator writes the same format. Key=value lines, last line crc32=&lt;8 hex&gt; over all bytes
 * before it. Re-read only when the file changed; a missing or invalid file returns null (callers then use the legacy
 * per-switch file, the migration source until the broker writes the profile).
 */
final class MibrViewProfile {
    static final String MAGIC="MIBR_NAV_VIEW_PROFILES/3\n";
    private static final Slot MAIN=new Slot(),BACKUP=new Slot();
    private MibrViewProfile(){}

    /** One cached file (path, mtime, length, validated body). */
    private static final class Slot {
        String path,body;
        long stamp=-1L,length=-1L;
        String read(String p){
            File f=new File(p);
            long st=f.lastModified(),len=f.length();
            long age=System.currentTimeMillis()-st;
            boolean racy=st!=0L&&age>=0L&&age<2000L;
            if(!racy&&p.equals(path)&&st==stamp&&len==length)return body;
            path=p;stamp=racy?-1L:st;length=len;body=null;
            if(st==0L||len<=0L||len>=16384L)return null;
            FileInputStream in=null;
            try{
                byte[] b=new byte[(int)len];
                in=new FileInputStream(f);
                int n=0,k;
                while(n<b.length&&(k=in.read(b,n,b.length-n))>0)n+=k;
                if(n!=b.length)return null;
                body=check(new String(b,0,n,"US-ASCII"));
            }catch(Throwable t){
                body=null;
            }finally{
                if(in!=null)try{in.close();}catch(Throwable ignored){}
            }
            return body;
        }
    }

    /** Validated body ("\n" + lines before the crc line) of the profile, else of its .lastgood backup when the main
     *  file exists but is invalid (same rule as the broker and GEN2); null when there is no usable profile. */
    static synchronized String body(String path){
        String b=MAIN.read(path);
        if(b!=null||!new File(path).exists())return b;
        return BACKUP.read(path+".lastgood");
    }

    /** Same rules as profile_check() in mibr_durable_switch.c (magic, printable lines, crc32 last); null if invalid. */
    static String check(String text){
        if(text==null||!text.startsWith(MAGIC)||!text.endsWith("\n"))return null;
        int crc=text.lastIndexOf("\ncrc32=");
        if(crc<0||text.indexOf('\n',crc+1)!=text.length()-1)return null;
        for(int i=0;i<text.length();i++){
            char c=text.charAt(i);
            if(c!='\n'&&(c<0x20||c>0x7e))return null;
        }
        CRC32 sum=new CRC32();
        byte[] b;
        try{b=text.substring(0,crc+1).getBytes("US-ASCII");}catch(Throwable t){return null;}
        sum.update(b,0,b.length);
        String hex=Long.toHexString(sum.getValue());
        while(hex.length()<8)hex="0"+hex;
        if(!text.substring(crc+7,text.length()-1).equals(hex))return null;
        return "\n"+text.substring(MAGIC.length(),crc+1);
    }

    static String get(String body,String key){
        String k="\n"+key+"=";
        int at=body.indexOf(k);
        if(at<0)return null;
        int end=body.indexOf('\n',at+k.length());
        return end<0?null:body.substring(at+k.length(),end);
    }

    /** Value in the menu/broker encoding (on/off, eta/rtt, "x,y,w,h"), or null when missing/unknown. */
    static String decode(String body,String key,int kind){
        if(kind==MibrDurableSwitch.PK_RECT){
            String x=get(body,key+".x"),y=get(body,key+".y"),w=get(body,key+".w"),h=get(body,key+".h");
            return x==null||y==null||w==null||h==null?null:x+","+y+","+w+","+h;
        }
        String v=get(body,key);
        if(v==null)return null;
        if(kind==MibrDurableSwitch.PK_BOOL)return "true".equals(v)?"on":"false".equals(v)?"off":null;
        if(kind==MibrDurableSwitch.PK_BOTTOM)return "remaining".equals(v)?"rtt":"eta".equals(v)?"eta":null;
        return v;
    }
}
