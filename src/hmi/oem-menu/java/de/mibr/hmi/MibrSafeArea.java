package de.mibr.hmi;

/**
 * Safe areas of the three cockpit views, stored as "x,y,w,h" inside the 1010x376 stream. The menu shows the four
 * edges in stream pixels, the numbers of the calibration picture: moving one edge leaves the other three alone.
 * A step that would leave the stream or fall below the minimum size stops at the limit.
 */
final class MibrSafeArea {
    static final int WIDTH=1010,HEIGHT=376,MIN_W=100,MIN_H=60;
    static final String STANDARD="std";
    static final String[] OPTIONS={"-50","-10","-2","+2","+10","+50",STANDARD};
    /** The reset row: all four numbers of the area back to the default. */
    static final int RESET_FIELD=4;
    static final String[] RESET_OPTIONS={STANDARD};
    private MibrSafeArea(){}

    /** {x,y,w,h}, or null unless it is canonical and inside the stream. */
    static int[] parse(String v){
        if(v==null)return null;
        int[] f=new int[4];
        int at=0;
        for(int i=0;i<4;i++){
            int end=v.indexOf(',',at);
            if(i==3){if(end>=0)return null;end=v.length();}
            else if(end<0)return null;
            if(end==at||end-at>4||(end-at>1&&v.charAt(at)=='0'))return null;
            int n=0;
            for(int k=at;k<end;k++){
                char c=v.charAt(k);
                if(c<'0'||c>'9')return null;
                n=n*10+(c-'0');
            }
            f[i]=n;
            at=end+1;
        }
        return f[2]>=MIN_W&&f[3]>=MIN_H&&f[0]+f[2]<=WIDTH&&f[1]+f[3]<=HEIGHT?f:null;
    }

    /** The edge of field 0 left, 1 top, 2 right, 3 bottom. */
    private static int edge(int[] f,int field){
        return field==0?f[0]:field==1?f[1]:field==2?f[0]+f[2]:f[1]+f[3];
    }

    /** The new value after a popup choice on one edge or on the reset row. */
    static String step(String value,String defaultValue,int field,String option){
        if(field==RESET_FIELD)return defaultValue;
        int[] f=parse(value);
        int[] d=parse(defaultValue);
        if(f==null)f=d;
        int left=f[0],top=f[1],right=f[0]+f[2],bottom=f[1]+f[3];
        int wanted=STANDARD.equals(option)?edge(d,field):
            edge(f,field)+Integer.parseInt(option.charAt(0)=='+'?option.substring(1):option);
        if(field==0)left=Math.max(0,Math.min(wanted,right-MIN_W));
        else if(field==1)top=Math.max(0,Math.min(wanted,bottom-MIN_H));
        else if(field==2)right=Math.min(WIDTH,Math.max(wanted,left+MIN_W));
        else bottom=Math.min(HEIGHT,Math.max(wanted,top+MIN_H));
        return left+","+top+","+(right-left)+","+(bottom-top);
    }

    static String field(String value,String defaultValue,int field){
        if(field==RESET_FIELD)return value==null||value.equals(defaultValue)?MibrI18n.pick("Standard","Default"):MibrI18n.pick("Geändert","Changed");
        int[] f=parse(value);
        if(f==null)f=parse(defaultValue);
        return String.valueOf(edge(f,field));
    }
}
