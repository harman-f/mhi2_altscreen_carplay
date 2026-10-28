/* SPDX-License-Identifier: MIT
 * Scroll indicator for the owned SMI_SETUP_MAIN page: the live skin has no Scrollbar
 * widget in this view, so a track and a thumb are drawn from project-owned assets.
 */
package de.mibr.hmi;

import de.vw.mib.graphics.Color;
import de.vw.mib.graphics.Gradient;
import de.vw.mib.graphics.Insets;
import de.vw.mib.graphics.image.Image;
import de.vw.mib.animation.easing.EasingParams;
import de.vw.mib.widgets.WidgetList;
import de.vw.mib.widgets.event.AdjustmentListener;
import de.vw.mib.widgets.interfaces.Adjustable;
import de.vw.mib.widgets.models.ContainerModel;
import de.vw.mib.widgets.models.ViewModel;
import de.vw.mib.widgets.models.WidgetModel;

/**
 * Follows the list Adjustable (value/min/max). Geometry is derived from the list and its
 * container; the first updates are written to /tmp/mibr-hmi-diag.log so the placement and the
 * Adjustable units can be verified in the car.
 */
final class MibrScrollIndicator implements AdjustmentListener {
    static final String TRACK = MibrIconState.ROOT + "mibr_scroll_track_v2.png";
    static final String THUMB = MibrIconState.ROOT + "mibr_scroll_thumb_v2.png";
    // r20: measured from the owner photos of the stock System settings bar (thumb ~10 px lime, white 4 px track,
    // thumb centre about 71 px left of the right edge of the 1280 px page).
    private static final int BAR_WIDTH = 10;
    private static final int TRACK_WIDTH = 4;
    private static final int RIGHT_MARGIN = 66;
    private static final int MIN_THUMB = 36;

    private static String thumbPath() {
        try {
            if ("seat_red".equals(System.getProperty("mibr.hmi.scrollbar.theme")))
                return MibrIconState.ROOT + "mibr_scroll_thumb_seat_red.png";
        } catch (SecurityException ignored) { }
        return THUMB;
    }

    private final WidgetList list;
    private final ContainerModel parent;
    private final MibrOwnedStaticImage track;
    private final MibrOwnedStaticImage thumb;
    private int logged;
    private boolean detached;

    private MibrScrollIndicator(WidgetList list, ContainerModel parent, ViewModel view) {
        this.list = list;
        this.parent = parent;
        track = create(TRACK, "MibrScrollTrack", -8811, view);
        thumb = create(thumbPath(), "MibrScrollThumb", -8812, view);
    }

    private static MibrOwnedStaticImage create(String path, String name, int id, ViewModel view) {
        MibrOwnedStaticImage image = new MibrOwnedStaticImage(path);
        Color transparent = new Color(0);
        image.init(true, 255, true, transparent, 0, transparent, false,
                new EasingParams[0], true, transparent, 0, false,
                new Gradient(), new Color[0], 8, new Image(), true,
                name, id, new Insets(), true, TRACK.equals(path) ? TRACK_WIDTH : BAR_WIDTH, 0, 0);
        image.setUI(new MibrScrollBarUI());
        if (view != null) image.init(view);
        return image;
    }

