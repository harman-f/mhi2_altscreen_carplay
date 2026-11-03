package de.mibr.hmi;

/**
 * One route guidance snapshot as the mibr-rgi helper writes it (/dev/shmem/mibr-rgi.guidance,
 * "MIBR_RGI/1" then key=value lines, "end=1" last), already mapped to the BAP values the stock
 * navigation-to-cluster path expects. Pure data and parsing, no HMI access (host-testable).
 */
final class MibrRgiGuidance {
    /* iAP2 RouteGuidanceState */
    static final int NO_ROUTE = 0, ROUTE_SET = 1, ARRIVED = 2, LOADING = 3, LOCATING = 4, REROUTING = 5, PROCEED = 6;

    String heartbeat = "";
    int seq = -1;
    boolean receiving;
    int routeState = -1;
    int maneuverIndex = -1;
    int type = -1, angle = MibrRgiManeuvers.UNKNOWN_ANGLE;
    boolean leftHandTraffic;
    int[] junction = new int[0];
    long distanceToManeuver = -1, distanceRemaining = -1, timeRemaining = -1;
    String street = "", road = "", destination = "";
    /* lanes: per lane position, status (0 not good, 1 good, 2 preferred), highlighted angle, angles */
    int[] lanePosition = new int[0], laneStatus = new int[0], laneHighlight = new int[0];
    int[][] laneAngles = new int[0][];

    /** The phone guides: a route is set (also while rerouting or on the way to the route). */
    boolean guiding(){
        return routeState==ROUTE_SET||routeState==REROUTING||routeState==PROCEED||routeState==ARRIVED;
    }

    /** @return {main element, direction} for the cluster, NO_INFO while no maneuver is known */
    int[] maneuver(){
        if(routeState==ARRIVED)return new int[]{MibrRgiManeuvers.ARRIVED,MibrRgiManeuvers.AHEAD};
        if(maneuverIndex<0||type<0)return new int[]{MibrRgiManeuvers.NO_INFO,MibrRgiManeuvers.AHEAD};
        return MibrRgiManeuvers.map(type,angle,leftHandTraffic);
    }

    String sideStreets(){
        int[] m=maneuver();
        // the stock ManeuverDescriptor drops side streets of these elements anyway
        if(m[0]!=MibrRgiManeuvers.TURN&&m[0]!=MibrRgiManeuvers.FOLLOW_STREET&&m[0]!=MibrRgiManeuvers.CHANGE_LANE)return "";
        return MibrRgiManeuvers.sideStreets(junction,angle);
    }

    /** Parses a complete snapshot; null if it is not one (wrong magic, missing end, bad numbers). */
    static MibrRgiGuidance parse(String text){
        if(text==null||!text.startsWith("MIBR_RGI/1\n")||!text.endsWith("end=1\n"))return null;
        MibrRgiGuidance g=new MibrRgiGuidance();
        int lanes=0;
        int[] pos=new int[8],status=new int[8],high=new int[8];
        int[][] ang=new int[8][];
        try{
            int at=11;
            while(at<text.length()){
                int nl=text.indexOf('\n',at);
                if(nl<0)return null;
                String line=text.substring(at,nl);
                at=nl+1;
                int eq=line.indexOf('=');
                if(eq<=0)return null;
                String k=line.substring(0,eq),v=line.substring(eq+1);
                if(k.equals("seq"))g.seq=Integer.parseInt(v);
                else if(k.equals("hb"))g.heartbeat=v;
                else if(k.equals("receiving"))g.receiving="1".equals(v);
                else if(k.equals("route_state"))g.routeState=Integer.parseInt(v);
                else if(k.equals("dist_man"))g.distanceToManeuver=Long.parseLong(v);
                else if(k.equals("dist_rem"))g.distanceRemaining=Long.parseLong(v);
                else if(k.equals("time_rem"))g.timeRemaining=Long.parseLong(v);
                else if(k.equals("road"))g.road=v;
                else if(k.equals("dest"))g.destination=v;
                else if(k.equals("man_index"))g.maneuverIndex=Integer.parseInt(v);
                else if(k.equals("type"))g.type=Integer.parseInt(v);
                else if(k.equals("angle"))g.angle=Integer.parseInt(v);
                else if(k.equals("side"))g.leftHandTraffic="1".equals(v);
                else if(k.equals("after"))g.street=v;
                else if(k.equals("angles"))g.junction=ints(v);
                else if(k.equals("lanes")){
                    lanes=Integer.parseInt(v);
                    if(lanes<0||lanes>8)return null;
                }else if(k.startsWith("lane")){
                    int i=Integer.parseInt(k.substring(4));
                    int[] f=ints(v);
                    if(i<0||i>=lanes||f.length<3||ang[i]!=null)return null;
                    pos[i]=f[0];status[i]=f[1];high[i]=f[2];
                    ang[i]=new int[f.length-3];
                    for(int j=3;j<f.length;j++)ang[i][j-3]=f[j];
                }
            }
        }catch(NumberFormatException e){
            return null;
        }
        for(int i=0;i<lanes;i++)if(ang[i]==null)return null;
        g.lanePosition=new int[lanes];g.laneStatus=new int[lanes];g.laneHighlight=new int[lanes];g.laneAngles=new int[lanes][];
        for(int i=0;i<lanes;i++){
            g.lanePosition[i]=pos[i];g.laneStatus[i]=status[i];g.laneHighlight[i]=high[i];g.laneAngles[i]=ang[i];
        }
        g.sortLanes();
        return g;
    }

