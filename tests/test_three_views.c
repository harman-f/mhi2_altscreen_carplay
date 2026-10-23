/* Three-view line: the patched settings core accepts up to three areas, nothing else changed. */
#include "../src/native/alt111-settings/include/alt111_settings.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    struct alt111_settings s, base;
    char error[256];
    assert(!alt111_settings_defaults(&base, "mibr_legacy"));
    assert(!alt111_settings_validate(&base, error, sizeof(error)));
    /* the three index values */
    assert(!alt111_setting_validate(ALTSET_VIEWAREA_SELECTED, "0"));
    assert(!alt111_setting_validate(ALTSET_VIEWAREA_SELECTED, "1"));
    assert(!alt111_setting_validate(ALTSET_VIEWAREA_SELECTED, "2"));
    assert(alt111_setting_validate(ALTSET_VIEWAREA_SELECTED, "3") < 0);
    assert(!alt111_setting_validate(ALTSET_VIEWAREAS_COUNT, "3"));
    assert(alt111_setting_validate(ALTSET_VIEWAREAS_COUNT, "4") < 0);
    assert(alt111_setting_validate(ALTSET_VIEWAREAS_COUNT, "0") < 0);
    assert(!alt111_setting_validate(ALTSET_VIEWAREAS_INITIAL, "2"));
    assert(alt111_setting_validate(ALTSET_VIEWAREAS_INITIAL, "3") < 0);
    /* count 3 with the Center index selected is a valid snapshot */
    s = base;
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREAS_COUNT, "3", ALT111_TEMP));
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREA_SELECTED, "2", ALT111_TEMP));
    assert(!alt111_settings_validate(&s, error, sizeof(error)));
    /* index 2 without three areas stays invalid */
    s = base;
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREA_SELECTED, "2", ALT111_TEMP));
    assert(alt111_settings_validate(&s, error, sizeof(error)) < 0);
    /* initial must stay inside the count */
    s = base;
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREAS_INITIAL, "2", ALT111_TEMP));
    assert(alt111_settings_validate(&s, error, sizeof(error)) < 0);
    /* geometry checks of the registry areas stay active with count 3 */
    s = base;
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREAS_COUNT, "3", ALT111_TEMP));
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREA_0_SAFE_X, "1009", ALT111_TEMP));
    assert(alt111_settings_validate(&s, error, sizeof(error)) < 0);
    /* the dual-view preset still requires exactly two areas */
    assert(!alt111_settings_defaults(&s, "mibr_dual_view"));
    assert(!alt111_settings_set(&s, ALTSET_VIEWAREAS_COUNT, "3", ALT111_TEMP));
    assert(alt111_settings_validate(&s, error, sizeof(error)) < 0);
    puts("THREE_VIEWS_CORE_TEST=PASS");
    return 0;
}
