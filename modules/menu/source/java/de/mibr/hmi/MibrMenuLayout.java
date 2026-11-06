package de.mibr.hmi;

import java.io.File;
import java.io.FileInputStream;
import java.util.Hashtable;
import java.util.Vector;

/**
 * The menu structure, from the stored menu file or else from the basic menu built into the JAR. Functions stay in
 * the code under a fixed ID; the file only says where they sit, what they are called and who sees them.
 * Format: tools/menu-editor/MENU_FILE_FORMAT.md.
 */
final class MibrMenuLayout {
    static final String STORED="/mnt/app/root/mibr/config/menu/layout.conf";
    /** Test seam. */
    static String storedPath=STORED;
    static final String SD_FILE="/net/mmx/fs/sda0/mibr-menu/mibr-menu.txt";
    static final int MAX_BYTES=16384,MAX_DEPTH=5,MAX_TITLE=60;
    static final int PAGE=0,KEY=1,DIAGNOSTICS=2,VERSION=3,NOTE=4,LOAD=5;

    static final class Node {
        final String id;
        final int kind,key,number;
        final boolean expert;
        final Node parent;
        final Vector children=new Vector();
        private String de,en;
        Node(String id,int kind,int key,int number,boolean expert,Node parent,String de,String en){
            this.id=id;this.kind=kind;this.key=key;this.number=number;this.expert=expert;this.parent=parent;this.de=de;this.en=en;
        }
        String title(){return MibrI18n.pick(de,en);}
        boolean opens(){return kind==PAGE||kind==DIAGNOSTICS||kind==VERSION;}
    }

    final Node root;
    /** Number of unknown IDs left out of the file. */
    final int skipped;
    private final Vector pages=new Vector();
    private boolean anyExpert;

    /** Refused file: the reason, one of the codes below; never a partial menu. */
    static final class Invalid extends Exception {
        Invalid(String code){super(code);}
    }

    private MibrMenuLayout(String text) throws Invalid {
        root=new Node("root",PAGE,-1,-1,false,null,MibrMenuDefinition.TITLE_DE,MibrMenuDefinition.TITLE_EN);
        skipped=build(text);
    }

    /** CRC-32 as in zip. A small loop: a menu file is read once per menu opening. */
    static String crc32(byte[] b,int length){
        int crc=~0;
        for(int i=0;i<length;i++){
            crc^=b[i]&0xff;
            for(int k=0;k<8;k++)crc=(crc>>>1)^(0xedb88320&-(crc&1));
        }
        String hex=Integer.toHexString(~crc);
        return "00000000".substring(hex.length())+hex;
    }

    /** The whole check: size, magic, checksum, structure. */
    static MibrMenuLayout parse(byte[] file) throws Invalid {
        if(file==null||file.length==0)throw new Invalid("EMPTY");
        if(file.length>MAX_BYTES)throw new Invalid("TOO_LARGE");
        int end=file.length;
        if(file[end-1]!='\n')throw new Invalid("CHECKSUM");
        int at=end-2;
        while(at>=0&&file[at]!='\n')at--;
        if(at<0)throw new Invalid("CHECKSUM");
        String text,last;
        try{
            text=new String(file,0,at+1,"UTF-8");
            last=new String(file,at+1,end-at-2,"US-ASCII");
        }catch(java.io.UnsupportedEncodingException e){throw new Invalid("CHARSET");}
        if(!text.startsWith("MIBR_MENU/1\n"))throw new Invalid("FORMAT");
        if(!last.equals("crc32="+crc32(file,at+1)))throw new Invalid("CHECKSUM");
        return new MibrMenuLayout(text);
    }

    private static String[] fields(String line,int count) throws Invalid {
        String[] out=new String[count];
        int from=0;
        for(int i=0;i<count;i++){
            int tab=line.indexOf('\t',from);
            if(i==count-1){
                if(tab>=0)throw new Invalid("FIELDS");
                tab=line.length();
            }else if(tab<0)throw new Invalid("FIELDS");
            out[i]=line.substring(from,tab);
            from=tab+1;
        }
        return out;
    }
    private static boolean validId(String id){
        if(id.length()==0||id.length()>64)return false;
        for(int i=0;i<id.length();i++){
            char c=id.charAt(i);
            if(!(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='.'))return false;
        }
        return true;
    }
    private static int catalogIndex(String id){
        for(int i=0;i<MibrMenuCatalog.IDS.length;i++)if(id.equals(MibrMenuCatalog.IDS[i]))return i;
        return -1;
    }
    private static int kindOf(String catalogKind,String id){
        if("page".equals(catalogKind))return PAGE;
        if("fixedpage".equals(catalogKind))return "version".equals(id)?VERSION:DIAGNOSTICS;
        if("hint".equals(catalogKind))return NOTE;
        if("action".equals(catalogKind))return LOAD;
        return KEY;
    }
    private Node node(String id,int kind,int key,boolean expert,Node parent,String de,String en){
        Node n=new Node(id,kind,key,kind==PAGE||kind==DIAGNOSTICS||kind==VERSION?pages.size():-1,expert,parent,de,en);
        if(n.number>=0)pages.addElement(n);
        if(expert)anyExpert=true;
        parent.children.addElement(n);
        return n;
    }
    private static int depth(Node n){int d=0;while(n.parent!=null){d++;n=n.parent;}return d;}

