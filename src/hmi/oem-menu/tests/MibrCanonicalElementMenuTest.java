package de.mibr.hmi;

/** r10 typed tree: 6 root settings + Erweitert; Diagnose nested in Erweitert. */
public final class MibrCanonicalElementMenuTest {
    private static void ok(boolean p,String m){if(!p)throw new AssertionError("CANONICAL_TYPED_MENU "+m);}
    private static int settings=0,diagnostic=0;
    private static void visit(MibrElementTree t){
        MibrElementTree.Page p=t.current();
        for(int k=0;k<p.size();k++){
            MibrElementSpec s=p.row(k);
            if(s.kind==MibrElementSpec.LINK){ok(t.open(k),"link opens");visit(t);ok(t.back(),"back");continue;}
            if(s.kind==MibrElementSpec.INFO){ok("diagnostics".equals(p.id)||"views".equals(p.id),"info only in Diagnose and Ansichten");diagnostic++;continue;}
            ok(!"hidden".equals(MibrSettingsCatalog.UI_SECTIONS[index(s.id)]),"visible "+s.id);
            ok(!"navigation.url".equals(s.id)&&!"preset.id".equals(s.id),"hidden in HMI "+s.id);
            ok(s.kind==MibrElementSpec.CHOICE,"choice "+s.id);
            if("viewarea.selected".equals(s.id)){
                String[] v=s.choices();ok(!s.readOnly&&v.length==3&&"2".equals(v[0])&&"1".equals(v[1])&&"0".equals(v[2]),"view dropdown Center/Voll/Wide");
                ok("Ansicht".equals(s.label),"view label");
            }
            if("carplay.enabled".equals(s.id)){
                String[] v=s.choices();ok(!s.readOnly&&v.length==2&&s.isOption("1")&&s.isOption("0"),"carplay dropdown (runtime pause)");
                ok("Erweitert".equals(p.title),"carplay under Erweitert");
            }
            if("navigation.compass".equals(s.id)||"navigation.ETA".equals(s.id)||"navigation.speedLimit".equals(s.id))
                ok(s.isOption("yes")&&s.isOption("no"),"yes/no wire kept");
            if("maxFPS".equals(s.id))ok(s.choices().length==4&&!s.isOption("35"),"fps");
            if("sourceVersion".equals(s.id))ok(s.readOnly&&s.choices().length==2,"source pending validator");
            settings++;
        }
    }
    public static void main(String[] args){
        MibrI18n.forced="de_DE";
        MibrElementTree t=MibrCanonicalElementMenu.createTree();
        MibrElementTree.Page root=t.current();
        ok(root.size()==8,"root 8");
        for(int i=0;i<6;i++)ok(root.row(i).kind!=MibrElementSpec.LINK,"root setting "+i);
        ok(root.row(6).kind==MibrElementSpec.LINK&&"Ansichten".equals(root.row(6).label),"Ansichten link");
        ok(root.row(7).kind==MibrElementSpec.LINK&&"Erweitert".equals(root.row(7).label),"Erweitert link");
        visit(t);
        ok(settings==9&&diagnostic==2,"9 settings + 2 info rows (Ansichten, Diagnose), got "+settings+"/"+diagnostic);
        MibrElementEngine e=MibrCanonicalElementMenu.createEngine();
        ok(e.count()==14,"engine count "+e.count()); // 6 root + Ansichten + info + Erweitert + 3 + Diagnose link + info
        e.detach();t.detach();
        System.out.println("MIBR_CANONICAL_TYPED_TREE_PASS keys=48 visible=9 hidden=39 root=8 nested=diagnostics");
    }
    private static int index(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)
            if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        throw new AssertionError("NONCANONICAL_KEY "+key);
    }
}
