package de.mibr.hmi;

/** R2 CarPlay-Navigation: snapshot parsing, maneuver/lane mapping, switch file and menu toggle. */
public final class MibrRgiTest {
    private static void check(boolean c,String name){if(!c)throw new AssertionError(name);}
    private static boolean pair(int[] p,int main,int dir){return p[0]==main&&p[1]==dir;}

    public static void main(String[] args){
        MibrI18n.forced="de_DE";
        // Snapshot exactly as mibr_rgi_guidance_text writes it (see carplay-rgi tests/rgi_guidance_test.c).
        String text="MIBR_RGI/1\nseq=7\nhb=123\nreceiving=1\nroute_state=1\nmaneuver_state=0\n"+
            "dist_man=250\ndist_rem=12000\ntime_rem=900\nroad=Ringstraße\ndest=Ziel\n"+
            "man_index=3\ntype=2\nangle=90\nside=0\njunction=0\nafter=Hauptstraße\nangles=-90,0,90\n"+
            "lanes=2\nlane1=1,2,90,90,0\nlane0=0,0,0,0\nend=1\n";
        MibrRgiGuidance g=MibrRgiGuidance.parse(text);
        check(g!=null&&g.guiding()&&g.receiving&&"123".equals(g.heartbeat),"parse");
        check(pair(g.maneuver(),MibrRgiManeuvers.TURN,MibrRgiManeuvers.RIGHT),"right turn");
        check(g.distanceToManeuver==250&&g.distanceRemaining==12000&&g.timeRemaining==900,"numbers");
        check("Hauptstraße".equals(g.street),"street after the maneuver");
        // side streets: left (64) and ahead (0), the exit (192) left out
        String sides=g.sideStreets();
        check(sides.length()==2&&sides.charAt(0)==(char)64&&sides.charAt(1)==(char)0,"side streets");
        check(g.lanePosition.length==2&&g.lanePosition[0]==0&&g.lanePosition[1]==1,"lanes sorted left to right");
        check(g.laneDirection(0)==0&&g.laneRecommendation(0)==0,"lane 0 ahead, not recommended");
        check(g.laneDirection(1)==192&&g.laneRecommendation(1)==2&&g.laneSideDirections(1).length==1&&
              g.laneSideDirections(1)[0]==0,"lane 1 right preferred, ahead as side direction");
        check(g.lanesUsable(),"lanes usable");
        // incomplete or foreign snapshots are refused
        check(MibrRgiGuidance.parse(text.substring(0,text.length()-6))==null,"missing end");
        check(MibrRgiGuidance.parse("X"+text)==null,"magic");
        check(MibrRgiGuidance.parse(text.replace("lanes=2","lanes=3"))==null,"lane count mismatch");
        check(MibrRgiGuidance.parse(text.replace("dist_man=250","dist_man=x"))==null,"bad number");
        // no route / no maneuver
        MibrRgiGuidance none=MibrRgiGuidance.parse("MIBR_RGI/1\nseq=1\nhb=1\nreceiving=0\nroute_state=-1\nman_index=-1\nlanes=0\nend=1\n");
        check(none!=null&&!none.guiding()&&pair(none.maneuver(),MibrRgiManeuvers.NO_INFO,0)&&!none.lanesUsable(),"empty");
        MibrRgiGuidance arrived=MibrRgiGuidance.parse(text.replace("route_state=1","route_state=2"));
        check(arrived.guiding()&&pair(arrived.maneuver(),MibrRgiManeuvers.ARRIVED,0),"arrived");
        check(!MibrRgiGuidance.parse(text.replace("route_state=1","route_state=0")).guiding(),"no route set");

        // maneuver table (right-hand traffic unless noted)
        check(pair(MibrRgiManeuvers.map(1,1000,false),13,64),"left");
        check(pair(MibrRgiManeuvers.map(3,1000,false),13,0),"straight");
        check(pair(MibrRgiManeuvers.map(5,1000,false),11,0),"follow road");
        check(pair(MibrRgiManeuvers.map(4,1000,false),25,64)&&pair(MibrRgiManeuvers.map(4,1000,true),25,192)&&
              pair(MibrRgiManeuvers.map(4,170,false),25,192),"u-turn");
        check(pair(MibrRgiManeuvers.map(7,1000,false),26,192)&&pair(MibrRgiManeuvers.map(7,1000,true),27,64),"exit roundabout");
        check(pair(MibrRgiManeuvers.map(8,1000,false),13,224)&&pair(MibrRgiManeuvers.map(8,-40,false),13,32),"ramps");
        check(pair(MibrRgiManeuvers.map(12,1000,false),3,0)&&pair(MibrRgiManeuvers.map(24,1000,false),3,64),"arrive");
        check(pair(MibrRgiManeuvers.map(11,50,false),13,224)&&pair(MibrRgiManeuvers.map(11,-100,false),13,64)&&
              pair(MibrRgiManeuvers.map(11,-150,false),13,96)&&pair(MibrRgiManeuvers.map(11,10,false),13,0),"start route angles");
        check(pair(MibrRgiManeuvers.map(13,1000,false),13,32)&&pair(MibrRgiManeuvers.map(14,1000,false),13,224),"keep");
        check(pair(MibrRgiManeuvers.map(19,1000,false),21,128)&&pair(MibrRgiManeuvers.map(19,1000,true),22,128),"u-turn roundabout");
        check(pair(MibrRgiManeuvers.map(29,0,false),21,0)&&pair(MibrRgiManeuvers.map(28,1000,false),21,192)&&
              pair(MibrRgiManeuvers.map(30,1000,false),21,64)&&pair(MibrRgiManeuvers.map(31,1000,false),21,128)&&
              pair(MibrRgiManeuvers.map(28,1000,true),22,64),"roundabout exits without angle");
        check(pair(MibrRgiManeuvers.map(29,-90,false),21,64)&&pair(MibrRgiManeuvers.map(30,135,false),21,160),"roundabout exit angle");
        check(pair(MibrRgiManeuvers.map(47,1000,false),13,96)&&pair(MibrRgiManeuvers.map(48,1000,false),13,160),"sharp");
        check(pair(MibrRgiManeuvers.map(52,1000,false),12,64)&&pair(MibrRgiManeuvers.map(53,1000,false),12,192),"change highway");
        check(pair(MibrRgiManeuvers.map(99,1000,false),1,0),"unknown type");
        check(MibrRgiManeuvers.sixteenths(-90)==64&&MibrRgiManeuvers.sixteenths(90)==192&&MibrRgiManeuvers.sixteenths(180)==128&&
              MibrRgiManeuvers.sixteenths(-180)==128&&MibrRgiManeuvers.sixteenths(0)==0&&MibrRgiManeuvers.sixteenths(-22)==16,"sixteenths");

        // demo route: one full loop produces a route, lanes, an arrival and a pause
        MibrRgiDemo demo=new MibrRgiDemo();
        boolean sawLanes=false,sawArrived=false,sawPause=false,sawRoundabout=false;
        for(int i=0;i<2000;i++){
            MibrRgiGuidance d=demo.next();
            if(d.lanesUsable())sawLanes=true;
            if(d.routeState==MibrRgiGuidance.ARRIVED)sawArrived=true;
            if(d.routeState==MibrRgiGuidance.NO_ROUTE)sawPause=true;
            if(d.maneuver()[0]==MibrRgiManeuvers.ROUNDABOUT_RIGHT)sawRoundabout=true;
        }
        check(sawLanes&&sawArrived&&sawPause&&sawRoundabout,"demo route covers lanes, roundabout, arrival, pause");

        // durable switch file: exact canonical content only
        check(MibrDurableSwitch.CARPLAY_NAV.parseOn("MIBR_CARPLAY_NAV/1\nrevision=3\nvalue=on\n"),"file on");
        check(!MibrDurableSwitch.SD_LOG.parseOn("MIBR_CARPLAY_NAV/1\nrevision=3\nvalue=on\n"),"each switch has its own magic");
        check(MibrDurableSwitch.SD_LOG.parseOn("MIBR_SD_LOG/1\nrevision=3\nvalue=on\n"),"sd log on");
        check("street".equals(MibrDurableSwitch.NAV_TEXT.parseValue("MIBR_NAV_LINE/1\nrevision=3\nvalue=street\n")),"nav text value");
        check("dist".equals(MibrDurableSwitch.NAV_TEXT.parseValue(null)),"nav text default");
        check("dist".equals(MibrDurableSwitch.NAV_TEXT.parseValue("MIBR_NAV_LINE/1\nrevision=3\nvalue=on\n")),"nav text foreign value");
        check(MibrRgiCockpit.wanted(true,true,"auto")&&!MibrRgiCockpit.wanted(true,false,"auto"),"auto follows the cockpit");
        check(MibrRgiCockpit.wanted(true,false,"phone")&&!MibrRgiCockpit.wanted(true,true,"stock")&&!MibrRgiCockpit.wanted(false,true,"phone"),"source");
        check(MibrRgiCockpit.syntheticLane("top",false,MibrRgiManeuvers.TURN)&&MibrRgiCockpit.syntheticLane("both",false,MibrRgiManeuvers.TURN),"synthetic lane");
        check(!MibrRgiCockpit.syntheticLane("side",false,MibrRgiManeuvers.TURN)&&!MibrRgiCockpit.syntheticLane("top",true,MibrRgiManeuvers.TURN)&&
              !MibrRgiCockpit.syntheticLane("top",false,MibrRgiManeuvers.ARRIVED),"real lanes win, none on arrival");
        check(MibrSafeArea.parse("0,58,1010,248")!=null&&MibrSafeArea.parse("0,58,1011,248")==null&&MibrSafeArea.parse("0,58,1010")==null&&
              MibrSafeArea.parse("00,58,100,60")==null&&MibrSafeArea.parse("0,0,99,60")==null&&MibrSafeArea.parse(null)==null,"safe area parse");
        check("10,58,580,248".equals(MibrSafeArea.step("0,58,590,248","200,58,590,248",0,"+10")),"left edge moves alone");
        check("0,58,592,248".equals(MibrSafeArea.step("2,58,590,248","200,58,590,248",0,"-10")),"left edge stops at 0");
        check("420,58,590,248".equals(MibrSafeArea.step("420,58,590,248","200,58,590,248",2,"+50")),"right edge stops at the stream");
        check("0,58,100,248".equals(MibrSafeArea.step("0,58,102,248","0,58,1010,248",2,"-10")),"minimum width from the right");
        check("902,58,108,248".equals(MibrSafeArea.step("900,58,110,248","0,58,1010,248",0,"+2")),"left edge up to the minimum");
        check("910,58,100,248".equals(MibrSafeArea.step("900,58,110,248","0,58,1010,248",0,"+50")),"minimum width from the left");
        check("0,58,1010,60".equals(MibrSafeArea.step("0,58,1010,62","0,58,1010,248",3,"-10")),"minimum height");
        check("0,48,1010,258".equals(MibrSafeArea.step("0,58,1010,248","0,58,1010,248",1,"-10")),"top edge moves alone");
        check("0,58,1010,248".equals(MibrSafeArea.step("0,58,1010,100","0,58,1010,248",3,MibrSafeArea.STANDARD)),"standard of one edge");
        check("590".equals(MibrSafeArea.field("200,58,390,248","0,58,1010,248",2))&&"306".equals(MibrSafeArea.field("200,58,390,248","0,58,1010,248",3)),"edges shown");
        check("200,58,590,248".equals(MibrSafeArea.step("10,20,300,100","200,58,590,248",MibrSafeArea.RESET_FIELD,MibrSafeArea.STANDARD)),"safe reset");
        check("1,2,300,400".equals(MibrPlatformDefaults.lookup("x=1\nsafe_voll=1,2,300,400\nsafe_wide=9\n","safe_voll")),"platform lookup");
        check(MibrPlatformDefaults.lookup("safe_voll_x=1\n","safe_voll")==null,"platform key is exact");
        check(MibrDurableSwitch.SAFE_VOLL.valid("0,58,1010,248")&&!MibrDurableSwitch.SAFE_VOLL.valid("on"),"safe switch valid");
        MibrRgiGuidance navText=new MibrRgiGuidance();
        navText.routeState=MibrRgiGuidance.ROUTE_SET;navText.maneuverIndex=0;navText.street="Ringstrasse";navText.type=2;navText.angle=90;
        check("Ringstrasse".equals(MibrRgiCockpit.lineAboveMap("street",navText)),"text street");
        check("".equals(MibrRgiCockpit.lineAboveMap("off",navText)),"text off");
        navText.distanceToManeuver=299;
        check("300 m · Ringstrasse".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text dist "+MibrRgiCockpit.lineAboveMap("dist",navText));
        navText.distanceToManeuver=2449;
        check("2,4 km · Ringstrasse".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text km");
        navText.distanceToManeuver=84;
        check("80 m · Ringstrasse".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text 10 m steps");
        navText.distanceToManeuver=12;
        check("Jetzt · Ringstrasse".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text now");
        navText.distanceToManeuver=-1;
        check("Ringstrasse".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text without distance");
        navText.street="";navText.distanceToManeuver=500;
        check("500 m".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text without street");
        navText.type=29;navText.angle=0;
        check("500 m · Kreisel 2. Ausfahrt".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text roundabout "+MibrRgiCockpit.lineAboveMap("dist",navText));
        navText.type=12;
        check("500 m · Ziel".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text destination");
        navText.routeState=MibrRgiGuidance.ARRIVED;
        check("Ziel erreicht".equals(MibrRgiCockpit.lineAboveMap("dist",navText)),"text arrived");
        check("12 km".equals(MibrRgiManeuvers.distance(12400))&&"1,0 km".equals(MibrRgiManeuvers.distance(1000))&&"900 m".equals(MibrRgiManeuvers.distance(949)),"distance steps");
        check("OK".equals(MibrServiceHealth.summary("broker=ok\nkey40d=ok\n")),"health ok");
        check("key40d restarted:1".equals(MibrServiceHealth.summary("broker=ok\nkey40d=restarted:1\n")),"health lists problems");
        check(!MibrDurableSwitch.CARPLAY_NAV.parseOn("MIBR_CARPLAY_NAV/1\nrevision=3\nvalue=off\n"),"file off");
        check(!MibrDurableSwitch.CARPLAY_NAV.parseOn("MIBR_CARPLAY_NAV/1\nrevision=x\nvalue=on\n")&&
              !MibrDurableSwitch.CARPLAY_NAV.parseOn("MIBR_CARPLAY_NAV/1\nrevision=3\nvalue=on\nextra\n")&&
              !MibrDurableSwitch.CARPLAY_NAV.parseOn(null),"damaged file is off");

        // menu checkbox: toggles on/off drafts only while the broker granted a writer
        MibrPopupEditorModel editor=new MibrPopupEditorModel();
        int k=MibrPopupEditorModel.CARPLAY_NAV;
        check(editor.directToggle(k)&&MibrPopupEditorModel.isVirtual(k),"checkbox row");
        check(editor.liveViewGated(k),"no writer before readback");
        MibrDurableSwitch.CARPLAY_NAV.readback("off","0",true);
        check(!editor.liveViewGated(k),"writer after readback");
        editor.setAvailable(true);
        editor.readback(k,"off");
        check(!editor.checked(k,"off")&&editor.checked(k,"on"),"checked state");
        check(editor.toggle(k)&&"on".equals(editor.draft(k)),"tap turns on");
        editor.discardDraft(k);editor.readback(k,"on");
        check(editor.toggle(k)&&"off".equals(editor.draft(k)),"tap turns off");
        check("Ein".equals(editor.label(k,"on"))&&"Aus".equals(editor.label(k,"off")),"labels");
        System.out.println("MIBR_RGI_TEST_PASS");
    }
}
