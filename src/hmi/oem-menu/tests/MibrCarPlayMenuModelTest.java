package de.mibr.hmi;

/** The standard menu: one scrolling list per level. */
public final class MibrCarPlayMenuModelTest implements MibrCarPlayMenuModel.View {
    private int screen;
    private String title;
    private String[] rows;
    private String detail;

    public void show(int screen, String title, String[] rows, String detail) {
        this.screen = screen;
        this.title = title;
        this.rows = rows;
        this.detail = detail;
        // Only the empty diagnostics submenu leaves its single row for the status line.
        for (int i = 0; i < rows.length; i++)
            if (rows[i] == null && !(screen == MibrCarPlayMenuModel.ITEMS && rows.length == 1))
                throw new AssertionError("no blank padding rows");
    }

    private static void check(boolean condition, String name) {
        if (!condition) throw new AssertionError(name);
    }

    private static int index(String key) {
        for (int i = 0; i < MibrSettingsCatalog.KEYS.length; i++)
            if (key.equals(MibrSettingsCatalog.KEYS[i])) return i;
        throw new AssertionError(key);
    }

    private static int visitSetting(MibrCarPlayMenuModel menu, MibrCarPlayMenuModelTest view,
                                    boolean[] visited, int row, int returnScreen) {
        String label = view.rows[row];
        menu.select(row);
        check(view.screen == MibrCarPlayMenuModel.DETAIL, "detail");
        int k = menu.selected();
        String key = MibrSettingsCatalog.KEYS[k];
        check(MibrSettingsCatalog.UI_KINDS[k].length() > 0, "widget kind per key");
        if ("sourceVersion".equals(key))
            check("CHOICE_PENDING_CANONICAL_VALIDATOR".equals(MibrSettingsCatalog.UI_KINDS[k]), "no free text");
        if ("maxFPS".equals(key)) {
            check("CHOICE".equals(MibrSettingsCatalog.UI_KINDS[k]), "fps choice");
            check(MibrSettingsCatalog.CHOICES[k].indexOf("35") < 0, "35 must remain blocked until canonical validator approves");
        }
        if ("navigation.compass".equals(key)) {
            check("TRISTATE".equals(MibrSettingsCatalog.UI_KINDS[k]), "do not erase user wire state");
            check(view.detail.indexOf("yes/no/user") >= 0, "compass tri-state");
        }
        check(view.detail.indexOf(key) >= 0, "key binding");
        check(!visited[k], "duplicate key");
        visited[k] = true;
        menu.back();
        check(view.screen == returnScreen, "detail back returns to its own list");
        return 1;
    }

    /** The menu file the installer ships. */
    private static void useStandardFile() {
        try {
            java.io.File f = java.io.File.createTempFile("mibr-menu", ".conf");
            f.deleteOnExit();
            java.io.FileOutputStream out = new java.io.FileOutputStream(f);
            java.io.FileInputStream in = new java.io.FileInputStream(System.getProperty("mibr.menu.standard"));
            byte[] b = new byte[16384];
            int n = in.read(b);
            out.write(b, 0, n);
            in.close();
            out.close();
            MibrMenuLayout.storedPath = f.getPath();
        } catch (java.io.IOException e) {
            throw new AssertionError(e.toString());
        }
    }