    private int build(String text) throws Invalid {
        Hashtable byId=new Hashtable();
        Hashtable dropped=new Hashtable();
        byId.put("root",root);
        int skipped=0,fileCatalog=-1,from=0,line=0;
        while(from<text.length()){
            int nl=text.indexOf('\n',from);
            String s=text.substring(from,nl);
            from=nl+1;
            line++;
            if(line==1)continue;
            if(line==2){
                if(!s.startsWith("catalog="))throw new Invalid("FORMAT");
                try{fileCatalog=Integer.parseInt(s.substring(8));}
                catch(NumberFormatException e){throw new Invalid("FORMAT");}
                continue;
            }
            if(line==3){if(!s.startsWith("brand="))throw new Invalid("FORMAT");continue;}
            if(line==4){if(!s.startsWith("name="))throw new Invalid("FORMAT");continue;}
            String[] f=fields(s,5);
            String id=f[0],de=f[3],en=f[4];
            if(!validId(id))throw new Invalid("FIELDS");
            if(de.length()>MAX_TITLE||en.length()>MAX_TITLE)throw new Invalid("TITLE");
            boolean expert="x".equals(f[2]);
            if(!expert&&!"-".equals(f[2]))throw new Invalid("FIELDS");
            if("root".equals(id)){
                if(de.length()>0)root.de=de;
                if(en.length()>0)root.en=en;
                continue;
            }
            if(byId.get(id)!=null)throw new Invalid("DUPLICATE");
            Node parent=(Node)byId.get(f[1]);
            if(parent==null){
                /* below an unknown ID the entry goes with it, anything else is a broken file */
                if(dropped.get(f[1])==null)throw new Invalid("PARENT");
                dropped.put(id,id);
                skipped++;
                continue;
            }
            if(parent.kind!=PAGE)throw new Invalid("PARENT");
            if(depth(parent)>=MAX_DEPTH)throw new Invalid("DEPTH");
            if(id.startsWith("page.")||id.startsWith("hint.")){
                if(de.length()==0||en.length()==0)throw new Invalid("TITLE");
                byId.put(id,node(id,id.startsWith("page.")?PAGE:NOTE,-1,expert,parent,de,en));
                continue;
            }
            int c=catalogIndex(id);
            if(c<0){dropped.put(id,id);skipped++;continue;}
            byId.put(id,catalogNode(c,expert,parent,de,en));
        }
        if(fileCatalog<0)throw new Invalid("FORMAT");
        /* never without a way to load a menu or to see the version */
        Node fallback=byId.get("advanced")!=null?(Node)byId.get("advanced"):root;
        ensure(byId,"menu.load",fallback);
        ensure(byId,"version",root);
        /* functions newer than the file */
        for(int c=0;c<MibrMenuCatalog.IDS.length;c++){
            if(MibrMenuCatalog.SINCE[c]<=fileCatalog||byId.get(MibrMenuCatalog.IDS[c])!=null)continue;
            byId.put(MibrMenuCatalog.IDS[c],catalogNode(c,false,fallback,"",""));
        }
        /* expert entries need their switch */
        if(anyExpert)ensure(byId,"expert.mode",fallback);
        requireVisible((Node)byId.get("menu.load"));
        requireVisible((Node)byId.get("version"));
        return skipped;
    }
    private Node catalogNode(int c,boolean expert,Node parent,String de,String en){
        String id=MibrMenuCatalog.IDS[c];
        int kind=kindOf(MibrMenuCatalog.KINDS[c],id);
        int key=kind==KEY?MibrMenuFunctions.key(id):-1;
        if(kind==KEY&&key<0)throw new IllegalStateException("MIBR_MENU_FUNCTION_UNKNOWN "+id);
        return node(id,kind,key,expert&&!"expert.mode".equals(id),parent,
            de.length()>0?de:MibrMenuCatalog.DE[c],en.length()>0?en:MibrMenuCatalog.EN[c]);
    }
    private void ensure(Hashtable byId,String id,Node parent){
        if(byId.get(id)!=null)return;
        byId.put(id,catalogNode(catalogIndex(id),false,parent,"",""));
    }

