package de.mibr.hmi;

import de.vw.mib.asl.api.carplay.ASLCarplayServicesListener;
import de.vw.mib.asl.api.navbap.ASLNavBAPAPI;
import de.vw.mib.asl.api.navbap.ASLNavBAPFactory;
import de.vw.mib.asl.api.navbap.INavLaneGuidanceDataNavBap;
import de.vw.mib.asl.framework.api.framework.ASLFrameworkFactory;
import de.vw.mib.asl.framework.api.framework.Services;
import de.vw.mib.asl.framework.internal.framework.GenericCollector;
import de.vw.mib.bap.mqbab2.common.api.APIFactory;
import de.vw.mib.bap.mqbab2.common.api.carplay.CarPlayService;
import de.vw.mib.bap.mqbab2.common.api.carplay.CarPlayServiceListener;
import de.vw.mib.bap.mqbab2.common.api.carplay.datatypes.CarPlayDeviceState;
import de.vw.mib.bap.mqbab2.common.api.carplay.datatypes.iterator.elements.CarPlayCall;
import de.vw.mib.asl.framework.api.dsiproxy.DSIProxy;
import de.vw.mib.asl.framework.api.dsiproxy.DSIProxyFactory;
import de.vw.mib.asl.internal.system.SystemAccessor;
import de.vw.mib.genericevents.Target;
import org.dsi.ifc.carplay.DSICarplay;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.util.Iterator;

/**
 * R2 "CarPlay-Navigation": the iPhone's route guidance as the stock turn arrows in the cockpit.
 *
 * One daemon thread, started from the CIO activator. Every 250 ms it
 *  - tells the native helper with WANT ("1"/"0") whether guidance is wanted: the durable switch
 *    (MibrCarPlayNav) is on and "CarPlay im Cockpit" is not paused;
 *  - reads the helper's snapshot GUIDANCE (heartbeat every second) or, for a parked test, a
 *    built-in demo route while DEMO_FILE exists;
 *  - while wanted, fresh and the phone guides, it owns the cluster: it writes the guidance into the
 *    ASL datapool exactly where the built-in navigation puts it (HsmTargetBap: property 732, lists
 *    751/838, ASLNavBAPAPI distance/turn-to/time/lanes), so the stock NavigationASLDataAdapter
 *    sends BAP NavSD and NavInfo to the cluster, and it answers false to
 *    CarPlayService.isCarPlayRouteGuidanceActive, so InfoStates does not show the
 *    "navigation on mobile device" notice instead of the arrows;
 *  - otherwise (switch off, CarPlay im Cockpit off, route ended, phone gone, helper silent) it
 *    clears its data once and hands the cluster back to the stock navigation.
 * No stock class is replaced; every ASL write runs on the ASL thread; every failure is swallowed.
 * Approach of the cockpit side after the public description of perkthefox/mst2-cluster-nav,
 * implemented against the Skoda MU1440 lsd.jar (MQB BAP NavSD), no code copied.
 */
public final class MibrRgiCockpit {
    static final String WANT = "/dev/shmem/mibr-rgi.want";
    static final String GUIDANCE = "/dev/shmem/mibr-rgi.guidance";
    static final String READY = "/dev/shmem/mibr-rgi-ready";
    static final String REJECTED = "/dev/shmem/mibr-rgi-rejected";
    static final String DEMO_FILE = "/tmp/mibr-rgi.demo";
    static final String PAUSE = "/tmp/mibr-parity-drive.pause";
    static final String LOG = "/tmp/mibr-rgi-hmi.log";
    private static final int ROUTE_GUIDANCE_STATE = 732, MANEUVER_DESCRIPTOR = 751, KOMBI_MANEUVER = 838;
    private static final int UNIT_AUTO = 255;
    private static final long STALE_MS = 5000L, LOG_MAX = 262144L;
    private static final int BARGRAPH_RANGE = 300;

    private static boolean started;
    private static volatile String status = "";
    /* thread-confined to the worker */
    private static int wantWritten = -1;
    private static String lastHeartbeat = "";
    private static long heartbeatSeenAt;
    private static boolean owning;
    private static String lastWritten = "";
    private static MibrRgiDemo demo;

    private MibrRgiCockpit(){}

    public static synchronized void start(){
        if(started)return;
        started=true;
        Thread t=new Thread(new Runnable(){public void run(){loop();}},"MibrRgiCockpit");
        t.setDaemon(true);
        t.start();
    }

    /** Read-only Diagnose line. */
    static String statusLine(){
        String s=status;
        return MibrI18n.pick("CarPlay-Navigation: ","CarPlay navigation: ")+(s.length()==0?MibrI18n.pick("startet","starting"):s);
    }

