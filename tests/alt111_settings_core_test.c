#include "alt111_settings.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    struct alt111_settings s, before, other;
    struct alt111_policy_config policy;
    char blob[2049], error[256];
    unsigned group, i;
    int n;
    assert(!alt111_settings_defaults(&s, "classic_single_view"));
    assert(!alt111_settings_validate(&s, error, sizeof(error)) && s.reference_match);
    assert(!alt111_settings_defaults(&s, "mibr_dual_view"));
    assert(!alt111_settings_validate(&s, error, sizeof(error)) && !s.reference_match);
    for (group = 0; group < ALTSET_GROUP_COUNT; ++group) {
        n = alt111_settings_render_group(&s, group, blob, sizeof(blob));
        assert(n > 0 && n <= 2048);
        assert(!alt111_settings_defaults(&other, "mibr_legacy"));
        assert(!alt111_settings_parse_group(&other, group, blob, (size_t)n, ALT111_TEMP, 0, error, sizeof(error)));
        for (i = 0; i < ALTSET_COUNT; ++i) if (alt111_setting(i)->group == group) {
            assert(!strcmp(s.value[i], other.value[i]));
            assert(other.layer[i] == ALT111_TEMP);
        }
    }
    before = s;
    group = alt111_setting(ALTSET_KEYFRAME_MODE)->group;
    n = alt111_settings_render_group(&s, group, blob, sizeof(blob));
    assert(alt111_settings_parse_group(&s, group, blob, (size_t)n - 1, ALT111_TEMP, 0, error, sizeof(error)) < 0);
    assert(!memcmp(&s, &before, sizeof(s)));
    strcat(blob, "mode=off\n");
    assert(alt111_settings_parse_group(&s, group, blob, strlen(blob), ALT111_TEMP, 0, error, sizeof(error)) < 0);
    assert(!memcmp(&s, &before, sizeof(s)));
    strcpy(blob, "schema=2\nmode=off\n");
    assert(alt111_settings_parse_group(&s, group, blob, strlen(blob), ALT111_TEMP, 0, error, sizeof(error)) < 0);
    assert(alt111_setting_validate(ALTSET_KEYFRAME_INTERVAL_FRAMES, "0") < 0);
    assert(alt111_setting_validate(ALTSET_KEYFRAME_INTERVAL_FRAMES, "1001") < 0);
    assert(alt111_setting_validate(ALTSET_KEYFRAME_INTERVAL_FRAMES, "20junk") < 0);
    assert(alt111_setting_validate(ALTSET_KEYFRAME_INTERVAL_FRAMES, "020") < 0);
    assert(alt111_setting_validate(ALTSET_KEYFRAME_INTERVAL_MS, "999999999999999999999") < 0);
    assert(!alt111_setting_validate(ALTSET_SOURCEVERSION, "950.7.1"));
    assert(!alt111_setting_validate(ALTSET_SOURCEVERSION, "stock"));
    assert(alt111_setting_validate(ALTSET_SOURCEVERSION, "65536.1") < 0);
    assert(alt111_setting_validate(ALTSET_SOURCEVERSION, "950.007.1") < 0);
    assert(alt111_setting_validate(ALTSET_SOURCEVERSION, "950.7.1 ") < 0);
    assert(alt111_setting_validate(ALTSET_SOURCEVERSION, "950..1") < 0);
    assert(alt111_setting_validate(ALTSET_DISPLAY_UUID, "zzzzzzzz-2222-4000-8000-000000000002") < 0);
    assert(!alt111_setting_validate(ALTSET_NAVIGATION_URL, "maps:/car/instrumentcluster/map?showETA=yes&maneuverLayout=leftAligned"));
    assert(alt111_setting_validate(ALTSET_NAVIGATION_URL, "maps:/car/instrumentcluster/map?showETA=yes&showETA=no") < 0);
    assert(alt111_setting_validate(ALTSET_NAVIGATION_URL, "http://elsewhere/") < 0);
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREA_0_SAFE_X, "1009", ALT111_TEMP));
    assert(alt111_settings_validate(&s, error, sizeof(error)) < 0);
    s = before;
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREAS_COUNT, "1", ALT111_TEMP));
    assert(alt111_settings_validate(&s, error, sizeof(error)) < 0);
    s = before;
    alt111_settings_policy(&s, &policy);
    assert(policy.mode == ALT111_SOURCE_FRAMES && policy.interval_frames == 20);
    assert(!alt111_settings_defaults(&before, "classic_single_view"));
    assert(!alt111_settings_defaults(&s, "mibr_dual_view"));
    assert(!alt111_settings_set(&s, ALTSET_SOURCEVERSION, "1.2.3", ALT111_TEMP));
    assert(!alt111_settings_set(&s, ALTSET_KEYFRAME_INTERVAL_FRAMES, "37", ALT111_TEMP));
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREA_SELECTED, "1", ALT111_TEMP));
    assert(!alt111_settings_set(&s, ALTSET_NAVIGATION_QUERY, "1", ALT111_TEMP));
    alt111_settings_runtime_overlay(&before, &s, ALT111_OVERLAY_LIVE);
    assert(!strcmp(before.value[ALTSET_SOURCEVERSION], "950.7.1"));
    assert(!strcmp(before.value[ALTSET_VIEWAREAS_COUNT], "1"));
    assert(!strcmp(before.value[ALTSET_VIEWAREA_0_SAFE_X], "202"));
    assert(!strcmp(before.value[ALTSET_VIEWAREA_SELECTED], "0"));
    assert(!strcmp(before.value[ALTSET_KEYFRAME_INTERVAL_FRAMES], "37"));
    assert(!strcmp(before.value[ALTSET_NAVIGATION_QUERY], "0"));
    alt111_settings_runtime_overlay(&before, &s, ALT111_OVERLAY_PRESENTATION);
    assert(!strcmp(before.value[ALTSET_NAVIGATION_QUERY], "1"));
    assert(!strcmp(before.value[ALTSET_VIEWAREAS_COUNT], "1"));
    puts("ALT111_SETTINGS_CORE_TEST=PASS");
    return 0;
}
