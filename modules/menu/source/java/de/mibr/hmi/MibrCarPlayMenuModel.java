/* Java 1.2 navigation model for the native CarPlay settings view. */
package de.mibr.hmi;

import java.util.Vector;

/**
 * The menu tree of MibrMenuLayout, one scrolling OEM list per level. CATEGORIES is the main list, ITEMS any other
 * page, DETAIL one setting. Rows are recomputed on every render: expert mode can change them at any time.
 */
public final class MibrCarPlayMenuModel {
    public static final int HOME = 0, CATEGORIES = 1, ITEMS = 2, DETAIL = 3;
    private static final int DIAG_ROWS = 7;

    public static interface View {
        void show(int screen, String title, String[] rows, String detail);
    }

    private final View view;
    private MibrMenuLayout layout;
    /** One-shot "default menu restored" row; kept for the life of this model so it survives re-renders. */
    private String restoredNotice;
    private int layoutGeneration;
    private MibrMenuLayout.Node page;
    private MibrMenuLayout.Node[] nodes = new MibrMenuLayout.Node[0];
    private int screen = HOME;
    private int selected = -1;

    public MibrCarPlayMenuModel(View view) {
        if (view == null) throw new IllegalArgumentException("view");
        this.view = view;
        load();
    }
    private void load() {
        layoutGeneration = MibrMenuLayout.generation();
        layout = MibrMenuLayout.current();
        page = layout.root;
    }

    /** Immutable UI state. Never carries a backend value or guessed readback.
     * page is always 0 since r8 (kept for snapshot/row identity callers). */
    public static final class Snapshot {
        public final int screen,group,page,selected;
        private final int generation;
        private Snapshot(int s,int g,int key,int generation){
            screen=s;group=g;page=0;selected=key;this.generation=generation;
        }
    }
    public Snapshot snapshot(){return new Snapshot(screen,group(),selected,layoutGeneration);}
    public void restore(Snapshot s){
        if(s==null || s.screen<CATEGORIES || s.screen>DETAIL || s.page!=0)
            throw new IllegalArgumentException("MENU_SNAPSHOT_INVALID");
        /* taken from an earlier menu file: its page numbers mean nothing now */
        if(s.generation!=layoutGeneration){open();return;}
        MibrMenuLayout.Node target=layout.page(s.group);
        if(target==null)throw new IllegalArgumentException("MENU_GROUP_SNAPSHOT");
        if(s.screen==CATEGORIES){
            if(s.group!=-1 || s.selected!=-1)
                throw new IllegalArgumentException("MENU_CATEGORY_SNAPSHOT");
        }else if(s.screen==ITEMS){
            if(s.group==-1 || s.selected!=-1)
                throw new IllegalArgumentException("MENU_GROUP_SNAPSHOT");
        }else{
            boolean found=false;
            for(int i=0;i<target.children.size();i++){
                MibrMenuLayout.Node n=(MibrMenuLayout.Node)target.children.elementAt(i);
                if(n.kind==MibrMenuLayout.KEY&&n.key==s.selected)found=true;
            }
            if(!found)throw new IllegalArgumentException("MENU_DETAIL_SNAPSHOT");
        }
        page=target;screen=s.screen;selected=s.selected;render();
    }
    public int screen() { return screen; }
    /** -1 on the main list and for a main-list setting's DETAIL. */
    public int group() { return page.number; }
    public int page() { return 0; }
    public int selected() { return selected; }
    private boolean listed(){return screen==CATEGORIES||screen==ITEMS;}
    private MibrMenuLayout.Node node(int row){
        return listed()&&row>=0&&row<nodes.length?nodes[row]:null;
    }
    public boolean onDiagnostics(){return screen==ITEMS&&page.kind==MibrMenuLayout.DIAGNOSTICS;}
    public boolean onVersion(){return screen==ITEMS&&page.kind==MibrMenuLayout.VERSION;}
    /** True when this page has the row of that key. */
    public boolean pageHas(int key){
        for(int i=0;i<page.children.size();i++){
            MibrMenuLayout.Node n=(MibrMenuLayout.Node)page.children.elementAt(i);
            if(n.kind==MibrMenuLayout.KEY&&n.key==key)return true;
        }
        return false;
    }
    public boolean scalingPageOpen(){
        return screen==ITEMS&&(pageHas(MibrPopupEditorModel.SCALE_MAIN)||pageHas(MibrPopupEditorModel.SCALE_CLUSTER)||
            pageHas(MibrPopupEditorModel.SCALE_PHYSICAL)||pageHas(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL));
    }
    /** Read-only text: never a setting or dropdown target. */
    public boolean noteRow(int row){MibrMenuLayout.Node n=node(row);return n!=null&&n.kind==MibrMenuLayout.NOTE;}
    public boolean loadRow(int row){MibrMenuLayout.Node n=node(row);return n!=null&&n.kind==MibrMenuLayout.LOAD;}
    /** Rows of the current list page (0 outside a list). */
    public int rowCount(){return listed()?nodes.length:0;}
    /** r15i: keys whose row is a collapsed stock Item header with an expandable OEM slider row: the four safe-area
     * edges (r15) and the cockpit zoom (6 discrete positions). Only while the owned slider rows are shown. */
    static boolean sliderKey(int key){
        return MibrPopupEditorModel.isSafe(key)&&MibrPopupEditorModel.safeField(key)<MibrSafeArea.RESET_FIELD||
            MibrScalingState.scaleSlider(key);
    }
    /** r15i: the current page has at least one slider-capable row (resolve the owned slider source first). */
    public boolean sliderPage(){
        if(screen!=ITEMS)return false;
        for(int i=0;i<page.children.size();i++){
            MibrMenuLayout.Node n=(MibrMenuLayout.Node)page.children.elementAt(i);
            if(n.kind==MibrMenuLayout.KEY&&sliderKey(n.key))return true;
        }
        return false;
    }
    /** r15: the safe-area edge (or r15i cockpit zoom) key behind an OEM slider row, else -1 (never a dropdown key). */
    public int sliderKeyForRow(int row){MibrMenuLayout.Node n=node(row);return n!=null&&n.kind==MibrMenuLayout.SLIDER?n.key:-1;}
    /** True when the current page shows safe-area edge rows (slider rows may be added). */
    public boolean safeEdgePage(){
        if(screen!=ITEMS)return false;
        for(int i=0;i<page.children.size();i++){
            MibrMenuLayout.Node n=(MibrMenuLayout.Node)page.children.elementAt(i);
            if(n.kind==MibrMenuLayout.KEY&&MibrPopupEditorModel.isSafe(n.key)&&
               MibrPopupEditorModel.safeField(n.key)<MibrSafeArea.RESET_FIELD)return true;
        }
        return false;
    }
    /** Page number behind a row, or -1 when the row opens nothing. */
    public int groupForRow(int row) {
        MibrMenuLayout.Node n=node(row);
        return n!=null&&n.opens()?n.number:-1;
    }
    /** Mapping for the owned editor; links, notes and diagnostics are never keys. */
    public int keyForRow(int row) {
        MibrMenuLayout.Node n=node(row);
        return n!=null&&n.kind==MibrMenuLayout.KEY?n.key:-1;
    }
    /** A new menu file replaces the tree: back to the main list. */
    public void refresh() {
        if(layoutGeneration!=MibrMenuLayout.generation()){
            load();
            if(screen!=HOME){screen=CATEGORIES;selected=-1;}
        }
        render();
    }

