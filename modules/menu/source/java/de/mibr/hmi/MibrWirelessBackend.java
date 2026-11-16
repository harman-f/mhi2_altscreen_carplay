package de.mibr.hmi;

/**
 * Injectable boundary from the menu to an independently owned native wireless controller.
 * This interface is a Java contract only; it does not implement a transport or radio operation.
 * Every reply must carry the supplied generation and, for commands, request ID.
 */
public interface MibrWirelessBackend {
    int ABI = 1;
    int CAP_PAIRING = 1;
    int CAP_CONTROL = 2;
    int CAP_STOCK_IAP = 4;
    int CAP_STOCK_MEDIA = 8;
    int CAP_REQUIRED = CAP_PAIRING | CAP_CONTROL | CAP_STOCK_IAP | CAP_STOCK_MEDIA;

    interface Listener {
        void onCapabilities(long generation,long requestId,Capabilities value);
        void onSnapshot(long generation,long requestId,Snapshot value);
        void onResult(long generation, long requestId, Result value);
    }

    /** Null or incomplete capabilities must be treated as unavailable. */
    final class Capabilities {
        public final int abi, mask;
        public final long generation;
        public Capabilities(int abi, int mask, long generation) {
            this.abi=abi; this.mask=mask; this.generation=generation;
        }
        public boolean complete() {
            return abi==ABI && generation>0 && (mask & CAP_REQUIRED)==CAP_REQUIRED;
        }
    }

    /** Native-confirmed state. Strings use the exact finite vocabulary below. */
    final class Snapshot {
        public final long generation;
        public final boolean confirmed, requestedOn;
        public final String state, pairing;
        public Snapshot(long generation, boolean confirmed, boolean requestedOn,
                        String state, String pairing) {
            this.generation=generation; this.confirmed=confirmed; this.requestedOn=requestedOn;
            this.state=state; this.pairing=pairing;
        }
        public boolean validFor(long expected) {
            return generation==expected && confirmed && oneOf(state,
                "OFF","IDLE","BOOTSTRAP","VERIFY","ACTIVE","STOPPING","FAILED") &&
                oneOf(pairing,"UNKNOWN","NOT_PAIRED","REQUESTED","PAIRED");
        }
        private static boolean oneOf(String value,String[] choices) {
            if(value==null)return false;
            for(int i=0;i<choices.length;i++)if(choices[i].equals(value))return true;
            return false;
        }
        private static boolean oneOf(String value,String a,String b,String c,String d,String e,String f,String g) {
            return a.equals(value)||b.equals(value)||c.equals(value)||d.equals(value)||e.equals(value)||f.equals(value)||g.equals(value);
        }
        private static boolean oneOf(String value,String a,String b,String c,String d) {
            return a.equals(value)||b.equals(value)||c.equals(value)||d.equals(value);
        }
    }

    /** A result is not a success unless the native owner acknowledged it and supplied verified state. */
    final class Result {
        public final long generation, requestId;
        public final int operation;
        public final boolean acknowledged;
        public final Snapshot snapshot;
        public Result(long generation,long requestId,int operation,boolean acknowledged,Snapshot snapshot) {
            this.generation=generation; this.requestId=requestId; this.operation=operation;
            this.acknowledged=acknowledged; this.snapshot=snapshot;
        }
    }

    boolean readCapabilities(long generation,long requestId,Listener listener);
    boolean readStatus(long generation,long requestId,Listener listener);
    boolean requestEnabled(long generation,long requestId,boolean enabled,Listener listener);
    boolean requestPairing(long generation,long requestId,Listener listener);
    boolean stop(long generation,long requestId,Listener listener);
}
