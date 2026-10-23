/* Java 1.2 navigation model for the native CarPlay settings view. */
package de.mibr.hmi;

/**
 * r8/r10 flat menu: the main list (CATEGORIES) shows the root settings
 * followed by the Erweitert link; ITEMS is one submenu; DETAIL is one
 * setting. Diagnose is reached from inside Erweitert (r10, owner 2026-10-20).
 * Every list is a single scrolling OEM list, no artificial pages.
 */
public final class MibrCarPlayMenuModel {
    public static final int HOME = 0, CATEGORIES = 1, ITEMS = 2, DETAIL = 3;
    private static final String[] GROUP_IDS = MibrMenuDefinition.GROUP_IDS;
    private static final String[] ROOT_KEYS = MibrMenuDefinition.ROOT_KEYS;
    /** Submenu reached from inside another submenu instead of the main list. */
    private static final int NESTED = index("diagnostics");
    private static final int DIAG_ROWS = 7;
    private static final int NESTED_PARENT = index("advanced");
    private static int index(String id) {
        for (int i = 0; i < GROUP_IDS.length; i++) if (id.equals(GROUP_IDS[i])) return i;
        return -1;
    }
    /** Main-list submenu links (every group except the nested one). */
    private static int[] links() {
        int n = 0;
        for (int g = 0; g < GROUP_IDS.length; g++) if (g != NESTED) n++;
        int[] out = new int[n];
        n = 0;
        for (int g = 0; g < GROUP_IDS.length; g++) if (g != NESTED) out[n++] = g;
        return out;
    }
    private static final int[] LINKS = links();
    /** Extra link row at the end of a submenu, or -1. */
    private static int nestedLink(int group) { return group == NESTED_PARENT && NESTED >= 0 ? NESTED : -1; }
    /** r46: the "Motorart" row (engine type of the CarPlay Identify) sits in Erweitert after the settings. */
    private static final int VIEWS = index("views");
    /** r56: Erweitert has one virtual row (Motorart); the "Ansichten" submenu has the six view rows. */
    private static int engineRows(int group) {
        if (group == VIEWS && VIEWS >= 0) return MibrViewState.ROWS;
        return group == NESTED_PARENT && NESTED_PARENT >= 0 ? 1 : 0;
    }
    /** First virtual key of the group's virtual rows. */
    private static int firstVirtual(int group) {
        return group == VIEWS && VIEWS >= 0 ? MibrPopupEditorModel.VIEW_FOLLOW : MibrPopupEditorModel.ENGINE;
    }
    /** True for the engine-type row of the Erweitert list (a tap is handled by the owned rows, not by select()). */
    public boolean isEngineRow(int row) {
        return screen == ITEMS && engineRows(group) > 0 && row >= count(group) && row < count(group) + engineRows(group);
    }

    public static interface View {
        void show(int screen, String title, String[] rows, String detail);
    }

    private final View view;
    private int screen = HOME;
    private int group = -1;
    private int selected = -1;

    public MibrCarPlayMenuModel(View view) {
        if (view == null) throw new IllegalArgumentException("view");
        this.view = view;
    }

    /** Immutable UI state. Never carries a backend value or guessed readback.
     * page is always 0 since r8 (kept for snapshot/row identity callers). */
    public static final class Snapshot {
        public final int screen,group,page,selected;
        private Snapshot(int s,int g,int key){
            screen=s;group=g;page=0;selected=key;
        }
    }
    public Snapshot snapshot(){return new Snapshot(screen,group,selected);}
    public void restore(Snapshot s){
        if(s==null || s.screen<CATEGORIES || s.screen>DETAIL || s.page!=0)
            throw new IllegalArgumentException("MENU_SNAPSHOT_INVALID");
        if(s.screen==CATEGORIES){
            if(s.group!=-1 || s.selected!=-1)
                throw new IllegalArgumentException("MENU_CATEGORY_SNAPSHOT");
        }else if(s.screen==ITEMS){
            if(s.group<0 || s.group>=GROUP_IDS.length || s.selected!=-1)
                throw new IllegalArgumentException("MENU_GROUP_SNAPSHOT");
        }else{
            // DETAIL of a main-list setting (group -1) or of a submenu setting.
            if(s.group<-1 || s.group>=GROUP_IDS.length)
                throw new IllegalArgumentException("MENU_GROUP_SNAPSHOT");
            boolean found=false;
            for(int i=0;i<count(s.group);i++)if(keyAt(s.group,i)==s.selected)found=true;
            if(!found)throw new IllegalArgumentException("MENU_DETAIL_SNAPSHOT");
        }
        screen=s.screen;group=s.group;selected=s.selected;render();
    }
    public int screen() { return screen; }
    /** -1 on the main list and for a main-list setting's DETAIL. */
    public int group() { return group; }
    public int page() { return 0; }
    public int selected() { return selected; }
    /** Number of main-list rows: root settings plus submenu links. */
    public static int rootRows() { return ROOT_KEYS.length + LINKS.length; }
    /** Submenu index of a main-list row, or -1 when the row is a setting. */
    public int groupForRow(int row) {
        if (screen == ITEMS && row == count(group) + engineRows(group) && nestedLink(group) >= 0) return nestedLink(group);
        if (screen != CATEGORIES || row < ROOT_KEYS.length || row >= rootRows()) return -1;
        return LINKS[row - ROOT_KEYS.length];
    }
    /** Mapping for the owned editor; links, diagnostics and hidden descriptors are never keys. */
    public int keyForRow(int row) {
        if (screen == CATEGORIES) return row >= 0 && row < ROOT_KEYS.length ? keyAt(-1, row) : -1;
        if (isEngineRow(row)) return firstVirtual(group) + (row - count(group));
        if (screen != ITEMS || row < 0 || row >= count(group)) return -1;
        return keyAt(group, row);
    }
    public void refresh() { render(); }

