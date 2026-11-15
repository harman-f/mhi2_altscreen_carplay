package de.mibr.hmi;

/** "Default menu restored": decision logic and the one-shot notice for a refused stored menu file. */
public final class MibrMenuRestoredNoticeTest {
    private static void check(boolean condition,String name){
        if(!condition)throw new AssertionError(name);
    }
    private static byte[] valid() throws Exception {
        String body="MIBR_MENU/1\ncatalog=1\nbrand=skoda\nname=Test\n";
        byte[] b=body.getBytes("UTF-8");
        return (body+"crc32="+MibrMenuLayout.crc32(b,b.length)+"\n").getBytes("UTF-8");
    }
    private static void write(java.io.File f,byte[] b) throws Exception {
        java.io.FileOutputStream out=new java.io.FileOutputStream(f);
        out.write(b);
        out.close();
    }
    public static void main(String[] args) throws Exception {
        check(MibrMenuLayout.restoredNoticeDue(true,"CHECKSUM",false),"corrupt stored file, not shown yet");
        check(!MibrMenuLayout.restoredNoticeDue(true,"CHECKSUM",true),"only once");
        check(!MibrMenuLayout.restoredNoticeDue(false,"EMPTY",false),"no stored file: nothing was restored");
        check(!MibrMenuLayout.restoredNoticeDue(true,null,false),"valid stored file");

        java.io.File f=java.io.File.createTempFile("mibr-layout",".conf");
        f.deleteOnExit();
        MibrMenuLayout.storedPath=f.getPath();
        write(f,valid());
        f.setLastModified(System.currentTimeMillis()-10000L);
        check(MibrMenuLayout.restoredNotice()==null,"no notice for a valid file");
        byte[] bad=valid();
        bad[5]^=1;
        write(f,bad);
        f.setLastModified(System.currentTimeMillis()-9000L);
        MibrMenuLayout.forget();
        String n=MibrMenuLayout.restoredNotice();
        check(n!=null&&(n.equals("Standardmenü wiederhergestellt")||n.equals("Default menu restored")),"notice text: "+n);
        check(MibrMenuLayout.restoredNotice()==null,"second call: already shown");
        check(MibrMenuLayout.storedProblem()!=null,"the default stands in");
        /* a valid load re-arms it for the next corruption */
        write(f,valid());
        f.setLastModified(System.currentTimeMillis()-8000L);
        MibrMenuLayout.forget();
        check(MibrMenuLayout.restoredNotice()==null,"valid again");
        write(f,bad);
        f.setLastModified(System.currentTimeMillis()-7000L);
        MibrMenuLayout.forget();
        check(MibrMenuLayout.restoredNotice()!=null,"next corruption notifies again");
        f.delete();
        MibrMenuLayout.forget();
        check(MibrMenuLayout.restoredNotice()==null,"no file: no restored notice");
        System.out.println("MibrMenuRestoredNoticeTest=PASS");
    }
}
