package de.mibr.hmi;

/** Java 1.2, owned session state. No transport, persistence, SET or SAVE. */
public final class MibrPopupEditorModel {
    /** r47: virtual row after the 48 registry keys: the engine type of the CarPlay Identify (not a registry setting). */
    public static final int ENGINE = MibrSettingsCatalog.KEYS.length;
    /** r55: virtual rows of "Bildbereich folgt Cockpit-Ansicht" (follow, pos, area at Voll / Wide / Center, sport). */
    public static final int VIEW_FOLLOW = ENGINE + 1, VIEW_POS = ENGINE + 2, VIEW_RS = ENGINE + 3, VIEW_MAP0 = ENGINE + 4,
        VIEW_MAP1 = ENGINE + 5, VIEW_MAP4 = ENGINE + 6, VIEW_SPORT = ENGINE + 7,
        SCALE_MAIN = ENGINE + 8, SCALE_CLUSTER = ENGINE + 9,
        MENU_LANGUAGE = ENGINE + 10, GPS_DEMO = ENGINE + 11,
        SCALE_PHYSICAL = ENGINE + 12,
        SCALE_MAIN_PHYSICAL = ENGINE + 13,
        /** R2 2026-10-31: main-list checkbox "CarPlay-Navigation" (broker CARPLAY_NAV_*, values on/off). */
        CARPLAY_NAV = ENGINE + 14,
        /** Erweitert checkbox "Logs auf SD-Karte" (broker SD_LOG_*, values on/off). */
        SD_LOG = ENGINE + 15,
        /** Pfeile im Cockpit, in menu order (broker NAV_*). */
        NAV_SOURCE = ENGINE + 16, NAV_DISPLAY = ENGINE + 17, NAV_TEXT = ENGINE + 18, NAV_BOTTOM = ENGINE + 19,
        NAV_SIDE = ENGINE + 20, NAV_LANES = ENGINE + 21,
        /** Demo route: RAM only, off again after every restart. */
        NAV_DEMO = ENGINE + 23,
        /** CarPlay map: automatic, light, dark. */
        NAV_NIGHT = ENGINE + 22,
        /** Safe areas: five rows (x, y, w, h, reset) each for Voll, Wide, Center. */
        SAFE_FIRST = ENGINE + 24, SAFE_END = SAFE_FIRST + 15,
        /** Expertenmodus: off, session (RAM), on (broker EXPERT_MODE). */
        EXPERT_MODE = SAFE_END,
        /** Kalibrierbild: RAM checkbox like the demo route. */
        CALIB_IMAGE = SAFE_END + 1, VIRTUAL_END = SAFE_END + 2;
    static boolean isSafe(int index){return index>=SAFE_FIRST&&index<SAFE_END;}
    static int safeField(int index){return (index-SAFE_FIRST)%5;}
    /** The first of the rows of a safe area, the key its broker readback is reported on. */
    static int safeBase(int index){return SAFE_FIRST+(index-SAFE_FIRST)/5*5;}
    /** The broker-owned durable choice behind a virtual row, or null. */
    static MibrDurableSwitch durable(int index) {
        if(index==CARPLAY_NAV)return MibrDurableSwitch.CARPLAY_NAV;
        if(index==SD_LOG)return MibrDurableSwitch.SD_LOG;
        if(index==NAV_SOURCE)return MibrDurableSwitch.NAV_SOURCE;
        if(index==NAV_DISPLAY)return MibrDurableSwitch.NAV_DISPLAY;
        if(index==NAV_TEXT)return MibrDurableSwitch.NAV_TEXT;
        if(index==NAV_BOTTOM)return MibrDurableSwitch.NAV_BOTTOM;
        if(index==NAV_SIDE)return MibrDurableSwitch.NAV_SIDE;
        if(index==NAV_LANES)return MibrDurableSwitch.NAV_LANES;
        if(index==NAV_NIGHT)return MibrDurableSwitch.NAV_NIGHT;
        if(index==EXPERT_MODE)return MibrDurableSwitch.EXPERT_MODE;
        if(isSafe(index)){
            int area=(index-SAFE_FIRST)/5;
            return area==0?MibrDurableSwitch.SAFE_VOLL:area==1?MibrDurableSwitch.SAFE_WIDE:MibrDurableSwitch.SAFE_CENTER;
        }
        return null;
    }
    static int keyOf(MibrDurableSwitch sw) {
        for(int i=ENGINE;i<VIRTUAL_END;i++)if(durable(i)==sw)return i;
        return -1;
    }
    /** Durable rows that are checkboxes; the other durable rows are dropdowns. */
    static boolean durableCheck(int index) {
        return index==CARPLAY_NAV||index==SD_LOG||index==NAV_SIDE||index==NAV_LANES;
    }
    /** True for the engine row and the view rows: values come from the broker, not from the 48-key registry. */
    public static boolean isVirtual(int index) { return index >= ENGINE && index < VIRTUAL_END; }
    public static boolean isScaling(int index) { return index == SCALE_MAIN || index == SCALE_CLUSTER || index == SCALE_PHYSICAL || index == SCALE_MAIN_PHYSICAL; }
    public static String scalingId(int index) {
        if(index==SCALE_MAIN)return "scaling.main.zoomFactor";
        if(index==SCALE_CLUSTER)return "scaling.cluster.zoomFactor";
        if(index==SCALE_PHYSICAL)return "scaling.cluster.physicalSize";
        if(index==SCALE_MAIN_PHYSICAL)return "scaling.main.physicalSize";
        return null;
    }
    private final MibrDraftChoiceModel[] drafts = new MibrDraftChoiceModel[VIRTUAL_END];
    private final String[] current = new String[VIRTUAL_END];
    private final boolean[] tempReadback = new boolean[VIRTUAL_END];
    private int opened = -1;
    private int operation;
    private boolean available;

