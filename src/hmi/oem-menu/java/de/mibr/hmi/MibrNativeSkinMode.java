/* SPDX-License-Identifier: MIT
 * Reads MU1440's native global day/night mode through its Image API and the active skin id.
 */
package de.mibr.hmi;

import de.vw.mib.graphics.image.Image;
import de.vw.mib.graphics.image.ScaleImage;
import de.vw.mib.hmi.internal.ServiceManagerCommon;

public final class MibrNativeSkinMode {
    private static final Image PROBE = new Image(new ScaleImage(), new ScaleImage());

    private MibrNativeSkinMode() {
    }

    public static boolean isDarkMode() {
        return PROBE.getCurrentImage() == PROBE.getNightImage();
    }

    /** Active skin id (1..3) from the OEM ConfigurationManager, 0 if unavailable. */
    public static int currentSkinId() {
        try {
            return ServiceManagerCommon.configurationManager.getCurrentSkinId();
        } catch (Throwable unavailable) {
            return 0;
        }
    }
}