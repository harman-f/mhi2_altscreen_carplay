package mib.mu1440.vehiclespeed;

import org.dsi.ifc.global.CarBCSpeed;
import org.dsi.ifc.global.CarConstants;

/** MU1440 CarBCSpeed validity/unit decoder from exact DSI constants + GAL scale. */
public final class Mu1440CarBCSpeedDecoder {
    private static final double KMPH_TO_MPS = 0.277777778;
    private static final double MPH_TO_MPS = 0.44704;

    private Mu1440CarBCSpeedDecoder() { }

    /** Return mm/s magnitude (GAL-compatible truncation) or -1 if invalid. */
    public static int toMillimetresPerSecond(CarBCSpeed value) {
        if (value == null ||
            value.speedValueState != CarConstants.BCVALUESTATE_VALID) return -1;
        float raw = value.speedValue;
        if (raw != raw || raw < 0.0f || raw > 100.0f * 3.6f) return -1;
        double metresPerSecond;
        if (value.speedUnit == CarConstants.SPEEDUNIT_KMPH) {
            metresPerSecond = (double) raw * KMPH_TO_MPS;
        } else if (value.speedUnit == CarConstants.SPEEDUNIT_MPH) {
            metresPerSecond = (double) raw * MPH_TO_MPS;
        } else {
            return -1;
        }
        double mmps = metresPerSecond * 1000.0;
        if (mmps < 0.0) return -1;
        int truncated = (int) mmps;
        return truncated <= 100000 ? truncated : -1;
    }
}