package de.mibr.hmi;

/**
 * r15i: cockpit zoom as a stock-like slider row (6 discrete positions). Host part only: position/value/preview
 * mapping, the model rows (expandable on the Skalierung page only while owned slider rows are shown, dropdown fallback
 * otherwise), the reveal rule after a toggle, and the debounced CAS save through a fake MIBR/3 broker (700 ms idle,
 * one SET in flight, final value always written, STALE_REVISION retried once). The OEM row itself needs the unit.
 */
public final class MibrZoomSliderTest implements MibrCarPlayMenuModel.View {
    private String title;
    private String[] rows;
    public void show(int screen,String title,String[] rows,String detail){this.title=title;this.rows=rows;}
    private static void check(boolean c,String name){if(!c)throw new AssertionError(name);}

    /** Scaling fake: counts SETs per value, can answer STALE_REVISION n times. */
    static final class Broker extends MibrScalingBindingTest.Fake {
        int staleSets;final java.util.Vector setValues=new java.util.Vector();
        public synchronized boolean send(String rid,String verb,String[] names,String[] values,Listener cb){
            if("SCALE_SET".equals(verb)){
                setValues.addElement(values[1]);
                if(staleSets>0){
                    staleSets--;sets++;revision=next(revision);
                    cb.onReply(MibrV3Protocol.parse("MIBR/3 "+rid+" ERR STALE_REVISION\n",rid),null);return true;
                }
            }
            return super.send(rid,verb,names,values,cb);
        }
    }
    /** The HMI runs every session callback on its one event dispatcher; the test serializes them the same way. */
    static final Object LOCK=new Object();
    static MibrV3Session session(MibrScalingBindingTest.Fake f,MibrPopupEditorModel d){
        return new MibrV3Session(f,d,new MibrV3Session.Dispatcher(){public void post(Runnable r){synchronized(LOCK){r.run();}}},
            new Runnable(){public void run(){}});
    }
    /** Called with LOCK held: releases it so the idle timers can run, like the HMI dispatcher between events. */
    private static void waitIdle() throws Exception {
        long end=System.currentTimeMillis()+MibrSafeArea.IDLE_MS+300L,left;
        while((left=end-System.currentTimeMillis())>0L)LOCK.wait(left);
    }

