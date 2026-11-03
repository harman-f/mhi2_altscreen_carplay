package de.mibr.hmi;

/** Fail-closed developer transport provisioning seam; NOT production credentials.
 * No default port/token, no broker launch and no automatic writable Unit install.
 * JVM -D arguments expose the token: this mode MUST NOT be used as a product
 * security design. Separate scoped stationary experiment and release required.
 */
final class MibrControlBootstrap {
    private MibrControlBootstrap(){}
    static MibrControlClient devClient(){
        try {
            if(!"1".equals(System.getProperty("mibr.control.devtest")))return null;
            String p=System.getProperty("mibr.control.port");
            String token=System.getProperty("mibr.control.token");
            if(p==null||token==null||p.length()<4||p.length()>5)return null;
            for(int i=0;i<p.length();i++)if(p.charAt(i)<'0'||p.charAt(i)>'9')return null;
            int port=Integer.parseInt(p);
            if(port<1024)return null;
            return new MibrControlClient(port,token);
        }catch(Throwable ignored){return null;}
    }
}