    private static void loop(){
        log("started");
        try{Thread.sleep(5000L);}catch(InterruptedException e){return;}
        while(true){
            try{tick();}catch(Throwable t){log("tick failed: "+t);}
            try{Thread.sleep(250L);}catch(InterruptedException e){return;}
        }
    }

    private static void tick(){
        boolean on=MibrDurableSwitch.CARPLAY_NAV.persistedOn();
        boolean cockpit=!new File(PAUSE).exists();
        String source=MibrDurableSwitch.NAV_SOURCE.persistedValue();
        boolean wanted=wanted(on,cockpit,source);
        writeWant(wanted);
        boolean demoOn=on&&new File(DEMO_FILE).exists();
        if(demoOn&&demo==null){demo=new MibrRgiDemo();log("demo route started");}
        if(!demoOn&&demo!=null){demo=null;log("demo route stopped");}
        MibrRgiGuidance g=demo!=null?demo.next():fresh(read());
        boolean phoneActive=demo!=null||carPlayActive();
        night(carPlayActive());
        boolean own=(wanted||demo!=null)&&phoneActive&&g!=null&&g.guiding();
        if(own){
            if(!owning){owning=true;ClusterCarPlay.setOwned(true);log("cluster: phone route guidance");}
            String key=signature(g);
            if(!key.equals(lastWritten)){lastWritten=key;publish(g);}
        }else if(owning){
            owning=false;lastWritten="";
            publish(null);
            ClusterCarPlay.setOwned(false);
            log("cluster: stock navigation");
        }
        status=describe(on,cockpit,g,own);
    }

    private static String describe(boolean on,boolean cockpit,MibrRgiGuidance g,boolean own){
        if(!on)return MibrI18n.pick("aus","off");
        if(demo!=null)return MibrI18n.pick("Demo-Route läuft","demo route running");
        if(!cockpit)return MibrI18n.pick("an · CarPlay im Cockpit ist aus","on · CarPlay in cockpit is off");
        if(new File(REJECTED).exists())return MibrI18n.pick("an · iPhone hat die Anmeldung abgelehnt","on · iPhone rejected the identification");
        if(!new File(READY).exists())return MibrI18n.pick("an · wartet auf iPhone","on · waiting for iPhone");
        if(g==null)return MibrI18n.pick("an · iPhone angemeldet, noch keine Daten","on · iPhone registered, no data yet");
        if(!own)return MibrI18n.pick("an · keine Route aktiv","on · no route active");
        return MibrI18n.pick("an · Route aktiv: ","on · route active: ")+routeLine(g);
    }

    static boolean demoRequested(){return new File(DEMO_FILE).exists();}
    /** The menu's demo row; the file lives in RAM, so a restart ends the demo. */
    static void requestDemo(boolean on){
        try{
            if(on)new FileOutputStream(DEMO_FILE).close();
            else new File(DEMO_FILE).delete();
        }catch(Throwable t){
            log("demo request failed: "+t);
        }
    }

    /** Diagnose: the next manoeuvre as the phone sends it. */
    static String routeLine(MibrRgiGuidance g){
        StringBuffer b=new StringBuffer(distanceLine(g));
        if(g.destination.length()>0)b.append(" → ").append(g.destination);
        return b.toString();
    }

    /** "stock" never takes the arrows; "phone" takes them also while the stock map is in the cockpit. */
    static boolean wanted(boolean on,boolean cockpit,String source){
        if(!on||"stock".equals(source))return false;
        return cockpit||"phone".equals(source);
    }

    /** The small symbol in the lane strip stands in for real lanes only, and never on arrival. */
    static boolean syntheticLane(String display,boolean realLanes,int main){
        return !"side".equals(display)&&!realLanes&&main!=MibrRgiManeuvers.ARRIVED&&
            main!=MibrRgiManeuvers.NO_INFO&&main!=MibrRgiManeuvers.NO_SYMBOL;
    }

    /** The line above the map, as chosen in the Pfeile im Cockpit submenu. */
    static String lineAboveMap(MibrRgiGuidance g){
        return lineAboveMap(MibrDurableSwitch.NAV_TEXT.persistedValue(),g);
    }
    static String lineAboveMap(String mode,MibrRgiGuidance g){
        if("off".equals(mode))return "";
        if("street".equals(mode))return g.street;
        return distanceLine(g);
    }

