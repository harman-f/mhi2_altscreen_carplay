#include "alt111.h"
#include <string.h>

#define ALT111_BRIDGE_STABLE_MS 1000u
static int snapshot_ready(const struct alt111_resync_snapshot *s,unsigned reason)
{
    return s && s->projection_desired && s->config_valid &&
           (s->consumer_primed || reason==ALT111_RESYNC_REASON_OVERFLOW) &&
           s->stream && s->codec && s->consumer;
}
static uint64_t after(uint64_t now,uint32_t delay)
{
    return UINT64_MAX-now<delay ? UINT64_MAX : now+delay;
}
void alt111_resync_init(struct alt111_resync *r)
{
    if (!r) return;
    memset(r, 0, sizeof(*r));
    r->state = ALT111_RESYNC_SYNCED;
    r->retry_ms = ALT111_RESYNC_RETRY_MIN_MS;
}
void alt111_resync_set_enabled(struct alt111_resync *r, unsigned enabled)
{
    if (!r) return;
    r->enabled = enabled ? 1u : 0u;
    if (!r->enabled && r->state != ALT111_RESYNC_SYNCED)
        alt111_resync_cancel(r, ALT111_RESYNC_CANCEL_DISABLED);
}
void alt111_resync_cancel(struct alt111_resync *r, unsigned reason)
{
    if (!r || r->state == ALT111_RESYNC_SYNCED) return;
    r->state = ALT111_RESYNC_SYNCED;
    r->cancel_reason = reason;
    r->cancels++;
    r->next_request_ms = 0;
    r->candidate_idr_ordinal = r->bridge_seen_ms = 0;
    r->bridge_first_blocks=r->bridge_first_sample_us=0;
    r->retry_ms = ALT111_RESYNC_RETRY_MIN_MS;
}
int alt111_resync_arm(struct alt111_resync *r, uint64_t now_ms,
                      unsigned reason,const struct alt111_resync_snapshot *s)
{
    if (!r || !s) return ALT111_INVALID;
    if (!r->enabled || !snapshot_ready(s,reason)) return ALT111_WAIT;
    if (r->state != ALT111_RESYNC_SYNCED) return ALT111_BUSY;
    r->state=ALT111_RESYNC_NEED_IDR;
    r->reason=reason;r->cancel_reason=ALT111_RESYNC_REASON_NONE;
    ++r->epoch;
    r->stream_at_arm=s->stream;r->codec_at_arm=s->codec;
    r->consumer_at_arm=s->consumer;
    r->au_at_arm=s->source_aus;r->idr_at_arm=s->source_idrs;
    r->overflow_at_arm=s->soft_recovery_epoch;
    r->candidate_idr_ordinal=r->bridge_seen_ms=0;
    r->bridge_first_blocks=r->bridge_first_sample_us=0;
    r->last_request_ms=0;r->next_request_ms=now_ms;
    r->completed_ms=0;r->retry_ms=ALT111_RESYNC_RETRY_MIN_MS;
    return ALT111_OK;
}
enum alt111_resync_action
alt111_resync_tick(struct alt111_resync *r, uint64_t now_ms,
                   const struct alt111_resync_snapshot *s)
{
    uint32_t delay;
    if (!r || !s || r->state==ALT111_RESYNC_SYNCED) return ALT111_RESYNC_NONE;
    if (!r->enabled) {
        alt111_resync_cancel(r,ALT111_RESYNC_CANCEL_DISABLED);
        return ALT111_RESYNC_CANCELLED;
    }
    if (!s->projection_desired) {
        alt111_resync_cancel(r,ALT111_RESYNC_CANCEL_PROJECTION);
        return ALT111_RESYNC_CANCELLED;
    }
    if (!s->config_valid) {
        alt111_resync_cancel(r,ALT111_RESYNC_CANCEL_CONFIG);
        return ALT111_RESYNC_CANCELLED;
    }
    if (!s->consumer) {
        alt111_resync_cancel(r,ALT111_RESYNC_CANCEL_CONSUMER);
        return ALT111_RESYNC_CANCELLED;
    }
    if (s->stream!=r->stream_at_arm) {
        alt111_resync_cancel(r,ALT111_RESYNC_CANCEL_STREAM);
        return ALT111_RESYNC_CANCELLED;
    }
    if (s->codec!=r->codec_at_arm) {
        alt111_resync_cancel(r,ALT111_RESYNC_CANCEL_CODEC);
        return ALT111_RESYNC_CANCELLED;
    }
    if (s->consumer!=r->consumer_at_arm) {
        alt111_resync_cancel(r,ALT111_RESYNC_CANCEL_CONSUMER_GEN);
        return ALT111_RESYNC_CANCELLED;
    }
    /* A new overload invalidates any previous candidate even if a stale
     * parity status file still reports an earlier completed IDR. */
    if(s->soft_recovery_epoch!=r->overflow_at_arm){
        r->overflow_at_arm=s->soft_recovery_epoch;
        r->au_at_arm=s->source_aus;r->idr_at_arm=s->source_idrs;
        r->candidate_idr_ordinal=r->bridge_seen_ms=0;
        r->bridge_first_blocks=r->bridge_first_sample_us=0;
        r->state=ALT111_RESYNC_NEED_IDR;
        r->next_request_ms=now_ms;
    }
    if(r->state==ALT111_RESYNC_NEED_IDR &&
       s->source_idrs>r->idr_at_arm && s->delivered_idr_ordinal>r->au_at_arm){
        r->candidate_idr_ordinal=s->delivered_idr_ordinal;
        ++r->source_recoveries;
        r->state=ALT111_RESYNC_NEED_BRIDGE;
        r->next_request_ms=after(now_ms,ALT111_RESYNC_RETRY_MAX_MS);
        return ALT111_RESYNC_SOURCE_RECOVERED;
    }
    if(r->state==ALT111_RESYNC_NEED_BRIDGE){
        if(s->bridge_healthy && s->bridge_idr_ordinal>=r->candidate_idr_ordinal){
            if(!r->bridge_seen_ms){
                r->bridge_seen_ms=now_ms ? now_ms : 1u;
                r->bridge_first_blocks=s->bridge_blocks;
                r->bridge_first_sample_us=s->bridge_sample_us;
            }
            /* A frozen writer sample is not evidence of continued health. */
            if(now_ms>=r->bridge_seen_ms &&
               now_ms-r->bridge_seen_ms>=ALT111_BRIDGE_STABLE_MS &&
               s->bridge_sample_us>r->bridge_first_sample_us &&
               s->bridge_blocks>r->bridge_first_blocks){
                r->state=ALT111_RESYNC_SYNCED;
                ++r->completions;r->completed_ms=now_ms;
                r->next_request_ms=0;r->retry_ms=ALT111_RESYNC_RETRY_MIN_MS;
                return ALT111_RESYNC_COMPLETED;
            }
            return ALT111_RESYNC_NONE;
        }
        r->bridge_seen_ms=0;
        r->bridge_first_blocks=r->bridge_first_sample_us=0;
        if(now_ms<r->next_request_ms)return ALT111_RESYNC_NONE;
        /* Writer has not confirmed the same generation+ordinal: retry with
         * a NEW source/consumer candidate; never claim VC presentation. */
        r->state=ALT111_RESYNC_NEED_IDR;
        r->au_at_arm=s->source_aus;r->idr_at_arm=s->source_idrs;
        r->candidate_idr_ordinal=0;
    }
    if(now_ms<r->next_request_ms)return ALT111_RESYNC_NONE;
    if(r->last_request_ms)++r->retries;
    ++r->requests;r->last_request_ms=now_ms;
    delay=r->retry_ms ? r->retry_ms : ALT111_RESYNC_RETRY_MIN_MS;
    r->next_request_ms=after(now_ms,delay);
    if(delay<ALT111_RESYNC_RETRY_MAX_MS){
        delay*=2u;
        if(delay>ALT111_RESYNC_RETRY_MAX_MS)delay=ALT111_RESYNC_RETRY_MAX_MS;
        r->retry_ms=delay;
    }
    return ALT111_RESYNC_REQUEST_KEYFRAME;
}
