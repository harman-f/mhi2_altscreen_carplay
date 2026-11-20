/*
 * K3346 Etap 5.2 - parser obiektu PPS /ramdisk/pps/iap2/telephony.
 *
 * Obiekt wypelnia stock sterownik iAP2 (mm-ipod, ppsdir=/ramdisk/pps/iap2)
 * z TelephonyCallStateInformation 0x4155 i TelephonyUpdate 0x4158. Nazwy
 * atrybutow wg /etc/eso/production/dio_manager.json K3346 (sekcja "telephony"):
 * UniqueCallID, CallStatePhoneNumber, CallStateCallerName, CallStateStatus,
 * CallStateDirection, TelephonySignalStrength, TelephonyRegistrationStatus,
 * TelephonyAirplaneModeStatus, MobileOperator.
 * Format PPS: "@obiekt", potem linie "atrybut:kodowanie:wartosc". Wartosci
 * wyliczeniowe moga byc liczba (wartosc iAP2) albo nazwa z dio_manager.json -
 * przyjmujemy obie formy. Nieznany format -> brak rozmowy (nic nie psuje).
 * Java 1.4.
 */
package de.audi.app.combi.bap.app.phone;

final class K3346PpsCall {
    static final K3346PpsCall NONE = new K3346PpsCall();

    private static final String[] STATUS_NAMES = {"Disconnected", "Active", "Holding", "Connecting"};
    private static final String[] DIRECTION_NAMES = {"Incoming", "Outgoing", "Unknown"};
    private static final String[] REGISTRATION_NAMES = {"Unknown", "Not Registered", "Searching", "Denied",
        "Registered Home", "Roaming", "Emergency Calls Only"};

    int status = 0;
    int direction = 2;
    String number = "";
    String name = "";
    String uuid = "";
    int signal = -1;
    int registration = -1;
    boolean airplane = false;
    String operator = "";

    static K3346PpsCall parse(String text) {
        K3346PpsCall c = new K3346PpsCall();
        if (text == null) return c;
        int start = 0;
        while (start < text.length()) {
            int end = text.indexOf('\n', start);
            if (end < 0) end = text.length();
            String line = text.substring(start, end);
            start = end + 1;
            if (line.length() == 0 || line.charAt(0) == '@') continue;
            int c1 = line.indexOf(':');
            if (c1 <= 0) continue;
            int c2 = line.indexOf(':', c1 + 1);
            if (c2 < 0) continue;
            String attr = line.substring(0, c1);
            String value = line.substring(c2 + 1).trim();
            if (attr.equals("CallStateStatus")) c.status = enumValue(value, STATUS_NAMES, 0);
            else if (attr.equals("CallStateDirection")) c.direction = enumValue(value, DIRECTION_NAMES, 2);
            else if (attr.equals("CallStatePhoneNumber")) c.number = value;
            else if (attr.equals("CallStateCallerName")) c.name = value;
            else if (attr.equals("UniqueCallID")) c.uuid = value;
            else if (attr.equals("TelephonySignalStrength")) c.signal = leadingInt(value, -1);
            else if (attr.equals("TelephonyRegistrationStatus")) c.registration = enumValue(value, REGISTRATION_NAMES, -1);
            else if (attr.startsWith("TelephonyAir")) c.airplane = isTrue(value);
            else if (attr.equals("MobileOperator")) c.operator = value;
        }
        return c;
    }

    /* liczba albo nazwa z listy (bez rozrozniania wielkosci liter) */
    static int enumValue(String value, String[] names, int dflt) {
        int n = leadingInt(value, Integer.MIN_VALUE);
        if (n != Integer.MIN_VALUE) return n;
        for (int i = 0; i < names.length; i++) {
            if (names[i].equalsIgnoreCase(value)) return i;
        }
        return dflt;
    }

    /* "3", "03", "3 bars" -> 3; brak cyfry na poczatku -> dflt */
    static int leadingInt(String value, int dflt) {
        if (value == null) return dflt;
        String v = value.trim();
        int i = 0, n = 0;
        boolean any = false;
        while (i < v.length() && Character.isDigit(v.charAt(i))) {
            n = n * 10 + (v.charAt(i) - '0');
            any = true;
            i++;
            if (n > 1000000) break;
        }
        return any ? n : dflt;
    }

    static boolean isTrue(String value) {
        return "true".equalsIgnoreCase(value) || "1".equals(value) || "yes".equalsIgnoreCase(value);
    }
}
