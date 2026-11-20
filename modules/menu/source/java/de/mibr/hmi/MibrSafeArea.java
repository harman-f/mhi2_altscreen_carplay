package de.mibr.hmi;

/**
 * Safe areas of the three cockpit views, stored as "x,y,w,h" inside the 1010x376 stream. The menu shows the four
 * edges in stream pixels, the numbers of the calibration picture: moving one edge leaves the other three alone.
 * A step that would leave the stream or fall below the minimum size stops at the limit.
 *
 * r15 (owner 2026-11-17): the edges Links (x1), Oben (y1), Rechts (x2), Unten (y2) are edited as absolute positions
 * (OEM slider rows, step SLIDER_STEP, plus the slider's own -/+ buttons for 1 px). Storage stays x,y,w,h with
 * x=x1, y=y1, w=x2-x1, h=y2-y1; the conversion lives only here. The minimum size stays MIN_W x MIN_H, the same
 * rule as rect_valid() in the broker (mibr_durable_switch.c) and the GEN2/HTML readers, so every value the menu
 * can produce is accepted by every reader and every stored value stays valid.
 */
final class MibrSafeArea {
    static final int WIDTH=1010,HEIGHT=376,MIN_W=100,MIN_H=60;
    /** Slider granularity in stream pixels; finer steps come from the -/+ buttons and the dropdown (1 px). */
    static final int SLIDER_STEP=10;
    /** Flash protection (owner rule): SAFE_*_SET rewrites a file on /mnt/app. A wish is only sent after the edge was
     * unchanged for IDLE_MS, at most one SET is in flight, the final value is always sent. A drag therefore writes
     * once when the finger pauses or lifts, not per slider event; the cockpit follows at that moment. */
    static final long IDLE_MS=700L;
    static final String STANDARD="std";
    /** True while the owned page resolved the native OEM slider source (MibrSafeSliderSource); false = fallback,
     * the edge rows alone (dropdown with 1/10/50 px steps), exactly the pre-r15 behaviour. */
    static volatile boolean sliderRows;
    /** r15d: sticky for the rest of the HMI run after a layout with slider rows threw (pre-r15 rows from then on). */
    static volatile boolean sliderDisabled;
    /** Slider rows are shown: source READY and never disabled by a layout failure. */
    static boolean slidersShown(){return sliderRows&&!sliderDisabled;}
    static final int FAIL_LEAVE=0,FAIL_FALLBACK=1;
    /** A render threw. With slider rows involved (first time): disable them for good and re-render without;
     * otherwise (or if that fallback render throws too) the existing failed()/leave path. */
    static synchronized int onLayoutFailure(boolean slidersInvolved){
        if(slidersInvolved&&!sliderDisabled){sliderDisabled=true;return FAIL_FALLBACK;}
        return FAIL_LEAVE;
    }
    /** r15c layout plan of one render (states as MibrSafeSliderSource: -1 none, 0 pending, 1 ready, 2 failed). */
    static final int PLAN_LAYOUT=0,PLAN_RESOLVE=1,PLAN_RERENDER=2;
    /** rowsHaveSliders: the rows were computed while slider rows were shown (r15g: collapsed rows have none). */
    static int sliderPlan(boolean edgePage,int sourceState,boolean rowsHaveSliders){
        if(!edgePage||sourceState<0||sliderDisabled)return PLAN_LAYOUT;
        if(sourceState==0)return PLAN_RESOLVE;                 // resolve now, before this page's first layout
        if(sourceState==1&&!rowsHaveSliders&&slidersShown())return PLAN_RERENDER; // rows were computed before READY
        return PLAN_LAYOUT;
    }
    /**
     * r15i polish (owner r15h list item 4): first list row after an expand/collapse tap. The page keeps its scroll
     * position; only when the expanded header or its slider row (header+1) would be off screen the list moves just
     * enough to show both (stock keeps the expanded slider visible without scrolling).
     * @param first first visible row before the tap, @param visible fully visible rows (<=0: unknown, 5 assumed),
     * @param header expanded header row or -1 (collapse), @param count rows after the tap
     */
    static int revealFirst(int first,int visible,int header,int count){
        if(count<=0)return 0;
        int n=visible>0?visible:5;
        int top=Math.max(0,first);
        if(header>=0){
            int last=Math.min(count-1,header+1);
            if(last>top+n-1)top=last-n+1;
            if(header<top)top=header;
        }
        return Math.max(0,Math.min(top,Math.max(0,count-n)));
    }
    static final String[] OPTIONS={"-50","-10","-1","+1","+10","+50",STANDARD};
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
        int wanted=STANDARD.equals(option)?edge(d,field):
            edge(f,field)+Integer.parseInt(option.charAt(0)=='+'?option.substring(1):option);
        return setEdge(f,field,wanted);
    }
    /** One edge (0 left, 1 top, 2 right, 3 bottom) moved to an absolute stream position, clamped to the stream and
     * to the minimum size against the opposite edge; the other three edges stay. */
    static String setEdge(String value,String defaultValue,int field,int wanted){
        int[] f=parse(value);
        if(f==null)f=parse(defaultValue);
        return setEdge(f,field,wanted);
    }
    private static String setEdge(int[] f,int field,int wanted){
        int left=f[0],top=f[1],right=f[0]+f[2],bottom=f[1]+f[3];
        if(field==0)left=Math.max(0,Math.min(wanted,right-MIN_W));
        else if(field==1)top=Math.max(0,Math.min(wanted,bottom-MIN_H));
        else if(field==2)right=Math.min(WIDTH,Math.max(wanted,left+MIN_W));
        else bottom=Math.min(HEIGHT,Math.max(wanted,top+MIN_H));
        return left+","+top+","+(right-left)+","+(bottom-top);
    }
    /** The edge position, from the value or else the default. */
    static int edgeValue(String value,String defaultValue,int field){
        int[] f=parse(value);
        if(f==null)f=parse(defaultValue);
        return edge(f,field);
    }
    /** Slider range of an edge: 0..1010 horizontally, 0..376 vertically. */
    static int span(int field){return field==0||field==2?WIDTH:HEIGHT;}
    /** r15h: step 0..8 of the stock 9-image mini-slider preview for an edge value (assumed linear). */
    static int previewStep(int value,int span){
        if(span<=0)return 0;
        int v=Math.max(0,Math.min(span,value));
        return (v*8+span/2)/span;
    }

    /* ---- live edit of one area (r15): the newest wish is kept, at most one SET is in flight ---- */

    /** The area as the rows show it: the unsent/unconfirmed wish, else the broker readback, else the file. */
    static String shown(MibrDurableSwitch sw){
        synchronized(sw){
            if(sw.wanted!=null)return sw.wanted;
        }
        return sw.revision()!=null?sw.value():sw.persistedValue();
    }
    /** A slider position: the newest wish for this area (other edges unchanged). */
    static String wantEdge(MibrDurableSwitch sw,int field,int px){return wantEdge(sw,field,px,System.currentTimeMillis());}
    static String wantEdge(MibrDurableSwitch sw,int field,int px,long now){
        String next=setEdge(shown(sw),sw.defaultValue(),field,px);
        synchronized(sw){sw.wanted=next;sw.wantedAt=now;}
        return next;
    }
    /** A -/+ press or a dropdown choice relative to the shown edge (same debounce as the slider). */
    static String wantOption(MibrDurableSwitch sw,int field,String option){return wantOption(sw,field,option,System.currentTimeMillis());}
    static String wantOption(MibrDurableSwitch sw,int field,String option,long now){
        String next=step(shown(sw),sw.defaultValue(),field,option);
        synchronized(sw){sw.wanted=next;sw.wantedAt=now;}
        return next;
    }
    /** The value to SET now, or null: nothing new, still moving (idle &lt; IDLE_MS) or a SET in flight. */
    static String due(MibrDurableSwitch sw){return due(sw,System.currentTimeMillis());}
    static String due(MibrDurableSwitch sw,long now){
        synchronized(sw){
            if(sw.setInFlight||sw.wanted==null)return null;
            if(sw.wanted.equals(sw.value())&&sw.revision()!=null){sw.wanted=null;return null;}
            if(now-sw.wantedAt<IDLE_MS)return null;
            return sw.wanted;
        }
    }
    /** Milliseconds until the newest wish becomes due (0 = now), or -1 when there is none. */
    static long waitMs(MibrDurableSwitch sw,long now){
        synchronized(sw){
            if(sw.wanted==null)return -1L;
            long left=IDLE_MS-(now-sw.wantedAt);
            return left>0L?left:0L;
        }
    }
    /** A failed or refused SET drops the wish: the rows show the stored value again. */
    static void drop(MibrDurableSwitch sw){synchronized(sw){sw.wanted=null;sw.staleRetry=false;sw.resendAfterRead=false;}}
    static final int STALE_REREAD=1,STALE_GIVE_UP=2;
    /** r15f: a SET answered STALE_REVISION: re-read the current value+revision once and resend; a second time: give up. */
    static synchronized int onStale(MibrDurableSwitch sw){
        synchronized(sw){
            if(sw.wanted!=null&&!sw.staleRetry){sw.staleRetry=true;sw.resendAfterRead=true;return STALE_REREAD;}
        }
        drop(sw);
        return STALE_GIVE_UP;
    }
    /** Diagnostic sink (the OEM rows route it to /tmp/mibr-hmi-diag.log); null on the host. */
    static interface Diag {void line(String text);}
    static volatile Diag diag;
    static void diag(String text){Diag d=diag;if(d!=null)try{d.line(text);}catch(Throwable ignored){}}

    static String field(String value,String defaultValue,int field){
        if(field==RESET_FIELD)return value==null||value.equals(defaultValue)?MibrI18n.pick("Standard","Default"):MibrI18n.pick("Geändert","Changed");
        int[] f=parse(value);
        if(f==null)f=parse(defaultValue);
        return String.valueOf(edge(f,field));
    }
}