    public void open() {
        load();
        selected = -1;
        screen = CATEGORIES;
        render();
    }

    /** r15g: the edge whose slider row is expanded (-1 none); reset on every page change. */
    private int expandedSafe=-1;
    private boolean builtWithSliders;
    public int expandedSafe(){return expandedSafe;}
    /** True when the current rows were computed while slider rows were shown. */
    public boolean builtWithSliders(){return builtWithSliders;}
    /** True for an edge row that expands a slider (instead of the pre-r15 dropdown). */
    public boolean safeToggleRow(int row){
        MibrMenuLayout.Node n=node(row);
        return MibrSafeArea.slidersShown()&&n!=null&&n.kind==MibrMenuLayout.KEY&&sliderKey(n.key);
    }
    /** r15i polish: set by a tap that expanded/collapsed a row, consumed by the next layout (keep header+slider on screen). */
    private boolean toggled;
    /** True once after a toggle render: the view keeps the scroll position and reveals the expanded pair. */
    public boolean consumeToggle(){boolean t=toggled;toggled=false;return t;}
    /** Row of the expanded header in the current rows, or -1. */
    public int expandedRow(){
        for(int i=0;i<nodes.length;i++)if(nodes[i].kind==MibrMenuLayout.KEY&&nodes[i].key==expandedSafe)return i;
        return -1;
    }
    /** Tap on an edge row: expand its slider (collapsing any other), or collapse it again. */
    public void toggleSafe(int row){
        if(!safeToggleRow(row))return;
        int key=node(row).key;
        expandedSafe=expandedSafe==key?-1:key;
        toggled=true;
        render();
    }
    public void select(int row) {
        MibrMenuLayout.Node n=node(row);
        if(n==null)return;
        if(n.opens()){
            expandedSafe=-1;
            page=n;selected=-1;screen=ITEMS;render();
        }else if(n.kind==MibrMenuLayout.KEY&&n.key>=0&&n.key<MibrSettingsCatalog.KEYS.length){
            selected=n.key;screen=DETAIL;render();
        }
    }

