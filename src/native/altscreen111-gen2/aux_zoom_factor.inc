/* SPDX-License-Identifier: GPL-3.0-or-later
 * Optional phone-side logical zoom metadata, applied to the auxiliary clone
 * only. Percent 70 was observed working on one SEAT/CUPRA MU1409 target.
 * No assumption of iOS acceptance, pixel padding or physical cluster scaling.
 */
static int aux_zoom_percent(const char *text)
{
    const char *p;
    char *end = NULL;
    long value;
    if (!text || !*text) return 0;
    /* Strict decimal input: no signs, spaces, suffixes or fractions. */
    for (p = text; *p; ++p)
        if (*p < '0' || *p > '9') return -1;
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno || !end || *end || (value && (value < 70 || value > 150)))
        return -1;
    return (int)value;
}

static int apply_aux_zoom_factor(CFMutableDictionaryRef auxiliary)
{
    int percent = aux_zoom_percent(getenv("ALTSCREEN111_ZOOM_FACTOR"));
    if (percent < 0) {
        logf_u2("GEN2 auxiliary zoomFactor invalid; stock fallback");
        return -1;
    }
    /* Absent/zero preserves the existing advertisement exactly. */
    if (!percent) return 0;
    if (set_i64(auxiliary, "zoomFactor", (int64_t)percent)) return -1;
    logf_u2("GEN2 auxiliary zoomFactor advertised percent=%d phone_applied=UNKNOWN geometry_unchanged=1", percent);
    return 0;
}
