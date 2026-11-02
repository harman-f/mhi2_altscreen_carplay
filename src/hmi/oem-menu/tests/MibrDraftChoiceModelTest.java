package de.mibr.hmi;

/** Host-only test: editor selection updates a draft; the session owns saving/apply. */
public final class MibrDraftChoiceModelTest {
    private static void check(boolean ok, String msg) {
        if (!ok) throw new AssertionError(msg);
    }

    private static MibrDraftChoiceModel model(String key) {
        for (int i = 0; i < MibrSettingsCatalog.KEYS.length; i++)
            if (key.equals(MibrSettingsCatalog.KEYS[i])) return new MibrDraftChoiceModel(i);
        throw new AssertionError("missing canonical key: " + key);
    }

    private static boolean contains(String[] values, String s) {
        for (int i = 0; i < values.length; i++) if (s.equals(values[i])) return true;
        return false;
    }

    public static void main(String[] unused) {
        MibrDraftChoiceModel fps = model("maxFPS");
        check(contains(fps.options(), "20") && contains(fps.options(), "25") &&
              contains(fps.options(), "30") && contains(fps.options(), "40") &&
              contains(fps.options(), "60"), "canonical fps");
        check(!contains(fps.options(), "35"), "no unapproved FPS35");
        check(!fps.chooseDraft("35"), "reject unapproved value");
        check(fps.chooseDraft("30") && "30".equals(fps.draft()), "draft fps");
        fps.discard();
        check(!fps.hasDraft(), "discard fps");

        MibrDraftChoiceModel compass = model("navigation.compass");
        check(compass.isChoiceValidationProven(), "exact enum present");
        check(contains(compass.options(), "yes") && contains(compass.options(), "no") &&
              contains(compass.options(), "user"), "keep all 3 wire values");
        check(compass.labelFor("user").indexOf("Automatisch") < 0, "do not assume user means automatic");
        check(compass.chooseDraft("user") && "user".equals(compass.draft()), "third-state draft");

        MibrDraftChoiceModel url = model("navigation.url");
        check(url.options().length == 3, "three fixed classic URLs");
        check(!url.isChoiceValidationProven(), "URL canonical validator not integrated");
        check(!url.chooseDraft("http://unapproved-host/"), "no free-text URLs");
        check(url.chooseDraft("maps:/car/instrumentcluster/map"), "known URL draft");

        MibrDraftChoiceModel ver = model("sourceVersion");
        check(ver.options().length == 2 && !ver.isChoiceValidationProven(), "reviewed version personas only");
        check(!ver.chooseDraft("arbitrary"), "no free-text persona");

        MibrDraftChoiceModel view = model("viewarea.selected");
        check(contains(view.options(), "0") && contains(view.options(), "1"), "view index choice");
        MibrDraftChoiceModel locked = model("display.uuid");
        check(locked.options().length == 0 && !locked.chooseDraft("00000000-0000-0000-0000-000000000000"),
              "locked UUID");
        System.out.println("MIBR_DRAFT_CHOICE_MODEL_PASS no_runtime_or_storage_mutations");
    }
}
