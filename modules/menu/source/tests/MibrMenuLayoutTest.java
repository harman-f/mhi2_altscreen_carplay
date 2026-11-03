package de.mibr.hmi;

/** The menu file: checks, placement, expert mode. */
public final class MibrMenuLayoutTest implements MibrCarPlayMenuModel.View {
    private String title;
    private String[] rows;
    public void show(int screen,String title,String[] rows,String detail){this.title=title;this.rows=rows;}

    private static void check(boolean condition,String name){
        if(!condition)throw new AssertionError(name);
    }
    private static byte[] file(String entries,int catalog) throws Exception {
        String body="MIBR_MENU/1\ncatalog="+catalog+"\nbrand=skoda\nname=Test\n"+entries;
        byte[] b=body.getBytes("UTF-8");
        return (body+"crc32="+MibrMenuLayout.crc32(b,b.length)+"\n").getBytes("UTF-8");
    }
    private static byte[] read(String path) throws Exception {
        byte[] b=MibrMenuLayout.read(path);
        check(b!=null,"read "+path);
        return b;
    }
    private static void write(java.io.File f,byte[] b) throws Exception {
        java.io.FileOutputStream out=new java.io.FileOutputStream(f);
        out.write(b);
        out.close();
    }
    private static String refused(byte[] b){
        try{MibrMenuLayout.parse(b);return null;}
        catch(MibrMenuLayout.Invalid bad){return bad.getMessage();}
    }
    private static MibrMenuLayout.Node child(MibrMenuLayout.Node page,String id){
        for(int i=0;i<page.children.size();i++){
            MibrMenuLayout.Node n=(MibrMenuLayout.Node)page.children.elementAt(i);
            if(id.equals(n.id))return n;
        }
        return null;
    }
    public static void main(String[] args) throws Exception {
        MibrI18n.forced="de_DE";
        byte[] known="123456789".getBytes("US-ASCII");
        check("cbf43926".equals(MibrMenuLayout.crc32(known,known.length)),"CRC-32 check value");
        byte[] standard=read(System.getProperty("mibr.menu.standard"));
        MibrMenuLayout s=MibrMenuLayout.parse(standard);
        check(s.skipped==0&&s.root.children.size()==11,"standard menu");
        check(child(child(s.root,"views"),"calib.image").key==MibrPopupEditorModel.CALIB_IMAGE,"calibration picture in Ansichten");
        check(child(s.root,"version")!=null&&child(child(s.root,"advanced"),"menu.load")!=null,"version on top, menu load in advanced");
        check(!child(child(s.root,"advanced"),"expert.mode").expert,"expert mode row is always visible");
        MibrMenuLayout b=MibrMenuLayout.parse(MibrMenuCatalog.BASIC.getBytes("UTF-8"));
        check(b.root.children.size()==2&&child(b.root,"version")!=null&&child(b.root,"advanced").children.size()==1&&child(child(b.root,"advanced"),"menu.load")!=null,"basic menu holds only version and menu load");

        /* every catalog function has a row in this build */
        for(int i=0;i<MibrMenuCatalog.IDS.length;i++){
            String kind=MibrMenuCatalog.KINDS[i];
            if(!kind.endsWith("page")&&!"hint".equals(kind)&&!"action".equals(kind))
                check(MibrMenuFunctions.key(MibrMenuCatalog.IDS[i])>=0,"function "+MibrMenuCatalog.IDS[i]);
        }

        /* damage */
        byte[] flipped=(byte[])standard.clone();
        flipped[40]^=1;
        check("CHECKSUM".equals(refused(flipped)),"flipped byte");
        byte[] cut=new byte[standard.length-1];
        System.arraycopy(standard,0,cut,0,cut.length);
        check("CHECKSUM".equals(refused(cut)),"cut file");
        check("EMPTY".equals(refused(null))&&"EMPTY".equals(refused(new byte[0])),"no file");
        check("TOO_LARGE".equals(refused(new byte[MibrMenuLayout.MAX_BYTES+1])),"size");
        check("FORMAT".equals(refused("x\ncrc32=00000000\n".getBytes("US-ASCII")))||
              "CHECKSUM".equals(refused("x\ncrc32=00000000\n".getBytes("US-ASCII"))),"magic");

        /* structure */
        check("PARENT".equals(refused(file("nav_side\tnav_hints\t-\t\t\n",2))),"parent must come first");
        check("PARENT".equals(refused(file("version\troot\t-\t\t\nnav_side\tversion\t-\t\t\n",2))),"fixed page takes no children");
        check("DUPLICATE".equals(refused(file("nav_side\troot\t-\t\t\nnav_side\troot\t-\t\t\n",2))),"unique IDs");
        check("TITLE".equals(refused(file("page.1\troot\t-\t\t\n",2))),"new page needs titles");
        check("FIELDS".equals(refused(file("nav_side\troot\t-\t\n",2))),"five fields");
        check("FIELDS".equals(refused(file("nav_side\troot\tq\t\t\n",2))),"flags");
        check("DEPTH".equals(refused(file("page.1\troot\t-\ta\ta\npage.2\tpage.1\t-\ta\ta\npage.3\tpage.2\t-\ta\ta\npage.4\tpage.3\t-\ta\ta\npage.5\tpage.4\t-\ta\ta\npage.6\tpage.5\t-\ta\ta\n",2))),"depth");

        check("EXPERT_LOCKED".equals(refused(file("version\troot\tx\t\t\n",2))),"version is never expert only");
        check("EXPERT_LOCKED".equals(refused(file("page.1\troot\tx\ta\ta\nmenu.load\tpage.1\t-\t\t\n",2))),"nor through its page");

        /* placement, titles, unknown IDs, required rows */
        MibrMenuLayout m=MibrMenuLayout.parse(file(
            "root\t-\t-\tMein Menü\tMy menu\n"+
            "page.1\troot\t-\tNavi\tNav\n"+
            "nav_side\tpage.1\t-\tStraßen\tStreets\n"+
            "future.page\tpage.1\t-\t\t\n"+
            "future.row\tfuture.page\t-\t\t\n"+
            "nav_lanes\troot\tx\t\t\n"+
            "hint.1\tpage.1\t-\tText\tText\n",2));
        check(m.skipped==2,"unknown IDs reported");
        check("Mein Menü".equals(m.root.title()),"menu title");
        MibrMenuLayout.Node page=child(m.root,"page.1");
        check("Straßen".equals(child(page,"nav_side").title())&&child(page,"nav_side").key==MibrPopupEditorModel.NAV_SIDE,"moved and renamed");
        check(child(page,"hint.1").kind==MibrMenuLayout.NOTE,"free hint");
        check(child(m.root,"nav_lanes").expert,"expert flag");
        check(child(m.root,"menu.load")!=null&&child(m.root,"version")!=null&&child(m.root,"expert.mode")!=null,"required rows come back");
        check(child(m.root,"carplay_nav")==null,"a function not in the file is unused");
        /* a function newer than the file is not lost */
        MibrMenuLayout newer=MibrMenuLayout.parse(file("advanced\troot\t-\t\t\n",1));
        check(child(child(newer.root,"advanced"),"calib.image")!=null,"new function appended");

        /* calibration marker */
        java.io.File marker=java.io.File.createTempFile("mibr-calib",".enabled");
        marker.delete();
        MibrCalibration.marker=marker.getPath();
        check(!MibrCalibration.on(),"off without the marker");
        MibrCalibration.set(true);
        check(MibrCalibration.on(),"on with the marker");
        MibrCalibration.set(false);
        check(!MibrCalibration.on(),"off again");
        check(new MibrPopupEditorModel().directToggle(MibrPopupEditorModel.CALIB_IMAGE),"a checkbox");
        MibrPopupEditorModel calib=new MibrPopupEditorModel();
        calib.setAvailable(true);
        calib.readback(MibrPopupEditorModel.CALIB_IMAGE,"off");
        check(calib.toggle(MibrPopupEditorModel.CALIB_IMAGE)&&"on".equals(calib.draft(MibrPopupEditorModel.CALIB_IMAGE)),"the checkbox toggles");

        /* expert mode */
        MibrExpert.session(false);
        check(!MibrExpert.on()&&"off".equals(MibrExpert.choice()),"off by default");
        MibrExpert.session(true);
        check(MibrExpert.on()&&"session".equals(MibrExpert.choice()),"until restart");
        MibrExpert.session(false);

        /* no stored file: the basic menu with a note */
        java.io.File stored=java.io.File.createTempFile("mibr-menu",".conf");
        stored.delete();
        stored.deleteOnExit();
        MibrMenuLayout.storedPath=stored.getPath();
        MibrMenuLayoutTest view=new MibrMenuLayoutTest();
        MibrCarPlayMenuModel menu=new MibrCarPlayMenuModel(view);
        menu.open();
        check(view.rows.length==3&&view.rows[0].indexOf("Kein Menü gespeichert")>=0&&menu.noteRow(0)&&"Version".equals(view.rows[1]),"basic menu with a note");
        menu.select(2);
        check(view.rows.length==1&&"Menü laden: Grundmenü".equals(view.rows[0])&&menu.loadRow(0),"only menu load");
        menu.back();

        /* a damaged file: same menu, the reason on top */
        write(stored,"damaged\n".getBytes("US-ASCII"));
        MibrMenuLayout.loaded();
        menu.open();
        check(view.rows[0].indexOf("Menüdatei defekt (CHECKSUM)")>=0,"damage is named");

        /* a stored file with expert entries: the switch comes along, the entries follow it */
        write(stored,file("advanced\troot\t-\t\t\nnav_lanes\tadvanced\tx\t\t\nmenu.load\tadvanced\t-\t\t\nversion\troot\t-\t\t\n",2));
        MibrMenuLayout.forget();
        menu.open();
        check(view.rows.length==2&&"Erweitert".equals(view.rows[0]),"no note with a good file");
        menu.select(0);
        check(view.rows.length==2&&"Expertenmodus".equals(view.rows[1])&&menu.keyForRow(1)==MibrPopupEditorModel.EXPERT_MODE,"expert entry hidden");
        check(view.rows[0].equals("Menü laden: aus Datei"),"status from file");
        MibrExpert.session(true);
        menu.refresh();
        check(view.rows.length==3&&"Spurempfehlung".equals(view.rows[0]),"expert entry shown");
        MibrPopupEditorModel editor=new MibrPopupEditorModel();
        check(editor.options(MibrPopupEditorModel.EXPERT_MODE).length==3&&"Bis Neustart".equals(editor.label(MibrPopupEditorModel.EXPERT_MODE,"session")),"three choices");
        MibrExpert.session(false);
        menu.refresh();
        check(view.rows.length==2,"expert entry gone again");

        /* an older file may carry the expert flag on the switch itself */
        MibrMenuLayout older=MibrMenuLayout.parse(file("advanced\troot\t-\t\t\nexpert.mode\tadvanced\tx\t\t\n",2));
        check(!child(child(older.root,"advanced"),"expert.mode").expert,"the switch is never hidden");

        /* a load replaces the tree */
        menu.close();menu.open();menu.select(0);
        MibrCarPlayMenuModel.Snapshot old=menu.snapshot();
        MibrMenuLayout.loaded();
        menu.refresh();
        check(menu.screen()==MibrCarPlayMenuModel.CATEGORIES,"back to the main list");
        menu.select(0);
        menu.restore(old);
        check(menu.screen()==MibrCarPlayMenuModel.CATEGORIES,"a snapshot of the old tree opens the main list");
        System.out.println("MIBR_MENU_LAYOUT_PASS");
    }
}
