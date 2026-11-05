package de.mibr.hmi;

import de.vw.mib.widgets.StaticImage;
import de.vw.mib.widgets.models.CommonImageModel;

/**
 * Transparent gear overlay for the owned HOME tile on the SEAT profiles.
 * The native CarPlay image array remains the base; this overlay is a
 * profile-owned asset that is loaded through the common-skin image cache.
 */
public final class MibrSeatGearOverlayImage extends StaticImage implements CommonImageModel {
    public static final String IMAGE_FILE =
            "/mnt/app/eso/hmi/lsd/Resources/skin0/Images/mibr_seat_home_gears_rgba_150x150-v2.png";

    public String get_imageFile() { return IMAGE_FILE; }
    public void set_imageFile(String path) { /* immutable profile-owned asset */ }
    public int get_imageType() { return CommonImageModel.IMAGE_TYPE_COMMON; }
    public void set_imageType(int type) { }
    public int get_scaleMode() { return CommonImageModel.SCALE_MODE_FIT; }
    public void set_scaleMode(int mode) { }
}
