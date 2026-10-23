package de.mibr.hmi;

/**
 * Adapts the EXISTING generated Classic111 48-key catalog/approved UI sections
 * to the typed generic page engine. Not a second registry and not yet wired to
 * the car's V4 row view; that integration has its own source/rendering gate.
 */
public final class MibrCanonicalElementMenu {
    private MibrCanonicalElementMenu(){}
    private static int index(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)
            if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        throw new IllegalArgumentException("CANONICAL_KEY_MISSING");
    }
    public static String displayLabel(String key){
        return MibrSettingsCatalog.label(index(key));
    }
    private static MibrElementSpec entry(String key){
        int i=index(key);
        if("hidden".equals(MibrSettingsCatalog.UI_SECTIONS[i]))
            throw new IllegalArgumentException("HIDDEN_KEY_REQUESTED");
        String label=displayLabel(key);
        String kind=MibrSettingsCatalog.UI_KINDS[i];
        if("carplay.enabled".equals(key)){
            if(!"TOGGLE".equals(kind))throw new IllegalStateException("CARPLAY_BOOLEAN_REGISTRY_DRIFT");
            // r10: Aktiviert/Deaktiviert dropdown under Erweitert, read-only until a
            // qualified session owner exists (native session_control=0).
            return MibrElementSpec.choice(key,label,new String[]{"1","0"},false);
        }
        if("viewarea.selected".equals(key)){
            if(!"CHOICE".equals(kind) || MibrSettingsCatalog.READ_ONLY[i] ||
               !"integer".equals(MibrSettingsCatalog.KINDS[i]))
                throw new IllegalStateException("VIEWAREA_BOOLEAN_REGISTRY_DRIFT");
            String[] wire=new MibrDraftChoiceModel(i).options();
            if(wire.length!=3 || !"2".equals(wire[0]) || !"1".equals(wire[1]) || !"0".equals(wire[2]))
                throw new IllegalStateException("VIEWAREA_BOOLEAN_DOMAIN_DRIFT");
            // r8: a dropdown with the original 0/1 wire values, read-only until a
            // qualified live viewarea owner exists. Never a boolean preference.
            return MibrElementSpec.choice(key,label,wire,false);
        }
        if("STATUS".equals(kind))return MibrElementSpec.status(key,label);
        String[] choices=new MibrDraftChoiceModel(i).options();
        if(choices.length>0)
            return MibrElementSpec.choice(key,label,choices,
                MibrSettingsCatalog.READ_ONLY[i] ||
                "CHOICE_PENDING_CANONICAL_VALIDATOR".equals(kind));
        return MibrElementSpec.status(key,label);
    }
    /** The existing live Ssm row renderer uses the exact same typed entry source. */
    public static MibrElementSpec describeVisible(String key){return entry(key);}
    private static int group(String id){
        for(int i=0;i<MibrMenuDefinition.GROUP_IDS.length;i++)
            if(id.equals(MibrMenuDefinition.GROUP_IDS[i]))return i;
        return -1;
    }
    private static MibrElementSpec link(int g){
        String id=MibrMenuDefinition.GROUP_IDS[g];
        return MibrElementSpec.link("page."+id,MibrMenuDefinition.groupNames()[g],id);
    }
    /** r10: main list = root settings + Erweitert; Diagnose is linked from Erweitert. */
    public static MibrElementTree createTree(){
        int groups=MibrMenuDefinition.GROUP_IDS.length;
        int direct=MibrMenuDefinition.ROOT_KEYS.length;
        int nested=group("diagnostics"),parent=group("advanced");
        MibrElementSpec[] rootLinks=new MibrElementSpec[direct+groups-(nested>=0?1:0)];
        for(int k=0;k<direct;k++)rootLinks[k]=entry(MibrMenuDefinition.ROOT_KEYS[k]);
        MibrElementTree.Page[] pages=new MibrElementTree.Page[groups+1];
        int n=direct;
        for(int i=0;i<groups;i++){
            String id=MibrMenuDefinition.GROUP_IDS[i];
            if(i!=nested)rootLinks[n++]=link(i);
            String[] keys=MibrMenuDefinition.GROUP_KEYS[i];
            MibrElementSpec[] rows;
            if(keys.length==0){
                rows=new MibrElementSpec[]{MibrElementSpec.info(id+".unavailable",
                                 "views".equals(id)?MibrI18n.pick("Zeilen werden im Live-Menue angezeigt", "Rows are shown in the live menu")
                                 :MibrI18n.pick("Noch keine nachgewiesenen Live-Werte", "No verified live values yet"))};
            }else{
                rows=new MibrElementSpec[keys.length+(i==parent&&nested>=0?1:0)];
                for(int j=0;j<keys.length;j++)rows[j]=entry(keys[j]);
                if(i==parent&&nested>=0)rows[keys.length]=link(nested);
            }
            pages[i+1]=new MibrElementTree.Page(id,MibrMenuDefinition.groupNames()[i],rows);
        }
        pages[0]=new MibrElementTree.Page("root",MibrMenuDefinition.title(),rootLinks);
        return new MibrElementTree(pages,"root");
    }
    private static void collect(MibrElementTree tree,java.util.Vector items){
        MibrElementTree.Page page=tree.current();
        for(int i=0;i<page.size();i++){
            items.addElement(page.row(i));
            if(!tree.open(i))continue; // a setting/info row, not a submenu link
            collect(tree,items);
            tree.back();
        }
    }
    public static MibrElementEngine createEngine(){
        MibrElementTree tree=createTree();
        java.util.Vector items=new java.util.Vector();
        collect(tree,items);
        MibrElementSpec[] out=new MibrElementSpec[items.size()];
        items.copyInto(out);tree.detach();
        return new MibrElementEngine(out);
    }
}
