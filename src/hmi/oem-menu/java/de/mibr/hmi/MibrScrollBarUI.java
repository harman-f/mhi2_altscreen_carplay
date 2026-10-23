/* SPDX-License-Identifier: MIT
 * Stretches one external PNG over the widget rectangle (scroll indicator).
 */
package de.mibr.hmi;

import de.vw.mib.graphics.Color4b;
import de.vw.mib.graphics.Graphics3D;
import de.vw.mib.graphics.Rectangle;
import de.vw.mib.graphics.drawable.image.ImageDrawable;
import de.vw.mib.graphics.image.BufferImage;
import de.vw.mib.graphics.image.ExifInfo;
import de.vw.mib.graphics.image.ImageInfo;
import de.vw.mib.graphics.image.ImageLoadingListener;
import de.vw.mib.widgets.internal.ServiceManager;
import de.vw.mib.widgets.models.CommonImageModel;
import de.vw.mib.widgets.models.ViewModel;
import de.vw.mib.widgets.models.WidgetModel;
import de.vw.mib.widgets.ui.CommonImageUI;
import org.dsi.ifc.global.ResourceLocator;

/**
 * One PNG, decoded once, drawn stretched to the CURRENT widget size on every paint,
 * so the thumb can change height without recreating anything. A failed load is
 * retried a bounded number of times, then the bar simply stays invisible.
 */
public final class MibrScrollBarUI extends CommonImageUI {
    private static final int MAX_FAILURES = 6;
    private static final long RETRY_MS = 1500L;
    private String path;
    private BufferImage image;
    private ImageDrawable drawable;
    private boolean pending;
    private int failures;
    private long failedAt;

    public void paintImage(Graphics3D graphics, ViewModel view, WidgetModel widget,
            Rectangle source, Rectangle destination, Color4b tint, float alpha) {
        if (!(widget instanceof CommonImageModel)) return;
        String wanted = ((CommonImageModel)widget).get_imageFile();
        if (wanted == null || wanted.length() == 0) return;
        if (path == null || !path.equals(wanted)) {
            release();
            path = wanted;
            failures = 0;
        }
        if (image == null) {
            request();
            return;
        }
        int width = widget.get_width();
        int height = widget.get_height();
        if (width <= 0 || height <= 0) return;
        try {
            if (drawable == null) {
                drawable = graphics.getDrawableManager().createImageDrawable();
                drawable.setImage(image);
                drawable.setSourceWidth(image.getWidth());
                drawable.setSourceHeight(image.getHeight());
            }
            drawable.setDestinationWidth(width);
            drawable.setDestinationHeight(height);
            drawable.setDestinationX(0);
            drawable.setDestinationY(0);
            drawable.setAlpha(alpha);
            drawable.draw();
        } catch (Throwable ignored) {
            releaseDrawable();
        }
    }

    private void request() {
        if (pending) return;
        if (failures > 0 && (failures >= MAX_FAILURES ||
                System.currentTimeMillis() - failedAt < RETRY_MS)) return;
        pending = true;
        try {
            ServiceManager.imageManager.getImageFromResource(
                    new ResourceLocator(path), new Request(), false);
        } catch (Throwable ignored) {
            pending = false;
            failures++;
            failedAt = System.currentTimeMillis();
        }
    }

    private void releaseDrawable() {
        if (drawable != null) {
            try { drawable.dispose(); } catch (Throwable ignored) { }
            drawable = null;
        }
    }

    private void release() {
        releaseDrawable();
        if (image != null) {
            try { image.dispose(); } catch (Throwable ignored) { }
            image = null;
        }
    }

    public void deInit() {
        release();
        super.deInit();
    }

    private void loaded(BufferImage value) {
        pending = false;
        if (value == null) {
            failures++;
            failedAt = System.currentTimeMillis();
            return;
        }
        release();
        image = value;
        try {
            WidgetModel widget = getWidget();
            if (widget != null) widget.repaint();
        } catch (Throwable ignored) {
        }
    }

    private final class Request implements ImageLoadingListener {
        public void imageAvailable(ResourceLocator source, BufferImage value) {
            MibrScrollBarUI.this.loaded(value);
        }

        public void imageError(ResourceLocator source, Exception error) {
            MibrScrollBarUI.this.loaded(null);
        }

        public void imageInfoAvailable(ResourceLocator source, ImageInfo info) { }
        public void imageInfoError(ResourceLocator source, Exception error) { }
        public void exifInfoAvailable(ResourceLocator source, int kind, int[] attributes, ExifInfo info) { }
        public void exifInfoError(ResourceLocator source, int kind, int[] attributes, Exception error) { }
        public void imageLoadingProgress(ResourceLocator source, int percentage) { }

        public void thumbnailImageAvailable(ResourceLocator source, BufferImage value) {
            if (value != null) value.dispose();
        }

        public void thumbnailImageError(ResourceLocator source, Exception error) { }
    }
}