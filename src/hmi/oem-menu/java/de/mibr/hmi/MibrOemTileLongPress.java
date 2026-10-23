package de.mibr.hmi;

import de.vw.mib.view.internal.AbstractViewHandler;
import de.vw.mib.view.internal.CloneData;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.ListItem;
import de.vw.mib.widgets.controller.AbstractWidgetController;
import de.vw.mib.widgets.controller.DefaultPushButtonController;
import de.vw.mib.widgets.event.OutEventListener;
import de.vw.mib.widgets.models.WidgetModel;
import java.lang.reflect.Field;
import java.util.Vector;

/**
 * Long press on the stock SmartPhoneIntegration HOME tile (SmartLink, CarPlay,
 * Android Auto, MirrorLink, CarLife: one tile, Sgm only swaps icon and text)
 * opens the owned CarPlay settings page.
 *
 * The stock tile button runs in buttonMode 0 (fires on release only). In
 * buttonMode 2 DefaultPushButtonController starts a startTimePrimary timer on
 * press and fires "longPressed"; the release after a long press fires
 * "longReleased" instead of "released", so Sgm's buttonReleased mapping (open
 * CarPlay/AA) is not triggered. A short tap is unchanged. Only clones that
 * match the exact Sgm layout are touched; every change is restored on detach.
 */
final class MibrOemTileLongPress {
    static final int LONG_PRESS_MS = 800;
    private static final String MASTER_FIELD = "gridMenuPlateWidgetListListItemSmartPhoneIntegrationCloneMaster";
    private static final String ITEM_NAME = "ListItemSmartPhoneIntegration";
    private static final String BUTTON_NAME = "ButtonSmartPhoneIntegration";
    private static final int STOCK_MODE = 0;
    private static final int LONG_MODE = 2;

    private final Field master;
    private final AbstractViewHandler sgm;
    private final Runnable action;
    private final Vector hooks = new Vector();

    private MibrOemTileLongPress(AbstractViewHandler sgm, Field master, Runnable action) {
        this.sgm = sgm; this.master = master; this.action = action;
    }

    /** Null when the handler is not the exact Sgm with the SmartPhoneIntegration clone master. */
    static MibrOemTileLongPress install(AbstractViewHandler sgm, Runnable action) throws Exception {
        if (sgm == null || action == null) return null;
        Field field;
        try { field = sgm.getClass().getDeclaredField(MASTER_FIELD); }
        catch (NoSuchFieldException absent) { return null; }
        if (field.getType() != CloneData.class) return null;
        field.setAccessible(true);
        MibrOemTileLongPress press = new MibrOemTileLongPress(sgm, field, action);
        press.refresh();
        return press;
    }

    /** Hooks every matching clone not yet hooked; re-arms clones Sgm re-initialised. */
    int refresh() throws Exception {
        int armed = 0;
        for (CloneData cd = (CloneData) master.get(sgm); cd != null; cd = cd.next) {
            Button button = tileButton(cd);
            if (button == null) continue;
            Hook hook = find(button);
            if (hook == null) {
                if (button.get_buttonMode() != STOCK_MODE) continue;
                hook = new Hook(button);
                if (hook.controller == null) continue;
                hooks.addElement(hook);
                hook.controller.addOutEventListener(hook);
            }
            if (button.get_buttonMode() != LONG_MODE || button.get_startTimePrimary() != LONG_PRESS_MS) {
                button.set_buttonMode(LONG_MODE);
                button.set_startTimePrimary(LONG_PRESS_MS);
                button.setTimerChanged(true);
            }
            armed++;
        }
        return armed;
    }

    /** Puts every hooked tile back into its stock state. */
    void restore() {
        for (int i = 0; i < hooks.size(); i++) {
            Hook hook = (Hook) hooks.elementAt(i);
            try {
                hook.controller.removeOutEventListener(hook);
                hook.button.set_buttonMode(hook.oldMode);
                hook.button.set_startTimePrimary(hook.oldStart);
                hook.button.setTimerChanged(true);
            } catch (Throwable failure) {
                System.err.println("MIBR_OEM_LONGPRESS_RESTORE_FAILED " + failure);
            }
        }
        hooks.removeAllElements();
    }

    private static Button tileButton(CloneData cd) {
        WidgetModel[] w = cd.widgets;
        if (w == null || w.length < 2) return null;
        if (!(w[0] instanceof ListItem) || !ITEM_NAME.equals(((ListItem) w[0]).get_name())) return null;
        if (!(w[1] instanceof Button) || !BUTTON_NAME.equals(((Button) w[1]).get_name())) return null;
        return (Button) w[1];
    }

    private Hook find(Button button) {
        for (int i = 0; i < hooks.size(); i++) {
            Hook hook = (Hook) hooks.elementAt(i);
            if (hook.button == button) return hook;
        }
        return null;
    }

    private final class Hook implements OutEventListener {
        final Button button;
        final int oldMode, oldStart;
        final AbstractWidgetController controller;

        Hook(Button button) {
            this.button = button;
            this.oldMode = button.get_buttonMode();
            this.oldStart = button.get_startTimePrimary();
            Object c = button.getController();
            this.controller = c instanceof DefaultPushButtonController ? (AbstractWidgetController) c : null;
        }

        public void outHMIEventFired(String event) {
            if (!"longPressed".equals(event)) return;
            try { action.run(); }
            catch (Throwable failure) { System.err.println("MIBR_OEM_LONGPRESS_ACTION_FAILED " + failure); }
        }
        public void outIntegerEventFired(String e, int v) {}
        public void outBooleanEventFired(String e, boolean v) {}
        public void outStringEventFired(String e, String v) {}
        public void outPointEventFired(String e, int a, int b, int c, int d) {}
        public void outListItemEventFired(String e, int a, int b, int c, int d, String s, long l) {}
        public void outSpellerEventFired(String e, String s, int a, int b, int c) {}
    }
}