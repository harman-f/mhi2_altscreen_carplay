package de.mibr.hmi;

/** The REAL request builder must accept every verb the session sends (host fakes bypass it). */
public final class MibrV3VerbTest {
    static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }
    public static void main(String[] args) {
        String secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        String[] none = new String[0];
        String[] verbs = {"HELLO", "CAPABILITIES", "STATUS", "SNAPSHOT", "REQUEST_STATUS", "ACTION", "ACTION_STATUS", "SHOW_STATUS"};
        for (int i = 0; i < verbs.length; i++)
            check(MibrV3Protocol.request("r" + i, verbs[i], none, none, secret).startsWith("MIBR/3 r" + i + " " + verbs[i] + " auth="), verbs[i]);
        boolean rejected = false;
        try { MibrV3Protocol.request("r9", "NOT_A_VERB", none, none, secret); } catch (IllegalArgumentException e) { rejected = true; }
        check(rejected, "unknown verbs stay rejected");
        System.out.println("MIBR_V3_VERB_ALLOWLIST_HOST_PASS");
    }
}