    /** Attaches track and thumb next to the list; returns null when the page layout is unexpected. */
    static MibrScrollIndicator attach(WidgetList list, ViewModel view) {
        MibrScrollIndicator created=null;
        try {
            WidgetModel parent = list.getParent();
            if (!(parent instanceof ContainerModel) || !(list instanceof Adjustable)) {
                MibrOemSsmTemplate.diag("MIBR_SCROLL_INDICATOR_NO_PARENT");
                return null;
            }
            WidgetModel[] present=((ContainerModel)parent).getChildren();
            for(int i=0;present!=null && i<present.length;i++)
                if(present[i]!=null && (present[i].get_targetId()==-8811 || present[i].get_targetId()==-8812))
                    throw new IllegalStateException("SCROLL_INDICATOR_ALREADY_ATTACHED");
            MibrScrollIndicator indicator = new MibrScrollIndicator(list, (ContainerModel)parent, view);
            created=indicator;
            WidgetModel[] old = ((ContainerModel)parent).getChildren();
            int n = old == null ? 0 : old.length;
            WidgetModel[] next = new WidgetModel[n + 2];
            if (n > 0) System.arraycopy(old, 0, next, 0, n);
            next[n] = indicator.track;
            next[n + 1] = indicator.thumb;
            ((ContainerModel)parent).setChildren(next);
            if (view != null && view.is_activated()) {
                indicator.track.activate();
                indicator.thumb.activate();
            }
            ((Adjustable)list).addAdjustmentListener(indicator);
            MibrOemSsmTemplate.diag("MIBR_SCROLL_INDICATOR_ATTACHED parent=" + parent.get_x() + "," + parent.get_y()
                    + " " + parent.get_width() + "x" + parent.get_height()
                    + " list=" + list.get_x() + "," + list.get_y() + " " + list.get_width() + "x" + list.get_height());
            indicator.update();
            return indicator;
        } catch (Throwable failure) {
            if(created!=null)try{created.detach();}catch(Throwable cleanup){MibrOemSsmTemplate.diag("SCROLL_CLEANUP_FAILED "+cleanup);}
            MibrOemSsmTemplate.diag("MIBR_SCROLL_INDICATOR_FAILED " + failure);
            return null;
        }
    }

    public void adjustmentValueChanged(Adjustable adjustable, int kind) {
        update();
    }

    /** Recomputes the thumb from the list Adjustable; hidden while everything fits. */
    void update() {
        if(detached)return;
        try {
            Adjustable adjustable = (Adjustable)list;
            int min = adjustable.getMinimum();
            int max = adjustable.getMaximum();
            int value = adjustable.getValue();
            int view = list.get_height();
            int span = max - min;
            if (logged < 24) {
                logged++;
                MibrOemSsmTemplate.diag("MIBR_SCROLL_INDICATOR_UPDATE min=" + min + " max=" + max
                        + " value=" + value + " block=" + adjustable.getBlockIncrement()
                        + " listH=" + view + " items=" + list.get_itemCount());
            }
            int x = parent.get_width() - RIGHT_MARGIN - BAR_WIDTH;
            int y = list.get_y();
            track.set_x(x + (BAR_WIDTH - TRACK_WIDTH) / 2);
            track.set_y(y);
            track.set_width(TRACK_WIDTH);
            track.set_height(view);
            if (span <= 0 || view <= 0) {
                track.set_visible(false);
                thumb.set_visible(false);
                track.repaint();
                return;
            }
            int total = span + view;
            int thumbHeight = Math.max(MIN_THUMB, (int)((long)view * view / total));
            if (thumbHeight > view) thumbHeight = view;
            int offset = value - min;
            if (offset < 0) offset = 0;
            if (offset > span) offset = span;
            int thumbY = y + (int)((long)(view - thumbHeight) * offset / span);
            thumb.set_x(x);
            thumb.set_y(thumbY);
            thumb.set_width(BAR_WIDTH);
            thumb.set_height(thumbHeight);
            track.set_visible(true);
            thumb.set_visible(true);
            track.repaint();
            thumb.repaint();
        } catch (Throwable failure) {
            MibrOemSsmTemplate.diag("MIBR_SCROLL_INDICATOR_UPDATE_FAILED " + failure);
        }
    }

    void detach() {
        if(detached)return;
        detached=true;
        ((Adjustable)list).removeAdjustmentListener(this);
        WidgetModel[] old=parent.getChildren();int count=0;
        for(int i=0;old!=null && i<old.length;i++)if(old[i]!=track && old[i]!=thumb)count++;
        WidgetModel[] next=new WidgetModel[count];count=0;
        for(int i=0;old!=null && i<old.length;i++)if(old[i]!=track && old[i]!=thumb)next[count++]=old[i];
        parent.setChildren(next);
        if(track.is_activated())track.deActivate();
        if(thumb.is_activated())thumb.deActivate();
        track.deInit();thumb.deInit();
        MibrOemSsmTemplate.diag("MIBR_SCROLL_INDICATOR_DETACHED");
    }
}
