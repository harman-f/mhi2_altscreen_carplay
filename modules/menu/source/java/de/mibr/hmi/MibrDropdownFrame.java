package de.mibr.hmi;

/** Dropdown popup frame arithmetic (host-testable, Java 1.2 compatible). */
final class MibrDropdownFrame {
    private MibrDropdownFrame() {}

    /** Frame padding around the option list. A measured value >=0 is used as is;
     *  otherwise (closed popup smaller than the hidden list) the popup insets are used. */
    static int chrome(int measuredChrome, boolean haveInsets, int insetTop, int insetBottom) {
        if (measuredChrome >= 0) return measuredChrome;
        if (haveInsets && insetTop >= 0 && insetBottom >= 0) {
            int sum = insetTop + insetBottom;
            if (sum >= 0) return sum;
        }
        throw new IllegalStateException("MIBR_SSM_OPTION_VIEW_BOUNDS chrome");
    }

    /** Number of visible option rows that fit into the view. */
    static int rows(int viewHeight, int rowHeight, int count, int chrome) {
        int available = viewHeight - 24 - chrome;
        if (rowHeight <= 0 || count <= 0 || chrome < 0 || available < rowHeight)
            throw new IllegalStateException("MIBR_SSM_OPTION_VIEW_BOUNDS rows");
        return Math.min(count, available / rowHeight);
    }
}
