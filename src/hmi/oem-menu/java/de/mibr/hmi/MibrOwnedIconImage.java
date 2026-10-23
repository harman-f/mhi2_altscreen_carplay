/* SPDX-License-Identifier: MIT
 * Image model owned by one MIBR-created SimpleGridMenu ListItem clone.
 */
package de.mibr.hmi;

import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.StaticImage;
import de.vw.mib.widgets.models.CommonImageModel;

/** A stock StaticImage widget whose UI loads the selected external PNG. */
public final class MibrOwnedIconImage extends StaticImage implements CommonImageModel {
    private final Button stateButton;

    public MibrOwnedIconImage(Button stateButton) {
        this.stateButton = stateButton;
    }

    public String get_imageFile() {
        return MibrIconState.path(MibrNativeSkinMode.currentSkinId(),
                MibrNativeSkinMode.isDarkMode(),
                stateButton != null && stateButton.is_selected(),
                stateButton != null && stateButton.isActivatedInternal(),
                pressed());
    }

    private boolean pressed() {
        if (stateButton instanceof MibrOwnedWidgets.TouchButton)
            return ((MibrOwnedWidgets.TouchButton) stateButton).showsPressed();
        return stateButton != null && stateButton.isPressed();
    }

    public void set_imageFile(String path) {
        /* The path is derived from native state, never mutable by stock scripts. */
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