    /** Lanes left to right (position 0 is the leftmost lane). */
    private void sortLanes(){
        for(int i=1;i<lanePosition.length;i++)
            for(int j=i;j>0&&lanePosition[j-1]>lanePosition[j];j--){
                int t=lanePosition[j];lanePosition[j]=lanePosition[j-1];lanePosition[j-1]=t;
                t=laneStatus[j];laneStatus[j]=laneStatus[j-1];laneStatus[j-1]=t;
                t=laneHighlight[j];laneHighlight[j]=laneHighlight[j-1];laneHighlight[j-1]=t;
                int[] a=laneAngles[j];laneAngles[j]=laneAngles[j-1];laneAngles[j-1]=a;
            }
    }

    /** Main direction of a lane: the highlighted angle, else its only distinct angle, else 255 (none). */
    int laneDirection(int i){
        if(MibrRgiManeuvers.known(laneHighlight[i]))return MibrRgiManeuvers.sixteenths(laneHighlight[i]);
        int found=-1;
        for(int k=0;k<laneAngles[i].length;k++){
            if(!MibrRgiManeuvers.known(laneAngles[i][k]))continue;
            int d=MibrRgiManeuvers.sixteenths(laneAngles[i][k]);
            if(found<0)found=d;else if(found!=d)return 255;
        }
        return found<0?255:found;
    }

    /** Other directions of the lane (one byte each, the main direction left out). */
    byte[] laneSideDirections(int i){
        int main=laneDirection(i);
        StringBuffer b=new StringBuffer();
        for(int k=0;k<laneAngles[i].length;k++){
            if(!MibrRgiManeuvers.known(laneAngles[i][k]))continue;
            int d=MibrRgiManeuvers.sixteenths(laneAngles[i][k]);
            if(d==main)continue;
            boolean seen=false;
            for(int j=0;j<b.length();j++)if(b.charAt(j)==(char)d)seen=true;
            if(!seen)b.append((char)d);
        }
        byte[] out=new byte[b.length()];
        for(int j=0;j<out.length;j++)out[j]=(byte)b.charAt(j);
        return out;
    }

    /** BAP recommendation: 0 not recommended, 1 recommended, 2 best. */
    int laneRecommendation(int i){
        int s=laneStatus[i];
        return s==2?2:s==1?1:0;
    }

    /** Lanes are shown only with at least one recognisable direction. */
    boolean lanesUsable(){
        if(lanePosition.length==0)return false;
        for(int i=0;i<lanePosition.length;i++){
            if(i>0&&lanePosition[i]==lanePosition[i-1])return false;
            if(lanePosition[i]==65535)return false;
        }
        for(int i=0;i<lanePosition.length;i++)if(laneDirection(i)!=255)return true;
        return false;
    }

    private static int[] ints(String v){
        if(v.length()==0)return new int[0];
        int n=1;
        for(int i=0;i<v.length();i++)if(v.charAt(i)==',')n++;
        int[] out=new int[n];
        int start=0,k=0;
        for(int i=0;i<=v.length();i++){
            if(i==v.length()||v.charAt(i)==','){
                out[k++]=Integer.parseInt(v.substring(start,i));
                start=i+1;
            }
        }
        return out;
    }
}
