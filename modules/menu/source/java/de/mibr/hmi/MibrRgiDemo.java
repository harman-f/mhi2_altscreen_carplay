package de.mibr.hmi;

/**
 * Built-in demo route for a parked test of the cockpit side (no iPhone needed): runs while
 * /tmp/mibr-rgi.demo exists and "CarPlay-Navigation" is on. Each call is one 250 ms tick at about
 * 54 km/h; the route loops: lanes before every turn: right turn, roundabout 2nd exit, keep left, sharp left,
 * arrival, a short pause without route.
 */
final class MibrRgiDemo {
    private static final int STEP_M = 4;
    /* type, exit angle, street after the maneuver, distance to it (m) */
    private static final int[][] LEGS = {
        {2, 90, 400},
        {29, 0, 350},
        {13, -30, 300},
        {47, -135, 250},
        {12, 0, 200},
    };
    private static final String[] STREETS = {
        "Hauptstraße", "Ringstraße", "Bahnhofstraße", "Am Markt", "Ziel"
    };
    private static final int[][] JUNCTIONS = {
        {-90, 0, 90}, {-90, 0, 90, 180}, {-30, 20}, {-135, 0, 90}, {}
    };
    private int leg, distance = LEGS[0][2], pause, tick;

    MibrRgiGuidance next(){
        tick++;
        MibrRgiGuidance g=new MibrRgiGuidance();
        g.heartbeat="demo"+tick;
        g.seq=tick;
        g.receiving=true;
        g.road=leg==0?"Startweg":STREETS[leg-1];
        g.destination="Demo";
        if(pause>0){
            pause--;
            g.routeState=pause>12?MibrRgiGuidance.ARRIVED:MibrRgiGuidance.NO_ROUTE;
            if(pause==0){leg=0;distance=LEGS[0][2];}
            return g;
        }
        g.routeState=MibrRgiGuidance.ROUTE_SET;
        g.maneuverIndex=leg;
        g.type=LEGS[leg][0];
        g.angle=LEGS[leg][1];
        g.junction=JUNCTIONS[leg];
        g.street=STREETS[leg];
        g.distanceToManeuver=distance;
        int rest=distance;
        for(int i=leg+1;i<LEGS.length;i++)rest+=LEGS[i][2];
        g.distanceRemaining=rest;
        g.timeRemaining=rest/15;
        if(leg<LEGS.length-1&&distance<=250){
            /* three lanes before every turn, the one towards the exit preferred */
            int exit=LEGS[leg][1];
            int best=exit<-10?0:exit>10?2:1;
            g.lanePosition=new int[]{0,1,2};
            g.laneStatus=new int[]{best==0?2:0,best==1?2:0,best==2?2:0};
            g.laneHighlight=new int[]{best==0?exit:1000,best==1?exit:1000,best==2?exit:1000};
            g.laneAngles=new int[][]{{-90},{0},{90}};
        }
        distance-=STEP_M;
        if(distance<=0){
            leg++;
            if(leg>=LEGS.length){pause=32;leg=LEGS.length-1;distance=0;}
            else distance=LEGS[leg][2];
        }
        return g;
    }
}
