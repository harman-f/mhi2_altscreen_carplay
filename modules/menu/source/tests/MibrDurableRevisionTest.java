package de.mibr.hmi;

import java.io.File;
import java.io.FileOutputStream;

/** Canonical revision rule (shared with mibr_durable_switch.c decimal()), platform defaults reload, racy cache. */
public final class MibrDurableRevisionTest {
    private static void check(boolean c,String name){if(!c)throw new AssertionError(name);}
    private static void write(File f,String s) throws Exception {
        FileOutputStream o=new FileOutputStream(f);
        o.write(s.getBytes("US-ASCII"));
        o.close();
    }
    private static String digits21(){return "123456789012345678901";}
    public static void main(String[] args) throws Exception {
        String[] ok={"0","1","18446744073709551615","10","9999999999999999999"};
        String[] bad={"01","007","","18446744073709551616","99999999999999999999",digits21(),"1a","a","-1","+1","1 "};
        File dir=File.createTempFile("mibr-durable",".d");
        dir.delete();dir.mkdir();
        File sw=new File(dir,"sw.conf");
        MibrDurableSwitch d=new MibrDurableSwitch(sw.getPath(),"MIBR_NAV_LINE/1","NAV_LINE","nav_line",
            new String[]{"dist","street","off"},"dist");
        String magic="MIBR_NAV_LINE/1\nrevision=";
        for(int i=0;i<ok.length;i++){
            check(MibrDurableSwitch.canonicalRevision(ok[i],0,ok[i].length()),"ok "+ok[i]);
            check("street".equals(d.parseValue(magic+ok[i]+"\nvalue=street\n")),"parse ok "+ok[i]);
            d.readback("street",ok[i],true);
        }
        for(int i=0;i<bad.length;i++){
            check(!MibrDurableSwitch.canonicalRevision(bad[i],0,bad[i].length()),"bad "+bad[i]);
            check("dist".equals(d.parseValue(magic+bad[i]+"\nvalue=street\n")),"parse bad "+bad[i]);
            boolean threw=false;
            try{d.readback("street",bad[i],true);}catch(IllegalArgumentException e){threw=true;}
            check(threw,"readback bad "+bad[i]);
        }
        check(MibrDurableSwitch.canonicalRevision("x12y",1,3),"range");

        /* racy cache: same length, different value, immediately */
        write(sw,"MIBR_NAV_LINE/1\nrevision=1\nvalue=dist\n");
        check("dist".equals(d.persistedValue()),"first read");
        write(sw,"MIBR_NAV_LINE/1\nrevision=2\nvalue=off\n");
        sw.setLastModified(System.currentTimeMillis());
        check("off".equals(d.persistedValue()),"racy reread");

        /* Regression probe: same size AND same mtime. The first read happens
           while the mtime is racy; a second write in the same tick keeps
           size and mtime. After the racy window a read must still see it. */
        long tick=System.currentTimeMillis()-500L;
        write(sw,"MIBR_NAV_LINE/1\nrevision=3\nvalue=dist\n");
        sw.setLastModified(tick);
        check("dist".equals(d.persistedValue()),"probe first read");
        long seen=sw.lastModified();
        write(sw,"MIBR_NAV_LINE/1\nrevision=10\nvalue=off\n");
        sw.setLastModified(seen);
        check(sw.lastModified()==seen,"probe mtime unchanged");
        check(sw.length()==("MIBR_NAV_LINE/1\nrevision=3\nvalue=dist\n").length(),"probe size unchanged");
        File pd0=new File(dir,"pd0.conf");
        MibrPlatformDefaults.path=pd0.getPath();
        write(pd0,"nav_line=dist\n");
        pd0.setLastModified(tick);
        check("dist".equals(MibrPlatformDefaults.get("nav_line")),"probe pd first");
        long seenPd=pd0.lastModified();
        write(pd0,"nav_line=offf\n");
        pd0.setLastModified(seenPd);
        Thread.sleep(2100L);
        check("off".equals(d.persistedValue()),"probe same size+mtime after window");
        check("offf".equals(MibrPlatformDefaults.get("nav_line")),"probe pd same size+mtime");
        pd0.delete();

        /* Old fixed timestamps (no racy window involved): a same-size rewrite
           that carries a different old mtime, e.g. a restore that keeps the
           backup's mtime, is seen. A rewrite that keeps both size and the
           exact old mtime is a documented limit of any mtime+size cache. */
        long old1=System.currentTimeMillis()-60000L,old2=old1-60000L;
        write(sw,"MIBR_NAV_LINE/1\nrevision=11\nvalue=off\n");
        sw.setLastModified(old1);
        check("off".equals(d.persistedValue()),"old stamp first");
        write(sw,"MIBR_NAV_LINE/1\nrevision=4\nvalue=dist\n");
        sw.setLastModified(old2);
        check("dist".equals(d.persistedValue()),"older stamp same size seen");

        /* platform defaults: change, new length, delete */
        File pd=new File(dir,"pd.conf");
        MibrPlatformDefaults.path=pd.getPath();
        check(MibrPlatformDefaults.get("nav_line")==null,"absent");
        write(pd,"nav_line=street\n");
        check("street".equals(MibrPlatformDefaults.get("nav_line")),"street");
        write(pd,"nav_line=dist\nnav_night=dark\n");
        check("dist".equals(MibrPlatformDefaults.get("nav_line")),"new length");
        check("dark".equals(MibrPlatformDefaults.get("nav_night")),"second key");
        write(pd,"nav_line=off\nnav_night=dark\n");
        check("off".equals(MibrPlatformDefaults.get("nav_line")),"same length");
        pd.delete();
        check(MibrPlatformDefaults.get("nav_line")==null,"deleted");
        sw.delete();dir.delete();
        System.out.println("MibrDurableRevisionTest PASS");
    }
}
