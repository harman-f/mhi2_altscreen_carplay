package de.mibr.hmi;

/**
 * r15: safe-area edges as sliders. Host part only: edge <-> x,y,w,h conversion, clamps, the live-edit coalescing
 * (newest wish, one SET in flight) and the model rows (slider row under each edge row only while the OEM source
 * resolved; fallback = the pre-r15 rows). The OEM clone itself (MibrSafeSliderSource) needs the unit.
 */
public final class MibrSafeSliderTest implements MibrCarPlayMenuModel.View {
    private String title;
    private String[] rows;
    public void show(int screen,String title,String[] rows,String detail){this.title=title;this.rows=rows;}
    private static void check(boolean c,String name){if(!c)throw new AssertionError(name);}

    public static void main(String[] args) throws Exception {
        String def="200,58,590,248";
        // edges: x1=x, y1=y, x2=x+w, y2=y+h
        check(MibrSafeArea.edgeValue("200,58,590,248",def,0)==200&&MibrSafeArea.edgeValue("200,58,590,248",def,1)==58&&
              MibrSafeArea.edgeValue("200,58,590,248",def,2)==790&&MibrSafeArea.edgeValue("200,58,590,248",def,3)==306,"edge values");
        check(MibrSafeArea.edgeValue("garbage",def,2)==790,"unreadable value shows the default edge");
        check("150,58,640,248".equals(MibrSafeArea.setEdge("200,58,590,248",def,0,150)),"Links moves alone, width follows");
        check("200,58,800,248".equals(MibrSafeArea.setEdge("200,58,590,248",def,2,1000)),"Rechts moves alone");
        check("200,58,810,248".equals(MibrSafeArea.setEdge("200,58,590,248",def,2,1010)),"Rechts up to the stream edge");
        check("200,58,810,248".equals(MibrSafeArea.setEdge("200,58,590,248",def,2,5000)),"Rechts clamps at 1010");
        check("0,58,790,248".equals(MibrSafeArea.setEdge("200,58,590,248",def,0,-30)),"Links clamps at 0");
        check("690,58,100,248".equals(MibrSafeArea.setEdge("200,58,590,248",def,0,780)),"Links stops MIN_W before Rechts (x1<x2)");
        check("200,58,100,248".equals(MibrSafeArea.setEdge("200,58,590,248",def,2,0)),"Rechts stops MIN_W after Links");
        check("200,246,590,60".equals(MibrSafeArea.setEdge("200,58,590,248",def,1,376)),"Oben stops MIN_H before Unten (y1<y2)");
        check("200,58,590,318".equals(MibrSafeArea.setEdge("200,58,590,248",def,3,376)),"Unten up to 376");
        check("200,58,590,60".equals(MibrSafeArea.setEdge("200,58,590,248",def,3,10)),"Unten stops MIN_H after Oben");
        for(int f=0;f<4;f++)for(int px=-20;px<=1030;px+=7){
            String v=MibrSafeArea.setEdge("13,7,600,300",def,f,px);
            check(MibrSafeArea.parse(v)!=null,"every slider position gives a value the broker accepts: "+v);
        }
        check(MibrSafeArea.span(0)==1010&&MibrSafeArea.span(2)==1010&&MibrSafeArea.span(1)==376&&MibrSafeArea.span(3)==376,"slider ranges");
        check(MibrSafeArea.SLIDER_STEP==10,"slider step 10 px");
        check(MibrSafeArea.previewStep(0,1010)==0&&MibrSafeArea.previewStep(1010,1010)==8&&MibrSafeArea.previewStep(505,1010)==4&&
              MibrSafeArea.previewStep(-5,376)==0&&MibrSafeArea.previewStep(400,376)==8&&MibrSafeArea.previewStep(30,1010)==0&&
              MibrSafeArea.previewStep(920,1010)==7,"r15h: 9-step stock mini-slider preview");
        check("201,58,589,248".equals(MibrSafeArea.step("200,58,590,248",def,0,"+1"))&&
              "200,58,589,248".equals(MibrSafeArea.step("200,58,590,248",def,2,"-1")),"1 px fine steps");
        boolean one=false;
        for(int i=0;i<MibrSafeArea.OPTIONS.length;i++)if("-1".equals(MibrSafeArea.OPTIONS[i]))one=true;
        check(one,"the dropdown fallback offers 1 px");
        check(MibrSafeArea.parse("0,58,1010,248")!=null&&MibrSafeArea.parse("0,0,99,60")==null,"stored values keep the old rule");

        // live edit: newest wish shown at once; durable SET only after IDLE_MS without change, one in flight
        MibrDurableSwitch sw=MibrDurableSwitch.SAFE_WIDE;
        sw.readback("200,58,590,248","4",true);
        check("200,58,590,248".equals(MibrSafeArea.shown(sw)),"shown = readback without a wish");
        long t=1000000L;
        MibrSafeArea.wantEdge(sw,0,150,t);
        check("150,58,640,248".equals(MibrSafeArea.shown(sw)),"wish shown at once");
        check(MibrSafeArea.due(sw,t+100)==null&&MibrSafeArea.waitMs(sw,t+100)==MibrSafeArea.IDLE_MS-100,"not sent while it may still move");
        check("150,58,640,248".equals(MibrSafeArea.due(sw,t+MibrSafeArea.IDLE_MS)),"sent once idle");
        sw.setInFlight=true;
        MibrSafeArea.wantEdge(sw,0,120,t+800);
        MibrSafeArea.wantEdge(sw,2,700,t+900);
        check(MibrSafeArea.due(sw,t+5000)==null,"nothing is sent while a SET is in flight");
        check("120,58,580,248".equals(MibrSafeArea.shown(sw)),"wishes accumulate across edges");
        sw.setInFlight=false;sw.readback("150,58,640,248","5",true);
        check("120,58,580,248".equals(MibrSafeArea.due(sw,t+5000)),"after the reply the newest wish is sent");
        sw.readback("120,58,580,248","6",true);
        check(MibrSafeArea.due(sw,t+6000)==null&&"120,58,580,248".equals(MibrSafeArea.shown(sw))&&MibrSafeArea.waitMs(sw,t+6000)==-1,"confirmed wish is cleared");
        MibrSafeArea.wantOption(sw,0,"-1",t+7000);
        check("119,58,581,248".equals(MibrSafeArea.shown(sw)),"-/+ is 1 px from the shown edge");
        check(MibrSafeArea.due(sw,t+7100)==null,"-/+ uses the same debounce");
        MibrSafeArea.drop(sw);
        check("120,58,580,248".equals(MibrSafeArea.shown(sw)),"a refused SET shows the stored value again");

        // flash protection: a drag of 50 slider events within 2 s, the broker answering each SET after 150 ms
        sw.readback("200,58,590,248","10",true);
        int sets=0;String last=null;long inflightUntil=-1L;String inflightValue=null;int rev=10;
        long start=t+20000;
        for(long now=start;now<=start+6000;now+=10){
            int i=(int)((now-start)/40);
            if(i<50&&(now-start)%40==0)MibrSafeArea.wantEdge(sw,2,700+2*i,now);
            if(sw.setInFlight&&now>=inflightUntil){sw.setInFlight=false;sw.readback(inflightValue,String.valueOf(++rev),true);}
            String due=MibrSafeArea.due(sw,now);
            if(due!=null){sets++;last=due;sw.setInFlight=true;inflightValue=due;inflightUntil=now+150;}
        }
        check(sets<=2&&sets>=1,"a 50-event drag in 2 s gives at most two durable SETs, got "+sets);
        check("200,58,598,248".equals(last)&&"200,58,598,248".equals(sw.value()),"the final value is always written: "+last);
        // the -/+ buttons: 10 presses in 1 s -> one SET
        sets=0;start+=10000;
        for(long now=start;now<=start+3000;now+=10){
            if(now-start<1000&&(now-start)%100==0)MibrSafeArea.wantOption(sw,2,"+1",now);
            if(sw.setInFlight&&now>=inflightUntil){sw.setInFlight=false;sw.readback(inflightValue,String.valueOf(++rev),true);}
            String due=MibrSafeArea.due(sw,now);
            if(due!=null){sets++;sw.setInFlight=true;inflightValue=due;inflightUntil=now+150;}
        }
        check(sets==1&&"200,58,608,248".equals(sw.value()),"ten 1 px presses give one SET of the final value");

        // model rows
        MibrI18n.forced="de_DE";
        MibrSafeSliderTest view=new MibrSafeSliderTest();
        useStandardFile();
        MibrSafeArea.sliderRows=false;
        MibrCarPlayMenuModel menu=new MibrCarPlayMenuModel(view);
        menu.open();menu.select(8);menu.select(9);
        check("Safe Area Wide".equals(view.title)&&view.rows.length==6,"fallback: the pre-r15 safe page "+view.title+" "+view.rows.length+" "+(view.rows.length>0?view.rows[0]:""));
        for(int r=0;r<6;r++)check(menu.sliderKeyForRow(r)==-1,"fallback: no slider rows");
        check(menu.safeEdgePage(),"safe page detected for the lazy slider resolve");
        MibrSafeArea.sliderRows=true;menu.refresh();
        // r15g: collapsed by default (stock Item/SubItem pattern), no slider row until an edge row is tapped
        check(view.rows.length==6&&menu.builtWithSliders(),"collapsed: no slider row yet");
        int base=MibrPopupEditorModel.SAFE_FIRST+5;
        for(int e=0;e<4;e++)check(menu.safeToggleRow(e)&&menu.keyForRow(e)==base+e,"edge row "+e+" is an expand toggle");
        check(!menu.safeToggleRow(4)&&!menu.safeToggleRow(5),"reset and hint are no toggles");
        menu.toggleSafe(0);
        check(view.rows.length==7&&menu.sliderKeyForRow(1)==base&&"".equals(view.rows[1])&&menu.expandedSafe()==base,"tap Links: its slider below");
        menu.toggleSafe(3); // Rechte Kante is at row 3 (Links, slider, Oben, Rechts)
        check(view.rows.length==7&&menu.sliderKeyForRow(3)==base+2&&menu.sliderKeyForRow(1)==-1,"only one expanded at a time");
        check("Linke Kante".equals(view.rows[0])&&"Rechte Kante".equals(view.rows[2])&&"Zurücksetzen".equals(view.rows[5]),"labels stay");
        menu.select(3);
        check("Safe Area Wide".equals(view.title)&&view.rows.length==7,"a slider row opens nothing");
        menu.toggleSafe(2);
        check(view.rows.length==6&&menu.expandedSafe()==-1,"second tap collapses");
        menu.toggleSafe(1);
        menu.back();
        check(!menu.safeEdgePage()&&view.rows.length==11,"Ansichten has no slider rows");
        menu.select(9);
        check(view.rows.length==6&&menu.expandedSafe()==-1,"page change collapses");
        MibrSafeArea.sliderRows=false;menu.refresh();
        check(view.rows.length==6&&!menu.safeToggleRow(0)&&!menu.builtWithSliders(),"source lost: pre-r15 dropdown rows");
        // r15c layout plan
        MibrSafeArea.sliderRows=false;
        check(MibrSafeArea.sliderPlan(false,0,false)==MibrSafeArea.PLAN_LAYOUT,"other pages never resolve");
        check(MibrSafeArea.sliderPlan(true,-1,false)==MibrSafeArea.PLAN_LAYOUT,"no source: fallback rows");
        check(MibrSafeArea.sliderPlan(true,0,false)==MibrSafeArea.PLAN_RESOLVE,"edge page with a pending source resolves before its first layout");
        check(MibrSafeArea.sliderPlan(true,2,false)==MibrSafeArea.PLAN_LAYOUT,"failed source: fallback rows, no loop");
        MibrSafeArea.sliderRows=true;
        check(MibrSafeArea.sliderPlan(true,1,false)==MibrSafeArea.PLAN_RERENDER,"became READY after the rows were computed: render once more");
        check(MibrSafeArea.sliderPlan(true,1,true)==MibrSafeArea.PLAN_LAYOUT,"rows built with sliders shown: lay out (no loop, also when collapsed)");
        // (a) READY at entry: the first layout already has the toggle rows
        menu.back();menu.open();menu.select(8);menu.select(8);
        check("Safe Area Voll".equals(view.title)&&view.rows.length==6&&menu.builtWithSliders()&&menu.safeToggleRow(0),"READY at entry: first layout has toggles");
        // (b) READY after the first layout: one refresh re-renders
        menu.back();MibrSafeArea.sliderRows=false;menu.select(10);
        check("Safe Area Center".equals(view.title)&&!menu.builtWithSliders(),"first layout before READY");
        MibrSafeArea.sliderRows=true;
        check(MibrSafeArea.sliderPlan(menu.safeEdgePage(),1,menu.builtWithSliders())==MibrSafeArea.PLAN_RERENDER,"plan asks for the second render");
        menu.refresh();
        check(menu.builtWithSliders()&&MibrSafeArea.sliderPlan(true,1,menu.builtWithSliders())==MibrSafeArea.PLAN_LAYOUT,"re-rendered once");
        menu.toggleSafe(3);
        check(view.rows.length==7&&menu.sliderKeyForRow(4)==MibrPopupEditorModel.SAFE_FIRST+13,"Center: Unten expanded");
        MibrSafeArea.sliderRows=false;
        // r15d fallback decision: a layout failure with slider rows -> pre-r15 rows for the rest of the run, once
        MibrSafeArea.sliderDisabled=false;
        check(MibrSafeArea.onLayoutFailure(false)==MibrSafeArea.FAIL_LEAVE&&!MibrSafeArea.sliderDisabled,"failure without sliders keeps failed()/leave");
        MibrSafeArea.sliderRows=true;
        check(MibrSafeArea.onLayoutFailure(true)==MibrSafeArea.FAIL_FALLBACK&&MibrSafeArea.sliderDisabled,"first failure with sliders: fallback, sticky disable");
        check(!MibrSafeArea.slidersShown(),"disabled although the source is READY");
        check(MibrSafeArea.onLayoutFailure(true)==MibrSafeArea.FAIL_LEAVE,"fallback render failing too: failed()/leave");
        check(MibrSafeArea.sliderPlan(true,0,false)==MibrSafeArea.PLAN_LAYOUT&&MibrSafeArea.sliderPlan(true,1,false)==MibrSafeArea.PLAN_LAYOUT,"disabled: never resolve or re-render again");
        menu.refresh();
        check("Safe Area Center".equals(view.title)&&view.rows.length==6&&menu.sliderKeyForRow(4)==-1&&!menu.safeToggleRow(0),"fallback render: the pre-r15 rows");
        MibrSafeArea.sliderDisabled=false;MibrSafeArea.sliderRows=false;
        System.out.println("MIBR_SAFE_SLIDER_HOST_PASS");
    }
    private static void useStandardFile() throws Exception {
        java.io.File f=java.io.File.createTempFile("mibr-menu",".conf");
        f.deleteOnExit();
        java.io.FileOutputStream out=new java.io.FileOutputStream(f);
        java.io.FileInputStream in=new java.io.FileInputStream(System.getProperty("mibr.menu.standard"));
        byte[] b=new byte[16384];int n=in.read(b);out.write(b,0,n);in.close();out.close();
        MibrMenuLayout.storedPath=f.getPath();
    }
}