    /** "300 m · Hauptstrasse": the arrow shows the direction, so the text says how far and where to. */
    static String distanceLine(MibrRgiGuidance g){
        int[] m=g.maneuver();
        if(m[0]==MibrRgiManeuvers.ARRIVED&&g.routeState==MibrRgiGuidance.ARRIVED)return MibrI18n.pick("Ziel erreicht","Arrived");
        String target=g.street;
        if(m[0]==MibrRgiManeuvers.ARRIVED)target=MibrI18n.pick("Ziel","Destination");
        else if((m[0]==MibrRgiManeuvers.ROUNDABOUT_RIGHT||m[0]==MibrRgiManeuvers.ROUNDABOUT_LEFT)&&g.type>=28&&g.type<=46)
            target=MibrI18n.pick("Kreisel ","Roundabout exit ")+(g.type-27)+MibrI18n.pick(". Ausfahrt","");
        long d=g.distanceToManeuver;
        if(d<0)return target;
        String how=d<JETZT_M?MibrI18n.pick("Jetzt","Now"):MibrRgiManeuvers.distance(d);
        return target.length()==0?how:how+" · "+target;
    }

    /** Stock sends the car's day/night on change only: while forced, it is sent again every 10 s. */
    private static final int NIGHT_TICKS=40;
    private static final long JETZT_M=20L;
    private static DSICarplay carplayDsi;
    private static String nightSent="auto";
    private static int nightTick;
    private static void night(boolean connected){
        String mode=MibrDurableSwitch.NAV_NIGHT.persistedValue();
        boolean changed=!mode.equals(nightSent);
        if(!changed&&("auto".equals(mode)||++nightTick<NIGHT_TICKS))return;
        nightTick=0;
        nightSent=mode;
        if(!connected)return;
        try{
            if(carplayDsi==null){
                DSIProxy proxy=DSIProxyFactory.getDSIProxyAPI().getDSIProxy();
                Target owner=SystemAccessor.getVehicleStatesTarget();
                if(proxy==null||owner==null)return;
                carplayDsi=(DSICarplay)proxy.getService(owner,DSICarplay.class);
                if(carplayDsi==null)return;
            }
            boolean dark="auto".equals(mode)?MibrNativeSkinMode.isDarkMode():"dark".equals(mode);
            carplayDsi.requestNightMode(dark);
            if(changed)log("night mode "+mode+" -> "+dark);
        }catch(Throwable t){
            carplayDsi=null;
            log("night mode failed: "+t);
        }
    }

    private static String signature(MibrRgiGuidance g){
        int[] m=g.maneuver();
        StringBuffer b=new StringBuffer();
        b.append(g.routeState).append('|').append(m[0]).append('|').append(m[1]).append('|').append(g.sideStreets())
         .append('|').append(g.distanceToManeuver).append('|').append(g.distanceRemaining).append('|')
         .append(g.timeRemaining/60L).append('|').append(lineAboveMap(g)).append('|')
         .append(MibrDurableSwitch.NAV_DISPLAY.persistedValue()).append('|').append(MibrDurableSwitch.NAV_BOTTOM.persistedValue()).append('|')
         .append(MibrDurableSwitch.NAV_SIDE.persistedValue()).append('|').append(MibrDurableSwitch.NAV_LANES.persistedValue()).append('|')
         .append(g.lanePosition.length);
        for(int i=0;i<g.lanePosition.length;i++)b.append(',').append(g.laneDirection(i)).append(':').append(g.laneStatus[i]);
        return b.toString();
    }

    /** A snapshot counts while the helper's heartbeat changed within STALE_MS. */
    private static MibrRgiGuidance fresh(MibrRgiGuidance g){
        long now=System.currentTimeMillis();
        if(g==null)return null;
        if(!g.heartbeat.equals(lastHeartbeat)){lastHeartbeat=g.heartbeat;heartbeatSeenAt=now;}
        return now-heartbeatSeenAt<=STALE_MS?g:null;
    }

    private static MibrRgiGuidance read(){
        File f=new File(GUIDANCE);
        long n=f.length();
        if(n<=0L||n>8192L)return null;
        FileInputStream in=null;
        try{
            byte[] b=new byte[(int)n];
            in=new FileInputStream(f);
            int got=0,k;
            while(got<b.length&&(k=in.read(b,got,b.length-got))>0)got+=k;
            return MibrRgiGuidance.parse(new String(b,0,got,"UTF-8"));
        }catch(Throwable t){
            return null;
        }finally{
            if(in!=null)try{in.close();}catch(Throwable ignored){}
        }
    }

