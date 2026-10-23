/* SPDX-License-Identifier: MIT
 * StaticImage with a fixed external PNG (scroll indicator track/thumb).
 */
package de.mibr.hmi;

import de.vw.mib.widgets.StaticImage;
import de.vw.mib.widgets.models.CommonImageModel;

/** A stock StaticImage whose UI stretches one external PNG over the widget rectangle. */
public final class MibrOwnedStaticImage extends StaticImage implements CommonImageModel {
    private final String path;

    public MibrOwnedStaticImage(String path) {
        this.path = path;
    }

    public String get_imageFile() {
        return path;
    }

    public void set_imageFile(String ignored) {
        /* fixed art, never mutable by stock scripts */
    }

    public int get_imageType() {
        return CommonImageModel.IMAGE_TYPE_COMMON;
    }

    public void set_imageType(int type) {
    }

    public int get_scaleMode() {
        return CommonImageModel.SCALE_MODE_FIT;
    }

    public void set_scaleMode(int mode) {
    }
}