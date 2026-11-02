package de.mibr.hmi;

/**
 * Compiled, typed descriptor for an independently owned Settings element.
 * It describes the UI/control contract; it NEVER defines a DSI, runtime writer
 * or a second Classic111 settings registry. Java 1.2 compatible.
 */
public final class MibrElementSpec {
    public static final int LINK=1, BOOLEAN=2, CHOICE=3, SLIDER=4, AXIS2=5,
        SPIN=6, INPUT=7, INFO=8, CONFIRM=9, STATUS=10, PROGRESS=11, ACTION=12;
    public final String id, label, page;
    public final int kind, min, max, step, minY, maxY, stepY, maxLength;
    public final boolean cyclic, masked, readOnly;
    private final String[] choices;
    private MibrElementSpec(String id,String label,int kind,String page,
          String[] choices,int min,int max,int step,int minY,int maxY,int stepY,
          int maxLength,boolean cyclic,boolean masked,boolean readOnly) {
        if(id==null || id.length()==0 || id.length()>128 || label==null ||
           label.length()==0 || label.length()>256 || kind<LINK || kind>ACTION)
            throw new IllegalArgumentException("ELEMENT_ID_LABEL_KIND");
        for(int i=0;i<id.length();i++){
            char c=id.charAt(i);
            if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
                 (c>='0'&&c<='9')||c=='.'||c=='_'||c=='-'))
                throw new IllegalArgumentException("ELEMENT_ID_CHARACTER");
        }
        if(kind==LINK && (page==null || page.length()==0))
            throw new IllegalArgumentException("LINK_TARGET_MISSING");
        if(kind!=LINK && page!=null)
            throw new IllegalArgumentException("NONLINK_PAGE");
        if((kind==CHOICE || kind==SPIN) && (choices==null || choices.length==0 ||
           choices.length>128))throw new IllegalArgumentException("OPTIONS_MISSING");
        if(kind!=CHOICE && kind!=SPIN && choices!=null)
            throw new IllegalArgumentException("OPTIONS_ON_NONCHOICE");
        if(choices!=null)for(int i=0;i<choices.length;i++){
            if(choices[i]==null || choices[i].length()==0 || choices[i].length()>256)
                throw new IllegalArgumentException("OPTION_INVALID");
            for(int j=0;j<i;j++)if(choices[i].equals(choices[j]))
                throw new IllegalArgumentException("OPTION_DUPLICATE");
        }
        if(kind==SLIDER || kind==AXIS2){
            if(step<=0 || min>=max || ((long)max-(long)min)%step!=0L)
                throw new IllegalArgumentException("X_RANGE");
        }
        if(kind==AXIS2 && (stepY<=0 || minY>=maxY ||
           ((long)maxY-(long)minY)%stepY!=0L))
            throw new IllegalArgumentException("Y_RANGE");
        if(kind==INPUT && (maxLength<1 || maxLength>4096))
            throw new IllegalArgumentException("INPUT_LENGTH");
        if(cyclic && kind!=SPIN)throw new IllegalArgumentException("NONSPIN_CYCLIC");
        if(masked && kind!=INPUT)throw new IllegalArgumentException("NONINPUT_MASK");
        this.id=id;this.label=label;this.kind=kind;this.page=page;
        this.choices=choices==null?new String[0]:(String[])choices.clone();
        this.min=min;this.max=max;this.step=step;
        this.minY=minY;this.maxY=maxY;this.stepY=stepY;
        this.maxLength=maxLength;this.cyclic=cyclic;this.masked=masked;this.readOnly=readOnly;
    }
    private static MibrElementSpec make(String id,String label,int kind,String page,
      String[] options,int min,int max,int step,int minY,int maxY,int stepY,
      int maxLength,boolean cyclic,boolean masked,boolean readOnly) {
      return new MibrElementSpec(id,label,kind,page,options,min,max,step,minY,maxY,
                                 stepY,maxLength,cyclic,masked,readOnly);
    }
    public static MibrElementSpec link(String id,String label,String target) {
        return make(id,label,LINK,target,null,0,0,0,0,0,0,0,false,false,true);
    }
    public static MibrElementSpec bool(String id,String label,boolean readOnly) {
        return make(id,label,BOOLEAN,null,null,0,0,0,0,0,0,0,false,false,readOnly);
    }
    public static MibrElementSpec choice(String id,String label,String[] values,boolean readOnly){
        return make(id,label,CHOICE,null,values,0,0,0,0,0,0,0,false,false,readOnly);
    }
    /** SpinLabel mode 0 is a display in OEM Date/Time; independent arrows own step events. */
    public static MibrElementSpec spin(String id,String label,String[] values,boolean cyclic){
        return make(id,label,SPIN,null,values,0,0,0,0,0,0,0,cyclic,false,false);
    }
    public static MibrElementSpec slider(String id,String label,int min,int max,int step){
        return make(id,label,SLIDER,null,null,min,max,step,0,0,0,0,false,false,false);
    }
    public static MibrElementSpec axis2(String id,String label,int minX,int maxX,
                                    int stepX,int minY,int maxY,int stepY){
        return make(id,label,AXIS2,null,null,minX,maxX,stepX,minY,maxY,stepY,
                    0,false,false,false);
    }
    public static MibrElementSpec input(String id,String label,int maxLength,boolean masked){
        return make(id,label,INPUT,null,null,0,0,0,0,0,0,maxLength,false,masked,false);
    }
    public static MibrElementSpec info(String id,String label){
        return make(id,label,INFO,null,null,0,0,0,0,0,0,0,false,false,true);
    }
    public static MibrElementSpec confirm(String id,String label){
        return make(id,label,CONFIRM,null,null,0,0,0,0,0,0,0,false,false,false);
    }
    public static MibrElementSpec status(String id,String label){
        return make(id,label,STATUS,null,null,0,0,0,0,0,0,0,false,false,true);
    }
    public static MibrElementSpec progress(String id,String label){
        return make(id,label,PROGRESS,null,null,0,0,0,0,0,0,0,false,false,true);
    }
    /** A visible action is a local request only; no implicit DSI/broker/IO action exists. */
    public static MibrElementSpec action(String id,String label){
        return make(id,label,ACTION,null,null,0,0,0,0,0,0,0,false,false,false);
    }
    public String[] choices(){return (String[])choices.clone();}
    public boolean isOption(String value){
        for(int i=0;i<choices.length;i++)if(choices[i].equals(value))return true;
        return false;
    }
    private static int number(String raw){
        if(raw==null || raw.length()==0 || !raw.equals(raw.trim()))
            throw new IllegalArgumentException("INTEGER_EMPTY_OR_SPACES");
        try {
            int n=Integer.parseInt(raw);
            if(!String.valueOf(n).equals(raw))throw new NumberFormatException();
            return n;
        }catch(NumberFormatException failure){throw new IllegalArgumentException("INTEGER_INVALID");}
    }
    private static void aligned(int n,int min,int max,int step){
        if(n<min || n>max || ((long)n-(long)min)%step!=0L)
            throw new IllegalArgumentException("VALUE_OUTSIDE_RANGE_OR_STEP");
    }
    /** Rejects invalid proposals, never rounds, changes domains or infers UNKNOWN as false. */
    public String validate(String proposed){
        if(proposed==null)throw new IllegalArgumentException("VALUE_MISSING");
        switch(kind){
            case BOOLEAN:
                if(!"0".equals(proposed)&&!"1".equals(proposed))
                    throw new IllegalArgumentException("BOOLEAN_NOT_0_OR_1");
                return proposed;
            case CHOICE:case SPIN:
                if(!isOption(proposed))throw new IllegalArgumentException("OPTION_NOT_DECLARED");
                return proposed;
            case SLIDER:
                aligned(number(proposed),min,max,step);return proposed;
            case AXIS2:
                int comma=proposed.indexOf(',');
                if(comma<1 || comma!=proposed.lastIndexOf(','))
                    throw new IllegalArgumentException("XY_PAIR_INVALID");
                aligned(number(proposed.substring(0,comma)),min,max,step);
                aligned(number(proposed.substring(comma+1)),minY,maxY,stepY);
                return proposed;
            case INPUT:
                if(proposed.length()>maxLength)throw new IllegalArgumentException("INPUT_TOO_LONG");
                for(int i=0;i<proposed.length();i++)
                    if(Character.isISOControl(proposed.charAt(i)))
                        throw new IllegalArgumentException("INPUT_CONTROL_CHARACTER");
                return proposed;
            case PROGRESS:
                int percent=number(proposed);
                if(percent<0 || percent>100)throw new IllegalArgumentException("PROGRESS_BOUNDS");
                return proposed;
            case INFO:case STATUS:
                if(proposed.length()>8192)throw new IllegalArgumentException("READBACK_TOO_LONG");
                return proposed;
            default:throw new IllegalArgumentException("ELEMENT_HAS_NO_VALUE");
        }
    }
}