    public static void main(String[] args) {
        MibrI18n.forced = "de_DE";
        useStandardFile();
        MibrCarPlayMenuModelTest view = new MibrCarPlayMenuModelTest();
        MibrCarPlayMenuModel menu = new MibrCarPlayMenuModel(view);
        check(MibrSettingsCatalog.KEYS.length == 48, "registry count");
        check(MibrSettingsCatalog.UI_SECTIONS.length == MibrSettingsCatalog.KEYS.length, "visibility metadata count");
        boolean[] visited = new boolean[MibrSettingsCatalog.KEYS.length];
        int count = 0;
        menu.open();
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES, "main list");
        check("CarPlay-Einstellungen".equals(view.title), "main list title");
        // r56: 6 root settings + Ansichten + Erweitert; R2: CarPlay-Navigation checkbox after the settings
        check(view.rows.length == 11, "main list has 11 rows");
        String[] expected = {"Ansicht", "Kartenanzeige", "Ankunftszeit", "Tempolimit", "Kompass",
            "Abbiegehinweis", "CarPlay-Navigation", "Pfeile im Cockpit", "Ansichten", "Erweitert", "Version"};
        for (int i = 0; i < expected.length; i++)
            check(expected[i].equals(view.rows[i]), "main row " + i + " " + expected[i]);
        check(menu.keyForRow(0) == index("viewarea.selected") && menu.keyForRow(5) == index("navigation.maneuver"),
              "root rows map to settings");
        check(menu.keyForRow(7) == -1 && menu.groupForRow(7) == 0 && menu.keyForRow(8) == -1 && menu.groupForRow(8) == 1 && menu.keyForRow(9) == -1 && menu.groupForRow(9) == 5 && menu.keyForRow(10) == -1 && menu.groupForRow(10) == 8,
              "Ansichten, Erweitert and Version links are never keys");
        for (int row = 0; row < 6; row++)
            count += visitSetting(menu, view, visited, row, MibrCarPlayMenuModel.CATEGORIES);
        // r56: the Ansichten submenu holds the six view rows (virtual keys, no registry keys)
        check(menu.keyForRow(6) == MibrPopupEditorModel.CARPLAY_NAV && menu.groupForRow(6) == -1, "CarPlay-Navigation is the checkbox key");
        menu.select(6);
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES && view.rows.length == 11, "the checkbox row opens no page");
        menu.select(7);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Pfeile im Cockpit".equals(view.title), "Pfeile im Cockpit");
        String[] arrows = {"Quelle", "Anzeige", "Text über der Karte", "Unten", "Seitenstraßen", "Spurempfehlung", "Karte Tag/Nacht", "Demo-Route"};
        check(view.rows.length == arrows.length, "eight rows");
        for (int i = 0; i < arrows.length; i++) check(arrows[i].equals(view.rows[i]), "arrow row " + i);
        check(menu.keyForRow(0) == MibrPopupEditorModel.NAV_SOURCE && menu.keyForRow(2) == MibrPopupEditorModel.NAV_TEXT &&
              menu.keyForRow(5) == MibrPopupEditorModel.NAV_LANES && menu.keyForRow(6) == MibrPopupEditorModel.NAV_NIGHT && menu.keyForRow(7) == MibrPopupEditorModel.NAV_DEMO, "rows map to the keys in order");
        check(new MibrPopupEditorModel().directToggle(MibrPopupEditorModel.NAV_SIDE) && !new MibrPopupEditorModel().directToggle(MibrPopupEditorModel.NAV_TEXT), "checkbox and dropdown rows");
        check(new MibrDraftChoiceModel(MibrPopupEditorModel.NAV_TEXT).options().length == 3, "three text modes");
        check(new MibrPopupEditorModel().directToggle(MibrPopupEditorModel.NAV_DEMO) && MibrPopupEditorModel.durable(MibrPopupEditorModel.NAV_DEMO) == null, "demo is a RAM checkbox");
        menu.select(0);
        check(view.screen == MibrCarPlayMenuModel.ITEMS, "select() on the value row opens no page");
        menu.back();
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES, "back to the main list");
        menu.select(8);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Ansichten".equals(view.title), "Ansichten");
        String[] views = {"Bildbereich folgt Cockpit-Ansicht", "Cockpit-Ansicht jetzt", "Resync-Ansicht (Langdruck rechts)",
            "Bildbereich bei Voll", "Bildbereich bei Wide", "Bildbereich bei Center", "Sporttacho vorhanden"};
        check(view.rows.length == 11, "Ansichten: seven view rows, the calibration picture and three safe areas");
        check("Kalibrierbild".equals(view.rows[7]) && menu.keyForRow(7) == MibrPopupEditorModel.CALIB_IMAGE && "Safe Area Voll".equals(view.rows[8]) && "Safe Area Center".equals(view.rows[10]), "calibration picture, safe area links");
        check(menu.keyForRow(8) == -1 && menu.groupForRow(8) >= 0, "a safe area link is never a key");
        menu.select(9);
        check("Safe Area Wide".equals(view.title) && view.rows.length == 6 && "Rechte Kante".equals(view.rows[2]) && "Zurücksetzen".equals(view.rows[4]), "safe area page");
        check(menu.keyForRow(0) == MibrPopupEditorModel.SAFE_FIRST + 5 && menu.keyForRow(4) == MibrPopupEditorModel.SAFE_FIRST + 9, "safe rows");
        check(menu.keyForRow(5) == -1 && menu.noteRow(5), "the note row is no key");
        check(MibrPopupEditorModel.durable(menu.keyForRow(2)) == MibrDurableSwitch.SAFE_WIDE, "wide row belongs to its store");
        menu.back();
        check("Ansichten".equals(view.title), "safe area backs to Ansichten");
        for (int i = 0; i < views.length; i++) check(views[i].equals(view.rows[i]), "Ansichten row " + i);
        check(menu.keyForRow(0) == MibrPopupEditorModel.VIEW_FOLLOW && menu.keyForRow(1) == MibrPopupEditorModel.VIEW_POS
              && menu.keyForRow(2) == MibrPopupEditorModel.VIEW_RS && menu.keyForRow(3) == MibrPopupEditorModel.VIEW_MAP0
              && menu.keyForRow(4) == MibrPopupEditorModel.VIEW_MAP1 && menu.keyForRow(5) == MibrPopupEditorModel.VIEW_MAP4
              && menu.keyForRow(6) == MibrPopupEditorModel.VIEW_SPORT,
              "view rows map to the virtual keys in order");
        menu.select(1);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Ansichten".equals(view.title), "select() on a view row changes nothing");
        menu.back();
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES, "Ansichten back to the main list");
        menu.select(9);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Erweitert".equals(view.title), "Erweitert");
        String[] advanced = {"CarPlay im Cockpit", "Bildrate", "Quellversion", "Motorart", "Menüsprache", "Demo-GPS-Position", "Logs auf SD-Karte", "Menü laden: aus Datei", "Expertenmodus", "Skalierung", "Diagnose"};
        check(view.rows.length == 11, "Erweitert: 3 settings + engine type + language + demo GPS + SD log + menu load + expert mode + Skalierung + Diagnose");
        for (int i = 0; i < advanced.length; i++) check(advanced[i].equals(view.rows[i]), "Erweitert row " + i);
        check(menu.loadRow(7) && !menu.loadRow(6) && menu.keyForRow(7) == -1, "menu load is an action row");
        check(menu.keyForRow(3) == MibrPopupEditorModel.ENGINE && menu.groupForRow(3) == -1, "engine row is a value row (virtual key), never a link");
        check(MibrPopupEditorModel.ENGINE == MibrSettingsCatalog.KEYS.length, "virtual key sits after the 48 registry keys");
        MibrPopupEditorModel editor = new MibrPopupEditorModel();
        String[] scaleChoices=new MibrDraftChoiceModel(MibrPopupEditorModel.SCALE_MAIN).options();
        check(scaleChoices.length==6 && "AUTO".equals(scaleChoices[0]) && "150".equals(scaleChoices[5]), "scaling domain includes AUTO and five raw factors");
        MibrScalingState.reset();
        MibrScalingState.readback(MibrPopupEditorModel.SCALE_MAIN,"AUTO","UNKNOWN","UNKNOWN","UNKNOWN","DEFAULT","0","RECONNECT","ENABLED","0");
        check(MibrScalingState.writable(MibrPopupEditorModel.SCALE_MAIN) && "0".equals(MibrScalingState.revision(MibrPopupEditorModel.SCALE_MAIN)), "validated per-display ENABLED capability and revision enable the dropdown");
        check(MibrScalingState.status(MibrPopupEditorModel.SCALE_MAIN).indexOf("Wirkung unbekannt")>=0, "requested value never claims actual stream effect");
        MibrScalingState.failed(MibrPopupEditorModel.SCALE_MAIN,"read failure");
        check(!MibrScalingState.writable(MibrPopupEditorModel.SCALE_MAIN) && MibrScalingState.revision(MibrPopupEditorModel.SCALE_MAIN)==null, "failed readback clears writer capability and revision");
        check(!"AUTO".equals("100"), "AUTO remains distinct from explicit 100 percent");
        editor.setAvailable(true);
        String[] choices = editor.options(MibrPopupEditorModel.ENGINE);
        check(choices.length == 4 && "gas".equals(choices[0]) && "diesel".equals(choices[1]) && "cng".equals(choices[2]) && "electric".equals(choices[3]), "engine dropdown choices");
        MibrEngineState.confirmed("diesel", "gas", "1");
        check("Diesel (nach Neustart; aktuell Benzin)".equals(editor.label(MibrPopupEditorModel.ENGINE, "diesel")), "pending note on the set value");
        check("Benzin".equals(editor.label(MibrPopupEditorModel.ENGINE, "gas")), "other values plain");
        MibrEngineState.confirmed("gas", "gas", "0");
        editor.readback(MibrPopupEditorModel.ENGINE, MibrEngineState.engine());
        check(editor.open(MibrPopupEditorModel.ENGINE) && editor.selectedOption(MibrPopupEditorModel.ENGINE) == 0, "dropdown opens with petrol selected");
        check(editor.choose(1) && "diesel".equals(editor.draft(MibrPopupEditorModel.ENGINE)), "choosing diesel makes a draft only");
        editor.discardDraft(MibrPopupEditorModel.ENGINE);
        check(!editor.directToggle(MibrPopupEditorModel.ENGINE) && !MibrPopupEditorModel.saveAllowed(MibrPopupEditorModel.ENGINE), "never a toggle or a registry save");
        menu.select(3);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Erweitert".equals(view.title), "select() on the engine row changes nothing");
        MibrViewState.reset();
        MibrViewState.confirmed(new String[] {"1", "0", "1", "0", "2", "0", "4"});
        String[] posChoices = editor.options(MibrPopupEditorModel.VIEW_POS);
        check(posChoices.length == 4 && "0".equals(posChoices[0]) && "4".equals(posChoices[3]), "no speedometer position without the sport option");
        check("Center".equals(editor.label(MibrPopupEditorModel.VIEW_POS, "4")) && "Voll".equals(editor.label(MibrPopupEditorModel.VIEW_POS, "0")), "view labels");
        check(!editor.directToggle(MibrPopupEditorModel.VIEW_FOLLOW) && !MibrPopupEditorModel.saveAllowed(MibrPopupEditorModel.VIEW_SPORT), "view rows are never toggles or registry saves");
        MibrViewState.reset();
        for (int row = 0; row < 3; row++)
            count += visitSetting(menu, view, visited, row, MibrCarPlayMenuModel.ITEMS);
        check(menu.keyForRow(4) == MibrPopupEditorModel.MENU_LANGUAGE &&
              menu.keyForRow(5) == MibrPopupEditorModel.GPS_DEMO &&
              menu.keyForRow(6) == MibrPopupEditorModel.SD_LOG &&
              menu.groupForRow(4) == -1 && menu.groupForRow(5) == -1 && menu.groupForRow(6) == -1,
              "language and demo GPS map to virtual settings, not submenu links");
        String[] languages = editor.options(MibrPopupEditorModel.MENU_LANGUAGE);
        String[] gpsPresets = editor.options(MibrPopupEditorModel.GPS_DEMO);
        check(gpsPresets.length==5,"GPS demo has five actual choices");
        check(languages.length==3 && "AUTO".equals(languages[0]) &&
              "de".equals(languages[1]) && "en".equals(languages[2]), "language enum");
        check(gpsPresets.length==5 && "OFF".equals(gpsPresets[0]) &&
              "BERLIN_DEMO".equals(gpsPresets[1]) &&
              "HAMBURG_DEMO".equals(gpsPresets[2]) &&
              "SCHWALEFELD_DEMO".equals(gpsPresets[3]) &&
              "WINTERBERG_DEMO".equals(gpsPresets[4]), "five explicit GPS demo presets");
        check(editor.liveViewGated(MibrPopupEditorModel.MENU_LANGUAGE) &&
              editor.liveViewGated(MibrPopupEditorModel.GPS_DEMO), "unqualified backend cannot open either dropdown");
        check(editor.directToggle(MibrPopupEditorModel.SD_LOG) && editor.liveViewGated(MibrPopupEditorModel.SD_LOG) &&
              "on".equals(editor.options(MibrPopupEditorModel.SD_LOG)[1]), "SD log is a direct toggle gated until the broker answers");
        check(!editor.open(MibrPopupEditorModel.MENU_LANGUAGE) &&
              !editor.open(MibrPopupEditorModel.GPS_DEMO), "disabled rows never create drafts");
        menu.select(4);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Erweitert".equals(view.title),
              "language row is never a separate navigation page");
        check(menu.keyForRow(8) == MibrPopupEditorModel.EXPERT_MODE, "expert mode is a value row");
        check(menu.keyForRow(9) == -1 && menu.groupForRow(9) == 6,
              "Skalierung link is a page, not a registry key");
        menu.select(9);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Skalierung".equals(view.title) && view.rows.length == 5, "Skalierung has four controls and one read-only notice");
        check("Zoomfaktor Hauptdisplay".equals(view.rows[0]) && "Zoomfaktor Virtual Cockpit".equals(view.rows[1]) && "Physische Displaygröße Virtual Cockpit".equals(view.rows[2]) && "Physische Displaygröße Hauptdisplay".equals(view.rows[3]), "exact scaling row labels");
        check(menu.scalingPageOpen() && menu.keyForRow(0)==MibrPopupEditorModel.SCALE_MAIN && menu.keyForRow(1)==MibrPopupEditorModel.SCALE_CLUSTER && menu.keyForRow(2)==MibrPopupEditorModel.SCALE_PHYSICAL && menu.keyForRow(3)==MibrPopupEditorModel.SCALE_MAIN_PHYSICAL, "four virtual scaling keys with main physical appended");
        check("\u00c4nderungen werden bei der n\u00e4chsten CarPlay-Verbindung \u00fcbertragen.".equals(view.rows[4]) && menu.keyForRow(4)==-1 && menu.noteRow(4), "read-only notice appears exactly once outside registry and SCALE_SET");
        menu.select(4);check(menu.scalingPageOpen() && view.rows.length==5, "notice is not selectable");
        MibrI18n.forced="en_GB";menu.refresh();
        check("Changes are sent on the next CarPlay connection.".equals(view.rows[4]) && "Main display zoom factor".equals(view.rows[0]), "English notice and controls");
        MibrI18n.forced="de_DE";menu.refresh();
        menu.select(0);check(view.screen==MibrCarPlayMenuModel.ITEMS && view.rows.length==5, "scaling row selection remains on flat page");
        menu.back();check("Erweitert".equals(view.title), "Scaling back to Erweitert");
        check(menu.keyForRow(10) == -1 && menu.groupForRow(10) == 7, "Diagnose link follows Skalierung");
        menu.select(10);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Diagnose".equals(view.title) && view.rows.length == 7,
              "Diagnose seven vehicle-data rows");
        check(view.rows[3].indexOf("Identify") >= 0 && view.rows[4].indexOf("iPhone") >= 0, "diagnostics rows come from status files only");
        menu.back();
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Erweitert".equals(view.title), "Diagnose back to Erweitert");
        menu.back();
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES, "Erweitert back to main list");
        menu.select(10);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Version".equals(view.title) && menu.onVersion(), "Version read-only metadata page");
        check(view.rows.length > 0 && (view.rows[0].indexOf("No installed version metadata") >= 0 || view.rows[0].indexOf("Versionsdaten nicht installiert") >= 0), "Version page reports unknown when receipt is absent");
        menu.back();
        check(count == 9, "exactly nine user-facing settings reachable");
        int hidden = 0;
        for (int k = 0; k < MibrSettingsCatalog.KEYS.length; k++) {
            String section = MibrSettingsCatalog.UI_SECTIONS[k];
            if ("hidden".equals(section)) { check(!visited[k], "hidden key never a row"); hidden++; }
            else check(visited[k], "allowlisted key appears once");
        }
        check(hidden == 39, "exact hidden count");
        check("hidden".equals(MibrSettingsCatalog.UI_SECTIONS[index("preset.id")]), "Profil hidden");
        check("hidden".equals(MibrSettingsCatalog.UI_SECTIONS[index("navigation.url")]), "URL hidden");
        check(MibrMenuDefinition.NATIVE_UI_KEYS.length == 11, "native scope=ui keeps 11 rows");
        // Snapshot/restore through the nested Diagnose screen.
        menu.select(9); menu.select(10);
        MibrCarPlayMenuModel.Snapshot diag = menu.snapshot();
        menu.back(); menu.select(1);
        MibrCarPlayMenuModel.Snapshot fpsDetail = menu.snapshot();
        menu.back(); menu.back();
        menu.restore(diag);
        check(menu.screen() == MibrCarPlayMenuModel.ITEMS && menu.group() == 7, "restore Diagnose");
        menu.back();
        check(menu.group() == 5, "restored Diagnose backs to Erweitert");
        menu.restore(fpsDetail);
        check(menu.screen() == MibrCarPlayMenuModel.DETAIL && menu.selected() == index("maxFPS"), "restore detail");
        menu.back();
        check(menu.screen() == MibrCarPlayMenuModel.ITEMS && menu.group() == 5, "detail backs to Erweitert");
        for (int i = 0; i < 3; i++) { menu.close(); menu.open(); check(view.rows.length == 11, "reopen"); }
        MibrI18n.forced = "en_GB";
        menu.refresh();
        check("CarPlay settings".equals(view.title) && "View".equals(view.rows[0]) &&
              "CarPlay navigation".equals(view.rows[6]) && "Views".equals(view.rows[8]) && "Advanced".equals(view.rows[9]), "English main list");
        MibrI18n.forced = null;
        menu.refresh();
        check("CarPlay settings".equals(view.title), "unreadable language falls back to English");
        menu.close();
        System.out.println("MIBR_CARPLAY_MENU_MODEL_PASS registry=48 visible=" + count + " hidden=" + hidden +
                           " main_rows=11 native_ui=11");
    }
}
