package mib.mu1440.vehiclespeed;

/** Fixed MVS1 v1 24-byte little-endian encoder. No IO and no timer. */
public final class Mvs1Codec {
    public static final int BYTES = 24;
    public static final int VALID_SPEED = 0x01;
    public static final int STANDSTILL = 0x02;
    public static final int GEAR_VALID = 0x04;
    public static final int REVERSE = 0x08;
    private static final int VALID_MASK = 0x0f;

    private Mvs1Codec() { }

    public static byte[] encode(long sampleMs, int speedMmps, int sourceSeq,
                                int flags) {
        if (sampleMs < 0L || (flags & ~VALID_MASK) != 0 ||
            speedMmps < 0 || speedMmps > 100000 ||
            ((flags & VALID_SPEED) == 0 && speedMmps != 0) ||
            ((flags & STANDSTILL) != 0 &&
                ((flags & VALID_SPEED) == 0 || speedMmps != 0)) ||
            ((flags & REVERSE) != 0 && (flags & GEAR_VALID) == 0)) {
            return null;
        }
        byte[] out = new byte[BYTES];
        out[0] = 'M'; out[1] = 'V'; out[2] = 'S'; out[3] = '1';
        out[4] = 1;
        out[5] = (byte) flags;
        put64(out, 8, sampleMs);
        put32(out, 16, speedMmps);
        put32(out, 20, sourceSeq);
        return out;
    }

    private static void put32(byte[] out, int offset, int value) {
        out[offset] = (byte) value;
        out[offset + 1] = (byte) (value >>> 8);
        out[offset + 2] = (byte) (value >>> 16);
        out[offset + 3] = (byte) (value >>> 24);
    }

    private static void put64(byte[] out, int offset, long value) {
        put32(out, offset, (int) value);
        put32(out, offset + 4, (int) (value >>> 32));
    }
}