    private static void writeWant(boolean wanted){
        int v=wanted?1:0;
        if(v==wantWritten&&new File(WANT).exists())return;
        FileOutputStream out=null;
        try{
            out=new FileOutputStream(WANT);
            out.write(wanted?'1':'0');
            out.write('\n');
            wantWritten=v;
            log("want="+v);
        }catch(Throwable t){
            wantWritten=-1;
        }finally{
            if(out!=null)try{out.close();}catch(Throwable ignored){}
        }
    }

    private static boolean carPlayActive(){
        try{return ClusterCarPlay.stockActive();}catch(Throwable t){return false;}
    }

    private static Services services(){
        return ASLFrameworkFactory.getASLFrameworkAPI().getServices();
    }

    /** Enqueues one complete datapool write on the ASL thread; null clears our guidance. */
    private static void publish(final MibrRgiGuidance g){
        try{
            services().getASLThreadSwitch().enqueue(new Runnable(){public void run(){
                try{write(g);}catch(Throwable t){log("datapool write failed: "+t);}
            }});
        }catch(Throwable t){
            log("ASL thread not available: "+t);
        }
    }

    private static void write(MibrRgiGuidance g){
        Services services=services();
        ASLNavBAPAPI bap=ASLNavBAPFactory.getNavBAPApi();
        boolean active=g!=null;
        int[] m=active?g.maneuver():new int[]{MibrRgiManeuvers.NO_SYMBOL,0};
        String display=MibrDurableSwitch.NAV_DISPLAY.persistedValue();
        boolean sideArrow=!"top".equals(display);
        GenericCollector c=new GenericCollector();
        c.setIntItem(0,sideArrow?m[0]:MibrRgiManeuvers.NO_SYMBOL);
        c.setIntItem(1,sideArrow?m[1]:0);
        c.setIntItem(2,0);
        c.setStringItem(3,active&&sideArrow&&MibrDurableSwitch.NAV_SIDE.persistedOn()?g.sideStreets():"");
        GenericCollector[] list=new GenericCollector[]{c};
        services.getASLListManager().getGenericASLList(MANEUVER_DESCRIPTOR).updateList(list);
        services.getASLListManager().getGenericASLList(KOMBI_MANEUVER).updateList(list);
        if(active){
            long d=g.distanceToManeuver;
            boolean bar=d>=0&&d<=BARGRAPH_RANGE&&m[0]!=MibrRgiManeuvers.ARRIVED;
            bap.updateBapDistanceToNextManeuver(d<0?-1:(int)Math.min(d,Integer.MAX_VALUE),0,bar,
                bar?(int)(d*100L/BARGRAPH_RANGE):0);
            bap.updateBapTurnToInfo(lineAboveMap(g),"");
            setRemainingTimeShown(bap,"rtt".equals(MibrDurableSwitch.NAV_BOTTOM.persistedValue()),g.timeRemaining);
            bap.updateBapTimeToDestinationRTT(g.timeRemaining);
            bap.updateBapDistanceToDestination(g.distanceRemaining<0?-1:(int)Math.min(g.distanceRemaining,Integer.MAX_VALUE),UNIT_AUTO,false);
            boolean lanes=MibrDurableSwitch.NAV_LANES.persistedOn()&&g.lanesUsable();
            if(syntheticLane(display,lanes,m[0])){
                bap.updateBapLaneGuidance(new INavLaneGuidanceDataNavBap[]{new Lane(m[1],new byte[0],2)},true);
            }else{
                bap.updateBapLaneGuidance(lanes?lanes(g):new INavLaneGuidanceDataNavBap[0],lanes);
            }
        }else{
            bap.updateBapDistanceToNextManeuver(-1,0,false,0);
            bap.updateBapTurnToInfo("","");
            setRemainingTimeShown(bap,false,0L);
            bap.updateBapTimeToDestinationRTT(-1L);
            bap.updateBapDistanceToDestination(-1,UNIT_AUTO,false);
            bap.updateBapLaneGuidance(new INavLaneGuidanceDataNavBap[0],false);
        }
        /* last, so every consumer sees complete data when guidance turns active */
        services.getASLPropertyManager().valueChangedInteger(ROUTE_GUIDANCE_STATE,active?1:0);
    }

    private static boolean remainingShown;
    /** Sets the time info flag of the stock collector; the RTT call right after brings the real values. */
    private static void setRemainingTimeShown(ASLNavBAPAPI bap,boolean remaining,long seconds){
        if(remaining==remainingShown)return;
        remainingShown=remaining;
        bap.updateBapTimeToDestination(remaining?1:0,0,seconds);
    }

