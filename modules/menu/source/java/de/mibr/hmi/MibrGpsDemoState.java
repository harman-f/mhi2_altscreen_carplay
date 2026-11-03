package de.mibr.hmi;

/** Session-scoped original-DIO demo GPS state, never a second GPS producer.
 *  Source status is actual owner admission, not an iPhone Maps render ACK.
 */
final class MibrGpsDemoState {
    private static String choice="OFF",epoch;
    private static boolean writer,active;
    private static String message;
    private MibrGpsDemoState(){}
    static boolean valid(String mode){
        return "OFF".equals(mode)||"BERLIN_DEMO".equals(mode)||"HAMBURG_DEMO".equals(mode)||
               "SCHWALEFELD_DEMO".equals(mode)||"WINTERBERG_DEMO".equals(mode);
    }
    static void reset(){
        choice="OFF";epoch=null;writer=false;active=false;message=null;
    }
    static void error(String why){writer=false;active=false;message=why;}
    static void saving(){writer=false;message=MibrI18n.pick("Umschalten...","Switching...");}
    static boolean writable(){return writer&&epoch!=null;}
    static String choice(){return choice;}
    static String epoch(){return epoch;}
    static boolean active(){return active;}
    static String message(){return MibrI18n.localize(message);}
    static void readback(String value,String newEpoch,String reportedActive,
                         String reportedStationary,boolean owner){
        if(!valid(value)||newEpoch==null||newEpoch.length()==0||
           !("0".equals(reportedActive)||"1".equals(reportedActive))||
           !("0".equals(reportedStationary)||"1".equals(reportedStationary)))
            throw new IllegalArgumentException("GPS_DEMO_READBACK_INVALID");
        for(int i=0;i<newEpoch.length();i++)
            if(newEpoch.charAt(i)<'0'||newEpoch.charAt(i)>'9')
                throw new IllegalArgumentException("GPS_DEMO_EPOCH_INVALID");
        boolean isActive="1".equals(reportedActive);
        if(isActive&&"OFF".equals(value))throw new IllegalArgumentException("GPS_DEMO_ACTIVE_OFF");
        choice=value;epoch=newEpoch;
        active=isActive;writer=owner;
        message=null;
    }
}
