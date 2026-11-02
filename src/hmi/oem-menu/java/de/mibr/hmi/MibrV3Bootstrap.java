package de.mibr.hmi;

/** Strictly opt-in integration seam; QNX provisioning, media and peer review still required.
 * The secret's FILE PATH, not its value, is passed to the Java process.
 */
final class MibrV3Bootstrap {
    private MibrV3Bootstrap(){}
    static MibrV3Client devClient(){
        try {
            if(!"1".equals(System.getProperty("mibr.control.v3.devtest")))return null;
            String port=System.getProperty("mibr.control.v3.port");
            String secret=System.getProperty("mibr.control.v3.secretFile");
            if(port==null||secret==null||port.length()<4||port.length()>5||secret.length()==0)return null;
            for(int i=0;i<port.length();i++)if(port.charAt(i)<'0'||port.charAt(i)>'9')return null;
            return new MibrV3Client(Integer.parseInt(port),secret);
        }catch(Throwable t){return null;}
    }
}
