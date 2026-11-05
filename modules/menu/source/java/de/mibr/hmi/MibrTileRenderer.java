package de.mibr.hmi;

import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.models.WidgetModel;

/** Renders the icon of one owned home tile; the strategy differs per profile. */
public interface MibrTileRenderer {
    /** Sets the touch button background art from the stock style button. */
    void configureBackground(Button style, Button touch);

    /** Icon child widgets for the tile (possibly empty); called once per tile. */
    WidgetModel[] createIcons(Button touch, int x, int y, int width, int height);

    /** Re-applies live skin resources; called after creation and on activation. */
    void refresh();
}
