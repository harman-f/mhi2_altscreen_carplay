package de.mibr.hmi;

public final class MibrDropdownFrameTest {
    private static void check(boolean ok, String what) {
        if (!ok) throw new AssertionError(what);
    }

    private static void throwsIse(int kind, String what) {
        try {
            if (kind == 0) MibrDropdownFrame.chrome(-465, false, 0, 0);
            else if (kind == 1) MibrDropdownFrame.chrome(-1, true, Integer.MAX_VALUE, 1);
            else if (kind == 2) MibrDropdownFrame.chrome(-1, true, -1, 3);
            else if (kind == 3) MibrDropdownFrame.rows(60, 56, 3, 6);
            else MibrDropdownFrame.rows(480, 56, 3, -1);
        } catch (IllegalStateException e) {
            check(e.getMessage().startsWith("MIBR_SSM_OPTION_VIEW_BOUNDS"), what + " message");
            return;
        }
        throw new AssertionError(what + " did not throw");
    }

    public static void main(String[] args) {
        // Skoda: measured chrome passes through unchanged, insets ignored.
        check(MibrDropdownFrame.chrome(30, false, 0, 0) == 30, "skoda");
        check(MibrDropdownFrame.chrome(0, true, 3, 3) == 0, "zero");
        check(MibrDropdownFrame.chrome(30, true, 3, 3) == 30, "skoda ignores insets");
        // SEAT: closed popup 334x6, hidden list 334x471.
        check(MibrDropdownFrame.chrome(6 - 471, true, 3, 3) == 6, "seat chrome");
        check(MibrDropdownFrame.rows(480, 56, 3, 6) == 3, "seat rows 3");
        check(MibrDropdownFrame.rows(480, 56, 9, 6) == 8, "seat rows 9");
        throwsIse(0, "no insets");
        throwsIse(1, "overflow");
        throwsIse(2, "negative inset");
        throwsIse(3, "small view");
        throwsIse(4, "negative chrome rows");
        System.out.println("MibrDropdownFrameTest OK");
    }
}
