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
    public static boolean physicalValid(String value){return "BASE".equals(value)||"P20".equals(value)||"P30".equals(value)||"P50".equals(value);}
    public static boolean valid(int index,String value){return (index==MibrPopupEditorModel.SCALE_PHYSICAL||index==MibrPopupEditorModel.SCALE_MAIN_PHYSICAL)?physicalValid(value):valid(value);}
    public static void reset(){for(int i=0;i<4;i++){desired[i]=advertised[i]=effective[i]=stored[i]=pending[i]=writer[i]=revision[i]=advertisedScope[i]=message[i]=null;requested[i]=stale[i]=saving[i]=refreshing[i]=false;}}
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
        if(index==MibrPopupEditorModel.SCALE_MAIN_PHYSICAL){
            if("BASE".equals(value))return MibrI18n.pick("Original","Original");
            if("P20".equals(value))return "+20 %";
            if("P30".equals(value))return "+30 %";
            if("P50".equals(value))return "+50 %";
        }
        if("BASE".equals(value))return "200 x 74 mm";
        if("P20".equals(value))return "240 x 89 mm";
        if("P30".equals(value))return "260 x 96 mm";
        if("P50".equals(value))return "300 x 111 mm";
        return "AUTO".equals(value)?MibrI18n.pick("Automatisch","Automatic"):value+" %";
    }
    /** The validated broker readback advertises writer support; storage ACK never implies display effect. */
    public static boolean writable(int index){int n=slot(index);return n>=0&&requested[n]&&"ENABLED".equals(writer[n])&&revisionValidForProtocol(revision[n])&&!saving[n]&&!stale[n]&&!refreshing[n];}
}
