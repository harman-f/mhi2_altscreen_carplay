#ifndef MIBR_ALT111_ZOOM_H
#define MIBR_ALT111_ZOOM_H

#include <stdint.h>

/* Pure C99 source-111 zoom policy. Platform adapter serializes calls.
 * No I/O, hook, QNX API, background thread or OEM event suppression here.
 * A caller must obtain actual VC map focus independently: a negotiated
 * source111 session alone never licenses an injected CarPlay zoom. */
#define ALT111_ZOOM_MAX_STEP 16
#define ALT111_ZOOM_BACKLOG 12
#define ALT111_ZOOM_MIN_GAP_MS 140u

enum alt111_zoom_result {
    ALT111_ZOOM_OK = 0,
    ALT111_ZOOM_WAIT = 1,
    ALT111_ZOOM_INVALID = -1,
    ALT111_ZOOM_STALE = -2
};
enum alt111_zoom_direction {
    ALT111_ZOOM_IN = 0,
    ALT111_ZOOM_OUT = 1
};
struct alt111_zoom_command {
    uint64_t session, request;
    unsigned direction;
};
struct alt111_zoom {
    uint64_t session, sequence, next_ms, flight_request;
    int pending;             /* relative desired target less completed sends */
    int flight_sign;
    unsigned active, vc_map_focus, source_visible, owner, in_flight;
    /* Determined independently against a real native map-scale observation.
     * 0 = unknown: all encoder inputs are rejected. */
    int positive_direction;  /* +1 = +step zoom IN, -1 = +step zoom OUT */
    uint64_t accepted, rejected, dropped, sent, completed, failed, stale;
};
void alt111_zoom_init(struct alt111_zoom *z);
void alt111_zoom_begin(struct alt111_zoom *z, uint64_t session);
void alt111_zoom_end(struct alt111_zoom *z);
int alt111_zoom_context(struct alt111_zoom *z, uint64_t session,
                        unsigned vc_map_focus, unsigned source_visible,
                        unsigned current_owner);
int alt111_zoom_polarity(struct alt111_zoom *z, uint64_t session,
                         int positive_direction);
int alt111_zoom_encoder(struct alt111_zoom *z, uint64_t session,
                        int keyboard, int encoder_id, int signed_steps,
                        int extra, int effective_validity);
/*
 * Candidate semantic OEM map-scale interception policy, host-only until the
 * exact MU1440 native zoom side-effect callsite and wheel-origin correlation
 * are proven. Caller MUST invoke this at that one specific OEM zoom branch,
 * never on the global DSI dispatcher. Preserve OEM BAP ACK/status and all
 * other listeners; do not call alt111_zoom_encoder separately for the same
 * detent. STOCK means execute original native zoom branch.
 * CARPLAY means a zoom intent was accepted into our retained 111 queue and
 * caller may skip ONLY the native zoom side effect. Submission is async; it
 * is not proof the iPhone app visually zoomed.
 */
enum alt111_zoom_route {
    ALT111_ZOOM_ROUTE_STOCK = 0,
    ALT111_ZOOM_ROUTE_CARPLAY = 1
};
enum alt111_zoom_route alt111_zoom_route_map_action(
    struct alt111_zoom *z, uint64_t session, unsigned semantic_action_verified,
    int keyboard, int encoder_id, int signed_steps,
    int extra, int effective_validity);
int alt111_zoom_next(struct alt111_zoom *z, uint64_t session,
                     uint64_t now_ms, struct alt111_zoom_command *out);
int alt111_zoom_complete(struct alt111_zoom *z, uint64_t session,
                         uint64_t request, int accepted, uint64_t now_ms);
#endif
