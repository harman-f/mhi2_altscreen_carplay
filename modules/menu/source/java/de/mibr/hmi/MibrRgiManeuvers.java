package de.mibr.hmi;

/**
 * CarPlay route guidance (iAP2 RouteGuidanceManeuverUpdate) to the Skoda/VW BAP NavSD
 * ManeuverDescriptor the stock cluster draws (main element, direction, side streets).
 * Main elements: de.vw.mib.bap.mqbab2.navsd.api.ASLNavSDConstants of the MU1440 lsd.jar.
 * BAP direction: byte, counter-clockwise, 0 ahead, 32 slight left, 64 left, 96 sharp left,
 * 128 back, 160 sharp right, 192 right, 224 slight right. iAP2 angles: degrees, negative =
 * left; +-1000 (or outside +-180) = unknown. Encoding facts as published for the MQB cluster by
 * perkthefox/mst2-cluster-nav docs/MANEUVERS.md; this is an own implementation.
 */
final class MibrRgiManeuvers {
    static final int NO_SYMBOL = 0, NO_INFO = 1, ARRIVED = 3, FOLLOW_STREET = 11, CHANGE_LANE = 12, TURN = 13,
        ROUNDABOUT_RIGHT = 21, ROUNDABOUT_LEFT = 22, UTURN = 25, EXIT_ROUNDABOUT_RIGHT = 26, EXIT_ROUNDABOUT_LEFT = 27;
    static final int AHEAD = 0, SLIGHT_LEFT = 32, LEFT = 64, SHARP_LEFT = 96, BACK = 128,
        SHARP_RIGHT = 160, RIGHT = 192, SLIGHT_RIGHT = 224;
    static final int UNKNOWN_ANGLE = 1000;
    private static final int MAX_SIDE_STREETS = 17;
    private MibrRgiManeuvers(){}

    static boolean known(int angle){return angle>=-180&&angle<=180;}

    /** Rounded like the cockpit's own arrow: whole km from 10 km, 0.1 km from 1 km, 100 m, then 10 m. */
    static String distance(long metres){
        if(metres>=10000L)return ((metres+500L)/1000L)+" km";
        if(metres>=1000L){
            long tenths=(metres+50L)/100L;
            return (tenths/10L)+MibrI18n.pick(",",".")+(tenths%10L)+" km";
        }
        if(metres>=100L)return ((metres+50L)/100L*100L)+" m";
        return ((metres+5L)/10L*10L)+" m";
    }

    /** @return {main element, direction} */
    static int[] map(int type,int angle,boolean leftHandTraffic){
        boolean known=known(angle);
        boolean signed=known&&angle!=0;
        switch(type){
        case 0: case 5: case 15: case 17: return pair(FOLLOW_STREET,AHEAD);
        case 1: return pair(TURN,LEFT);
        case 2: return pair(TURN,RIGHT);
        case 3: return pair(TURN,AHEAD);
        case 4: case 18: case 26:
            return pair(UTURN,signed?(angle<0?LEFT:RIGHT):(leftHandTraffic?RIGHT:LEFT));
        case 6: return pair(TURN,leftHandTraffic?LEFT:RIGHT);
        case 7: return leftHandTraffic?pair(EXIT_ROUNDABOUT_LEFT,LEFT):pair(EXIT_ROUNDABOUT_RIGHT,RIGHT);
        case 8: case 9:
            return pair(TURN,signed?(angle<0?SLIGHT_LEFT:SLIGHT_RIGHT):(leftHandTraffic?SLIGHT_LEFT:SLIGHT_RIGHT));
        case 10: case 12: case 27: return pair(ARRIVED,AHEAD);
        case 11: case 16: case 51: return pair(TURN,known?quantize(angle):AHEAD);
        case 13: case 49: case 22: return pair(TURN,SLIGHT_LEFT);
        case 14: case 50: case 23: return pair(TURN,SLIGHT_RIGHT);
        case 19: return pair(leftHandTraffic?ROUNDABOUT_LEFT:ROUNDABOUT_RIGHT,BACK);
        case 20: return pair(TURN,known&&angle<0?quantize(angle):LEFT);
        case 21: return pair(TURN,known&&angle>0?quantize(angle):RIGHT);
        case 24: return pair(ARRIVED,LEFT);
        case 25: return pair(ARRIVED,RIGHT);
        case 47: return pair(TURN,SHARP_LEFT);
        case 48: return pair(TURN,SHARP_RIGHT);
        case 52: return pair(CHANGE_LANE,LEFT);
        case 53: return pair(CHANGE_LANE,RIGHT);
        default:
            if(type>=28&&type<=46){
                int exit=type-27;
                int main=leftHandTraffic?ROUNDABOUT_LEFT:ROUNDABOUT_RIGHT;
                if(signed)return pair(main,sixteenths(angle));
                // Without an angle the exit number gives the usual four-arm roundabout.
                if(exit==1)return pair(main,leftHandTraffic?LEFT:RIGHT);
                if(exit==2)return pair(main,AHEAD);
                if(exit==3)return pair(main,leftHandTraffic?RIGHT:LEFT);
                return pair(main,BACK);
            }
            return pair(NO_INFO,AHEAD);
        }
    }

    /** iAP2 degrees (negative = left) to a BAP direction in 22.5 degree steps. */
    static int sixteenths(int angle){
        double steps=Math.floor(-angle/22.5+0.5);
        int s=((int)steps)%16;
        if(s<0)s+=16;
        return s*16;
    }

    /** Plain turn: ahead, slight, normal or sharp to the side of the angle. */
    static int quantize(int angle){
        int a=angle<0?-angle:angle;
        boolean left=angle<0;
        if(a<=22)return AHEAD;
        if(a<=67)return left?SLIGHT_LEFT:SLIGHT_RIGHT;
        if(a<=112)return left?LEFT:RIGHT;
        return left?SHARP_LEFT:SHARP_RIGHT;
    }

    /** Side streets of the junction: one direction char per road, the exit road and unknown angles left out. */
    static String sideStreets(int[] angles,int exitAngle){
        if(angles==null)return "";
        int exit=known(exitAngle)?sixteenths(exitAngle):-1;
        StringBuffer b=new StringBuffer();
        for(int i=0;i<angles.length&&b.length()<MAX_SIDE_STREETS;i++){
            if(!known(angles[i]))continue;
            int d=sixteenths(angles[i]);
            if(d==exit)continue;
            boolean seen=false;
            for(int k=0;k<b.length();k++)if(b.charAt(k)==(char)d)seen=true;
            if(!seen)b.append((char)d);
        }
        return b.toString();
    }

    private static int[] pair(int main,int direction){return new int[]{main,direction};}
}
