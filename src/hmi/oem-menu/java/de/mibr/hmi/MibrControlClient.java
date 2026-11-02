package de.mibr.hmi;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;

/**
 * Bounded asynchronous legacy MIBR/1 fixture and gated native TEMP MIBR/2 client.
 * TEMP replies identify desired data only, NEVER live/effective stream ACK.
 * Listener runs on a worker thread: a later HMI integration MUST marshal
 * results back to the proven OEM UI dispatcher before touching any widget.
 *
 * No daemon is launched here; no config/persistence, shell or OEM calls.
 */
public final class MibrControlClient {
    public static interface Listener {
        void onReply(String response);
    }
    private final int port;
    private final String token;
    private boolean verified;
    private boolean pending;
    private static final int MAX_REPLY = 768;

    public MibrControlClient(int port) {this(port,null);}
    /** A product token must come from a separately reviewed owner/provisioner. */
    public MibrControlClient(int port,String token) {
        if(port<1||port>65535 || (token!=null&&!MibrControlProtocol.token(token)))
            throw new IllegalArgumentException("port_or_token");
        this.port=port;this.token=token;
    }
    public synchronized boolean isProductVerified(){return token!=null&&verified;}
    /** Capability handshake must succeed before any product request. */
    public synchronized boolean hello(Listener listener){
        if(token==null||listener==null||pending)return false;
        verified=false;
        return start("HELLO "+token+" MIBR/2",listener);
    }
    /** Build only from the current generated 11-visible-key menu and DRAFTs. */
    synchronized MibrControlProtocol.Batch draftBatch(String revision,MibrPopupEditorModel drafts){
        return token!=null&&verified?MibrControlProtocol.collect(token,revision,drafts):null;
    }
    public synchronized boolean tempBatch(MibrControlProtocol.Batch batch,Listener listener){
        if(token==null||!verified||pending||batch==null||listener==null||
           !batch.command.startsWith("TEMPBATCH "+token+" ") ||
           batch.command.length()>512)return false;
        return start(batch.command,listener);
    }

    private static boolean knownKey(String key) {
        if (key == null) return false;
        for (int i = 0; i < MibrSettingsCatalog.KEYS.length; i++)
            if (key.equals(MibrSettingsCatalog.KEYS[i])) return true;
        return false;
    }

    /** False means busy/invalid: there is deliberately no unbounded queue. */
    public synchronized boolean get(final String key, final Listener listener) {
        if (!knownKey(key) || listener == null || pending) return false;
        if(token!=null&&!verified)return false;
        return start(token==null?"GET "+key:"GET "+token+" "+key,listener);
    }

    public synchronized boolean status(final Listener listener) {
        if (listener == null || pending) return false;
        if(token!=null&&!verified)return false;
        return start(token==null?"STATUS":"STATUS "+token,listener);
    }

    private synchronized boolean start(final String command, final Listener listener) {
        if (pending) return false;
        if(command.length()>512)return false;
        pending = true;
        Thread worker = new Thread(new Runnable() {
            public void run() {
                String result;
                try { result = exchange(command); }
                catch (IOException e) { result = "ERROR TRANSPORT_UNAVAILABLE"; }
                catch (Throwable t) { result = "ERROR CLIENT_FAILURE"; }
                synchronized (MibrControlClient.this) {
                    if(command.startsWith("HELLO "))verified=MibrControlProtocol.HELLO.equals(result);
                    pending=false;
                }
                // Worker-thread callback only. It must not mutate HMI widgets directly.
                try { listener.onReply(result); }
                catch (Throwable ignored) { }
            }
        }, "MibrControlWorker");
        worker.setDaemon(true);
        worker.start();
        return true;
    }

    private String exchange(String command) throws IOException {
        Socket socket = null;
        try {
            // Loopback only. A fixture or later reviewed production broker owns the port.
            socket = new Socket("127.0.0.1", port);
            socket.setSoTimeout(3000);
            OutputStream out = socket.getOutputStream();
            out.write((command + "\n").getBytes("US-ASCII"));
            out.flush();
            InputStream in = socket.getInputStream();
            StringBuffer result = new StringBuffer();
            int c;
            while (result.length() < MAX_REPLY && (c = in.read()) != -1) {
                if (c == '\n') {
                    String line = result.toString();
                    // Fail closed: a backend response must not be equated to APPLIED.
                    if (line.indexOf('\r') >= 0 || line.length() == 0)
                        throw new IOException("invalid response");
                    return line;
                }
                if (c < 32 || c > 126) throw new IOException("invalid encoding");
                result.append((char)c);
            }
            throw new IOException("missing/oversized line");
        } finally {
            if (socket != null) try { socket.close(); } catch (IOException ignored) {}
        }
    }
}