    /** The basic entries are always there: never expert only, not even through a page above them. */
    private static void requireVisible(Node n) throws Invalid {
        for(;n!=null;n=n.parent)if(n.expert)throw new Invalid("EXPERT_LOCKED");
    }
    /** Page by its number, or null: root is -1. */
    Node page(int number){
        if(number==-1)return root;
        return number>=0&&number<pages.size()?(Node)pages.elementAt(number):null;
    }

    private static MibrMenuLayout current;
    private static long currentStamp=-2L,currentLength=-2L;
    private static String problem;
    private static String message;
    private static int generation;

    static byte[] read(String path){
        File f=new File(path);
        long length=f.length();
        if(length<=0L||length>MAX_BYTES)return length>MAX_BYTES?new byte[MAX_BYTES+1]:null;
        FileInputStream in=null;
        try{
            byte[] b=new byte[(int)length];
            in=new FileInputStream(f);
            int n=0,k;
            while(n<b.length&&(k=in.read(b,n,b.length-n))>0)n+=k;
            if(n==b.length)return b;
            byte[] part=new byte[n];
            System.arraycopy(b,0,part,0,n);
            return part;
        }catch(Throwable t){
            return null;
        }finally{
            if(in!=null)try{in.close();}catch(Throwable ignored){}
        }
    }
    private static MibrMenuLayout basic(){
        try{
            return parse(MibrMenuCatalog.BASIC.getBytes("UTF-8"));
        }catch(Exception e){
            throw new IllegalStateException("MIBR_MENU_BASIC_INVALID "+e.getMessage());
        }
    }
    /** Stored file, else the basic menu. Cached until the file changes. */
    static synchronized MibrMenuLayout current(){
        File f=new File(storedPath);
        long stamp=f.exists()?f.lastModified():-1L,length=f.length();
        long age=System.currentTimeMillis()-stamp;
        /* Only a recent past mtime is racy; a unit clock behind the file time keeps the old cache rule. */
        boolean racy=stamp!=-1L&&age>=0L&&age<2000L;
        if(!racy&&current!=null&&stamp==currentStamp&&length==currentLength)return current;
        /* Parsed while racy: do not trust this entry once the window has passed (-2 never matches). */
        currentStamp=racy?-2L:stamp;currentLength=length;
        problem=null;
        if(stamp==-1L){current=basic();return current;}
        try{
            current=parse(read(storedPath));
        }catch(Invalid bad){
            System.err.println("MIBR_MENU_STORED_INVALID "+bad.getMessage());
            problem=bad.getMessage();
            current=basic();
        }
        return current;
    }
    /** Why the stored file was refused, or null. */
    static synchronized String storedProblem(){current();return problem;}
    static synchronized boolean storedActive(){current();return currentStamp!=-1L&&problem==null;}
    /** Line for the top of the main list while the basic menu stands in. */
    static String recoveryNote(){
        if(storedActive())return null;
        String code=storedProblem();
        return code!=null?MibrI18n.pick("Menüdatei defekt ("+code+"), Grundmenü aktiv. Erweitert > Menü laden",
            "Menu file damaged ("+code+"), basic menu active. Advanced > Load menu"):
            MibrI18n.pick("Kein Menü gespeichert, Grundmenü aktiv. Erweitert > Menü laden",
            "No menu stored, basic menu active. Advanced > Load menu");
    }
    /** Status behind "Menü laden". */
    static synchronized String status(){
        if(message!=null)return message;
        return storedActive()?MibrI18n.pick("aus Datei","from file"):MibrI18n.pick("Grundmenü","basic menu");
    }
    static synchronized void message(String text){message=text;}
    /** Changes after every successful load: the open menu then rebuilds from the main list. */
    static synchronized int generation(){return generation;}
    static synchronized void loaded(){generation++;}
    /** The next read goes to the file again. */
    static synchronized void forget(){current=null;}
    /** A refusal in the words of the menu row. */
    static String describe(Invalid bad){
        String code=bad.getMessage();
        if("CHECKSUM".equals(code))return MibrI18n.pick("Prüfsumme falsch","wrong checksum");
        if("EMPTY".equals(code))return MibrI18n.pick("keine Datei auf der SD","no file on the SD");
        if("TOO_LARGE".equals(code))return MibrI18n.pick("Datei zu groß","file too large");
        return MibrI18n.pick("Datei ungültig","file invalid")+" ("+code+")";
    }
}