    public MibrPopupEditorModel() {
        for (int i = 0; i < drafts.length; i++) drafts[i] = new MibrDraftChoiceModel(i);
    }
    public void setAvailable(boolean value) { available = value; if (!value) cancel(); }
    public boolean available() { return available; }
    public static boolean visible(int index) {
        if (isVirtual(index)) return true;
        return index >= 0 && index < MibrSettingsCatalog.KEYS.length &&
            !"hidden".equals(MibrSettingsCatalog.UI_SECTIONS[index]);
    }
    /**
     * r10 (owner 2026-10-20): Ankunftszeit, Tempolimit and Kompass are stock
     * CHECK rows over the canonical yes/no values. The canonical "user"
     * (App-Vorgabe) is not offered, but a read-back "user" is shown unchecked.
     */
    public boolean directToggle(int index) {
        if(durableCheck(index)||index==NAV_DEMO||index==CALIB_IMAGE)return true;
        if(!visible(index) || isVirtual(index))return false;
        String key=MibrSettingsCatalog.KEYS[index];
        return "navigation.ETA".equals(key) || "navigation.speedLimit".equals(key) ||
               "navigation.compass".equals(key);
    }
    /** Checkbox state of a direct toggle for a value (never inferred when unknown). */
    public boolean checked(int index, String value) {
        return "yes".equals(value) || "1".equals(value) || "on".equals(value);
    }
    /** Owner-approved HMI writes. FPS is persisted with unit-reboot apply semantics. */
    public static boolean saveAllowed(int index) {
        if(!visible(index) || isVirtual(index))return false;
        String key=MibrSettingsCatalog.KEYS[index];
        // r14: Ansicht (viewarea.selected) is a live TEMP index and saved like the navigation values.
        // r23: carplay.enabled ("CarPlay im Cockpit") is the runtime pause shared with the KEY40 long press.
        return "viewarea.selected".equals(key) || "carplay.enabled".equals(key) || "maxFPS".equals(key) ||
               key.startsWith("navigation.") && !"navigation.url".equals(key);
    }
    /**
     * viewarea.selected ("Ansicht" dropdown) is a live index into the two
     * viewareas CarPlay negotiated, not a preference. No qualified
     * requestViewArea/updateViewArea owner exists yet, so the row is shown but
     * never opens, drafts or SETs.
     */
    public boolean liveViewGated(int index) {
        if(isScaling(index))return !MibrScalingState.writable(index);
        // No writable UI without a separately verified MIBR/3 language store
        // or qualified original-DIO GPS-demo session owner.
        if(index==MENU_LANGUAGE)return !MibrI18n.menuWritable();
        if(index==GPS_DEMO)return !MibrGpsDemoState.writable();
        if(durable(index)!=null)return !durable(index).writable();
        if(!visible(index) || isVirtual(index))return false;
        String key=MibrSettingsCatalog.KEYS[index];
        // carplay.enabled (r10 dropdown under Erweitert) needs a qualified
        // session owner as well (native session_control=0).
        return false;
    }
    public String[] options(int index) {
        if(index>=0&&index<MibrSettingsCatalog.KEYS.length&&"maxFPS".equals(MibrSettingsCatalog.KEYS[index]))
            return new String[]{"30","60"};
        return drafts[index].options();
    }
    public String label(int index, String value) { return drafts[index].labelFor(value); }
    public String draft(int index) { return drafts[index].draft(); }
    public String current(int index) { return current[index]; }
    /** Snapshot input only, never inferred from catalog defaults or a draft. */
    public void readback(int index, String value) { readback(index,value,false); }
    /** Desired/persisted/profile snapshot, NEVER effective runtime state. */
    public void readback(int index,String value,boolean fromTemp){
        current[index]=value;tempReadback[index]=fromTemp;
    }
    public boolean isTempConfirmed(int index){return tempReadback[index];}
    /** Called only after independent matching TEMP GET for all batch keys. */
    /** Only after verified MIBR/3 durable receipt AND matching atomic post-commit snapshot. */
    public void confirmPersistent(int index,String value){
        if(value==null || !value.equals(drafts[index].draft()))
            throw new IllegalStateException("PERSISTENT_DRAFT_RACE");
        readback(index,value,false);drafts[index].discard();
    }
    public void confirmTemp(int index,String value){
        if(value==null || !value.equals(drafts[index].draft()))
            throw new IllegalStateException("TEMP_DRAFT_RACE");
        readback(index,value,true);drafts[index].discard();
    }
    /** A refused save drops the wish; the row shows the stored value again. */
    public void discardDraft(int index){drafts[index].discard();}
    public String valueText(int index) {
        return drafts[index].hasDraft() ? "DRAFT: " + drafts[index].draft() :
            "CURRENT: " + (current[index] == null ? "UNKNOWN" : current[index]);
    }
    public int selectedOption(int index) {
        String value = drafts[index].hasDraft() ? drafts[index].draft() : current[index];
        String[] opts = options(index);
        for (int i = 0; i < opts.length; i++) if (opts[i].equals(value)) return i;
        return -1; // UNKNOWN and current URL 'auto' are not fabricated choices.
    }
    public boolean open(int index) {
        cancel();
        if (!available || !visible(index) || directToggle(index) || liveViewGated(index) ||
            options(index).length == 0) return false;
        opened = index; return true;
    }
    public boolean choose(int option) {
        if (opened < 0) return false;
        String[] opts = options(opened);
        if (option < 0 || option >= opts.length) return false;
        boolean accepted = drafts[opened].chooseDraft(opts[option]);
        if (accepted) cancel();
        return accepted;
    }
    public boolean toggle(int index) {
        if (!available || !directToggle(index)) return false;
        String value = drafts[index].hasDraft() ? drafts[index].draft() : current[index];
        // First explicit tap selects 1 if current UNKNOWN. Never display an
        // inferred effective value: the draft is only local and not ACKed.
        if (durableCheck(index)||index==NAV_DEMO||index==CALIB_IMAGE) return drafts[index].chooseDraft(checked(index, value) ? "off" : "on");
        String on = "TRISTATE".equals(MibrSettingsCatalog.UI_KINDS[index]) ? "yes" : "1";
        String off = "TRISTATE".equals(MibrSettingsCatalog.UI_KINDS[index]) ? "no" : "0";
        return drafts[index].chooseDraft(checked(index, value) ? off : on);
    }
    public int opened() { return opened; }
    public int operationToken() { return operation; }
    public void cancelIfOperation(int token) { if(token==operation)cancel(); }
    public void cancel() { opened = -1; operation++; }
    public void detach() { available = false; cancel(); for (int i=0;i<drafts.length;i++) drafts[i].discard(); }

    /** Bounded native scrolling, never a fixed two-choice slice. */
    public static final class Bounds {
        public final int x, y, width, height, rowHeight;
        public final boolean scroll;
        public Bounds(int hostWidth, int hostHeight, int anchorY, int count, int requestedRowHeight) {
            if (hostWidth < 360 || hostHeight < 280 || count < 1 || count > 128)
                throw new IllegalArgumentException("popup bounds");
            int margin = 12;
            x = margin; width = hostWidth - 2 * margin;
            rowHeight = Math.max(64, requestedRowHeight);
            int availableHeight = hostHeight - 2 * margin;
            height = Math.min(availableHeight, count * rowHeight + 24);
            y = Math.max(margin, Math.min(anchorY, hostHeight - margin - height));
            scroll = count * rowHeight > height - 24;
        }
    }
}
