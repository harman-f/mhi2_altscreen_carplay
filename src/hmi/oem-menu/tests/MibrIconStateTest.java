package de.mibr.hmi;

public final class MibrIconStateTest {
    private static void check(boolean value, String name) {
        if (!value) throw new AssertionError(name);
    }

    public static void main(String[] args) {
        check(MibrIconState.variant(true, false) == MibrIconState.DARK_NORMAL,
                "dark normal");
        check(MibrIconState.variant(true, true) == MibrIconState.DARK_ACTIVE,
                "dark selected active");
        check(MibrIconState.variant(false, false) == MibrIconState.LIGHT_NORMAL,
                "light normal");
        check(MibrIconState.variant(false, true) == MibrIconState.LIGHT_ACTIVE,
                "light selected active");
        check(MibrIconState.variant(true, false, true, false)
                == MibrIconState.DARK_NORMAL, "activated alone is not active art");
        check(MibrIconState.variant(false, false, false, true)
                == MibrIconState.LIGHT_ACTIVE, "pressed selects green-bar art (stock 758)");
        check(MibrIconState.variant(true, true, false, false)
                == MibrIconState.DARK_NORMAL, "selected/focus alone keeps normal art");
        check(MibrIconState.variant(false, true, true, true)
                == MibrIconState.LIGHT_ACTIVE, "pressed wins in every state");
        check(MibrIconState.path(true, false).endsWith(
                "mibr_vc_settings_dark_normal_235x154_rgba.png"), "dark normal path");
        check(MibrIconState.path(true, true).endsWith(
                "mibr_vc_settings_dark_active_235x154_rgba.png"), "dark active path");
        check(MibrIconState.path(false, false).endsWith(
                "mibr_vc_settings_light_normal_235x154_rgba.png"), "light normal path");
        check(MibrIconState.path(false, true).endsWith(
                "mibr_vc_settings_light_active_235x154_rgba.png"), "light active path");
        check(MibrIconState.path(1, true, false, false, true).endsWith(
                "mibr_vc_settings_skin1_dark_active_235x151_rgba.png"), "skin1 dark pressed");
        check(MibrIconState.path(1, false, true, false, false).endsWith(
                "mibr_vc_settings_skin1_light_normal_235x151_rgba.png"), "skin1 light normal");
        check(MibrIconState.path(3, false, false, false, true).equals(MibrIconState.path(false, true)),
                "skin3 keeps the existing set");
        check(MibrIconState.path(0, true, false, false, false).equals(MibrIconState.path(true, false)),
                "unknown skin keeps the existing set");
        check(MibrIconState.counterpart(MibrIconState.path(1, true, false, false, false)).equals(
                MibrIconState.path(1, true, false, false, true)), "skin1 counterpart");
        check(MibrIconState.ROOT.equals("/mnt/app/eso/hmi/lsd/mibr/icons/"),
                "MIBR-owned icon root");

        for (int skin = 1; skin <= 3; skin += 2) {
            for (int mode = 0; mode < 2; mode++) {
                boolean dark = mode == 0;
                String idle = MibrIconState.path(skin, dark, true, true, false);
                String held = MibrIconState.path(skin, dark, false, false, true);
                check(MibrIconState.fallbackPath(idle) == null,
                        "loading/failed normal image must not show pressed underline");
                check(idle.equals(MibrIconState.fallbackPath(held)),
                        "loading pressed image may safely show normal art");
                check(MibrIconState.fallbackPath(MibrIconState.fallbackPath(held)) == null,
                        "release while normal art retries cannot reuse cached pressed art");
            }
        }
        check(MibrIconState.fallbackPath(null) == null, "missing path has no pressed fallback");

        MibrIconLoadState load = new MibrIconLoadState();
        String normal = MibrIconState.path(false, false);
        String active = MibrIconState.path(false, true);
        check(load.selectPath(normal), "initial path change");
        long oldRequest = load.beginRequest();
        check(oldRequest >= 0L, "normal request starts");
        check(load.selectPath(active), "selection switches path");
        long activeRequest = load.beginRequest();
        check(activeRequest != oldRequest, "new request generation");
        check(!load.markLoaded(oldRequest, normal), "late old image rejected");
        check(!load.selectPath(active), "same state does not restart request");
        check(load.beginRequest() < 0L, "duplicate request suppressed");
        check(load.markLoaded(activeRequest, active), "current image accepted");
        check(load.isLoaded(), "active image ready");

        check(load.selectPath(MibrIconState.path(true, true)), "day-night switch path");
        long missingRequest = load.beginRequest();
        check(load.markFailed(missingRequest, load.path()), "missing PNG marks fallback");
        check(load.isFailed() && !load.needsRequest(), "missing PNG does not spin");
        check(!load.markLoaded(missingRequest, load.path()),
                "failed request cannot later become visible");
        check(load.selectPath(active), "path transition permits a fresh request");
        long retryRequest = load.beginRequest();
        check(retryRequest >= 0L, "new state may load its own asset");
        load.dispose();
        check(!load.isCurrent(retryRequest, active),
                "clone teardown rejects late callback");
        check(!load.isLoaded(), "teardown releases loaded state");
        System.out.println("MIBR_ICON_STATE_PASS four_variants pressed_is_active=true");
    }
}
