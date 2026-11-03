package de.mibr.hmi;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;

/** Bounded one-request-per-connection J9 loopback transport, not a writer.
 * An out-of-band secret file is required; never pass the secret as a JVM -D argument.
 * Callbacks execute on a worker thread. No OEM widgets may be touched there.
 */
public class MibrV3Client {
    public static interface Listener {void onReply(MibrV3Protocol.Frame reply,String error);}
    private final int port;
    private final String secretPath;
    private boolean pending;
    public MibrV3Client(int port,String secretPath){
        if(port<1024||port>65535||secretPath==null||secretPath.length()==0)
            throw new IllegalArgumentException("V3_PROVISIONING_MISSING");
        this.port=port;this.secretPath=secretPath;
    }
    private String secret() throws IOException {
        FileInputStream in=null;byte[] b=new byte[66];int n=0;
        try {
            in=new FileInputStream(secretPath);
            int c;while(n<b.length&&(c=in.read())!=-1)b[n++]=(byte)c;
            if(n!=65||b[64]!='\n'||in.read()!=-1)throw new IOException("invalid credential file");
            StringBuffer s=new StringBuffer();
            for(int i=0;i<64;i++){
                char ch=(char)(b[i]&255);
                if(!((ch>='a'&&ch<='f')||(ch>='0'&&ch<='9')))throw new IOException("invalid credential");
                s.append(ch);
            }
            return s.toString();
        } finally {
            for(int i=0;i<b.length;i++)b[i]=0;
            if(in!=null)try{in.close();}catch(IOException ignored){}
        }
    }
    public synchronized boolean send(final String rid,final String verb,
            final String[] names,final String[] values,final Listener callback){
        if(pending||callback==null||!MibrV3Protocol.id(rid))return false;
        pending=true;
        Thread thread=new Thread(new Runnable(){
            public void run(){
                MibrV3Protocol.Frame answer=null;String failure=null;
                try{
                    String line=MibrV3Protocol.request(rid,verb,names,values,secret());
                    answer=MibrV3Protocol.parse(exchange(line),rid);
                }catch(Throwable ex){failure="TRANSPORT_OR_PROTOCOL_UNCONFIRMED";}
                synchronized(MibrV3Client.this){pending=false;}
                try{callback.onReply(answer,failure);}catch(Throwable ignored){}
            }
        },"MibrV3Worker");
        thread.setDaemon(true);thread.start();return true;
    }
    private String exchange(String message) throws IOException {
        Socket socket=null;
        try{
            socket=new Socket("127.0.0.1",port);socket.setSoTimeout(3000);
            OutputStream out=socket.getOutputStream();out.write(message.getBytes("US-ASCII"));out.flush();
            InputStream in=socket.getInputStream();StringBuffer b=new StringBuffer();
            int c;while(b.length()<MibrV3Protocol.MAX_REPLY && (c=in.read())!=-1){
                if(c=='\n'){b.append('\n');return b.toString();}
                if(c<32||c>126)throw new IOException("non-ASCII response");
                b.append((char)c);
            }
            throw new IOException("missing or oversized reply");
        }finally{if(socket!=null)try{socket.close();}catch(IOException ignored){}}
    }
}