    public void back() {
        if (screen == DETAIL) {
            screen = page == layout.root ? CATEGORIES : ITEMS;
            selected = -1;
        } else if (screen == ITEMS) {
            expandedSafe = -1;
            page = page.parent;
            screen = page == layout.root ? CATEGORIES : ITEMS;
        } else {
            screen = HOME;
            page = layout.root;
        }
        render();
    }

    public void close() {
        screen = HOME;
        page = layout.root;
        selected = -1;
        render();
    }

    private void visibleNodes() {
        Vector out=new Vector();
        builtWithSliders=MibrSafeArea.slidersShown();
        boolean expert=MibrExpert.on();
        if(restoredNotice==null)restoredNotice=MibrMenuLayout.restoredNotice();
        if(page==layout.root&&restoredNotice!=null)
            out.addElement(new MibrMenuLayout.Node("restored",MibrMenuLayout.NOTE,-1,-1,false,page,restoredNotice,restoredNotice));
        if(page==layout.root&&MibrMenuLayout.recoveryNote()!=null)
            out.addElement(new MibrMenuLayout.Node("recovery",MibrMenuLayout.NOTE,-1,-1,false,page,
                MibrMenuLayout.recoveryNote(),MibrMenuLayout.recoveryNote()));
        for(int i=0;i<page.children.size();i++){
            MibrMenuLayout.Node n=(MibrMenuLayout.Node)page.children.elementAt(i);
            if(expert||!n.expert){
                out.addElement(n);
                // r15g: like the stock sound Item/SubItem pair: the edge row is collapsed; tapping it expands its OEM
                // slider row directly below (one at a time). Only while the native slider source resolved.
                if(MibrSafeArea.slidersShown()&&n.kind==MibrMenuLayout.KEY&&n.key==expandedSafe&&sliderKey(n.key))
                    out.addElement(new MibrMenuLayout.Node(n.id+".slider",MibrMenuLayout.SLIDER,n.key,-1,n.expert,page,"",""));
            }
        }
        nodes=new MibrMenuLayout.Node[out.size()];
        out.copyInto(nodes);
    }

    private void render() {
        String[] rows = new String[0];
        String title = layout.root.title();
        String detail = "";
        if (screen == CATEGORIES || screen == ITEMS) {
            if (screen == ITEMS) title = page.title();
            visibleNodes();
            if (page.kind == MibrMenuLayout.DIAGNOSTICS) {
                rows = new String[DIAG_ROWS];
                String[] live = MibrVdataDiag.read();
                for (int j = 0; j < rows.length && j < live.length; j++) rows[j] = live[j];
                detail = MibrI18n.pick("Fahrzeugdaten zum iPhone: nur Anzeige, nichts wird hier geändert.", "Vehicle data to iPhone: display only, nothing is changed here.");
            } else if (page.kind == MibrMenuLayout.VERSION) {
                rows = MibrVersionInfo.rows();
            } else if (nodes.length == 0) {
                rows = new String[]{MibrI18n.pick("Keine Einträge", "No entries")};
            } else {
                rows = new String[nodes.length];
                for (int j = 0; j < nodes.length; j++) {
                    rows[j] = nodes[j].title();
                    if (nodes[j].kind == MibrMenuLayout.LOAD) rows[j] += ": " + MibrMenuLayout.status();
                }
            }
        } else if (screen == DETAIL && selected >= 0) {
            title = MibrCanonicalElementMenu.displayLabel(MibrSettingsCatalog.KEYS[selected]);
            String key = MibrSettingsCatalog.KEYS[selected];
            String options = MibrSettingsCatalog.CHOICES[selected];
            detail = key + "\n" + MibrI18n.pick("Wert: unbekannt", "Value: unknown")
                + "\n" + MibrI18n.pick("Quelle: unbekannt", "Source: unknown")
                + "\n" + MibrI18n.pick("Aktivierung: ", "Activation: ") + MibrSettingsCatalog.APPLY[selected]
                + (options.length() > 0 ? "\n" + MibrI18n.pick("Werte: ", "Values: ") + options.replace('|', '/') : "")
                + (MibrSettingsCatalog.READ_ONLY[selected] ? "\n" + MibrI18n.pick("Nur Anzeige", "Display only")
                   : "\n" + MibrI18n.pick("Sichttest: kein Schreibzugriff", "Visual test: no write access"));
            if("maxFPS".equals(key))detail += "\n" + MibrI18n.pick("Unit-Neustart erforderlich", "Unit restart required");
        }
        view.show(screen, title, rows, detail);
    }
}
