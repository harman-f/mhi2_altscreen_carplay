package de.mibr.extender;

import de.vw.mib.extstartup.spi.ExtendedStartupSPI;
import de.vw.mib.extstartup.spi.StartupResumeListener;

/** Independently authored exact-MU1440 bootstrap; the menu attaches later at CIO readiness. */
public final class MibrStartupHook implements ExtendedStartupSPI {
    public MibrStartupHook() {
        try { MibrExtenderCore.constructed(); }
        catch (Throwable failure) { MibrExtenderCore.error("construct", failure); }
    }
    public void addBootResumeListener(StartupResumeListener listener) { }
    public boolean isResumeFromSnapshotBoot() { return false; }
    public boolean isSnapshotBoot() {
        try { MibrExtenderCore.beforeAutostart(); }
        catch (Throwable failure) { MibrExtenderCore.error("preautostart", failure); }
        return false;
    }
    public boolean providesExtendedBootSupport() { return false; }
    public void readyToMakeSnaphot() { }
    public void setSnapshotCorrupted() { }
}
