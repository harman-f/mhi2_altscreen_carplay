package de.mibr.hmi;

import de.vw.mib.graphics.image.Image;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.models.WidgetModel;

/** Default profile: exact MU1440 firmware. Reproduces the pre-profile behaviour. */
public class MibrSkodaMu1440Profile implements MibrOemProfile {
    public String id() { return "skoda-mu1440-p4526"; }

    public int internalViewId() { return 982; }

    public int[] homeTileGeometry(int width, int height) {
        int iconWidth = Math.min(235, Math.max(0, width - 60));
        int iconHeight = Math.min(154, Math.max(0, height - 80));
        int iconX = (width - iconWidth) / 2;
        int iconY = Math.min(30, Math.max(0, height - iconHeight - 50));
        int labelWidth = Math.min(235, Math.max(0, width - 60));
        return new int[] {iconX, iconY, iconWidth, iconHeight, labelWidth};
    }

    public MibrTileRenderer createTileRenderer() { return new FourStateRenderer(); }

    public int nativeDropdownStrategy() { return DROPDOWN_STYLE_PROFILE; }

    public int[][] passThroughAnimationTable() { return null; }

    public int imageIndexOffset() { return 0; }

    public boolean listenersClearedOnDeInit() { return false; }

    /** Four-state owned icon; the stock flat pressed bitmap is blanked behind it. */
    private static final class FourStateRenderer implements MibrTileRenderer {
        public void configureBackground(Button style, Button touch) {
            Image[] stockArt = style.get_imagesBackground();
            Image[] blankArt = new Image[stockArt == null ? 0 : stockArt.length];
            for (int i = 0; i < blankArt.length; i++) blankArt[i] = new Image();
            touch.set_imagesBackground(blankArt);
        }

        public WidgetModel[] createIcons(Button touch, int x, int y, int width, int height) {
            if (width <= 0 || height <= 0) return new WidgetModel[0];
            final WidgetModel icon = MibrOwnedWidgets.createFourStateIcon(null, touch,
                    "MibrCarPlayTileIcon", -8803, x, y, width, height);
            if (touch instanceof MibrOwnedWidgets.TouchButton) {
                ((MibrOwnedWidgets.TouchButton)touch).setStateListener(
                    new Runnable() { public void run() { icon.repaint(); } });
            }
            return new WidgetModel[] {icon};
        }

        public void refresh() { }
    }
}
