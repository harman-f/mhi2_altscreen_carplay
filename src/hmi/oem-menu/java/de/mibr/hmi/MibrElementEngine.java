package de.mibr.hmi;

import java.util.Hashtable;

/**
 * Bounded, backend-free interaction engine for owned OEM element adapters.
 * CURRENT is explicit observed data; a DRAFT is never effective/ACK/applied.
 * Single pending editor, complete cancel/close/detach, no I/O or widget calls.
 */
public final class MibrElementEngine {
    private final MibrElementSpec[] elements;
    private final Hashtable indices=new Hashtable();
    private final String[] observed, draft;
    private int editing=-1, revision;
    private String pending;
    private boolean detached;
    public MibrElementEngine(MibrElementSpec[] descriptors){
        if(descriptors==null || descriptors.length==0 || descriptors.length>256)
            throw new IllegalArgumentException("ELEMENT_COUNT");
        elements=(MibrElementSpec[])descriptors.clone();
        observed=new String[elements.length];draft=new String[elements.length];
        for(int i=0;i<elements.length;i++){
            MibrElementSpec s=elements[i];
            if(s==null || indices.put(s.id,new Integer(i))!=null)
                throw new IllegalArgumentException("DUPLICATE_OR_NULL_ELEMENT");
        }
    }
    private void active(){if(detached)throw new IllegalStateException("ELEMENT_SESSION_DETACHED");}
    private int index(String id){
        Integer n=(Integer)indices.get(id);
        if(n==null)throw new IllegalArgumentException("ELEMENT_NOT_FOUND");
        return n.intValue();
    }
    public MibrElementSpec element(String id){return elements[index(id)];}
    public int count(){return elements.length;}
    public int revision(){return revision;}
    public boolean editing(){return editing>=0;}
    public String editingId(){return editing<0?null:elements[editing].id;}
    /** Masked input never escapes through generic state getters. */
    public String observed(String id){int i=index(id);return elements[i].masked &&
        observed[i]!=null?"MASKED":observed[i];}
    public String draft(String id){int i=index(id);return elements[i].masked &&
        draft[i]!=null?"MASKED":draft[i];}
    public String presentation(String id){
        int i=index(id);MibrElementSpec s=elements[i];
        if(s.masked)return draft[i]==null?"CURRENT: "+(observed[i]==null?"UNKNOWN":"MASKED")
            :"DRAFT: MASKED";
        if(draft[i]!=null)return "DRAFT: "+draft[i];
        return "CURRENT: "+(observed[i]==null?"UNKNOWN":observed[i]);
    }
    /** Called ONLY with a proven external snapshot; never from a default or UI tap. */
    public void observe(String id,String value){
        active();int i=index(id);
        MibrElementSpec s=elements[i];
        if(s.kind==MibrElementSpec.LINK || s.kind==MibrElementSpec.CONFIRM ||
           s.kind==MibrElementSpec.ACTION)
            throw new IllegalArgumentException("NONVALUE_OBSERVATION");
        observed[i]=value==null?null:s.validate(value);
        revision++;
    }
    public void begin(String id){
        active();cancel();
        int i=index(id);MibrElementSpec s=elements[i];
        if(s.readOnly || s.kind==MibrElementSpec.LINK ||
           s.kind==MibrElementSpec.ACTION || s.kind==MibrElementSpec.CONFIRM)
            throw new IllegalArgumentException("NOT_EDITABLE");
        editing=i;
    }
    public void propose(String proposed){
        active();if(editing<0)throw new IllegalStateException("NO_EDIT_SESSION");
        pending=elements[editing].validate(proposed);
    }
    /** Works for choice/SpinLabel; mode0 display-only uses separate arrow actions. */
    public void spin(int delta){
        active();if(editing<0)throw new IllegalStateException("NO_EDIT_SESSION");
        MibrElementSpec s=elements[editing];
        if(s.kind!=MibrElementSpec.SPIN || (delta!=1 && delta!=-1))
            throw new IllegalArgumentException("SPIN_DELTA");
        String[] values=s.choices();
        String value=pending==null?(draft[editing]==null?observed[editing]:draft[editing]):pending;
        int index=-1;for(int i=0;i<values.length;i++)if(values[i].equals(value))index=i;
        if(index<0)throw new IllegalStateException("SPIN_CURRENT_UNKNOWN");
        int next=index+delta;
        if(s.cyclic){if(next<0)next=values.length-1;if(next>=values.length)next=0;}
        else{if(next<0)next=0;if(next>=values.length)next=values.length-1;}
        pending=values[next];
    }
    /** Locally commits a candidate label ONLY. No state write or runtime action. */
    public void acceptDraft(){
        active();if(editing<0 || pending==null)throw new IllegalStateException("NO_PENDING_VALUE");
        draft[editing]=pending;editing=-1;pending=null;revision++;
    }
    public void cancel(){
        pending=null;editing=-1;revision++;
    }
    public void discardDraft(String id){active();draft[index(id)]=null;revision++;}
    public void discardAll(){
        active();cancel();
        for(int i=0;i<draft.length;i++)draft[i]=null;
        revision++;
    }
    /** No public getter for a masked value; only dedicated user input is allowed. */
    public String pendingForWidget(){
        if(editing<0)return null;
        return elements[editing].masked?(pending==null?null:"MASKED"):pending;
    }
    /** Confirm/Action return a local request token; NOTHING invokes an OEM action. */
    public String localIntent(String id,boolean userConfirmed){
        active();MibrElementSpec spec=elements[index(id)];
        if(spec.kind!=MibrElementSpec.CONFIRM && spec.kind!=MibrElementSpec.ACTION)
            throw new IllegalArgumentException("NOT_AN_ACTION");
        if(spec.kind==MibrElementSpec.CONFIRM && !userConfirmed)return null;
        cancel();return "LOCAL_INTENT_ONLY:"+id;
    }
    public void detach(){
        if(detached)return;
        cancel();
        for(int i=0;i<observed.length;i++){observed[i]=null;draft[i]=null;}
        indices.clear();detached=true;revision++;
    }
    public boolean isDetached(){return detached;}
}
