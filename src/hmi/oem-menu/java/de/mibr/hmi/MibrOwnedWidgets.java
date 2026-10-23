package de.mibr.hmi;

import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.models.AbstractButtonModel;
import de.vw.mib.widgets.TextArea;
import de.vw.mib.widgets.controller.DefaultPushButtonController;
import de.vw.mib.widgets.models.TextAreaModel;
import de.vw.mib.widgets.models.ViewModel;
import de.vw.mib.widgets.models.WidgetModel;
import de.vw.mib.widgets.ui.ButtonUI;
import de.vw.mib.widgets.ui.TextAreaUI;
import de.vw.mib.graphics.Color;
import de.vw.mib.graphics.Gradient;
import de.vw.mib.graphics.image.Image;
import de.vw.mib.graphics.Insets;
import de.vw.mib.animation.easing.EasingParams;

/**
 * Small constructors for widgets owned by the MU1440 HOME tile and page.
 */
public final class MibrOwnedWidgets {
    public interface ActionSink {
        public void onReleased();
    }

    public static final class ActionButtonController extends DefaultPushButtonController {
        private final ActionSink sink;

        public ActionButtonController(ActionSink sink) {
            super();
            this.sink = sink;
        }

        public void fire_released() {
            super.fire_released();
            if (this.sink != null) {
                this.sink.onReleased();
            }
        }
    }

    /**
     * Stock Button that reports every native press-state change (the icon art follows pressed).
     * A short tap releases before the pressed art is painted; OEM tiles still show their bar
     * because the button image crossfades back. Keep the pressed art for RELEASE_HOLD_MS.
     */
    public static final class TouchButton extends Button {
        static final long RELEASE_HOLD_MS = 500L;
        private Runnable stateListener;
        private long holdUntil;
        private de.vw.mib.timer.Timer holdTimer;

        void setStateListener(Runnable listener) {
            this.stateListener = listener;
        }

        /** Pressed, or released less than RELEASE_HOLD_MS ago. */
        public boolean showsPressed() {
            return isPressed() || System.currentTimeMillis() < holdUntil;
        }

        protected void pressedChanged(boolean previous) {
            super.pressedChanged(previous);
            if (previous && !isPressed()) {
                holdUntil = System.currentTimeMillis() + RELEASE_HOLD_MS;
                armHoldEnd();
            }
            notifyState();
        }

        private void notifyState() {
            Runnable listener = this.stateListener;
            if (listener != null) {
                try { listener.run(); } catch (Throwable ignored) { }
            }
        }

        private void armHoldEnd() {
            try {
                if (holdTimer == null) {
                    holdTimer = de.vw.mib.widgets.internal.ServiceManager.timerManager.createTimer(
                        "MibrTileReleaseHold", RELEASE_HOLD_MS, false,
                        new Runnable() { public void run() { notifyState(); } },
                        de.vw.mib.widgets.internal.ServiceManager.eventDispatcher);
                }
                holdTimer.stop();
                holdTimer.start();
            } catch (Throwable failure) {
                holdUntil = 0L;
            }
        }
    }

    private MibrOwnedWidgets() {
    }

    public static Button createTouchButton(ViewModel viewModel, ActionSink sink,
            String name, int targetId, int x, int y, int width, int height) {
        Button button = new TouchButton();

        button.init(false, 255, true, null, true, height, true,
                name, targetId, null, true, width, x, y);
        button.set_interactive(true);
        button.setController(new ActionButtonController(sink));
        button.setUI(new ButtonUI());
        if (viewModel != null) button.init(viewModel);

        return button;
    }

    public static TextArea createLabel(ViewModel viewModel, TextAreaModel donor,
            String text, String name, int targetId, int x, int y, int width, int height) {
        TextArea label = new TextArea();

        label.init(false, 255, true, null, true, height, true,
                name, targetId, null, true, width, x, y);
        label.setUI(new TextAreaUI());

        if (donor != null) {
            label.set_font(donor.get_font());
            label.set_fontStyles(donor.get_fontStyles());
            label.set_colorForeground(donor.get_colorForeground());
            label.set_colorBackground(donor.get_colorBackground());
            label.set_alignmentHorizontal(donor.get_alignmentHorizontal());
            label.set_alignmentVertical(donor.get_alignmentVertical());
            label.set_lineSpacing(donor.get_lineSpacing());
            label.set_padding(donor.get_padding());
            label.set_baselineOffset(donor.get_baselineOffset());
            label.set_textStylingEnabled(donor.is_textStylingEnabled());
            label.set_lineBreakMode(donor.get_lineBreakMode());
            label.set_shorten(donor.is_shorten());
        }

        label.set_text(text);
        if (viewModel != null) label.init(viewModel);

        return label;
    }

    public static MibrOwnedIconImage createFourStateIcon(ViewModel viewModel,
            AbstractButtonModel stateButton, String name, int targetId,
            int x, int y, int width, int height) {
        Button button = stateButton instanceof Button ? (Button)stateButton : null;
        MibrOwnedIconImage image = new MibrOwnedIconImage(button);
        Color transparent = new Color(0);
        image.init(true, 255, true, transparent, 0, transparent, false,
                new EasingParams[0], true, transparent, 0, false,
                new Gradient(), new Color[0], height, new Image(), true,
                name, targetId, new Insets(), true, width, x, y);
        image.setUI(new MibrFourStateIconUI());
        if (viewModel != null) image.init(viewModel);
        return image;
    }

    public static WidgetModel[] appendTwo(WidgetModel[] stock, WidgetModel first, WidgetModel second) {
        int stockLength = stock == null ? 0 : stock.length;
        WidgetModel[] result = new WidgetModel[stockLength + 2];

        if (stockLength > 0) {
            System.arraycopy(stock, 0, result, 0, stockLength);
        }

        result[stockLength] = first;
        result[stockLength + 1] = second;
        return result;
    }
}