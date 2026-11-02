package de.mibr.hmi;

public final class MibrElementEngineTest {
    private static int checks;
    private static void eq(Object a,Object b){
        checks++;if(a==null?b!=null:!a.equals(b))
            throw new AssertionError("expected="+a+" actual="+b);
    }
    private static void yes(boolean ok){checks++;if(!ok)throw new AssertionError("check "+checks);}
    private static interface Run {void run();}
    private static void reject(Run r){
        checks++;try{r.run();throw new AssertionError("EXPECTED_REJECTION "+checks);}
        catch(IllegalArgumentException expected){}
        catch(IllegalStateException expected){}
    }
    private static MibrElementSpec[] elements(){
        return new MibrElementSpec[]{
            MibrElementSpec.bool("a.boolean","Checkbox",false),
            MibrElementSpec.choice("a.choice","Dropdown",new String[]{"yes","no","user"},false),
            MibrElementSpec.slider("a.slider","Slider",-9,9,3),
            MibrElementSpec.axis2("a.xy","Balance/Fader",-4,4,2,-6,6,3),
            MibrElementSpec.spin("a.spin","SpinLabel",new String[]{"12h","24h"},true),
            MibrElementSpec.input("a.input","Speller",5,false),
            MibrElementSpec.input("a.mask","Masked speller",8,true),
            MibrElementSpec.info("a.info","Versions"),
            MibrElementSpec.confirm("a.confirm","Reset?"),
            MibrElementSpec.status("a.status","Status"),
            MibrElementSpec.progress("a.progress","Progress"),
            MibrElementSpec.action("a.action","Download"),
            MibrElementSpec.link("a.link","Nested","child")
        };
    }
    private static void validation(){
        MibrElementSpec[] s=elements();
        eq("0",s[0].validate("0"));eq("1",s[0].validate("1"));
        reject(new Run(){public void run(){elements()[0].validate("unknown");}});
        eq("user",s[1].validate("user"));
        reject(new Run(){public void run(){elements()[1].validate("automatic");}});
        eq("-9",s[2].validate("-9"));eq("9",s[2].validate("9"));
        reject(new Run(){public void run(){elements()[2].validate("4");}});
        reject(new Run(){public void run(){elements()[2].validate("2147483648");}});
        reject(new Run(){public void run(){elements()[2].validate(" 0");}});
        eq("-4,6",s[3].validate("-4,6"));
        reject(new Run(){public void run(){elements()[3].validate("1,3");}});
        reject(new Run(){public void run(){elements()[3].validate("1,3,4");}});
        eq("24h",s[4].validate("24h"));
        eq("",s[5].validate(""));eq("abcde",s[5].validate("abcde"));
        reject(new Run(){public void run(){elements()[5].validate("abcdef");}});
        reject(new Run(){public void run(){elements()[5].validate("abc\n");}});
        eq("100",s[10].validate("100"));
        reject(new Run(){public void run(){elements()[10].validate("101");}});
        reject(new Run(){public void run(){elements()[8].validate("yes");}});
        reject(new Run(){public void run(){
            MibrElementSpec.choice("choice","Duplicates",new String[]{"yes","yes"},false);}});
        reject(new Run(){public void run(){
            MibrElementSpec.slider("range","Overflow",Integer.MIN_VALUE,Integer.MAX_VALUE,2);}});
        reject(new Run(){public void run(){MibrElementSpec.input("m","Bad",0,false);}});
        String[] choices=new String[]{"a","b"};
        MibrElementSpec copy=MibrElementSpec.choice("copy","copy",choices,false);
        choices[0]="mutated";copy.choices()[1]="mutated";
        eq("a",copy.choices()[0]);eq("b",copy.choices()[1]);
    }
    private static void lifecycle(){
        final MibrElementEngine e=new MibrElementEngine(elements());
        eq("CURRENT: UNKNOWN",e.presentation("a.boolean"));
        e.begin("a.boolean");e.propose("1");
        eq(null,e.draft("a.boolean"));eq("1",e.pendingForWidget());
        e.cancel();eq(null,e.draft("a.boolean"));
        e.begin("a.boolean");e.propose("1");e.acceptDraft();
        eq("DRAFT: 1",e.presentation("a.boolean"));
        eq(null,e.observed("a.boolean"));
        e.observe("a.boolean","0");
        eq("DRAFT: 1",e.presentation("a.boolean"));
        e.discardDraft("a.boolean");eq("CURRENT: 0",e.presentation("a.boolean"));
        e.observe("a.choice","user");eq("CURRENT: user",e.presentation("a.choice"));
        e.begin("a.choice");e.propose("yes");e.acceptDraft();
        eq("DRAFT: yes",e.presentation("a.choice"));
        e.begin("a.spin");
        reject(new Run(){public void run(){e.spin(1);}}); // unknown MUST NOT mean 12h
        e.cancel();e.observe("a.spin","24h");e.begin("a.spin");
        e.spin(1);eq("12h",e.pendingForWidget());e.spin(-1);eq("24h",e.pendingForWidget());
        e.acceptDraft();eq("DRAFT: 24h",e.presentation("a.spin"));
        e.begin("a.xy");e.propose("4,-6");e.acceptDraft();
        eq("DRAFT: 4,-6",e.presentation("a.xy"));
        e.begin("a.mask");e.propose("secret");eq("MASKED",e.pendingForWidget());
        e.acceptDraft();eq("DRAFT: MASKED",e.presentation("a.mask"));
        eq("MASKED",e.draft("a.mask"));
        e.observe("a.mask","secret");eq("MASKED",e.observed("a.mask"));
        e.observe("a.info","Version\nInformation");
        eq("CURRENT: Version\nInformation",e.presentation("a.info"));
        e.observe("a.progress","0");eq("CURRENT: 0",e.presentation("a.progress"));
        reject(new Run(){public void run(){e.observe("a.link","other");}});
        reject(new Run(){public void run(){e.begin("a.status");}});
        reject(new Run(){public void run(){e.begin("a.action");}});
        eq(null,e.localIntent("a.confirm",false));
        eq("LOCAL_INTENT_ONLY:a.confirm",e.localIntent("a.confirm",true));
        eq("LOCAL_INTENT_ONLY:a.action",e.localIntent("a.action",false));
        e.discardAll();eq(null,e.draft("a.xy"));
        e.detach();yes(e.isDetached());eq(null,e.editingId());
        reject(new Run(){public void run(){e.begin("a.boolean");}});
        reject(new Run(){public void run(){e.observe("a.info","x");}});
        reject(new Run(){public void run(){new MibrElementEngine(new MibrElementSpec[]{
            MibrElementSpec.bool("dup","x",false),MibrElementSpec.bool("dup","y",false)});}});
    }
    private static void navigation(){
        MibrElementTree.Page root=new MibrElementTree.Page("root","Settings",new MibrElementSpec[]{
           MibrElementSpec.link("root.first","Submenu","child"),
           MibrElementSpec.status("root.status","Status")});
        MibrElementTree.Page child=new MibrElementTree.Page("child","Submenu",new MibrElementSpec[]{
           MibrElementSpec.link("child.nested","Nested","leaf"),
           MibrElementSpec.info("child.info","Information")});
        MibrElementTree.Page leaf=new MibrElementTree.Page("leaf","Versions",new MibrElementSpec[]{
           MibrElementSpec.info("leaf.text","Text")});
        MibrElementTree tree=new MibrElementTree(new MibrElementTree.Page[]{root,child,leaf},"root");
        yes(!tree.open(1));tree.remember(1,0);yes(tree.open(0));eq("child",tree.current().id);
        tree.remember(1,0);yes(tree.open(0));eq("leaf",tree.current().id);
        yes(tree.back());eq("child",tree.current().id);eq(new Integer(1),new Integer(tree.focus()));
        yes(tree.back());eq("root",tree.current().id);eq(new Integer(1),new Integer(tree.focus()));
        yes(!tree.back());tree.reset();eq("root",tree.current().id);
        reject(new Run(){public void run(){new MibrElementTree(new MibrElementTree.Page[]{
          new MibrElementTree.Page("a","A",new MibrElementSpec[]{MibrElementSpec.link("a.b","B","b")}),
          new MibrElementTree.Page("b","B",new MibrElementSpec[]{MibrElementSpec.link("b.a","A","a")})},"a");}});
        reject(new Run(){public void run(){new MibrElementTree(new MibrElementTree.Page[]{
          new MibrElementTree.Page("a","A",new MibrElementSpec[]{MibrElementSpec.link("missing","Missing","missing")})},"a");}});
        tree.detach();reject(new Run(){public void run(){tree.current();}});
    }
    private static void detail(){
        String[] v=MibrElementDetailRows.lines("key\nWert: unbekannt\nQuelle: unbekannt\nAktivierung: reconnect\nSichttest: kein Schreibzugriff");
        eq(new Integer(5),new Integer(v.length));eq("Wert: unbekannt",v[1]);
        eq("Keine Detailinformationen",MibrElementDetailRows.lines(null)[0]);
        String longLine="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        String[] wrapped=MibrElementDetailRows.lines(longLine);
        yes(wrapped.length>=2);
        for(int i=0;i<wrapped.length;i++)yes(wrapped[i].length()<=52);
        reject(new Run(){public void run(){MibrElementDetailRows.lines("bad\u0000byte");}});
    }
    public static void main(String[] args){
        MibrI18n.forced="de_DE";
        validation();lifecycle();navigation();detail();
        System.out.println("MIBR_TYPED_OEM_ELEMENTS_HOST_PASS checks="+checks+
          " kinds=12 nested_back=PASS draft_unknown=PASS no_IO=PASS");
    }
}
