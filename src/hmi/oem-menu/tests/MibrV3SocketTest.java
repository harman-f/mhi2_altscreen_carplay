package de.mibr.hmi;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;

/** Real localhost wire (no QNX, no settings core, no vehicle). */
public final class MibrV3SocketTest {
    private static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
    private static final String SECRET="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    private static final class Report implements MibrV3Client.Listener {
        MibrV3Protocol.Frame frame;String error;boolean finished;
        public synchronized void onReply(MibrV3Protocol.Frame f,String e){
            frame=f;error=e;finished=true;notifyAll();
        }
        synchronized void await() throws Exception {
            long deadline=System.currentTimeMillis()+7000;
            while(!finished){
                long remaining=deadline-System.currentTimeMillis();
                if(remaining<=0)throw new AssertionError("callback timeout");
                wait(remaining);
            }
        }
    }
    private static final class Service extends Thread {
        final ServerSocket socket;
        volatile String seen,problem;
        final boolean wrongId;
        Service(ServerSocket s,boolean wrong){socket=s;wrongId=wrong;setDaemon(true);}
        public void run(){
            Socket accepted=null;
            try{
                accepted=socket.accept();accepted.setSoTimeout(3000);
                InputStream in=accepted.getInputStream();
                StringBuffer message=new StringBuffer();int c;
                while((c=in.read())!=-1&&c!='\n'&&message.length()<4096)message.append((char)c);
                seen=message.toString();
                String[] header=seen.split(" ",4);
                if(header.length!=4 || !"MIBR/3".equals(header[0]) ||
                   !"HELLO".equals(header[2]) || !seen.endsWith("auth="+SECRET))
                    throw new IllegalArgumentException("bad received wire");
                String rid=wrongId?"wrong":header[1];
                String answer="MIBR/3 "+rid+" OK version=MIBR%2F3;schema=2;registry_keys=48;phase=NATIVE_READONLY_OFFLINE\n";
                OutputStream out=accepted.getOutputStream();out.write(answer.getBytes("US-ASCII"));out.flush();
            }catch(Throwable t){problem=t.toString();}
            finally{
                if(accepted!=null)try{accepted.close();}catch(Exception ignored){}
                try{socket.close();}catch(Exception ignored){}
            }
        }
    }
    private static void runCase(File credential,boolean wrongId) throws Exception {
        ServerSocket server=new ServerSocket(0,1,InetAddress.getByName("127.0.0.1"));
        Service service=new Service(server,wrongId);service.start();
        MibrV3Client client=new MibrV3Client(server.getLocalPort(),credential.getAbsolutePath());
        Report report=new Report();
        check(client.send("sock1","HELLO",new String[0],new String[0],report),"start");
        report.await();service.join(4000);
        check(service.problem==null,"server "+service.problem);
        check(service.seen!=null && service.seen.endsWith("auth="+SECRET),"file credential used");
        if(wrongId)check(report.frame==null&&report.error!=null,"mismatched response rejected");
        else check(report.error==null && MibrV3Protocol.hello(report.frame),"end-to-end HELLO");
    }
    public static void main(String[] args) throws Exception {
        File credential=File.createTempFile("mibr-v3-socket-", ".secret");
        FileOutputStream out=new FileOutputStream(credential);
        try{out.write((SECRET+"\n").getBytes("US-ASCII"));}
        finally{out.close();}
        try{runCase(credential,false);runCase(credential,true);}
        finally{credential.delete();}
        System.out.println("MIBR_V3_SOCKET_AUTH_HOST_PASS");
    }
}
