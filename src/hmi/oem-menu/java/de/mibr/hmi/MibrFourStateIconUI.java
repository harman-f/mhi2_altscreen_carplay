/* SPDX-License-Identifier: MIT
 * Async external-PNG renderer scoped to MIBR-owned tile images only.
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
 * Loads the exact sidecar files. Press state and day/night are read from the
 * native model at paint time. The current art and its press counterpart are
 * kept loaded, so the green-bar art appears immediately on touch instead of
 * after an asynchronous reload (which a short tap never outlasted).
 */
public final class MibrFourStateIconUI extends CommonImageUI {
    private static final int SLOTS = 4;
    private final Slot[] slots = new Slot[SLOTS];
    private long nextToken;

    private static final class Slot {
        final String path;
        Request request;
        BufferImage image;
        ImageDrawable drawable;
        boolean failed;
        /** Retry bookkeeping: a boot-time load error must not blank the art for good. */
        int failures;
        long failedAt;
        long requestedAt;
        /** r51: when the decoded image arrived; art younger than SETTLE_MS is not drawn (unfinished texture = white/pink tile). */
        long decodedAt;
        Slot(String path) { this.path = path; }
    }

    /** A failed load/draw is retried at most this often (owner 2026-10-20: white pressed art after a reboot). */
    private static final int MAX_FAILURES = 6;
    private static final long RETRY_MS = 1500L;
    /** r45: after MAX_FAILURES keep trying slowly (a boot-time failure must never blank the art for good). */
    private static final long SLOW_RETRY_MS = 10000L;
    /** r45: a request that neither delivers nor fails for this long is cancelled and counted as a failure. */
    private static final long HANG_MS = 4000L;
    private boolean repaintScheduled;
    /** r51: a freshly decoded image is drawn only after this long; until then the counterpart (normal art) stays. */
    private static final long SETTLE_MS = 400L;
    /** r51: failed slots are not retried before this long after start: the menu is still being assembled then. */
    private static final long STARTUP_QUIET_MS = 20000L;
    private static final long LOADED_AT = System.currentTimeMillis();

    /** A failed or pending slot only gets another chance when something repaints the tile: do it ourselves. */
    private void scheduleRepaint(final long delayMs) {
        synchronized (this) {
            if (repaintScheduled) return;
            repaintScheduled = true;
        }
        long quiet = LOADED_AT + STARTUP_QUIET_MS - System.currentTimeMillis();
        final long sleepMs = delayMs > quiet ? delayMs : quiet;
        Thread t = new Thread(new Runnable() {
            public void run() {
                try { Thread.sleep(sleepMs); } catch (InterruptedException ignored) { }
                synchronized (MibrFourStateIconUI.this) { repaintScheduled = false; }
                try {
                    WidgetModel widget = getWidget();
                    if (widget != null) widget.repaint();
                } catch (Throwable ignored) { }
            }
        }, "MibrIconRetry");
        t.setDaemon(true);
        t.start();
    }

    private void markFailed(Slot slot) {
        slot.failed = true;
        slot.failures++;
        slot.failedAt = System.currentTimeMillis();
        scheduleRepaint(slot.failures >= MAX_FAILURES ? SLOW_RETRY_MS : RETRY_MS);
    }

    public void paintImage(Graphics3D graphics, ViewModel view, WidgetModel widget,
            Rectangle source, Rectangle destination, Color4b tint, float alpha) {
        if (!(widget instanceof CommonImageModel)) return;
        String wanted = ((CommonImageModel)widget).get_imageFile();
        if (wanted == null || wanted.length() == 0) return;
        String other = MibrIconState.counterpart(wanted);
        Slot slot = ensure(wanted, other);
        Slot fallback = other == null ? null : ensure(other, wanted);
        // Until the wanted art is decoded keep showing its counterpart, never a blank tile.
        if (!settled(slot) || !draw(graphics, widget, slot, alpha)) draw(graphics, widget, fallback, alpha);
    }

    /** True when the slot's art has been decoded for SETTLE_MS (or has no image yet: draw() then returns false). */
    private boolean settled(Slot slot) {
        if (slot == null || slot.image == null) return true;
        long age = System.currentTimeMillis() - slot.decodedAt;
        if (age >= SETTLE_MS) return true;
        scheduleRepaint(SETTLE_MS - age + 20L);
        return false;
    }

    private boolean draw(Graphics3D graphics, WidgetModel widget, Slot slot, float alpha) {
        if (slot == null || slot.image == null || slot.failed) return false;
        if (slot.drawable == null && !createDrawable(graphics, widget, slot)) {
            markFailed(slot);
            return false;
        }
        try {
            slot.drawable.setAlpha(alpha);
            slot.drawable.draw();
            return true;
        } catch (Throwable ignored) {
            releaseDrawable(slot);
            markFailed(slot);
            return false;
        }
    }

