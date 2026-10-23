/* SPDX-License-Identifier: MIT
 * Four-state, read-only icon selection for the owned MU1440 HOME tile.
 */
package de.mibr.hmi;

/**
 * Maps the native day/night mode and the tile button state to the four
 * owner-supplied transparent PNGs. As in the stock CarPlay tile image array
 * 758 (states 7/9/11/13 -> bitmap 1834), the green-bar art is the PRESSED
 * state; selected/focused or activated alone keep the normal art.
 * Skin 1 (stock) gets its own 235x151 set from images.mcf records 1834/1835;
 * every other skin id keeps the Skin3-derived 235x154 set.
 */
public final class MibrIconState {
    public static final String ROOT = "/mnt/app/eso/hmi/lsd/mibr/icons/";

    public static final int DARK_NORMAL = 0;
    public static final int DARK_ACTIVE = 1;
    public static final int LIGHT_NORMAL = 2;
    public static final int LIGHT_ACTIVE = 3;

    private MibrIconState() {
    }

    public static final int SKIN1 = 1;

    public static int variant(boolean dark, boolean selected) {
        if (dark) return selected ? DARK_ACTIVE : DARK_NORMAL;
        return selected ? LIGHT_ACTIVE : LIGHT_NORMAL;
    }

    public static int variant(boolean dark, boolean selected,
            boolean activated, boolean pressed) {
        /* Stock array 758: every pressed index uses the green-bar bitmap. */
        return variant(dark, pressed);
    }

    /** Two-state form: {@code active} selects the green-bar (pressed) art. */
    public static String path(boolean dark, boolean active) {
        return path(dark, false, false, active);
    }

    public static String path(boolean dark, boolean selected,
            boolean activated, boolean pressed) {
        return path(0, dark, selected, activated, pressed);
    }

    public static String path(int skin, boolean dark, boolean selected,
            boolean activated, boolean pressed) {
        int v = variant(dark, selected, activated, pressed);
        if (skin == SKIN1) {
            return ROOT + "mibr_vc_settings_skin1_" + (dark ? "dark" : "light")
                    + (v == DARK_ACTIVE || v == LIGHT_ACTIVE ? "_active_" : "_normal_")
                    + "235x151_rgba.png";
        }
        switch (v) {
            case DARK_NORMAL:
                return ROOT + "mibr_vc_settings_dark_normal_235x154_rgba.png";
            case DARK_ACTIVE:
                return ROOT + "mibr_vc_settings_dark_active_235x154_rgba.png";
            case LIGHT_NORMAL:
                return ROOT + "mibr_vc_settings_light_normal_235x154_rgba.png";
            default:
                return ROOT + "mibr_vc_settings_light_active_235x154_rgba.png";
        }
    }

    /** The same day/night variant with the other press state, so both can be preloaded. */
    public static String counterpart(String path) {
        if (path == null) return null;
        int active = path.indexOf("_active_");
        if (active >= 0) return path.substring(0, active) + "_normal_" + path.substring(active + 8);
        int normal = path.indexOf("_normal_");
        if (normal >= 0) return path.substring(0, normal) + "_active_" + path.substring(normal + 8);
        return null;
    }
}