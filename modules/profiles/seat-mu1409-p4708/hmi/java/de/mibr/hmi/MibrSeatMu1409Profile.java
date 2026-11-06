package de.mibr.hmi;

import de.vw.mib.animation.easing.EasingParams;
import de.vw.mib.graphics.Color;
import de.vw.mib.graphics.Gradient;
import de.vw.mib.graphics.Insets;
import de.vw.mib.graphics.image.Image;
import de.vw.mib.hmi.internal.ServiceManagerCommon;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.StaticImage;
import de.vw.mib.widgets.models.WidgetModel;
import de.vw.mib.widgets.ui.StaticImageUI;

/**
 * SEAT MU1409 profile. Native CarPlay image array as the tile base plus a
 * transparent gear overlay, 150x150 tile art, live OEM dropdown widgets,
 * container-level home animation and listener re-registration on every init.
 */
public class MibrSeatMu1409Profile implements MibrOemProfile {
    private static final int CARPLAY_IMAGE_ARRAY = 107;
    private static final int[][] PASS_THROUGH_TABLE = {
        {-176518671, 2, -1, 47, 0},
        {-329854490, 3, -1, 11, 0},
        {-780313585, 0, -1, 54, 0}
    };

    public String id() { return "seat-mu1409-p4708"; }

    public int internalViewId() { return 957; }

    public int[] homeTileGeometry(int width, int height) {
        int iconWidth = Math.min(150, width);
        int iconHeight = Math.min(150, height);
        int iconX = (width - iconWidth) / 2;
        int iconY = Math.max(0, (height - iconHeight - 30) / 2);
        int labelWidth = Math.min(150, width);
        return new int[] {iconX, iconY, iconWidth, iconHeight, labelWidth};
    }

    public MibrTileRenderer createTileRenderer() { return new NativeImageRenderer(); }

    public int nativeDropdownStrategy() { return DROPDOWN_LIVE_OEM_WIDGETS; }

    public int[][] passThroughAnimationTable() { return PASS_THROUGH_TABLE; }

    public int imageIndexOffset() { return 0; }

    public boolean listenersClearedOnDeInit() { return true; }

    /** Native StaticImage state art from the live skin plus the gear overlay. */
    private static final class NativeImageRenderer implements MibrTileRenderer {
        private Button tileButton;
        private StaticImage nativeIcon;

        public void configureBackground(Button style, Button touch) {
            touch.set_imagesBackground(style.get_imagesBackground());
        }

        public WidgetModel[] createIcons(Button touch, int x, int y, int width, int height) {
            tileButton = touch;
            if (width <= 0 || height <= 0) return new WidgetModel[0];
            Color transparent = new Color(0);
            nativeIcon = new StaticImage();
            nativeIcon.init(true, 255, true, transparent, 0, transparent, false,
                    new EasingParams[0], true, transparent, 0, false,
                    new Gradient(), new Color[0], height, new Image(), true,
                    "MibrSeatNativeTileIcon", -8803, new Insets(), true,
                    width, x, y);
            nativeIcon.setUI(new StaticImageUI());
            touch.set_imageStateRef(nativeIcon);
            MibrSeatGearOverlayImage gear = new MibrSeatGearOverlayImage();
            gear.init(true, 255, true, transparent, 0, transparent, false,
                    new EasingParams[0], true, transparent, 0, false,
                    new Gradient(), new Color[0], height, new Image(), true,
                    "MibrSeatSettingsGearOverlay", -8804, new Insets(), true,
                    width, x, y);
            // Common-skin cache/load path; the image model yields an asset only
            // on the skin that carries it, other skins stay OEM-native.
            gear.setUI(new MibrFourStateIconUI());
            return new WidgetModel[] {nativeIcon, gear};
        }

        /** Live-skin CarPlay Image[] already owns press and day/night selection. */
        public void refresh() {
            if (tileButton == null || nativeIcon == null || ServiceManagerCommon.skinImagePool == null) return;
            Image[] images;
            try { images = ServiceManagerCommon.skinImagePool.getImageArray(CARPLAY_IMAGE_ARRAY); }
            catch (Throwable t) {
                System.err.println("MIBR_SEAT_CARPLAY_IMAGE_ARRAY_FAILED " + t);
                return;
            }
            if (images == null || images.length == 0) {
                System.err.println("MIBR_SEAT_CARPLAY_IMAGE_ARRAY_EMPTY");
                return;
            }
            tileButton.set_imagesState(images);
            nativeIcon.repaint();
            tileButton.repaint();
        }
    }
}
