package de.mibr.hmi;

/**
 * Native choice-page data model. OFFLINE DRAFT ONLY.
 * Does not speak to a broker, apply a runtime effect or save any file.
 * All canonical enum options derive from MibrSettingsCatalog generated from
 * the one Classic111 settings registry. Candidate URL/version presentation
 * values are intentionally not claimed validated until the live core accepts.
 */
public final class MibrDraftChoiceModel {
    private final int index;
    private String draft;

    public MibrDraftChoiceModel(int index) {
        if (index < 0 || index >= MibrPopupEditorModel.VIRTUAL_END)
            throw new IllegalArgumentException("index");
        this.index = index;
    }

    private static String[] fromSeparated(String input) {
        if (input == null || input.length() == 0) return new String[0];
        java.util.StringTokenizer t = new java.util.StringTokenizer(input, "|");
        String[] out = new String[t.countTokens()];
        for (int i = 0; i < out.length; i++) out[i] = t.nextToken();
        return out;
    }

    public String[] options() {
        if (index == MibrPopupEditorModel.ENGINE) return MibrEngineState.VALUES;
        if (index > MibrPopupEditorModel.ENGINE) return MibrViewState.options(index - MibrPopupEditorModel.VIEW_FOLLOW);
        String kind = MibrSettingsCatalog.UI_KINDS[index];
        String key = MibrSettingsCatalog.KEYS[index];
        if ("STATUS".equals(kind)) return new String[0];
        if ("CHOICE_PENDING_CANONICAL_VALIDATOR".equals(kind)) {
            if ("navigation.url".equals(key))
                return new String[] {
                    "maps:/car/instrumentcluster",
                    "maps:/car/instrumentcluster/map",
                    "maps:/car/instrumentcluster/instructioncard"
                };
            if ("sourceVersion".equals(key))
                return new String[] { "950.7.1", "1005.8.1" };
            // For a multi-URL set, current schema has no per-choice allowlist.
            return new String[0];
        }
        if ("TOGGLE".equals(kind)) return new String[] { "0", "1" };
        if ("CHOICE".equals(kind) || "TRISTATE".equals(kind)) {
            // Three-view line: dropdown order Center, Voll, Wide = wire index 2, 1, 0.
            if ("viewarea.selected".equals(key)) return new String[] { "2", "1", "0" };
            String[] enumerated = fromSeparated(MibrSettingsCatalog.CHOICES[index]);
            if (enumerated.length > 0) return enumerated;
            // Registry constrains these to index 0..1; they are NOT booleans.
            if ("viewarea.selected".equals(key) || "viewareas.initial".equals(key) ||
                key.endsWith(".adjacent")) return new String[] { "0", "1" };
        }
        return new String[0];
    }

    public boolean isChoiceValidationProven() {
        if (MibrPopupEditorModel.isVirtual(index)) return true;
        // This flag is only about LOCAL canonical enum membership, never
        // backend availability or actual application of a selected value.
        String kind = MibrSettingsCatalog.UI_KINDS[index];
        return "CHOICE".equals(kind) || "TOGGLE".equals(kind) || "TRISTATE".equals(kind);
    }

    public String labelFor(String value) {
        if (index == MibrPopupEditorModel.ENGINE) return MibrEngineState.valueLabel(value);
        if (index > MibrPopupEditorModel.ENGINE) return MibrViewState.valueLabel(index - MibrPopupEditorModel.VIEW_FOLLOW, value);
        if ("user".equals(value) && "TRISTATE".equals(MibrSettingsCatalog.UI_KINDS[index]))
            return MibrI18n.pick("App-Vorgabe", "App default");
        // Display labels only. chooseDraft retains exact canonical URL bytes.
        if ("navigation.url".equals(MibrSettingsCatalog.KEYS[index])) {
            if ("maps:/car/instrumentcluster".equals(value)) return "Cluster";
            if ("maps:/car/instrumentcluster/map".equals(value)) return MibrI18n.pick("Karte", "Map");
            if ("maps:/car/instrumentcluster/instructioncard".equals(value)) return MibrI18n.pick("Manoeverkarte", "Maneuver card");
        }
        // Wire values stay 0/1. 1 = Voll/Full, 0 = Wide (CPVC profile safe areas); Center later. Was: profile/negotiation
        // mapping is proven; until then the neutral index names.
        if ("viewarea.selected".equals(MibrSettingsCatalog.KEYS[index])) {
            if ("0".equals(value)) return MibrI18n.pick("Wide", "Wide");
            if ("1".equals(value)) return MibrI18n.pick("Voll", "Full");
            if ("2".equals(value)) return "Center";
        }
        String key = MibrSettingsCatalog.KEYS[index];
        if ("navigation.surface".equals(key)) {
            if ("base".equals(value)) return MibrI18n.pick("Standard", "Standard");
            if ("map".equals(value)) return MibrI18n.pick("Karte", "Map");
            if ("instructioncard".equals(value)) return MibrI18n.pick("Manöverkarte", "Maneuver card");
        }
        if ("navigation.maneuver".equals(key)) {
            if ("none".equals(value)) return MibrI18n.pick("Keiner", "None");
            if ("left".equals(value)) return MibrI18n.pick("Links", "Left");
            if ("right".equals(value)) return MibrI18n.pick("Rechts", "Right");
            if ("top".equals(value)) return MibrI18n.pick("Oben", "Top");
        }
        if ("carplay.enabled".equals(key)) {
            if ("1".equals(value)) return MibrI18n.pick("Aktiviert", "Enabled");
            if ("0".equals(value)) return MibrI18n.pick("Deaktiviert", "Disabled");
        }
        if ("yes".equals(value)) return MibrI18n.pick("Ja", "Yes");
        if ("no".equals(value)) return MibrI18n.pick("Nein", "No");
        return value;
    }

    public boolean chooseDraft(String proposed) {
        if (proposed == null) return false;
        String[] opts = options();
        for (int i = 0; i < opts.length; i++) {
            if (proposed.equals(opts[i])) {
                draft = proposed;
                return true;
            }
        }
        return false;
    }

    public boolean hasDraft() { return draft != null; }
    public String draft() { return draft; }
    public void discard() { draft = null; }

    /** Explicitly no SET/SAVE/ACTION in this class. */
}
