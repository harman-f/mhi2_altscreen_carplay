package de.mibr.hmi;

import de.vw.mib.view.internal.AbstractViewHandler;
import de.vw.mib.view.internal.AnimationAdapters;
import de.vw.mib.view.internal.CloneData;
import de.vw.mib.view.internal.WidgetAnimator;
import de.vw.mib.widgets.models.WidgetModel;
import java.lang.reflect.Field;

/**
 * Pass-through for the stock Sgm AnimationAdapters. Every call reaches the
 * original adapter unchanged; tile tracks are additionally mirrored onto the
 * owned CP tile, which is in no Sgm clone chain and was therefore static.
 *
 * Foreign transitions: mirrored value per property = median of Tuner, Sound
 * and Settings. A transition moves at most one tile type forward, so the
 * median is the receding OEM choreography. Own transition (CP tile tapped,
 * page Ssm_5458 = SMI_SETUP_MAIN): mirror the SmartPhoneIntegration tile,
 * the stock tile of that page, so ours follows the OEM forward track.
 */
final class MibrHomeAnimationMirror extends AnimationAdapters {
    static interface Targets { WidgetModel[] ownedTiles(); }

    private static final int LISTITEM = 27;
    private static final int[] WHATS = {5, 1, 9, 16};
    /** cd0 root indices in Sgm.assignCloneMasters: Tuner, Sound, Settings, SmartPhoneIntegration. */
    private static final int[] DONORS = {5, 18, 22, 13};
    private static final int OWN = 3;
    private static final long SETTLE_MS = 1500L;
    /** Own leave/return window: from the tap until the HOME return has settled. */
    private static long ownUntil;

    static synchronized void ownTransitionStarted() { ownUntil = Long.MAX_VALUE; }
    static synchronized void ownTransitionEnded() {
        ownUntil = System.currentTimeMillis() + SETTLE_MS;
    }
    private static synchronized boolean ownTransition() {
        return System.currentTimeMillis() < ownUntil;
    }
    /** 18 tile types x 4 ListItem rows plus one view-level row. */
    private static final int TABLE_ROWS = 73;

    private final AnimationAdapters stock;
    private final WidgetAnimator animator;
    private final Targets targets;
    /** accessId -> [donor slot, what slot]; -1 if not a donor row. */
    private final int[] ids;
    private final int[][] slot;
    private final int[][] intValue = new int[DONORS.length][WHATS.length];
    private final float[][] floatValue = new float[DONORS.length][WHATS.length];
    private final boolean[][] intSeen = new boolean[DONORS.length][WHATS.length];
    private final boolean[][] floatSeen = new boolean[DONORS.length][WHATS.length];

    private MibrHomeAnimationMirror(AnimationAdapters stock, WidgetAnimator animator,
            int[] ids, int[][] slot, Targets targets) {
        super(new int[0][], new CloneData(1, CloneData.ROOT_MASTER_ID), animator);
        this.stock = stock; this.animator = animator; this.ids = ids; this.slot = slot;
        this.targets = targets;
    }

    private static Field field(Class owner, String name, Class type) throws Exception {
        Field field = owner.getDeclaredField(name);
        if (field.getType() != type) throw new IllegalStateException("MIBR_ANIM_DESCRIPTOR " + name);
        field.setAccessible(true);
        return field;
    }

    /** Returns the installed mirror, or null when the stock table is not the exact Sgm one. */
    static MibrHomeAnimationMirror install(AbstractViewHandler sgm, Targets targets) throws Exception {
        Field adapters = field(AbstractViewHandler.class, "animationAdapters", AnimationAdapters.class);
        Object current = adapters.get(sgm);
        if (current == null || current.getClass() != AnimationAdapters.class) return null;
        MibrHomeAnimationMirror mirror = wrap((AnimationAdapters) current, targets);
        if (mirror != null) adapters.set(sgm, mirror);
        return mirror;
    }