    /** Returns the slot for {@code path}, requesting it once; may evict slots other than keep. */
    private Slot ensure(String path, String keep) {
        int free = -1;
        int failures = 0;
        for (int i = 0; i < SLOTS; i++) {
            if (slots[i] != null && slots[i].path.equals(path)) {
                Slot existing = slots[i];
                long now = System.currentTimeMillis();
                if (!existing.failed && existing.request != null && now - existing.requestedAt >= HANG_MS) {
                    markFailed(existing);   /* hung request: no image, no error */
                }
                if (!existing.failed) {
                    if (existing.request != null) scheduleRepaint(HANG_MS);
                    return existing;
                }
                long wait = existing.failures >= MAX_FAILURES ? SLOW_RETRY_MS : RETRY_MS;
                if (now - existing.failedAt < wait || now < LOADED_AT + STARTUP_QUIET_MS) return existing;
                // Bounded retry of a failed slot, keeping the failure count.
                failures = existing.failures;
                release(existing);
                slots[i] = null;
                free = i;
                break;
            }
            if (slots[i] == null && free < 0) free = i;
        }
        if (free < 0) {
            for (int i = 0; i < SLOTS && free < 0; i++) {
                if (!slots[i].path.equals(keep)) { release(slots[i]); slots[i] = null; free = i; }
            }
        }
        Slot slot = new Slot(path);
        slot.failures = failures;
        slots[free] = slot;
        Request request = new Request(path, ++nextToken);
        slot.request = request;
        slot.requestedAt = System.currentTimeMillis();
        try {
            ServiceManager.imageManager.getImageFromResource(
                    new ResourceLocator(path), request, false);
        } catch (Throwable ignored) {
            slot.request = null;
            markFailed(slot);
        }
        return slot;
    }

    private Slot owner(Request request) {
        for (int i = 0; i < SLOTS; i++) {
            if (slots[i] != null && slots[i].request == request) return slots[i];
        }
        return null;
    }

    private boolean createDrawable(Graphics3D graphics, WidgetModel widget, Slot slot) {
        int originalWidth = slot.image.getWidth();
        int originalHeight = slot.image.getHeight();
        int width = widget.get_width();
        int height = widget.get_height();
        if (originalWidth <= 0 || originalHeight <= 0 || width <= 0 || height <= 0) {
            return false;
        }
        float fit = Math.min((float)width / (float)originalWidth,
                (float)height / (float)originalHeight);
        int drawWidth = (int)(fit * (float)originalWidth);
        int drawHeight = (int)(fit * (float)originalHeight);
        try {
            ImageDrawable next = graphics.getDrawableManager().createImageDrawable();
            next.setImage(slot.image);
            next.setSourceWidth(originalWidth);
            next.setSourceHeight(originalHeight);
            next.setDestinationWidth(drawWidth);
            next.setDestinationHeight(drawHeight);
            next.setDestinationX((width - drawWidth) / 2);
            next.setDestinationY((height - drawHeight) / 2);
            slot.drawable = next;
            return true;
        } catch (Throwable ignored) {
            releaseDrawable(slot);
            return false;
        }
    }

    private void release(Slot slot) {
        Request request = slot.request;
        slot.request = null;
        if (request != null) {
            try {
                ServiceManager.imageManager.cancelGetImageFromResource(
                        new ResourceLocator(request.path), request);
            } catch (Throwable ignored) {
            }
        }
        releaseDrawable(slot);
        if (slot.image != null) {
            try { slot.image.dispose(); } catch (Throwable ignored) { }
            slot.image = null;
        }
    }

    private static void releaseDrawable(Slot slot) {
        if (slot.drawable != null) {
            try { slot.drawable.dispose(); } catch (Throwable ignored) { }
            slot.drawable = null;
        }
    }

    private void imageAvailable(Request request, ResourceLocator source, BufferImage value) {
        Slot slot = owner(request);
        if (value == null) {
            imageError(request);
            return;
        }
        if (slot == null || source == null || !request.path.equals(source.getUrl())) {
            value.dispose();
            return;
        }
        slot.request = null;
        releaseDrawable(slot);
        if (slot.image != null) slot.image.dispose();
        slot.image = value;
        slot.decodedAt = System.currentTimeMillis();
        try {
            WidgetModel widget = getWidget();
            if (widget != null) widget.repaint();
        } catch (Throwable ignored) {
        }
    }

    private void imageError(Request request) {
        Slot slot = owner(request);
        if (slot != null) {
            slot.request = null;
            markFailed(slot); // bounded retry (MAX_FAILURES), then give up: no endless loop
        }
    }

    public void deInit() {
        for (int i = 0; i < SLOTS; i++) {
            if (slots[i] != null) { release(slots[i]); slots[i] = null; }
        }
        super.deInit();
    }

    private final class Request implements ImageLoadingListener {
        private final String path;
        private final long token;

        Request(String path, long token) {
            this.path = path;
            this.token = token;
        }

        public void imageAvailable(ResourceLocator source, BufferImage value) {
            MibrFourStateIconUI.this.imageAvailable(this, source, value);
        }

        public void imageError(ResourceLocator source, Exception error) {
            MibrFourStateIconUI.this.imageError(this);
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
