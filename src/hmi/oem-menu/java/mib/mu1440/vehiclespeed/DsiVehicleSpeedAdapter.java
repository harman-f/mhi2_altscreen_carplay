package mib.mu1440.vehiclespeed;

import de.vw.mib.asl.framework.api.dsiproxy.DSIProxy;
import de.vw.mib.genericevents.Target;
import org.dsi.ifc.base.DSIListener;
import org.dsi.ifc.carvehiclestates.DSICarVehicleStates;
import org.dsi.ifc.carvehiclestates.DSICarVehicleStatesListener;
import org.dsi.ifc.carvehiclestates.DynamicVehicleInfoHighFrequent;
import org.dsi.ifc.carvehiclestates.DynamicVehicleInfoHighFrequentViewOptions;
import org.dsi.ifc.carvehiclestates.DynamicVehicleInfoMidFrequent;
import org.dsi.ifc.carvehiclestates.DynamicVehicleInfoMidFrequentViewOptions;
import org.dsi.ifc.carvehiclestates.DynamicVehicleInfoSCR;
import org.dsi.ifc.carvehiclestates.KeyData;
import org.dsi.ifc.carvehiclestates.OilLevelData;
import org.dsi.ifc.carvehiclestates.SemiStaticDataViewOptions;
import org.dsi.ifc.carvehiclestates.SemiStaticVehicleData;
import org.dsi.ifc.carvehiclestates.VehicleInfoViewOptions;
import org.dsi.ifc.generalvehiclestates.AirbagData;
import org.dsi.ifc.generalvehiclestates.DSIGeneralVehicleStates;
import org.dsi.ifc.generalvehiclestates.DSIGeneralVehicleStatesListener;
import org.dsi.ifc.generalvehiclestates.TLOViewOptions;
import org.dsi.ifc.generalvehiclestates.TankInfo;
import org.dsi.ifc.global.CarBCSpeed;
import org.dsi.ifc.global.CarViewOption;