    /** Validates the exact Sgm table; null when it differs. */
    static MibrHomeAnimationMirror wrap(AnimationAdapters stock, Targets targets) throws Exception {
        if (stock == null || stock.getClass() != AnimationAdapters.class) return null;
        int[][] data = (int[][]) field(AnimationAdapters.class, "data", int[][].class).get(stock);
        WidgetAnimator animator = (WidgetAnimator)
            field(AnimationAdapters.class, "widgetAnimator", WidgetAnimator.class).get(stock);
        if (data == null || animator == null || data.length != TABLE_ROWS) return null;
        int[] ids = new int[DONORS.length * WHATS.length];
        int[][] slot = new int[ids.length][];
        int found = 0;
        for (int r = 0; r < data.length; r++) {
            int[] row = data[r];
            if (row.length != 5) return null;
            int d = indexOf(DONORS, row[1]), w = indexOf(WHATS, row[4]);
            if (d < 0) continue;
            if (w < 0 || row[2] != 0 || row[3] != LISTITEM) return null;
            ids[found] = row[0]; slot[found] = new int[] {d, w}; found++;
        }
        if (found != ids.length) return null;
        return new MibrHomeAnimationMirror(stock, animator, ids, slot, targets);
    }

    /** Puts the original adapter back if this mirror is still installed. */
    void restore(AbstractViewHandler sgm) throws Exception {
        Field adapters = field(AbstractViewHandler.class, "animationAdapters", AnimationAdapters.class);
        if (adapters.get(sgm) == this) adapters.set(sgm, stock);
    }

    private static int indexOf(int[] values, int value) {
        for (int i = 0; i < values.length; i++) if (values[i] == value) return i;
        return -1;
    }

    private int[] slotOf(int accessId) {
        for (int i = 0; i < ids.length; i++) if (ids[i] == accessId) return slot[i];
        return null;
    }

    private static int median(int a, int b, int c) {
        return Math.max(Math.min(a, b), Math.min(Math.max(a, b), c));
    }

    private static float median(float a, float b, float c) {
        return Math.max(Math.min(a, b), Math.min(Math.max(a, b), c));
    }

    public boolean getAnimBooleanValue(int id, int index) { return stock.getAnimBooleanValue(id, index); }
    public void setAnimBooleanValue(int id, int index, boolean value) { stock.setAnimBooleanValue(id, index, value); }
    public int getAnimIntValue(int id, int index) { return stock.getAnimIntValue(id, index); }
    public float getAnimFloatValue(int id, int index) { return stock.getAnimFloatValue(id, index); }

    public void setAnimIntValue(int id, int index, int value) {
        stock.setAnimIntValue(id, index, value);
        try {
            int[] s = slotOf(id);
            if (s == null) return;
            intValue[s[0]][s[1]] = value; intSeen[s[0]][s[1]] = true;
            int w = s[1];
            if (ownTransition()) { if (s[0] == OWN) apply(w, value, 0f, true); return; }
            if (s[0] == OWN || !intSeen[0][w] || !intSeen[1][w] || !intSeen[2][w]) return;
            apply(w, median(intValue[0][w], intValue[1][w], intValue[2][w]), 0f, true);
        } catch (Throwable failure) { System.err.println("MIBR_ANIM_MIRROR_FAILED " + failure); }
    }

    public void setAnimFloatValue(int id, int index, float value) {
        stock.setAnimFloatValue(id, index, value);
        try {
            int[] s = slotOf(id);
            if (s == null) return;
            floatValue[s[0]][s[1]] = value; floatSeen[s[0]][s[1]] = true;
            int w = s[1];
            if (ownTransition()) { if (s[0] == OWN) apply(w, 0, value, false); return; }
            if (s[0] == OWN || !floatSeen[0][w] || !floatSeen[1][w] || !floatSeen[2][w]) return;
            apply(w, 0, median(floatValue[0][w], floatValue[1][w], floatValue[2][w]), false);
        } catch (Throwable failure) { System.err.println("MIBR_ANIM_MIRROR_FAILED " + failure); }
    }

    private void apply(int w, int intV, float floatV, boolean isInt) {
        WidgetModel[] tiles = targets.ownedTiles();
        for (int i = 0; tiles != null && i < tiles.length; i++) {
            if (tiles[i] == null) continue;
            if (isInt) animator.setAnimatableIntValue(tiles[i], LISTITEM, WHATS[w], intV);
            else animator.setAnimatableFloatValue(tiles[i], LISTITEM, WHATS[w], floatV);
        }
    }
}