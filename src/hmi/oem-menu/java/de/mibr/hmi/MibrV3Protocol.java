package de.mibr.hmi;

import java.io.ByteArrayOutputStream;
import java.io.UnsupportedEncodingException;
import java.util.Hashtable;
import java.util.StringTokenizer;

/** Strict MIBR/3 frame/typed-state codec for IBM J9 (Java 1.2 source level).
 * Canonical registry is native; this checks only the generated 11-row UI projection.
 * STORED is not ACTIVE; runtime_correlated=0 forbids a live-effect claim.
 */
public final class MibrV3Protocol {
    private MibrV3Protocol(){}
    public static final int MAX_REQUEST=4096, MAX_REPLY=16384;
    public static final class Frame {
        public final String id, error;
        private final Hashtable fields;
        Frame(String id,String error,Hashtable fields){this.id=id;this.error=error;this.fields=fields;}
        public boolean ok(){return error==null;}
        public String get(String key){return (String)fields.get(key);}
    }
    public static final class Snapshot {
        public final String revision,stored,connected,session,pending;
        public final String[] keys=new String[11],values=new String[11],sources=new String[11],apply=new String[11];
        private Snapshot(Frame f){
            revision=required(f,"revision");stored=required(f,"stored");
            connected=required(f,"connected");session=required(f,"session");pending=required(f,"pending");
        }
    }
    public static final class Commit {
        public final String revision,activation,apply,materialized,stored;
        private Commit(Frame f){
            stored=required(f,"stored");
            revision=required(f,"revision");activation=required(f,"activation");
            apply=required(f,"apply");materialized=required(f,"materialized");
        }
    }
    private static boolean safe(int c){
        return c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='.'||c=='-'||c=='~';
    }
    public static boolean id(String s){
        if(s==null||s.length()<1||s.length()>64)return false;
        for(int i=0;i<s.length();i++){
            char c=s.charAt(i);
            if(!(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-'))return false;
        }
        return true;
    }
    public static boolean revision(String s){
        if(s==null||s.length()<1||s.length()>20||s.charAt(0)=='0')return false;
        for(int i=0;i<s.length();i++)if(s.charAt(i)<'0'||s.charAt(i)>'9')return false;
        return s.length()<20||s.compareTo("18446744073709551615")<=0;
    }
    public static String encode(String s){
        if(s==null||s.length()==0)throw new IllegalArgumentException("EMPTY_FIELD");
        try {
            byte[] data=s.getBytes("UTF-8");
            StringBuffer b=new StringBuffer();final char[] hex="0123456789ABCDEF".toCharArray();
            for(int i=0;i<data.length;i++){
                int c=data[i]&255;
                if(c<32||c==127)throw new IllegalArgumentException("CONTROL_CHARACTER");
                if(safe(c))b.append((char)c);
                else b.append('%').append(hex[c>>4]).append(hex[c&15]);
            }
            if(data.length>512)throw new IllegalArgumentException("FIELD_OVERSIZE");
            return b.toString();
        }catch(UnsupportedEncodingException e){throw new IllegalStateException("UTF8_MISSING");}
    }
    private static int hex(char c){return c>='0'&&c<='9'?c-'0':c>='A'&&c<='F'?c-'A'+10:-1;}
    static String decode(String s){
        if(s==null||s.length()==0)throw new IllegalArgumentException("EMPTY_FIELD");
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        for(int i=0;i<s.length();i++){
            int c=s.charAt(i);
            if(c=='%'){
                if(i+2>=s.length()||hex(s.charAt(i+1))<0||hex(s.charAt(i+2))<0)
                    throw new IllegalArgumentException("BAD_PERCENT");
                c=(hex(s.charAt(i+1))<<4)|hex(s.charAt(i+2));i+=2;
                if(safe(c))throw new IllegalArgumentException("NONCANONICAL_PERCENT");
            }else if(!safe(c))throw new IllegalArgumentException("BAD_FIELD_ENCODING");
            b.write(c);
        }
        try {
            byte[] data=b.toByteArray();String value=new String(data,"UTF-8");
            byte[] check=value.getBytes("UTF-8");
            if(check.length!=data.length)throw new IllegalArgumentException("BAD_UTF8");
            for(int i=0;i<data.length;i++)if(check[i]!=data[i])throw new IllegalArgumentException("BAD_UTF8");
            for(int i=0;i<value.length();i++)if(value.charAt(i)<32||value.charAt(i)==127)
                throw new IllegalArgumentException("CONTROL_CHARACTER");
            return value;
        }catch(UnsupportedEncodingException e){throw new IllegalStateException("UTF8_MISSING");}
    }
    /** A request's auth must be the last field; never print or log the result. */
    public static String request(String rid,String op,String[] names,String[] values,String secret){
        if(!id(rid)||!op.equals("HELLO")&&!op.equals("CAPABILITIES")&&!op.equals("STATUS")&&
           !op.equals("SNAPSHOT")&&!op.equals("SET")&&!op.equals("REQUEST_STATUS")&&
           !op.equals("ACTION")&&!op.equals("ACTION_STATUS")&&
           // r34: SHOW_STATUS (r23) was missing here, so the real client rejected it before any byte left the
           // HMI and the "Im Cockpit bestaetigt" text could never appear; the host fakes bypassed this check.
           !op.equals("SHOW_STATUS")&&
           // r46: engine type of the CarPlay Identify (iap2.cfg [vehicle] engine=) via the helper in the broker
           !op.equals("ENGINE_GET")&&!op.equals("ENGINE_SET")&&
           // r55: cockpit view follow (position counter and safe area per view) via the helper in the broker
           !op.equals("VIEW_GET")&&!op.equals("VIEW_SET"))
            throw new IllegalArgumentException("BAD_VERB_OR_ID");
        if(names==null||values==null||names.length!=values.length||names.length>64||
           secret==null||secret.length()!=64)throw new IllegalArgumentException("BAD_FIELDS");
        for(int i=0;i<64;i++)if(!((secret.charAt(i)>='a'&&secret.charAt(i)<='f')||
                                       (secret.charAt(i)>='0'&&secret.charAt(i)<='9')))
            throw new IllegalArgumentException("BAD_AUTH");
        StringBuffer out=new StringBuffer("MIBR/3 ").append(rid).append(' ').append(op);
        Hashtable seen=new Hashtable();
        for(int i=0;i<names.length;i++){
            String n=names[i];
            if(n==null||n.length()==0||!Character.isLetter(n.charAt(0))||
               seen.put(n,n)!=null||"auth".equals(n))throw new IllegalArgumentException("BAD_FIELD_NAME");
            for(int j=1;j<n.length();j++)if(!safe(n.charAt(j)))throw new IllegalArgumentException("BAD_FIELD_NAME");
            out.append(i==0?' ':';').append(n).append('=').append(encode(values[i]));
        }
        out.append(names.length==0?' ':';').append("auth=").append(secret).append('\n');
        if(out.length()>MAX_REQUEST)throw new IllegalArgumentException("REQUEST_OVERSIZE");
        return out.toString();
    }
    /** Reject mismatched request ID, duplicate keys, invalid/noncanonical percent and partial frames. */
    public static Frame parse(String wire,String expected){
        if(!id(expected)||wire==null||wire.length()<13||wire.length()>MAX_REPLY||
           wire.charAt(wire.length()-1)!='\n'||wire.indexOf('\r')>=0)
            throw new IllegalArgumentException("BAD_REPLY");
        for(int i=0;i<wire.length()-1;i++)if(wire.charAt(i)<32||wire.charAt(i)>126)
            throw new IllegalArgumentException("NON_ASCII_REPLY");
        String head="MIBR/3 "+expected+" ";
        if(!wire.startsWith(head))throw new IllegalArgumentException("WRONG_PROTOCOL_OR_ID");
        String body=wire.substring(head.length(),wire.length()-1);
        if(body.startsWith("ERR ")){
            String error=body.substring(4);
            if(!id(error))throw new IllegalArgumentException("BAD_ERROR");
            return new Frame(expected,error,new Hashtable());
        }
        if(!body.startsWith("OK "))throw new IllegalArgumentException("BAD_STATUS");
        Hashtable fields=new Hashtable();
        String payload=body.substring(3);
        if(payload.length()==0||payload.charAt(0)==';'||payload.charAt(payload.length()-1)==';'||
           payload.indexOf(";;")>=0)throw new IllegalArgumentException("BAD_DELIMITERS");
        StringTokenizer tokens=new StringTokenizer(payload,";");
        int count=0;
        while(tokens.hasMoreTokens()){
            String pair=tokens.nextToken();int eq=pair.indexOf('=');
            if(eq<1||eq==pair.length()-1||pair.indexOf('=',eq+1)>=0||count++>=320)
                throw new IllegalArgumentException("BAD_PAIR");
            String name=pair.substring(0,eq);
            if(!Character.isLetter(name.charAt(0)))throw new IllegalArgumentException("BAD_KEY");
            for(int j=1;j<name.length();j++)if(!safe(name.charAt(j)))throw new IllegalArgumentException("BAD_KEY");
            String value=decode(pair.substring(eq+1));
            if(fields.put(name,value)!=null)throw new IllegalArgumentException("DUPLICATE_FIELD");
        }
        if(fields.size()!=count||count==0)throw new IllegalArgumentException("BAD_FIELD_COUNT");
        return new Frame(expected,null,fields);
    }
    private static String required(Frame f,String name){
        if(f==null||!f.ok()||f.get(name)==null)throw new IllegalArgumentException("MISSING_"+name);
        return f.get(name);
    }
    public static boolean hello(Frame f){
        return f!=null&&f.ok()&&"MIBR/3".equals(f.get("version"))&&
            "2".equals(f.get("schema"))&&"48".equals(f.get("registry_keys"));
    }
    public static boolean capabilities(Frame f){
        return f!=null&&f.ok()&&"1".equals(f.get("snapshot"))&&
            ("0".equals(f.get("durable_set"))||"1".equals(f.get("durable_set")))&&
            "0".equals(f.get("reconnect"))&&"0".equals(f.get("presentation_refresh"))&&
            "0".equals(f.get("session_control"));
    }
    public static boolean durable(Frame f){
        return capabilities(f)&&"1".equals(f.get("durable_set"))&&
            "NATIVE_PROFILE_GUARDED".equals(f.get("phase"));
    }
    public static Snapshot snapshot(Frame f){
        if(f==null||!f.ok()||!"11".equals(f.get("row_count"))||
           !revision(f.get("revision"))||!"0".equals(f.get("runtime_correlated"))||
           !"NONE".equals(f.get("session")))throw new IllegalArgumentException("SNAPSHOT_HEADER");
        Snapshot snap=new Snapshot(f);
        if(!"UNCONFIRMED".equals(snap.stored)&&!"VERIFIED".equals(snap.stored))
            throw new IllegalArgumentException("SNAPSHOT_STORED");
        // Native scope=ui keeps its exact 11-row order, even where
        // the r8 HMI hides a row (navigation.url): parse all, draw only visible.
        String[] section=MibrMenuDefinition.NATIVE_UI_KEYS;
        if(section.length!=11)throw new IllegalStateException("NATIVE_UI_KEY_DRIFT");
        {
            int j=0;
            for(int i=0;i<section.length;i++,j++){
                String prefix="row."+j+".";
                String key=required(f,prefix+"key"),value=required(f,prefix+"value");
                String source=required(f,prefix+"source"),apply=required(f,prefix+"apply");
                if(!section[i].equals(key)||!known(key)||!source.equals("temp")&&!source.equals("profile")&&!source.equals("persistent")||
                   !"UNKNOWN".equals(f.get(prefix+"active"))||!"UNKNOWN".equals(f.get(prefix+"advertised"))||
                   !apply.equals(MibrSettingsCatalog.APPLY[index(key)])||value.length()==0)
                    throw new IllegalArgumentException("SNAPSHOT_ROW_"+j);
                snap.keys[j]=key;snap.values[j]=value;snap.sources[j]=source;snap.apply[j]=apply;
            }
        }
        return snap;
    }
    public static int index(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)if(MibrSettingsCatalog.KEYS[i].equals(key))return i;
        return -1;
    }
    public static boolean known(String key){return index(key)>=0;}
    /** SHOW_STATUS: NONE, PENDING, SHOWN, FAILED, NO_SESSION or TIMEOUT. Anything else counts as UNKNOWN. */
    public static String showState(Frame f){
        String s=f==null||!f.ok()?null:f.get("state");
        if("NONE".equals(s)||"PENDING".equals(s)||"SHOWN".equals(s)||"FAILED".equals(s)||
           "NO_SESSION".equals(s)||"TIMEOUT".equals(s))return s;
        return "UNKNOWN";
    }
    /** ENGINE_GET / ENGINE_SET reply: engine, announced and pending must all be present and well-formed, else null. */
    public static String[] engine(Frame f){
        if(f==null||!f.ok())return null;
        String e=f.get("engine"),a=f.get("announced"),p=f.get("pending");
        if(MibrEngineState.index(e)<0||MibrEngineState.index(a)<0||!"0".equals(p)&&!"1".equals(p))return null;
        return new String[]{e,a,p};
    }
    /** VIEW_GET / VIEW_SET reply: follow, sport, m0, m1, m4, rs, pos must all be well-formed single digits, else null. */
    public static String[] view(Frame f){
        if(f==null||!f.ok())return null;
        String follow=f.get("follow"),sport=f.get("sport"),m0=f.get("m0"),m1=f.get("m1"),m4=f.get("m4"),
               rs=f.get("rs"),pos=f.get("pos");
        if(!bit(follow)||!bit(sport)||!area(m0)||!area(m1)||!area(m4)||!view5(rs)||!view5(pos))return null;
        return new String[]{follow,sport,m0,m1,m4,rs,pos};
    }
    private static boolean view5(String s){return s!=null&&s.length()==1&&s.charAt(0)>='0'&&s.charAt(0)<='4';}
    private static boolean bit(String s){return "0".equals(s)||"1".equals(s);}
    private static boolean area(String s){return "0".equals(s)||"1".equals(s)||"2".equals(s);}
    public static Commit commit(Frame f,String key,String wanted){
        if(f==null||!f.ok()||!known(key)||wanted==null||
           !"VERIFIED".equals(f.get("stored"))&&!"PENDING_PERSIST".equals(f.get("stored"))&&!"RUNTIME_ONLY".equals(f.get("stored"))||!"UNKNOWN".equals(f.get("active"))||
           !revision(f.get("revision"))||
           !"UNCHANGED".equals(f.get("apply"))&&!"PENDING".equals(f.get("apply"))||
           !"1".equals(f.get("materialized"))&&!"0".equals(f.get("materialized")))
            throw new IllegalArgumentException("SET_NOT_VERIFIED");
        String expected=MibrSettingsCatalog.APPLY[index(key)].toUpperCase();
        if(!expected.equals(f.get("activation")))throw new IllegalArgumentException("SET_APPLY_DRIFT");
        return new Commit(f);
    }

    /* ---- Visible-route ACTION. Momentary, never a stored preference. ---- */
    public static final String STOCK110="STOCK110",DIRECT111="DIRECT111",UNKNOWN_ROUTE="UNKNOWN";
    public static boolean knownRoute(String r){return STOCK110.equals(r)||DIRECT111.equals(r);}
    /** CAPABILITIES.route_action: 0 is the legitimate default, not an error. */
    public static boolean routeAction(Frame f){
        return capabilities(f)&&"1".equals(f.get("route_action"));
    }
    /** Fresh STATUS observation. session/generation are valid only when correlated and known. */
    public static final class RouteState {
        public final boolean correlated;
        public final String visible,session,generation;
        private RouteState(boolean c,String v,String s,String g){correlated=c;visible=v;session=s;generation=g;}
        /** True only for an independently observed owner state that an ACTION may compare-and-set against. */
        public boolean actionable(){return correlated&&knownRoute(visible)&&session!=null&&generation!=null;}
        public String opposite(){return STOCK110.equals(visible)?DIRECT111:DIRECT111.equals(visible)?STOCK110:null;}
    }
    public static RouteState routeState(Frame f){
        if(f==null||!f.ok())throw new IllegalArgumentException("ROUTE_STATUS");
        String corr=f.get("route_correlated"),visible=f.get("visible_route");
        if(!"0".equals(corr)&&!"1".equals(corr)||visible==null||
           !UNKNOWN_ROUTE.equals(visible)&&!knownRoute(visible))throw new IllegalArgumentException("ROUTE_STATUS_FIELDS");
        if("0".equals(corr)||UNKNOWN_ROUTE.equals(visible))
            return new RouteState(false,UNKNOWN_ROUTE,null,null);
        String s=f.get("route_session"),g=f.get("route_generation");
        if(!revision(s)||!revision(g))throw new IllegalArgumentException("ROUTE_OWNER_PROOF");
        return new RouteState(true,visible,s,g);
    }
    /** Exact seven ACTION fields in contract order; the target is always the explicit opposite of the observed route. */
    public static String[][] routeActionFields(RouteState observed,String rid){
        if(observed==null||!observed.actionable()||!id(rid))throw new IllegalArgumentException("ROUTE_NOT_ACTIONABLE");
        return new String[][]{
            {"kind","target","expected_route","expected_session","expected_generation","origin","request_id"},
            {"SET_VISIBLE_ROUTE",observed.opposite(),observed.visible,observed.session,observed.generation,"HMI",rid}};
    }
    public static final class RouteReceipt {
        public final String target,apply;
        public final boolean active;
        private RouteReceipt(String t,String a){target=t;apply=a;active="ACTIVE".equals(a);}
    }
    private static RouteReceipt receipt(Frame f,String kind,String target,boolean status,String rid){
        if(f==null||!f.ok()||!"SET_VISIBLE_ROUTE".equals(f.get("kind"))||!target.equals(f.get("target"))||
           !"UNCHANGED".equals(f.get("stored")))throw new IllegalArgumentException("ROUTE_RECEIPT");
        String apply=f.get("apply");
        if(!"ACTIVE".equals(apply)&&!"PENDING".equals(apply))throw new IllegalArgumentException("ROUTE_APPLY");
        if(status){
            if(!rid.equals(f.get("original_request_id"))||!"HISTORICAL".equals(f.get("receipt_scope")))
                throw new IllegalArgumentException("ROUTE_STATUS_RECEIPT");
        }else if("ACTIVE".equals(apply)){
            if(!target.equals(f.get("visible_route"))||!revision(f.get("owner_session"))||!revision(f.get("owner_generation")))
                throw new IllegalArgumentException("ROUTE_ACTIVE_WITHOUT_OWNER_PROOF");
        }else if(!UNKNOWN_ROUTE.equals(f.get("visible_route")))
            throw new IllegalArgumentException("ROUTE_PENDING_VISIBLE");
        return new RouteReceipt(target,apply);
    }
    public static RouteReceipt actionReceipt(Frame f,String target){return receipt(f,"ACTION",target,false,null);}
    /** ACTION_STATUS is historical: always follow with a fresh STATUS before updating the display. */
    public static RouteReceipt actionStatusReceipt(Frame f,String target,String originalRid){
        return receipt(f,"ACTION_STATUS",target,true,originalRid);
    }
}
