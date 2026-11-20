package de.mibr.hmi;

/** Requested scaling preference and independent vehicle readbacks for the two displays. */
public final class MibrScalingState {
    private static final String[] IDS={"scaling.main.zoomFactor","scaling.cluster.zoomFactor","scaling.cluster.physicalSize","scaling.main.physicalSize"};
    private static final String[] desired=new String[4],advertised=new String[4],effective=new String[4],stored=new String[4],pending=new String[4],writer=new String[4],revision=new String[4],advertisedScope=new String[4],message=new String[4];
    private static final boolean[] requested=new boolean[4],stale=new boolean[4],saving=new boolean[4],refreshing=new boolean[4];
    private MibrScalingState(){}
    public static int slot(int index){return index==MibrPopupEditorModel.SCALE_MAIN?0:index==MibrPopupEditorModel.SCALE_CLUSTER?1:index==MibrPopupEditorModel.SCALE_PHYSICAL?2:index==MibrPopupEditorModel.SCALE_MAIN_PHYSICAL?3:-1;}
    public static String id(int index){int n=slot(index);return n<0?null:IDS[n];}
    public static boolean valid(String value){return "AUTO".equals(value)||"70".equals(value)||"85".equals(value)||"100".equals(value)||"125".equals(value)||"150".equals(value);}
    public static boolean physicalValid(String value){return physicalPercent(value)>0;}
    /** r15j: physical size = percent of the base size, 50..200 in 10 % steps. The legacy presets stay the canonical
     * spelling of 100/120/130/150 (BASE/P20/P30/P50, same as the native store); the other twelve are the plain number.
     * Returns -1 for anything else (also the non-canonical "100"/"120"/"130"/"150"). */
    public static int physicalPercent(String value){
        if(value==null)return -1;
        if("BASE".equals(value))return 100;
        if("P20".equals(value))return 120;
        if("P30".equals(value))return 130;
        if("P50".equals(value))return 150;
        int n=value.length();if(n<2||n>3||value.charAt(0)=='0')return -1;
        int p=0;for(int i=0;i<n;i++){char c=value.charAt(i);if(c<'0'||c>'9')return -1;p=p*10+(c-'0');}
        if(p<PHYS_MIN||p>PHYS_MAX||p%10!=0||p==100||p==120||p==130||p==150)return -1;
        return p;
    }
    /** The canonical stored value of a percentage (legacy token for 100/120/130/150), null when off-grid. */
    public static String physicalValue(int percent){
        if(percent<PHYS_MIN||percent>PHYS_MAX||percent%10!=0)return null;
        if(percent==100)return "BASE";
        if(percent==120)return "P20";
        if(percent==130)return "P30";
        if(percent==150)return "P50";
        return String.valueOf(percent);
    }
    static final int PHYS_MIN=50,PHYS_MAX=200,PHYS_STEP=10;
    /** Base millimetres scaled like the native store (nearest, half up). */
    static int scaleMm(int base,int percent){return (base*percent+50)/100;}
    /** Dropdown/status text of a physical value: main = change against the OEM size, cluster with the advertised mm. */
    static String physicalLabel(boolean main,String value){
        int p=physicalPercent(value);if(p<0)return value;
        if(p==100)return main?MibrI18n.pick("Original","Original"):MibrI18n.pick("Original (200 x 74 mm)","Baseline (200 x 74 mm)");
        String delta=(p>100?"+":"-")+Math.abs(p-100)+" %";
        return main?delta:delta+" ("+scaleMm(200,p)+" x "+scaleMm(74,p)+" mm)";
    }
    public static boolean valid(int index,String value){return (index==MibrPopupEditorModel.SCALE_PHYSICAL||index==MibrPopupEditorModel.SCALE_MAIN_PHYSICAL)?physicalValid(value):valid(value);}
    public static void reset(){for(int i=0;i<4;i++){desired[i]=advertised[i]=effective[i]=stored[i]=pending[i]=writer[i]=revision[i]=advertisedScope[i]=message[i]=null;requested[i]=stale[i]=saving[i]=refreshing[i]=false;wanted[i]=null;wantedAt[i]=0L;staleRetry[i]=false;}}

    /* ---- r15i/r15j: the four scaling keys as stock-like slider rows, Skoda owned rows only ---- */

