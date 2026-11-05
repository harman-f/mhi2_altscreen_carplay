package de.mibr.hmi;

/**
 * Variation points between the supported firmware profiles. The shared menu
 * core calls this interface instead of embedding per-firmware literals; one
 * implementation is bound at build time through the generated MibrProfileBinding.
 * Only plain Java types appear here so host tests need no OEM stubs.
 */
public interface MibrOemProfile {
    /** Native dropdown availability is derived from the Skoda image/colour style. */
    int DROPDOWN_STYLE_PROFILE = 0;
    /** Native dropdown availability is derived from the live OEM popup widgets. */
    int DROPDOWN_LIVE_OEM_WIDGETS = 1;

    /** Profile identifier as used under modules/profiles. */
    String id();

    /** Internal view id of the stock setup page (SMI_SETUP_MAIN). */
    int internalViewId();

    /**
     * Home tile layout for a tile of the given size:
     * {iconX, iconY, iconWidth, iconHeight, labelWidth}.
     */
    int[] homeTileGeometry(int width, int height);

    /** New renderer for one owned home tile. */
    MibrTileRenderer createTileRenderer();

    /** One of the DROPDOWN_* constants. */
    int nativeDropdownStrategy();

    /**
     * Stock home animation table that is accepted with pass-through (no per-tile
     * choreography), or null when only the full Skoda table is accepted.
     */
    int[][] passThroughAnimationTable();

    /** Offset added to individual native getImage indices (image arrays are unaffected). */
    int imageIndexOffset();

    /**
     * True when the firmware clears widget controller listeners on deInit, so
     * hooks must be re-registered on every init and stock clone transfer.
     */
    boolean listenersClearedOnDeInit();
}
