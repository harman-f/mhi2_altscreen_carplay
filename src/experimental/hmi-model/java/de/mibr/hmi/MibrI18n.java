package de.mibr.hmi;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * Menu language: the HMI language reported by the ConfigurationManager
 * (current.gui.language, e.g. "de_DE"). German selects German; any other
 * language, an empty or unreadable value selects English. Evaluated per
 * lookup, so a page shows a changed language the next time it is built.
 * The service is reached by reflection so this class has no compile-time
 * dependency. Where no HMI service class exists at all, the language is
 * also unreadable and falls back to English;
 * host tests that check German texts set {@link #forced}.
 */
final class MibrI18n {
    private MibrI18n() {}

    /** Test seam: null = read the unit, otherwise a forced language tag. */
    static String forced;

    static boolean german() {
        String tag = forced;
        if (tag == null) {
            Object manager;
            try {
                Class sm = Class.forName("de.vw.mib.desktop.internal.common.ServiceManager");
                Field f = sm.getField("configurationManager");
                manager = f.get(null);
            } catch (Throwable absent) { return false; }
            try {
                Class api = Class.forName("de.vw.mib.configuration.ConfigurationManager");
                Method m = api.getMethod("getCurrentGuiLanguage", new Class[0]);
                tag = (String) m.invoke(manager, new Object[0]);
            } catch (Throwable unreadable) { tag = null; }
        }
        return tag != null && tag.toLowerCase().startsWith("de");
    }

    static String pick(String de, String en) { return german() ? de : en; }
}