    public static void main(String[] args) throws Exception {synchronized(LOCK){run();}}
    private static void run() throws Exception {
        int c=MibrPopupEditorModel.SCALE_CLUSTER,m=MibrPopupEditorModel.SCALE_MAIN;
        // mapping
        check(MibrScalingState.ZOOM.length==6&&"AUTO".equals(MibrScalingState.zoomValue(0))&&"150".equals(MibrScalingState.zoomValue(5))&&
              MibrScalingState.zoomValue(6)==null&&MibrScalingState.zoomValue(-1)==null,"six positions, AUTO first");
        for(int p=0;p<6;p++)check(MibrScalingState.zoomPosition(MibrScalingState.zoomValue(p))==p&&MibrScalingState.valid(MibrScalingState.zoomValue(p)),"position round trip "+p);
        int[] preview={0,2,3,5,6,8};
        for(int p=0;p<6;p++)check(MibrScalingState.zoomPreviewStep(p)==preview[p],"preview mapping "+p+" -> "+MibrScalingState.zoomPreviewStep(p));
        check("Auto".equals(MibrScalingState.zoomLabel("AUTO"))&&"85".equals(MibrScalingState.zoomLabel("85")),"value text: Auto or the number");
        check(MibrScalingState.zoomSlider(c)&&!MibrScalingState.zoomSlider(m)&&!MibrScalingState.zoomSlider(MibrPopupEditorModel.SCALE_PHYSICAL),"only the cockpit zoom is a slider");

        // reveal rule (r15h polish 4): keep the scroll position, move only to show header + slider
        check(MibrSafeArea.revealFirst(0,6,0,7)==0,"top row expanded: nothing scrolls");
        check(MibrSafeArea.revealFirst(0,6,4,7)==0,"slider row (5) still on screen");
        check(MibrSafeArea.revealFirst(0,6,5,7)==1,"slider row would be cut: move by one");
        check(MibrSafeArea.revealFirst(3,6,1,8)==1,"header above the viewport: header becomes the first row");
        check(MibrSafeArea.revealFirst(2,6,-1,6)==0,"collapse: clamped, no gap at the end");
        check(MibrSafeArea.revealFirst(0,0,5,7)==2&&MibrSafeArea.revealFirst(0,6,0,0)==0,"unknown viewport / empty list");

        // model rows on the Skalierung page
        MibrI18n.forced="de_DE";
        MibrZoomSliderTest view=new MibrZoomSliderTest();
        java.io.File f=java.io.File.createTempFile("mibr-menu",".conf");f.deleteOnExit();
        java.io.FileOutputStream out=new java.io.FileOutputStream(f);java.io.FileInputStream in=new java.io.FileInputStream(System.getProperty("mibr.menu.standard"));
        byte[] b=new byte[16384];int n=in.read(b);out.write(b,0,n);in.close();out.close();
        MibrMenuLayout.storedPath=f.getPath();
        MibrSafeArea.sliderRows=false;MibrSafeArea.sliderDisabled=false;
        MibrCarPlayMenuModel menu=new MibrCarPlayMenuModel(view);
        menu.open();
        int adv=-1;for(int r=0;r<view.rows.length;r++)if("Erweitert".equals(view.rows[r]))adv=r;
        menu.select(adv);
        int sc=-1;for(int r=0;r<view.rows.length;r++)if("Skalierung".equals(view.rows[r]))sc=r;
        menu.select(sc);
        check("Skalierung".equals(view.title)&&view.rows.length==5,"Skalierung page "+view.title+" "+view.rows.length);
        check(menu.sliderPage()&&!menu.safeEdgePage(),"zoom page resolves the slider source (no safe-area refresh)");
        check(!menu.safeToggleRow(1)&&menu.keyForRow(1)==c,"fallback (no owned rows, e.g. SEAT): the dropdown row stays");
        MibrSafeArea.sliderRows=true;menu.refresh();
        check(menu.safeToggleRow(1)&&!menu.safeToggleRow(0)&&!menu.safeToggleRow(2)&&!menu.safeToggleRow(3)&&!menu.safeToggleRow(4),"only the cockpit zoom row toggles");
        check(!menu.consumeToggle(),"no toggle yet");
        menu.toggleSafe(1);
        check(menu.consumeToggle()&&!menu.consumeToggle(),"toggle flag is one-shot");
        check(view.rows.length==6&&menu.sliderKeyForRow(2)==c&&menu.expandedRow()==1&&"Zoomfaktor Virtual Cockpit".equals(view.rows[1]),"expanded: slider row below the header");
        check("Wirkt nach Neuverbinden".equals(view.rows[5])&&menu.noteRow(5),"short reconnect hint (single row)");
        menu.toggleSafe(1);
        check(view.rows.length==5&&menu.expandedRow()==-1,"second tap collapses");
        menu.toggleSafe(1);menu.back();
        check(menu.expandedSafe()==-1,"page change collapses");
        MibrSafeArea.sliderRows=false;

        // debounced CAS save through the fake broker
        MibrI18n.forced="en_US";
        Broker fake=new Broker();MibrPopupEditorModel model=new MibrPopupEditorModel();model.setAvailable(true);
        MibrV3Session s=session(fake,model);s.open();s.scaleRefresh();
        check("AUTO".equals(MibrScalingState.shown(c))&&MibrScalingState.writable(c),"readback AUTO, writable");
        int sets=fake.sets;
        for(int p=1;p<=4;p++)s.zoomSlide(c,p); // a quick drag over four positions
        check("125".equals(MibrScalingState.shown(c))&&fake.sets==sets,"wish shown at once, nothing written while moving");
        waitIdle();
        check(fake.sets==sets+1&&"125".equals(fake.setValues.lastElement())&&"125".equals(MibrScalingState.desired(c))&&MibrScalingState.wanted(c)==null,
              "one SET of the final position after 700 ms idle: "+fake.setValues);
        sets=fake.sets;
        s.zoomNudge(c,1);s.zoomNudge(c,1);
        check("150".equals(MibrScalingState.shown(c)),"+ clamps at 150");
        s.zoomNudge(c,-1);s.zoomNudge(c,-1);
        check("100".equals(MibrScalingState.shown(c)),"- one position per press");
        waitIdle();
        check(fake.sets==sets+1&&"100".equals(fake.setValues.lastElement()),"four presses, one SET");
        sets=fake.sets;
        s.zoomSlide(c,2);s.zoomSlide(c,3);waitIdle();
        check(fake.sets==sets&&MibrScalingState.wanted(c)==null,"back to the stored value: no SET");
        // STALE_REVISION once: re-read, then the newest wish again with the fresh revision
        sets=fake.sets;fake.staleSets=1;
        s.zoomSlide(c,0);waitIdle();
        check(fake.sets==sets+2&&"AUTO".equals(MibrScalingState.desired(c))&&MibrScalingState.wanted(c)==null,"stale once: re-read and resend "+fake.setValues);
        // STALE twice: give up, the stored value is shown
        sets=fake.sets;fake.staleSets=2;
        s.zoomSlide(c,5);waitIdle();
        check(fake.sets==sets+2&&"AUTO".equals(MibrScalingState.shown(c))&&MibrScalingState.wanted(c)==null,"stale twice: dropped, no loop");
        // leaving the page writes an unsent wish
        sets=fake.sets;
        s.zoomSlide(c,1);s.detach();
        check(fake.sets==sets+1&&"70".equals(fake.setValues.lastElement()),"page leave sends the final wish");
        // main display zoom is not a slider
        Broker other=new Broker();MibrPopupEditorModel m2=new MibrPopupEditorModel();m2.setAvailable(true);
        MibrV3Session s2=session(other,m2);s2.open();s2.scaleRefresh();
        s2.zoomSlide(m,3);waitIdle();
        check(other.setValues.size()==0,"main zoom never takes slider wishes");
        s2.detach();
        System.out.println("MIBR_ZOOM_SLIDER_HOST_PASS");
    }
}
