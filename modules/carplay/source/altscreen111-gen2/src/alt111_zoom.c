#include "alt111_zoom.h"
#include <limits.h>
#include <string.h>

static int live(const struct alt111_zoom *z, uint64_t session)
{
    return z && z->active && session && z->session == session;
}
static int allowed(const struct alt111_zoom *z)
{
    return z->vc_map_focus && z->source_visible && z->owner &&
           (z->positive_direction == 1 || z->positive_direction == -1);
}
static void discard(struct alt111_zoom *z)
{
    if (z->pending) z->dropped += (uint64_t)(z->pending < 0 ? -z->pending : z->pending);
    z->pending = 0;
    z->in_flight = 0;
    z->flight_request = 0;
    z->flight_sign = 0;
    z->next_ms = 0;
}
void alt111_zoom_init(struct alt111_zoom *z)
{
    if (z) memset(z, 0, sizeof(*z));
}
void alt111_zoom_begin(struct alt111_zoom *z, uint64_t session)
{
    if (!z) return;
    /* No command or verified VC focus is carried into another session. */
    memset(z, 0, sizeof(*z));
    if (session) { z->active = 1; z->session = session; }
}
void alt111_zoom_end(struct alt111_zoom *z)
{
    if (!z) return;
    discard(z);
    z->active = z->vc_map_focus = z->source_visible = z->owner = 0;
    z->positive_direction = 0;
    z->session = 0;
}
int alt111_zoom_context(struct alt111_zoom *z, uint64_t session,
                        unsigned vc_map_focus, unsigned source_visible,
                        unsigned current_owner)
{
    if (!live(z, session)) return ALT111_ZOOM_STALE;
    if (vc_map_focus > 1 || source_visible > 1 || current_owner > 1) return ALT111_ZOOM_INVALID;
    z->vc_map_focus = vc_map_focus;
    z->source_visible = source_visible;
    z->owner = current_owner;
    if (!allowed(z)) {
        discard(z);
        /* Never resurrect stale proof after the projection or VC page changes.
         * A later visibility recovery needs a NEW trusted focus/owner bind. */
        if (!vc_map_focus || !source_visible || !current_owner) {
            z->vc_map_focus = 0;
            z->owner = 0;
        }
    }
    return ALT111_ZOOM_OK;
}
int alt111_zoom_polarity(struct alt111_zoom *z, uint64_t session, int positive_direction)
{
    if (!live(z, session)) return ALT111_ZOOM_STALE;
    if (positive_direction != -1 && positive_direction != 0 && positive_direction != 1)
        return ALT111_ZOOM_INVALID;
    if (z->positive_direction != positive_direction) discard(z);
    z->positive_direction = positive_direction;
    return ALT111_ZOOM_OK;
}
int alt111_zoom_encoder(struct alt111_zoom *z, uint64_t session,
                        int keyboard, int encoder_id, int signed_steps,
                        int extra, int effective_validity)
{
    int next;
    if (!live(z, session)) return ALT111_ZOOM_STALE;
    if (keyboard != 4 || encoder_id != 40 || extra != 0 ||
        effective_validity != 1 || !signed_steps ||
        signed_steps < -ALT111_ZOOM_MAX_STEP || signed_steps > ALT111_ZOOM_MAX_STEP ||
        !allowed(z)) {
        ++z->rejected;
        return ALT111_ZOOM_WAIT;
    }
    next = z->pending + signed_steps;
    if (next > ALT111_ZOOM_BACKLOG) {
        z->dropped += (uint64_t)(next - ALT111_ZOOM_BACKLOG);
        next = ALT111_ZOOM_BACKLOG;
    } else if (next < -ALT111_ZOOM_BACKLOG) {
        z->dropped += (uint64_t)(-ALT111_ZOOM_BACKLOG - next);
        next = -ALT111_ZOOM_BACKLOG;
    }
    z->pending = next;
    ++z->accepted;
    return ALT111_ZOOM_OK;
}
enum alt111_zoom_route alt111_zoom_route_map_action(
    struct alt111_zoom *z, uint64_t session, unsigned semantic_action_verified,
    int keyboard, int encoder_id, int signed_steps,
    int extra, int effective_validity)
{
    int wanted;
    /*
     * A mere active source111 or raw DSI event is insufficient. This function
     * is exclusively for a PROVEN wheel-origin semantic OEM map-zoom branch.
     * All uncertainty and queue saturation leave the native branch intact.
     */
    if (!live(z, session) || semantic_action_verified != 1u ||
        !allowed(z) || keyboard != 4 || encoder_id != 40 ||
        extra != 0 || effective_validity != 1 ||
        signed_steps == 0 || signed_steps < -ALT111_ZOOM_MAX_STEP ||
        signed_steps > ALT111_ZOOM_MAX_STEP)
        return ALT111_ZOOM_ROUTE_STOCK;
    wanted = z->pending + signed_steps;
    if (wanted > ALT111_ZOOM_BACKLOG || wanted < -ALT111_ZOOM_BACKLOG)
        return ALT111_ZOOM_ROUTE_STOCK; /* never silently consume a detent */
    return alt111_zoom_encoder(z, session, keyboard, encoder_id, signed_steps,
                               extra, effective_validity) == ALT111_ZOOM_OK
        ? ALT111_ZOOM_ROUTE_CARPLAY : ALT111_ZOOM_ROUTE_STOCK;
}
int alt111_zoom_next(struct alt111_zoom *z, uint64_t session,
                     uint64_t now_ms, struct alt111_zoom_command *out)
{
    int sign;
    if (!out) return ALT111_ZOOM_INVALID;
    memset(out, 0, sizeof(*out));
    if (!live(z, session)) return ALT111_ZOOM_STALE;
    if (!allowed(z)) { discard(z); return ALT111_ZOOM_WAIT; }
    if (!z->pending || z->in_flight || now_ms < z->next_ms) return ALT111_ZOOM_WAIT;
    sign = z->pending > 0 ? 1 : -1;
    z->in_flight = 1;
    z->flight_sign = sign;
    z->flight_request = ++z->sequence;
    out->session = session;
    out->request = z->flight_request;
    out->direction = (sign == z->positive_direction) ? ALT111_ZOOM_IN : ALT111_ZOOM_OUT;
    return ALT111_ZOOM_OK;
}
int alt111_zoom_complete(struct alt111_zoom *z, uint64_t session,
                         uint64_t request, int accepted, uint64_t now_ms)
{
    if (!live(z, session) || !z->in_flight || z->flight_request != request) {
        if (z) ++z->stale;
        return ALT111_ZOOM_STALE;
    }
    if (accepted) {
        /* A reverse detent arriving during flight changes the desired target:
         * subtract the completed direction from the NEW pending target. */
        z->pending -= z->flight_sign;
        if (z->pending > ALT111_ZOOM_BACKLOG) {
            z->dropped += (uint64_t)(z->pending - ALT111_ZOOM_BACKLOG);
            z->pending = ALT111_ZOOM_BACKLOG;
        } else if (z->pending < -ALT111_ZOOM_BACKLOG) {
            z->dropped += (uint64_t)(-ALT111_ZOOM_BACKLOG - z->pending);
            z->pending = -ALT111_ZOOM_BACKLOG;
        }
        ++z->completed;
    } else {
        ++z->failed;
        discard(z); /* fail open: don't retry commands after uncertain failure */
    }
    z->in_flight = 0;
    z->flight_request = 0;
    z->flight_sign = 0;
    ++z->sent;
    z->next_ms = UINT64_MAX - now_ms < ALT111_ZOOM_MIN_GAP_MS
        ? UINT64_MAX : now_ms + ALT111_ZOOM_MIN_GAP_MS;
    return ALT111_ZOOM_OK;
}
