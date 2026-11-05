package de.mibr.hmi;

/** Standalone host test: no OEM runtime, car, socket or original framework. */
public final class PublicProtocolSmokeTest {
    private static void check(boolean value, String why) {
        if (!value) throw new AssertionError(why);
    }
    public static void main(String[] args) {
        check(MibrSettingsCatalog.KEYS.length == 48, "display registry projection");
        check(MibrMenuDefinition.NATIVE_UI_KEYS.length == 11, "UI projection");
        check(MibrV3Protocol.id("public_1"), "request id");
        check(!MibrV3Protocol.id("not.valid"), "bad id");
        check(MibrV3Protocol.revision("42"), "revision");
        check(!MibrV3Protocol.revision("0"), "zero revision");
        check("%C3%9C%20%26".equals(MibrV3Protocol.encode("Ü &")), "canonical UTF-8");
        check(MibrV3Protocol.known("navigation.ETA"), "known UI key");
        check(!MibrV3Protocol.known("not.a.setting"), "unknown UI key");
        MibrI18n.forced = "de_DE";
        check("CarPlay-Einstellungen".equals(MibrMenuDefinition.title()), "German UI title");
        MibrI18n.forced = "en_US";
        check("CarPlay settings".equals(MibrMenuDefinition.title()), "English fallback");
        System.out.println("MIBR_V3_PUBLIC_JAVA_PROTOCOL_MODEL_HOST_PASS");
    }
}
