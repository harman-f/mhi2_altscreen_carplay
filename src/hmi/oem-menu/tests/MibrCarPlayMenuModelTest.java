package de.mibr.hmi;

/** r8 flat menu: 7 root settings + 3 submenu links, one scrolling list per screen. */
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

    public static void main(String[] args) {
        MibrI18n.forced = "de_DE";
        MibrCarPlayMenuModelTest view = new MibrCarPlayMenuModelTest();
        MibrCarPlayMenuModel menu = new MibrCarPlayMenuModel(view);
        check(MibrSettingsCatalog.KEYS.length == 48, "registry count");
        check(MibrSettingsCatalog.UI_SECTIONS.length == MibrSettingsCatalog.KEYS.length, "visibility metadata count");
        boolean[] visited = new boolean[MibrSettingsCatalog.KEYS.length];
        int count = 0;
        menu.open();
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES, "main list");
        check("CarPlay-Einstellungen".equals(view.title), "main list title");
        // r56: 6 root settings + Ansichten + Erweitert
        check(view.rows.length == 8 && MibrCarPlayMenuModel.rootRows() == 8, "main list has 8 rows");
        String[] expected = {"Ansicht", "Kartenanzeige", "Ankunftszeit", "Tempolimit", "Kompass",
            "Abbiegehinweis", "Ansichten", "Erweitert"};
        for (int i = 0; i < expected.length; i++)
            check(expected[i].equals(view.rows[i]), "main row " + i + " " + expected[i]);
        check(menu.keyForRow(0) == index("viewarea.selected") && menu.keyForRow(5) == index("navigation.maneuver"),
              "root rows map to settings");
        check(menu.keyForRow(6) == -1 && menu.groupForRow(6) == 0 && menu.keyForRow(7) == -1 && menu.groupForRow(7) == 1,
              "Ansichten and Erweitert links are never keys");
        for (int row = 0; row < 6; row++)
            count += visitSetting(menu, view, visited, row, MibrCarPlayMenuModel.CATEGORIES);
        // r56: the Ansichten submenu holds the six view rows (virtual keys, no registry keys)
        menu.select(6);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Ansichten".equals(view.title), "Ansichten");
        String[] views = {"Bildbereich folgt Cockpit-Ansicht", "Cockpit-Ansicht jetzt", "Resync-Ansicht (Langdruck rechts)",
            "Bildbereich bei Voll", "Bildbereich bei Wide", "Bildbereich bei Center", "Sporttacho vorhanden"};
        check(view.rows.length == 7, "Ansichten: seven view rows");
        for (int i = 0; i < views.length; i++) check(views[i].equals(view.rows[i]), "Ansichten row " + i);
        check(menu.isEngineRow(0) && menu.isEngineRow(6) && !menu.isEngineRow(7), "all seven rows are virtual rows");
        check(menu.keyForRow(0) == MibrPopupEditorModel.VIEW_FOLLOW && menu.keyForRow(1) == MibrPopupEditorModel.VIEW_POS
              && menu.keyForRow(2) == MibrPopupEditorModel.VIEW_RS && menu.keyForRow(3) == MibrPopupEditorModel.VIEW_MAP0
              && menu.keyForRow(4) == MibrPopupEditorModel.VIEW_MAP1 && menu.keyForRow(5) == MibrPopupEditorModel.VIEW_MAP4
              && menu.keyForRow(6) == MibrPopupEditorModel.VIEW_SPORT,
              "view rows map to the virtual keys in order");
        menu.select(1);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Ansichten".equals(view.title), "select() on a view row changes nothing");
        menu.back();
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES, "Ansichten back to the main list");
        menu.select(7);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Erweitert".equals(view.title), "Erweitert");
        String[] advanced = {"CarPlay im Cockpit", "Bildrate", "Quellversion", "Motorart", "Diagnose"};
        check(view.rows.length == 5, "Erweitert: 3 settings + engine type + Diagnose link");
        for (int i = 0; i < advanced.length; i++) check(advanced[i].equals(view.rows[i]), "Erweitert row " + i);
        check(menu.isEngineRow(3) && !menu.isEngineRow(2) && !menu.isEngineRow(4), "only row 3 is the engine row");
        check(menu.keyForRow(3) == MibrPopupEditorModel.ENGINE && menu.groupForRow(3) == -1, "engine row is a value row (virtual key), never a link");
        check(MibrPopupEditorModel.ENGINE == MibrSettingsCatalog.KEYS.length, "virtual key sits after the 48 registry keys");
        MibrPopupEditorModel editor = new MibrPopupEditorModel();
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
        check(menu.keyForRow(4) == -1 && menu.groupForRow(4) == 2, "Diagnose link");
        menu.select(4);
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Diagnose".equals(view.title) && view.rows.length == 7,
              "Diagnose seven vehicle-data rows");
        check(view.rows[3].indexOf("Identify") >= 0 && view.rows[4].indexOf("iPhone") >= 0, "diagnostics rows come from status files only");
        menu.back();
        check(view.screen == MibrCarPlayMenuModel.ITEMS && "Erweitert".equals(view.title), "Diagnose back to Erweitert");
        menu.back();
        check(view.screen == MibrCarPlayMenuModel.CATEGORIES, "Erweitert back to main list");
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
        menu.select(7); menu.select(4);
        MibrCarPlayMenuModel.Snapshot diag = menu.snapshot();
        menu.back(); menu.select(1);
        MibrCarPlayMenuModel.Snapshot fpsDetail = menu.snapshot();
        menu.back(); menu.back();
        menu.restore(diag);
        check(menu.screen() == MibrCarPlayMenuModel.ITEMS && menu.group() == 2, "restore Diagnose");
        menu.back();
        check(menu.group() == 1, "restored Diagnose backs to Erweitert");
        menu.restore(fpsDetail);
        check(menu.screen() == MibrCarPlayMenuModel.DETAIL && menu.selected() == index("maxFPS"), "restore detail");
        menu.back();
        check(menu.screen() == MibrCarPlayMenuModel.ITEMS && menu.group() == 1, "detail backs to Erweitert");
        for (int i = 0; i < 3; i++) { menu.close(); menu.open(); check(view.rows.length == 8, "reopen"); }
        MibrI18n.forced = "en_GB";
        menu.refresh();
        check("CarPlay settings".equals(view.title) && "View".equals(view.rows[0]) &&
              "Views".equals(view.rows[6]) && "Advanced".equals(view.rows[7]), "English main list");
        MibrI18n.forced = null;
        menu.refresh();
        check("CarPlay settings".equals(view.title), "unreadable language falls back to English");
        menu.close();
        System.out.println("MIBR_CARPLAY_MENU_MODEL_PASS registry=48 visible=" + count + " hidden=" + hidden +
                           " main_rows=8 native_ui=11");
    }
}