    /** Zoom slider positions 0..5 = the six broker values, in the order of the old dropdown. */
    static final String[] ZOOM={"AUTO","70","85","100","125","150"};
    /** r15i cockpit zoom; r15j also the main-display zoom and both physical sizes. */
    static boolean scaleSlider(int index){return MibrPopupEditorModel.isScaling(index);}
    static boolean physical(int index){return index==MibrPopupEditorModel.SCALE_PHYSICAL||index==MibrPopupEditorModel.SCALE_MAIN_PHYSICAL;}
    static int zoomPosition(String value){for(int i=0;i<ZOOM.length;i++)if(ZOOM[i].equals(value))return i;return -1;}
    static String zoomValue(int position){return position>=0&&position<ZOOM.length?ZOOM[position]:null;}
    /** Right-aligned value of the expanded header: "Auto" for AUTO, else the plain number (stock shows numbers only). */
    static String zoomLabel(String value){return value==null?"":"AUTO".equals(value)?"Auto":value;}
    /** Number of slider positions: 6 zoom values, 16 physical steps (50..200 %). */
    static int positions(int index){return physical(index)?(PHYS_MAX-PHYS_MIN)/PHYS_STEP+1:ZOOM.length;}
    /** Slider position of a value, -1 when unknown. */
    static int position(int index,String value){
        if(!physical(index))return zoomPosition(value);
        int p=physicalPercent(value);return p<0?-1:(p-PHYS_MIN)/PHYS_STEP;
    }
    /** Broker value of a slider position, null when out of range. */
    static String valueAt(int index,int position){
        if(!physical(index))return zoomValue(position);
        return position<0||position>=positions(index)?null:physicalValue(PHYS_MIN+PHYS_STEP*position);
    }
    /** Header value text: zoom "Auto"/number, physical "Original" or the percentage of the base size. */
    static String sliderLabel(int index,String value){
        if(!physical(index))return zoomLabel(value);
        int p=physicalPercent(value);
        return value==null?"":p==100?MibrI18n.pick("Original","Original"):p<0?value:p+" %";
    }
    /** Position onto the 9 stock mini-slider preview images 0..8, linear and rounded (zoom 0,2,3,5,6,8). */
    static int previewStep(int index,int position){
        int last=positions(index)-1;
        int p=Math.max(0,Math.min(last,position));
        return (p*8+last/2)/last;
    }
    static int zoomPreviewStep(int position){return previewStep(MibrPopupEditorModel.SCALE_CLUSTER,position);}
    private static final String[] wanted=new String[4];
    private static final long[] wantedAt=new long[4];
    private static final boolean[] staleRetry=new boolean[4];
    /** The value the slider row shows: the unsent/unconfirmed wish, else the readback (null = unread). */
    static String shown(int index){int n=slot(index);return n<0?null:wanted[n]!=null?wanted[n]:desired[n];}
    static String wanted(int index){int n=slot(index);return n<0?null:wanted[n];}
    static long wantedAt(int index){int n=slot(index);return n<0?0L:wantedAt[n];}
    /** A slider move or -/+: the newest wish, shown at once; the durable SET waits for IDLE_MS (same rule as r15 edges). */
    static void want(int index,String value,long now){
        int n=slot(index);if(n<0||!valid(index,value))return;
        wanted[n]=value;wantedAt[n]=now;
    }
    /** The value to SET now, or null: nothing new, still moving, or the service busy (SET or GET in flight). */
    static String due(int index,long now,boolean busy){
        int n=slot(index);if(n<0||wanted[n]==null||busy)return null;
        if(wanted[n].equals(desired[n])&&revision[n]!=null&&!stale[n]&&!saving[n]){wanted[n]=null;staleRetry[n]=false;return null;}
        if(now-wantedAt[n]<MibrSafeArea.IDLE_MS)return null;
        return wanted[n];
    }
    /** Milliseconds until the newest wish becomes due (0 = now), or -1 when there is none. */
    static long waitMs(int index,long now){
        int n=slot(index);if(n<0||wanted[n]==null)return -1L;
        long left=MibrSafeArea.IDLE_MS-(now-wantedAt[n]);
        return left>0L?left:0L;
    }
    /** A refused/failed SET drops the wish: the row shows the stored value again. */
    static void drop(int index){int n=slot(index);if(n>=0){wanted[n]=null;staleRetry[n]=false;}}
    /** A verified SET: a later stale answer may retry again. */
    static void saved(int index){int n=slot(index);if(n>=0)staleRetry[n]=false;}
    /** STALE_REVISION: keep the wish once (it is resent after the re-read), drop it the second time (no loop). */
    static boolean retryAfterStale(int index){
        int n=slot(index);if(n<0||wanted[n]==null)return false;
        if(!staleRetry[n]){staleRetry[n]=true;return true;}
        drop(index);return false;
    }
    public static void beginRefresh(){for(int i=0;i<4;i++)refreshing[i]=true;}
    public static void finishRefresh(){for(int i=0;i<4;i++)refreshing[i]=false;}
    public static boolean begin(int index){int n=slot(index);if(n<0||requested[n])return false;requested[n]=true;message[n]=MibrI18n.pick("Wert wird gelesen", "Reading value");return true;}
    public static void readback(int index,String want,String ad,String effect,String scope,String store,String pend,String apply,String write,String rev){
        int n=slot(index);if(n<0||!valid(index,want)||!("DEFAULT".equals(store)||"VERIFIED".equals(store)||"UNKNOWN".equals(store))||!("0".equals(pend)||"1".equals(pend))||!revisionValidForProtocol(rev)||!("UNKNOWN".equals(ad)||valid(index,ad))||!("UNKNOWN".equals(scope)||"HISTORICAL".equals(scope))||("UNKNOWN".equals(ad)!= "UNKNOWN".equals(scope))||!"UNKNOWN".equals(effect)||!"RECONNECT".equals(apply)||!("ENABLED".equals(write)||"DISABLED".equals(write)))throw new IllegalArgumentException("SCALING_READBACK_INVALID");
        boolean wasStale=stale[n];desired[n]=want;advertised[n]=ad;effective[n]=effect;stored[n]=store;pending[n]=pend;writer[n]=write;revision[n]=rev;advertisedScope[n]=scope;message[n]=wasStale?MibrI18n.pick("Wert hat sich geändert; bitte neu wählen", "Value changed; choose again"):null;requested[n]=true;saving[n]=false;stale[n]=false;
    }
    public static void failed(int index,String text){int n=slot(index);if(n>=0){message[n]=text;requested[n]=true;saving[n]=false;writer[n]=null;revision[n]=null;}}
    public static void saving(int index){int n=slot(index);if(n>=0){message[n]=MibrI18n.pick("Speicherung wird geprüft", "Verifying stored preference");stale[n]=false;saving[n]=true;}}
    public static void stale(int index){int n=slot(index);if(n>=0)stale[n]=true;}
    public static void staleReadback(int index){int n=slot(index);if(n>=0&&stale[n])message[n]=MibrI18n.pick("Wert hat sich geändert; bitte neu wählen", "Value changed; choose again");}
    public static String desired(int index){int n=slot(index);return n<0?null:desired[n];}
    public static String advertised(int index){int n=slot(index);return n<0?null:advertised[n];}
    public static String advertisedScope(int index){int n=slot(index);return n<0?null:advertisedScope[n];}
    public static String effective(int index){int n=slot(index);return n<0?null:effective[n];}
    public static String stored(int index){int n=slot(index);return n<0?null:stored[n];}
    public static String pending(int index){int n=slot(index);return n<0?null:pending[n];}
    public static String writer(int index){int n=slot(index);return n<0?null:writer[n];}
    public static String revision(int index){int n=slot(index);return n<0?null:revision[n];}
    public static boolean revisionValidForProtocol(String s){if(s==null||s.length()==0||s.length()>20)return false;if(s.length()>1&&s.charAt(0)=='0')return false;for(int i=0;i<s.length();i++)if(s.charAt(i)<'0'||s.charAt(i)>'9')return false;return true;}
    public static boolean loaded(int index){return desired(index)!=null;}
    /** Only transient loading, write, stale-revision or read errors belong beside an HMI value. */
    public static String uiMessage(int index){
        int n=slot(index);if(n<0)return null;
        return message[n]!=null?MibrI18n.localize(message[n]):desired[n]==null?MibrI18n.pick("Lesestand nicht verfügbar","Readback unavailable"):null;
    }
    public static String status(int index){
        int n=slot(index);if(n<0)return "";
        if(message[n]!=null)return MibrI18n.localize(message[n]);
        if(desired[n]==null)return MibrI18n.pick("Lesestand nicht verfügbar", "Readback unavailable");
        String text="DEFAULT".equals(stored[n])?MibrI18n.pick("Standardwert", "Compiled default"):"VERIFIED".equals(stored[n])?MibrI18n.pick("Wunsch gespeichert", "Preference stored"):MibrI18n.pick("Speicherstatus unbekannt", "Storage status unknown");
        if("1".equals(pending[n]))text+=MibrI18n.pick(" · Verbindung ausstehend", " · reconnect pending");
        if(!"UNKNOWN".equals(advertised[n]))text+=MibrI18n.pick(" · historisch in /info bestätigt: ", " · historically advertised in /info: ")+valueLabel(index,advertised[n]);
        return text+MibrI18n.pick(" · aktuelle Wirkung unbekannt", " · current effect unknown");
    }
    private static String valueLabel(int index,String value){
        if(physical(index))return physicalLabel(index==MibrPopupEditorModel.SCALE_MAIN_PHYSICAL,value);
        return "AUTO".equals(value)?MibrI18n.pick("Automatisch","Automatic"):value+" %";
    }
    /** The validated broker readback advertises writer support; storage ACK never implies display effect. */
    public static boolean writable(int index){int n=slot(index);return n>=0&&requested[n]&&"ENABLED".equals(writer[n])&&revisionValidForProtocol(revision[n])&&!saving[n]&&!stale[n]&&!refreshing[n];}
}
