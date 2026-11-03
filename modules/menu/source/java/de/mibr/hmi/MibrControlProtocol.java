package de.mibr.hmi;

import java.util.StringTokenizer;

/** Java 1.2: strictly typed TEMP-only MIBR/2 command/response boundary.
 * Desired TEMP readback is NEVER proof of effective stream application.
 */
public final class MibrControlProtocol {
    public static final String HELLO =
        "HELLO MIBR/2 mode=TEMP_NATIVE mutations=TEMP_ONLY keys=48 effective=UNCONFIRMED";
    public static final class Batch {
        public final String command;
        public final String[] keys,values;
        private Batch(String wire,String[] k,String[] v){command=wire;keys=k;values=v;}
        public int count(){return keys.length;}
    }
    public static final class Commit {
        public final String revision,state;
        private Commit(String r,String s){revision=r;state=s;}
    }
    private MibrControlProtocol(){}
    static boolean token(String t){
        if(t==null||t.length()!=32)return false;
        for(int i=0;i<32;i++){
            char c=t.charAt(i);
            if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;
        }
        return true;
    }
    static boolean revision(String n){
        if(n==null||n.length()<1||n.length()>20||n.charAt(0)=='0')return false;
        for(int i=0;i<n.length();i++)if(n.charAt(i)<'0'||n.charAt(i)>'9')return false;
        return n.length()<20||n.compareTo("18446744073709551615")<=0;
    }
    private static String field(String reply,String name){
        if(reply==null||reply.length()==0)return null;
        StringTokenizer t=new StringTokenizer(reply," ");
        String found=null,prefix=name+"=";
        while(t.hasMoreTokens()){
            String part=t.nextToken();
            if(part.startsWith(prefix)){
                if(found!=null || part.length()==prefix.length())return null;
                found=part.substring(prefix.length());
            }
        }
        return found;
    }
    private static boolean mode(String s,String prefix){
        return s!=null && s.startsWith(prefix) &&
            "UNCONFIRMED".equals(field(s,"effective")) &&
            "NONE".equals(field(s,"session"));
    }
    public static String statusRevision(String reply){
        if(!mode(reply,"STATUS mode=TEMP_NATIVE "))return null;
        if(!"UNCONFIRMED".equals(field(reply,"stored")))return null;
        String r=field(reply,"revision");return revision(r)?r:null;
    }
    public static String desiredValue(String reply,String key,String expectedRevision){
        if(!mode(reply,"VALUE key=")||!revision(expectedRevision) ||
           !key.equals(field(reply,"key")) ||
           !expectedRevision.equals(field(reply,"revision")))return null;
        String origin=field(reply,"source");
        if(!"profile".equals(origin)&&!"persistent".equals(origin)&&!"temp".equals(origin))
            return null;
        String v=field(reply,"desired");
        if(v==null||"UNCONFIRMED".equals(v))return null;
        return v;
    }
    public static boolean isTempSource(String reply){return "temp".equals(field(reply,"source"));}
    public static Batch collect(String token,String revision,MibrPopupEditorModel model){
        if(!token(token)||!revision(revision)||model==null)
            throw new IllegalArgumentException("CONTROL_BATCH_CONTEXT");
        StringBuffer payload=new StringBuffer();
        String[] keys=new String[11],values=new String[11];int count=0;
        {
            String[] groupKeys=MibrMenuDefinition.VISIBLE_KEYS;
            for(int n=0;n<groupKeys.length;n++){
                String key=groupKeys[n];int index=-1;
                for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)
                    if(key.equals(MibrSettingsCatalog.KEYS[i])){index=i;break;}
                if(index<0||!MibrPopupEditorModel.visible(index)||
                    MibrSettingsCatalog.READ_ONLY[index])
                    throw new IllegalStateException("CONTROL_VISIBLE_REGISTRY_DRIFT");
                String draft=model.draft(index);
                if(draft==null)continue;
                if(count==11)throw new IllegalStateException("CONTROL_BATCH_TOO_MANY");
                boolean legal=false;
                String[] choices=model.options(index);
                for(int i=0;i<choices.length;i++)if(draft.equals(choices[i]))legal=true;
                if(!legal)throw new IllegalArgumentException("CONTROL_DRAFT_NOT_UI_CHOICE");
                for(int i=0;i<draft.length();i++){
                    char ch=draft.charAt(i);
                    if(ch<33||ch>126||ch==';')throw new IllegalArgumentException("CONTROL_DRAFT_ENCODING");
                }
                if(count>0)payload.append(';');
                payload.append(key).append('=').append(draft);
                keys[count]=key;values[count]=draft;count++;
            }
        }
        if(count==0)throw new IllegalStateException("CONTROL_NO_PENDING_DRAFT");
        String wire="TEMPBATCH "+token+" "+revision+" "+payload.toString();
        if(wire.length()>512)throw new IllegalArgumentException("CONTROL_BATCH_OVERSIZE");
        String[] actualK=new String[count],actualV=new String[count];
        System.arraycopy(keys,0,actualK,0,count);
        System.arraycopy(values,0,actualV,0,count);
        return new Batch(wire,actualK,actualV);
    }
    public static Commit tempResult(String reply,int expectedCount){
        if(!mode(reply,"RESULT state=")||expectedCount<1||expectedCount>11 ||
           !"TEMP_READBACK".equals(field(reply,"desired")))return null;
        String state=field(reply,"state"),count=field(reply,"count"),rev=field(reply,"revision");
        if(!String.valueOf(expectedCount).equals(count)||!revision(rev))return null;
        if(!"QUEUED".equals(state)&&!"PRESENTATION_REFRESH_REQUIRED".equals(state)&&
           !"SESSION_TRANSITION_REQUIRED".equals(state)&&!"RECONNECT_REQUIRED".equals(state))
            return null;
        return new Commit(rev,state);
    }
}
