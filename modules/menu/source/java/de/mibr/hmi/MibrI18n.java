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
 * also unreadable and falls back to English (owner requirement 2026-10-19);
 * host tests that check German texts set {@link #forced}.
 */
final class MibrI18n {
    private MibrI18n() {}

    /* Status text is stored in a session while the operator can change the menu
     * language. Keep the source text stable and localize on every render. */
    private static final String[][] STATUS_COPY={
        {"Konfigurationsdienst nicht geprüft","Configuration service not checked"},
        {"Dienst beschäftigt; Entwurf behalten","Service busy; selection retained"},
        {"Konfigurationsdienst prüfen","Checking configuration service"},
        {"MIBR/3 nicht bestätigt","MIBR/3 not confirmed"},
        {"Fähigkeiten unbestätigt","Capabilities not confirmed"},
        {"Bereit; Speicherung möglich, Stream-Wirkung unbestätigt","Ready; saving available, stream effect unverified"},
        {"Nur Lesen: dauerhafte Speicherung nicht freigeschaltet","Read-only: persistent saving not enabled"},
        {"Konsistenter Lesestand fehlt","Consistent readback unavailable"},
        {"Speicherung bestätigt; Nachlesung unklar, vor weiteren Änderungen neu laden","Save confirmed; readback uncertain. Reload before further changes"},
        {"Speichern nicht verfügbar; Entwurf behalten","Saving unavailable; selection retained"},
        {"Speichern für diese Einstellung noch nicht freigegeben","Saving not enabled for this setting"},
        {"Kein neuer Wert","No new value"},
        {"Wert nicht freigegeben","Value not permitted"},
        {"Speicherquittung ungültig; Zustand unklar","Invalid save receipt; state uncertain"},
        {"Dauerhaft gespeichert; TEMP-Materialisierung ausstehend, neu laden","Saved persistently; TEMP update pending. Reload"},
        {"SET-Ergebnis unklar; nicht erneut senden, Zustand neu prüfen","SET outcome uncertain; do not resend. Check state"},
        {"Dauerhaft gespeichert; Materialisierung ausstehend, neu laden","Saved persistently; pending materialization. Reload"},
        {"Im Cockpit bestätigt; wird in Kürze dauerhaft gesichert","Confirmed in Virtual Cockpit; persistent save pending"},
        {"Cockpit hat die Anzeige nicht bestätigt (Fehler)","Virtual Cockpit did not confirm display (error)"},
        {"Gespeichert; wird bei der nächsten CarPlay-Verbindung angezeigt","Saved; will appear on the next CarPlay connection"},
        {"Keine Bestätigung vom Cockpit; Wert ist gesetzt","No Virtual Cockpit confirmation; value was set"},
        {"Scaling-Dienst nicht freigeschaltet","Scaling service not enabled"},
        {"Lesen nicht bestätigt","Read not confirmed"},
        {"Lesestand ungültig","Invalid readback"},
        {"Schreiben nicht freigeschaltet","Writing not enabled"},
        {"Ergebnis unklar; Lesestand wird abgeglichen","Outcome uncertain; checking readback"},
        {"Speicherung nicht bestätigt; Lesestand wird abgeglichen","Save not confirmed; checking readback"},
        {"Umschalten nicht verfügbar","Switching unavailable"},
        {"Prüfe Umschaltung","Checking switch availability"},
        {"Dienst beschäftigt","Service busy"},
        {"Umgeschaltet","Switched"},{"Bereit","Ready"},{"Umschalten","Switching"},
        {"Antwort verloren; Ergebnis wird geprüft","Response lost; checking outcome"},
        {"Quittung ungültig; Ergebnis wird geprüft","Invalid receipt; checking outcome"},
        {"Umschaltung ausstehend","Switch pending"},
        {"Umschaltung unbestätigt; Anzeige neu prüfen","Switch not confirmed; check display"},
        {"Zustand prüfen","Checking state"},{"Umschaltung wird geprüft","Checking switch status"},
        {"Sprachdienst nicht verfügbar","Language service unavailable"},
        {"Sprachwahl nicht lesbar","Unable to read language"},
        {"Sprachwahl ungültig","Invalid language response"},
        {"Speicherung unbestätigt","Save not confirmed"},
        {"GPS-Demo nicht verfügbar","GPS demo unavailable"},
        {"GPS-Dienst nicht erreichbar","GPS service unavailable"},
        {"GPS-Rückmeldung ungültig","Invalid GPS response"},
        {"GPS-Rückmeldung ungültig","Invalid GPS state"},
        {"Umschalten...","Switching..."},
        {"Dienst nicht verbunden","Service not connected"},
        {"Dienst noch nicht geprüft","Service not checked yet"},
        {"Dienst nicht bestätigt","Service not confirmed"},
        {"Status nicht bestätigt","Status not confirmed"},
        {"Statusabfrage fehlgeschlagen","Status request failed"},
        {"Bereit; Wirkung unbestätigt","Ready; effect unverified"},
        {"Dienst nicht bereit","Service not ready"},
        {"Ungültiger Entwurf","Invalid selection"},
        {"Kein gültiger Entwurf","No valid selection"},
        {"TEMP-Übernahme läuft","Applying TEMP values"},
        {"Übernahme unbestätigt; Entwurf behalten","Apply not confirmed; selection retained"},
        {"Leseabfrage fehlgeschlagen","Read request failed"},
        {"Lesestand nicht konsistent","Readback is inconsistent"},
        {"Übernahme unbestätigt; Entwurf behalten","Apply not confirmed; selection retained"},
        {"TEMP-Transport nicht bereit","TEMP transport not ready"},
        {"Entwurf während Übernahme verändert","Selection changed during apply"},
        {"TEMP Readback unbestätigt; Entwurf behalten","TEMP readback not confirmed; selection retained"},
        {"TEMP Readback fehlgeschlagen","TEMP readback failed"}
        ,{"Bitte warten","Please wait"}
        ,{"Temporär übernehmen","Apply temporarily"}
        ,{"Übernehmen (Dienst offline)","Apply (service offline)"}
        ,{"CarPlay im Cockpit pausiert (bis Neustart)","CarPlay paused in Virtual Cockpit (until restart)"}
        ,{"CarPlay im Cockpit wieder aktiv","CarPlay re-enabled in Virtual Cockpit"}
        ,{"Gesendet; warte auf Bestätigung vom Cockpit","Sent; awaiting Virtual Cockpit confirmation"}
        ,{"Speichern...","Saving..."}
        ,{"Wert wird gelesen","Reading value"}
        ,{"Wert hat sich geändert; bitte neu wählen","Value changed; choose again"}
        ,{"Speicherung wird geprüft","Verifying stored preference"}
        ,{"Lesestand nicht verfügbar","Readback unavailable"}
        ,{"Standardwert","Compiled default"}
        ,{"Wunsch gespeichert","Preference stored"}
        ,{"Speicherstatus unbekannt","Storage status unknown"}
        ,{" · Verbindung ausstehend"," · reconnect pending"}
        ,{" · historisch in /info bestätigt: "," · historically advertised in /info: "}
        ,{" · aktuelle Wirkung unbekannt"," · current effect unknown"}
    };

    static String localize(String text) {
        if(text==null)return null;
        for(int i=0;i<STATUS_COPY.length;i++)
            if(text.equals(STATUS_COPY[i][0])||text.equals(STATUS_COPY[i][1]))
                return pick(STATUS_COPY[i][0],STATUS_COPY[i][1]);
        if(text.startsWith("Speichern wartet: "))
            return pick("Speichern wartet: ","Save pending: ")+text.substring(18);
        if(text.startsWith("Save pending: "))
            return pick("Speichern wartet: ","Save pending: ")+text.substring(14);
        if(text.startsWith("Dauerhaft speichern: "))
            return pick("Dauerhaft speichern: ","Saving persistently: ")+text.substring(21);
        if(text.startsWith("Saving persistently: "))
            return pick("Dauerhaft speichern: ","Saving persistently: ")+text.substring(21);
        if(text.startsWith("Nicht gespeichert: "))
            return pick("Nicht gespeichert: ","Not saved: ")+text.substring(19);
        if(text.startsWith("Not saved: "))
            return pick("Nicht gespeichert: ","Not saved: ")+text.substring(11);
        if(text.startsWith("Nicht umgeschaltet: "))
            return pick("Nicht umgeschaltet: ","Not switched: ")+routeCode(text.substring(20));
        if(text.startsWith("Not switched: "))
            return pick("Nicht umgeschaltet: ","Not switched: ")+routeCode(text.substring(14));
        if(text.startsWith("RECEIPT:"))return receipt(text);
        if(text.startsWith("TEMP bestätigt: ")||text.startsWith("TEMP confirmed: ")){
            String tail=text.substring(16);
            String suffix="; Wirkung unbestätigt";
            String englishSuffix="; effect unverified";
            if(tail.endsWith(suffix))tail=tail.substring(0,tail.length()-suffix.length());
            else if(tail.endsWith(englishSuffix))tail=tail.substring(0,tail.length()-englishSuffix.length());
            return pick("TEMP bestätigt: ","TEMP confirmed: ")+tail+pick(suffix,englishSuffix);
        }
        return text;
    }

    private static String routeCode(String code){
        return "UNBEKANNT".equals(code)?pick("Unbekannt","Unknown"):code;
    }

    private static String receipt(String token){
        String[] parts=token.split(":");
        if(parts.length!=3)return token;
        String when=parts[1],state=parts[2];
        String activation="SESSION".equals(when)?pick("bei der nächsten Sitzung","on the next session"):
            "LIVE".equals(when)?pick("sofort","immediately"):
            "PRESENTATION".equals(when)?pick("bei der nächsten Anzeige","on the next presentation"):
            "RECONNECT".equals(when)?pick("bei der nächsten Verbindung","on the next connection"):when;
        String result="UNCHANGED".equals(state)?pick("unverändert","unchanged"):
            "PENDING".equals(state)?pick("Aktivierung ausstehend","activation pending"):state;
        return pick("Dauerhaft gespeichert; ","Saved persistently; ")+activation+" "+result+
            pick("; Stream-Wirkung unbestätigt","; stream effect unverified");
    }

    /** Test seam: null = read the unit, otherwise a forced language tag. */
    static String forced;

    /*
     * Independently owned MIBR menu-language preference, NOT the vehicle
     * ConfigurationManager language. The authenticated broker must load and
     * validate its durable value before calling this method. The Java UI
     * never writes a preferences file or fabricates a storage acknowledgement.
     */
    private static volatile String menuOverride = "AUTO";
    private static volatile String menuRevision;
    private static volatile boolean menuWriter;
    private static volatile String menuMessage;
    static boolean menuWritable(){return menuWriter&&menuRevision!=null;}
    static String menuRevision(){return menuRevision;}
    static String menuMessage(){return localize(menuMessage);}
    static void menuLoading(){menuWriter=false;menuRevision=null;menuMessage=null;}
    static void menuFailed(String reason){menuWriter=false;menuRevision=null;menuMessage=reason;}
    static void menuReadback(String mode,String revision,boolean writer){
        if(!validMenuOverride(mode)||revision==null||revision.length()==0)
            throw new IllegalArgumentException("MIBR_MENU_READBACK_INVALID");
        for(int i=0;i<revision.length();i++)
            if(revision.charAt(i)<'0'||revision.charAt(i)>'9')
                throw new IllegalArgumentException("MIBR_MENU_REVISION_INVALID");
        applyMenuOverride(mode);menuRevision=revision;menuWriter=writer;menuMessage=null;
    }
    static void menuSaving(){menuWriter=false;menuMessage=MibrI18n.pick("Speichern...","Saving...");}

    static boolean validMenuOverride(String mode) {
        return "AUTO".equals(mode) || "de".equals(mode) || "en".equals(mode);
    }
    static void applyMenuOverride(String mode) {
        if (!validMenuOverride(mode)) throw new IllegalArgumentException("MIBR_MENU_LANGUAGE_INVALID");
        menuOverride = mode;
    }
    static String menuOverride() { return menuOverride; }

    static boolean german() {
        String mode = menuOverride;
        if ("de".equals(mode)) return true;
        if ("en".equals(mode)) return false;
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