    public void open() {
        group = -1;
        selected = -1;
        screen = CATEGORIES;
        render();
    }

    public void select(int row) {
        if (row < 0) return;
        if (screen == CATEGORIES) {
            if (row < ROOT_KEYS.length) {
                selected = keyAt(-1, row);
                screen = DETAIL;
            } else if (row < rootRows()) {
                group = LINKS[row - ROOT_KEYS.length];
                selected = -1;
                screen = ITEMS;
            } else return;
            render();
            return;
        }
        if (screen != ITEMS) return;
        if (row == count(group) + engineRows(group) && nestedLink(group) >= 0) {
            group = nestedLink(group);
            selected = -1;
            render();
            return;
        }
        if (row >= count(group)) return; // the engine row is acted on by the owned rows
        selected = keyAt(group, row);
        screen = DETAIL;
        render();
    }

    public void back() {
        if (screen == DETAIL) {
            screen = group < 0 ? CATEGORIES : ITEMS;
            selected = -1;
        } else if (screen == ITEMS && group == NESTED) {
            group = NESTED_PARENT;
        } else if (screen == ITEMS) {
            screen = CATEGORIES;
            group = -1;
        } else {
            screen = HOME;
            group = -1;
        }
        render();
    }

    public void close() {
        screen = HOME;
        group = -1;
        selected = -1;
        render();
    }

    /** group -1 is the main list's settings. */
    private static int count(int group) {
        if (group == -1) return ROOT_KEYS.length;
        if (group < 0 || group >= GROUP_IDS.length) return 0;
        return MibrMenuDefinition.GROUP_KEYS[group].length;
    }

    private static int keyAt(int group, int rank) {
        if(group<-1 || group>=GROUP_IDS.length || rank<0 || rank>=count(group))return -1;
        String key=group==-1?ROOT_KEYS[rank]:MibrMenuDefinition.GROUP_KEYS[group][rank];
        for (int i = 0; i < MibrSettingsCatalog.KEYS.length; i++) {
            if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        }
        throw new IllegalStateException("MIBR_MENU_KEY_MISSING "+key);
    }

    private static String rowLabel(int index) {
        String label = MibrCanonicalElementMenu.displayLabel(MibrSettingsCatalog.KEYS[index]);
        return label;
    }

    private void render() {
        String[] rows = new String[0];
        String[] groupNames = MibrMenuDefinition.groupNames();
        String title = MibrMenuDefinition.title();
        String detail = "";
        if (screen == CATEGORIES) {
            rows = new String[rootRows()];
            for (int i = 0; i < ROOT_KEYS.length; i++) rows[i] = rowLabel(keyAt(-1, i));
            for (int g = 0; g < LINKS.length; g++) rows[ROOT_KEYS.length + g] = groupNames[LINKS[g]];
        } else if (screen == ITEMS) {
            title = groupNames[group];
            int count = count(group);
            int nested = nestedLink(group);
            // An empty submenu still renders one row (status line or notice).
            int engine = engineRows(group);
            rows = new String[count + engine == 0 ? ("diagnostics".equals(GROUP_IDS[group]) ? DIAG_ROWS : 1) : count + engine + (nested >= 0 ? 1 : 0)];
            for (int j = 0; j < count; j++) rows[j] = rowLabel(keyAt(group, j));
            if (engine > 0) {
                if (group == VIEWS) {
                    for (int v = 0; v < MibrViewState.ROWS; v++) rows[count + v] = MibrViewState.rowLabel(v);
                } else {
                    rows[count] = MibrI18n.pick("Motorart", "Engine type");
                }
            }
            if (nested >= 0) rows[count + engine] = groupNames[nested];
            if (count == 0 && "diagnostics".equals(GROUP_IDS[group])) {
                String[] live = MibrVdataDiag.read();
                for (int j = 0; j < rows.length && j < live.length; j++) rows[j] = live[j];
            }
            if (count + engine == 0) detail = "diagnostics".equals(GROUP_IDS[group])
                ? MibrI18n.pick("Fahrzeugdaten zum iPhone: nur Anzeige, nichts wird hier ge\u00e4ndert.", "Vehicle data to iPhone: display only, nothing is changed here.")
                : MibrI18n.pick("Noch keine freigegebenen Parameter.", "No approved parameters yet.");
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
        }
        view.show(screen, title, rows, detail);
    }
}