/** Optional passive DSI subscriber. Requires a target-qualified policy. */
public final class DsiVehicleSpeedAdapter implements
        DSICarVehicleStatesListener, DSIGeneralVehicleStatesListener {
    public interface Policy {
        /** True only after speed state/unit and a shared monotonic clock are proven. */
        boolean ready();
        /** Return mm/s for a valid CarBCSpeed, or -1 when invalid/unrecognized. */
        int toMillimetresPerSecond(CarBCSpeed speed);
        /** Monotonic milliseconds in the SAME domain used by the receiver. */
        long monotonicMillis();
        /** Must be bounded, non-blocking, and drop rather than wait on pressure. */
        boolean offer(byte[] mvs1);
    }

    private final Policy policy;
    private DSICarVehicleStates car;
    private DSIGeneralVehicleStates general;
    private boolean reverseKnown;
    private boolean reverse;
    private boolean standstillKnown;
    private boolean standstill;
    private int sequence;
    private volatile boolean active;
    private boolean sessionKnown;
    private boolean sessionActive;
    private long sessionToken;

    /** MIBR r42: adapter WITHOUT its own DSI subscription; the caller feeds updateDynamicVehicleInfoHighFrequent
     *  from a read-only tap on the stock cache (own DSI subscriptions deliver nothing on the MU1440 HMI). */
    public static DsiVehicleSpeedAdapter offline(Policy policy) {
        return new DsiVehicleSpeedAdapter(policy);
    }

    DsiVehicleSpeedAdapter(Policy policy) {
        this.policy = policy;
        this.active = true;
    }

    /**
     * Attach through the stock DSIProxy service registry. Returns null when
     * unavailable; callers must treat this optional module as disabled.
     */
    public static DsiVehicleSpeedAdapter attach(Target owner, DSIProxy proxy,
                                                 Policy policy) {
        if (owner == null || proxy == null || policy == null || !ready(policy)) {
            return null;
        }
        DsiVehicleSpeedAdapter a = new DsiVehicleSpeedAdapter(policy);
        try {
            a.car = (DSICarVehicleStates) proxy.getService(owner,
                    DSICarVehicleStates.class);
            a.general = (DSIGeneralVehicleStates) proxy.getService(owner,
                    DSIGeneralVehicleStates.class);
            if (a.car == null || a.general == null) return null;
            a.active = true;
            a.car.setNotification(new int[] { 14 }, (DSIListener) a);
            a.general.setNotification(new int[] { 20, 22 }, (DSIListener) a);
            return a;
        } catch (Throwable ignored) {
            a.close();
            return null;
        }
    }

    /** Remove only this adapter's notification registrations. */
    public synchronized void close() {
        active = false;
        sessionActive = false;
        try { if (car != null) car.clearNotification(new int[] { 14 }, this); }
        catch (Throwable ignored) { }
        try { if (general != null) general.clearNotification(new int[] { 20, 22 }, this); }
        catch (Throwable ignored) { }
        car = null;
        general = null;
        reverseKnown = false;
        standstillKnown = false;
    }

    /** Begin only for a newly identified CarPlay session token. */
    public synchronized boolean beginCarPlaySession(long token) {
        if (!active || !ready(policy) || (sessionKnown && token == sessionToken)) {
            return false;
        }
        sessionKnown = true;
        sessionToken = token;
        sessionActive = true;
        sequence = 0;
        reverseKnown = false;
        standstillKnown = false;
        return true;
    }

    /** End the matching session; a later request/start must not reset sequence. */
    public synchronized void endCarPlaySession(long token) {
        if (sessionKnown && token == sessionToken) {
            sessionActive = false;
            reverseKnown = false;
            standstillKnown = false;
        }
    }

    public synchronized void updateDynamicVehicleInfoHighFrequent(
            DynamicVehicleInfoHighFrequent value, int result) {
        if (!active || !sessionActive || !ready(policy)) return;
        if (result != 1) {
            publish(0, 0);
            return;
        }
        int speed = -1;
        if (value != null) {
            speed = decode(value.realVehicleSpeed);
            if (speed < 0) speed = decode(value.vehicleSpeed);
        }
        boolean speedValid = speed >= 0;
        int flags = 0;
        if (speedValid && speed <= 100000) flags |= Mvs1Codec.VALID_SPEED;
        else speed = 0;
        if (speedValid && standstillKnown && standstill) {
            flags |= Mvs1Codec.VALID_SPEED | Mvs1Codec.STANDSTILL;
            speed = 0;
        }
        if (reverseKnown) {
            flags |= Mvs1Codec.GEAR_VALID;
            if (reverse) flags |= Mvs1Codec.REVERSE;
        }
        publish(flags, speed);
    }

    private int decode(CarBCSpeed value) {
        if (value == null) return -1;
        try {
            int speed = policy.toMillimetresPerSecond(value);
            return speed >= 0 && speed <= 100000 ? speed : -1;
        } catch (Throwable ignored) { return -1; }
    }

    public synchronized void updateReverseGear(boolean value, int result) {
        if (!sessionActive) return;
        if (result == 1) { reverseKnown = true; reverse = value; }
        else reverseKnown = false;
    }

    public synchronized void updateVehicleStandstill(boolean value, int result) {
        if (!sessionActive) return;
        if (result == 1) { standstillKnown = true; standstill = value; }
        else standstillKnown = false;
    }

    private synchronized void publish(int flags, int speed) {
        try {
            long timestamp = policy.monotonicMillis();
            if (timestamp < 0L) return;
            byte[] sample = Mvs1Codec.encode(timestamp, speed, sequence++, flags);
            if (sample != null) policy.offer(sample);
        } catch (Throwable ignored) {
            /* Optional telemetry must never escape into/block OEM HMI code. */
        }
    }

    private static boolean ready(Policy policy) {
        try { return policy.ready(); }
        catch (Throwable ignored) { return false; }
    }

    public void updateOilLevelViewOption(CarViewOption v, int r) { }
    public void asyncException(int code, String message, int requestId) { }
    public void updateOilLevelData(OilLevelData v, int r) { }
    public void updateVINViewOption(CarViewOption v, int r) { }
    public void updateVINData(String v, int r) { }
    public void updateKeyViewOption(CarViewOption v, int r) { }
    public void updateKeyData(KeyData v, int r) { }
    public void updateDrvSchoolSystem(boolean v, int r) { }
    public void updateVehicleInfoViewOptions(VehicleInfoViewOptions v, int r) { }
    public void updateDynamicVehicleInfoHighFrequentViewOptions(DynamicVehicleInfoHighFrequentViewOptions v, int r) { }
    public void updateDynamicVehicleInfoMidFrequentViewOptions(DynamicVehicleInfoMidFrequentViewOptions v, int r) { }
    public void updateDynamicVehicleInfoMidFrequent(DynamicVehicleInfoMidFrequent v, int r) { }
    public void updateSemiStaticVehicleDataViewOptions(SemiStaticDataViewOptions v, int r) { }
    public void updateSemiStaticVehicleData(SemiStaticVehicleData v, int r) { }
    public void updateDynamicVehicleInfoSCR(DynamicVehicleInfoSCR v, int r) { }

    public void updateAirbagData(AirbagData v, int r) { }
    public void updateTankInfo(TankInfo v, int r) { }
    public void updateDimmedHeadlight(boolean v, int r) { }
    public void updateAcousticParkingSystem(boolean v, int r) { }
    public void updateCarVelocityThreshold(boolean v, int r) { }
    public void updateTVVelocityThreshold(boolean v, int r) { }
    public void updateHDDVelocityThreshold(boolean v, int r) { }
    public void updateBrowserSlideShowVelocityThreshold(boolean v, int r) { }
    public void updateBrowserBordBookVelocityThreshold(boolean v, int r) { }
    public void updateBrowserTravelAgentVelocityThreshold(boolean v, int r) { }
    public void updateBrowserWebVelocityThreshold(boolean v, int r) { }
    public void updateBWSVelocityThreshold(boolean v, int r) { }
    public void updateRadiotextVelocityThreshold(boolean v, int r) { }
    public void updateDisplayDayNightDesign(boolean v, int r) { }
    public void updateBTBondingVelocityThreshold(boolean v, int r) { }
    public void updateMessagingVelocityThreshold(boolean v, int r) { }
    public void updateDestinationInputVelocityThreshold(boolean v, int r) { }
    public void updateDSSSViewOption(CarViewOption v, int r) { }
    public void updateServiceKeyData(byte[] v, int r) { }
    public void updateServiceKeyViewOption(CarViewOption v, int r) { }
    public void updatePersonalizationStatus(boolean v, int r, int x) { }
    public void updateTLOViewOptions(TLOViewOptions v, int r) { }
    public void updateEmergencyAssistVolLowering(int v, int r) { }
    public void updateParkingBrake(boolean v, int r) { }
    public void updateAppConnectTrigger(int v, int r) { }
    public void updateSTPState(int v, int r) { }
    public void updateAutomaticGearShiftTransMode(int v, int r) { }
}