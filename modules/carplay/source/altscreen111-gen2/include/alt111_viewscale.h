#ifndef ALT111_VIEWSCALE_H
#define ALT111_VIEWSCALE_H
/* per-view 111 zoom transition coordinator (pure, host-testable).
 *
 * One transition at a time. Latest request wins, but a new run starts only after
 * the running one is CONFIRMED, FAILED/ROLLED_BACK or timed out. A run counts as
 * CONFIRMED only when, after its start, the phone set up stream 111 again AND a
 * phone/preflight /info build advertised the target zoom. Sending a command is
 * never "applied". On timeout exactly one restore (111 re-added with the last
 * confirmed zoom) is requested; there is no retry loop. A full-session teardown
 * resets everything: the next connect advertises the selected view's zoom.
 *
 * No I/O, no locks, no clock: the caller owns all of that. */
#include <stdint.h>

#define ALT111_VS_ZOOM_CAP 8u

enum alt111_vs_state {
    ALT111_VS_IDLE = 0,
    ALT111_VS_APPLYING,
    ALT111_VS_CONFIRMED,
    ALT111_VS_RESTORING,
    ALT111_VS_ROLLED_BACK,
    ALT111_VS_FAILED,
    ALT111_VS_PENDING_RECONNECT
};

enum alt111_vs_action {
    ALT111_VS_ACT_NONE = 0,
    ALT111_VS_ACT_START,     /* send the P8 operation with vs->target */
    ALT111_VS_ACT_RESTORE    /* send 111 re-add with vs->active (once) */
};

struct alt111_vs_config {
    unsigned enabled;
    unsigned min_interval_ms;   /* between the END of one run and the next start */
    unsigned confirm_timeout_ms;
};

struct alt111_vs {
    enum alt111_vs_state state;
    char active[ALT111_VS_ZOOM_CAP];   /* last zoom the phone verifiably got ("" = unknown) */
    char target[ALT111_VS_ZOOM_CAP];   /* zoom of the running/last run */
    char want[ALT111_VS_ZOOM_CAP];     /* latest requested zoom ("" = none) */
    unsigned want_area, target_area;
    unsigned have_want;
    uint64_t started_ms, ended_ms;
    unsigned seen_setup111, seen_info_target, fail_now;
    uint64_t runs, confirmed, failed, restored, skipped_same, deferred, pending_reconnect;
    char last_result[32];
};

void alt111_vs_init(struct alt111_vs *vs);
/* Latest wins. zoom is "70".."150" or "AUTO"; AUTO cannot be switched live. */
void alt111_vs_request(struct alt111_vs *vs, unsigned area, const char *zoom);
/* Decide the next action. On START/RESTORE the caller sends and reports with
 * alt111_vs_sent(). */
enum alt111_vs_action alt111_vs_tick(struct alt111_vs *vs, const struct alt111_vs_config *cfg, uint64_t now_ms);
void alt111_vs_sent(struct alt111_vs *vs, enum alt111_vs_action act, int ok, uint64_t now_ms);
/* Observations from the receiver. internal builds (probe descriptor) must NOT be reported. */
void alt111_vs_observe_info(struct alt111_vs *vs, const char *zoom, uint64_t now_ms);
void alt111_vs_observe_setup111(struct alt111_vs *vs, uint64_t now_ms);
void alt111_vs_observe_full_teardown(struct alt111_vs *vs);
/* Zoom /info must advertise: during a run the target, while restoring the last
 * confirmed zoom; NULL = use the selected view's zoom (normal connect). */
const char *alt111_vs_advert_zoom(const struct alt111_vs *vs);
const char *alt111_vs_state_name(enum alt111_vs_state s);

#endif
