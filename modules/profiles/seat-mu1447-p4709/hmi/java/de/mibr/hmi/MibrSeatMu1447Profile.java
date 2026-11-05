package de.mibr.hmi;

/**
 * SEAT MU1447 profile: the MU1409 adapter with the individual native image
 * indices shifted by 6. Image arrays (the CarPlay tile array) are unaffected.
 * Built together with the MU1409 adapter sources (adapter_from).
 */
public class MibrSeatMu1447Profile extends MibrSeatMu1409Profile {
    public String id() { return "seat-mu1447-p4709"; }

    public int imageIndexOffset() { return 6; }
}