    private static INavLaneGuidanceDataNavBap[] lanes(MibrRgiGuidance g){
        INavLaneGuidanceDataNavBap[] out=new INavLaneGuidanceDataNavBap[g.lanePosition.length];
        for(int i=0;i<out.length;i++)out[i]=new Lane(g.laneDirection(i),g.laneSideDirections(i),g.laneRecommendation(i));
        return out;
    }

    private static final class Lane implements INavLaneGuidanceDataNavBap {
        private final short direction;private final byte[] sides;private final byte guidance;
        Lane(int direction,byte[] sides,int guidance){
            this.direction=(short)direction;this.sides=sides;this.guidance=(byte)guidance;
        }
        public short getLaneDirection(){return direction;}
        public byte getGuidanceInfo(){return guidance;}
        public byte getLaneDescription(){return 15;} // NOT_SUPPORTED_NO_DESCRIPTION_AVAILABLE
        public byte getLaneMarkingLeft(){return 0;}
        public byte getLaneMarkingRight(){return 0;}
        public short getLaneType(){return 0;} // UNSPECIFIC
        public byte[] getLaneSideStreets(){return sides;}
    }

    /**
     * The cluster's view of CarPlay while the phone's guidance feeds the arrows. When CarPlay
     * guides, BAP NavSD InfoStates sends 6 "navigation in mobile device" and the cluster shows that
     * notice instead of arrows. InfoStates asks APIFactory for the CarPlay service on every update,
     * so while we own the cluster this delegate sits in the factory's slot and answers false
     * there; everything else goes to the stock service. Nothing is replaced when CarPlay is not
     * coded (the factory then holds its dummy service).
     */
    static final class ClusterCarPlay implements CarPlayService {
        private static Field slot;
        private static CarPlayService stock;
        private static volatile boolean owned;
        private static boolean tried;
        private ClusterCarPlay(){}

        static boolean stockActive(){
            CarPlayService s=stock;
            if(s==null)s=APIFactory.getAPIFactory().getCarPlayService();
            return s!=null&&s.isCarPlayActive();
        }

        static void setOwned(final boolean own){
            owned=own;
            try{
                services().getASLThreadSwitch().enqueue(new Runnable(){public void run(){
                    try{
                        if(own)install();
                        /* the stock notification InfoStates listens to (CarPlayASLDataAdapter) */
                        if(stock!=null)((ASLCarplayServicesListener)stock).updateCarPlayRouteGuidanceActive(false);
                    }catch(Throwable t){log("CarPlay service hand-over failed: "+t);}
                }});
            }catch(Throwable t){log("ASL thread not available: "+t);}
        }

        /** Once, on the ASL thread: the delegate takes the factory slot and stays (it forwards). */
        private static void install() throws Exception {
            if(tried)return;
            tried=true;
            Field[] fields=APIFactory.class.getDeclaredFields();
            for(int i=0;i<fields.length;i++)
                if(fields[i].getType()==CarPlayService.class&&java.lang.reflect.Modifier.isStatic(fields[i].getModifiers()))
                    slot=fields[i];
            if(slot==null){log("CarPlay service slot not found: notice stays");return;}
            slot.setAccessible(true);
            CarPlayService current=APIFactory.getAPIFactory().getCarPlayService();
            if(!(current instanceof ASLCarplayServicesListener)){log("CarPlay not coded: notice left alone");return;}
            stock=current;
            slot.set(null,new ClusterCarPlay());
            log("CarPlay route guidance hidden from the cluster while the phone feeds the arrows");
        }

        public boolean isCarPlayRouteGuidanceActive(){return !owned&&stock.isCarPlayRouteGuidanceActive();}
        public void addCarPlayServiceListener(CarPlayServiceListener l,int[] ids){stock.addCarPlayServiceListener(l,ids);}
        public void removeCarPlayServiceListener(CarPlayServiceListener l,int[] ids){stock.removeCarPlayServiceListener(l,ids);}
        public boolean isCarPlayActive(){return stock.isCarPlayActive();}
        public CarPlayDeviceState getCarPlayDeviceState(){return stock.getCarPlayDeviceState();}
        public Iterator getCarPlayCalls(){return stock.getCarPlayCalls();}
        public void hangUpCall(CarPlayCall call){stock.hangUpCall(call);}
        public void acceptCall(int i){stock.acceptCall(i);}
    }

    static void log(String msg){
        FileOutputStream out=null;
        try{
            File f=new File(LOG);
            if(f.length()>LOG_MAX)return;
            out=new FileOutputStream(LOG,true);
            out.write((System.currentTimeMillis()+" "+msg+"\n").getBytes("UTF-8"));
        }catch(Throwable ignored){
        }finally{
            if(out!=null)try{out.close();}catch(Throwable ignored){}
        }
    }
}
