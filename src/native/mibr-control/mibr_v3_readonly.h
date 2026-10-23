/* SPDX-License-Identifier: GPL-3.0-or-later
 * MIBR/3 read-only native application handler. No transport, writer or stream owner.
 */
#ifndef MIBR_V3_READONLY_H
#define MIBR_V3_READONLY_H
#include "alt111_settings.h"
#include "mibr_v3_runtime_observer.h"
#include <stddef.h>
struct mibr_v3_receipt {
    char rid[65];
    char frame[4097];
    char response[1024];
    size_t n;
    int materialized;
    int unchanged;
};
/* A route observer must independently prove current visible VC route and owner.
 * Caller serializes callbacks and the MIBR/3 handler. Zero is successful.
 * SOURCE111 merely connected or passive GEN2 status is NOT this proof. */
enum mibr_v3_visible_route { MIBR_ROUTE_UNKNOWN=0, MIBR_ROUTE_STOCK110=110,
                            MIBR_ROUTE_DIRECT111=111 };
struct mibr_v3_route_observation {
    enum mibr_v3_visible_route visible;
    uint64_t session, generation;
    int confirmed;
    char ack_request_id[65]; /* qualified actual owner correlation, blank = unknown */
};
typedef int (*mibr_v3_route_read_fn)(void *,struct mibr_v3_route_observation *);
/* Return 0 only after owner provides fresh verified target route, same
 * request/current owner; 1 = accepted but unconfirmed; -1 = proven NO dispatch;
 * -2 = dispatch outcome uncertain (e.g. lost ACK after possible side effect).
 * Other negative returns are treated as uncertain, never as safe retry.
 * Never implement with merely an unacknowledged /tmp marker write. */
typedef int (*mibr_v3_route_set_fn)(void *,enum mibr_v3_visible_route,
    const struct mibr_v3_route_observation *,const char *request_id,
    struct mibr_v3_route_observation *);
struct mibr_v3_route_receipt {
    char rid[65],frame[4097],response[1024];
    size_t n;
    enum mibr_v3_visible_route target;
    uint64_t expected_session, expected_generation;
    unsigned role;
    int active; /* last verified owner ACK; historical receipt, not current UI */
};
struct mibr_v3_reader {
    struct alt111_settings cached;
    int ready;
    struct alt111_settings_paths paths;
    /* NULL in the test read-only harness and on unqualified target media. */
    int (*durable_set)(void *,const struct alt111_settings_paths *,
        const struct alt111_settings *,unsigned,const char *,uint64_t,char *,size_t);
    void *storage_context;
    /* Optional (NULL = off): after a VERIFIED durable SET with materialized TEMP of a
     * PRESENTATION key, ask the EXISTING GEN2 current-session owner for one SHOW
     * (marker file). A request is never a completion ACK: the receipt stays
     * apply=PENDING;active=UNKNOWN. */
    int (*presentation_request)(void *,unsigned);
    void *presentation_context;
    /* r23: "CarPlay im Cockpit" pause (same pause file as the KEY40 long press) and cockpit SHOW confirmation.
     * Implemented by the service layer; this library only calls the hooks. */
    int (*carplay_pause)(void *,int enabled);
    int (*carplay_paused)(void *);
    void *carplay_context;
    int (*show_state)(void *,char *out,size_t cap);
    void *show_context;
    /* r46: engine type announced in the CarPlay Identify (iap2.cfg [vehicle] engine=), implemented by the service
     * layer through the unit helper script. op is "get" or "set"; out receives key=value lines. Returns 0 when the
     * helper ran and reported result=OK. */
    int (*engine_op)(void *,const char *op,const char *value,char *out,size_t cap);
    void *engine_context;
    /* r55: cockpit view follow (position counter, safe area per view), implemented by the service layer through the
     * unit helper mibr-view.ksh. op is "get" or "set"; for "set" key/value are already allowlisted by the caller;
     * out receives key=value lines. Returns 0 when the helper ran and reported result=OK. */
    int (*view_op)(void *,const char *op,const char *key,const char *value,char *out,size_t cap);
    void *view_context;
    /* r13 live-first hooks (implemented in the storage layer, never in this library). */
    int (*live_apply)(const struct alt111_settings_paths *,const struct alt111_settings *,unsigned,const char *,uint64_t *);
    int (*live_revert)(const struct alt111_settings_paths *,unsigned,const char *,uint64_t);
    /* r14 write-behind: live TEMP now, one coalesced durable flush after a quiet period.
     * persist_delay_ms==0 keeps the synchronous r13 behaviour. Unflushed values are lost on
     * power loss (profile stays the boot truth); .lastgood backup/rename is unchanged. */
    int persist_delay_ms,persist_max_ms,persist_pending;
    int persist_dirty[ALTSET_COUNT];
    char persist_old[ALTSET_COUNT][96];
    long long persist_first_ms,persist_last_ms;
    int stored_pending;
    int stored_verified;
    struct mibr_v3_runtime_observation runtime;
    /* Set only after independently qualified target owner + VC-visible readback.
     * A callback pointer or passive GEN2 status alone never unlocks ACTION. */
    int route_qualified;
    mibr_v3_route_read_fn route_read;
    mibr_v3_route_set_fn route_set;
    void *route_context;
    struct mibr_v3_route_receipt route_receipts[8];
    unsigned route_receipt_cursor;
    /* One owner transition maximum until independent original-RID ACK. A
     * pending/unknown owner result never permits a fresh competing ACTION. */
    int route_inflight;
    char route_inflight_rid[65];
    struct mibr_v3_receipt receipts[8];
    unsigned receipt_cursor;
};
enum mibr_v3_role { MIBR_V3_UI = 0, MIBR_V3_SHELL = 1, MIBR_V3_INPUT = 2 };
/* Boot warm: exactly one original-core resolved load. No fallback defaults. */
int mibr_v3_open(struct mibr_v3_reader *r, const struct alt111_settings_paths *paths);
/* Explicit, serialized invalidation/reload after a verified external change.
 * One staged original-core load; publication only on success. A failure keeps
 * prior bytes for diagnostics but marks NOT_READY (GET/SNAPSHOT fail closed).
 * Caller MUST serialize refresh with all handle calls; no periodic menu reads.
 * This is not a persistence, transport, or live runtime operation. */
int mibr_v3_refresh(struct mibr_v3_reader *r, const struct alt111_settings_paths *paths);
/* r14: run the coalesced durable flush when due (or when force!=0). Returns 0 when nothing
 * was pending or all values are durable, 1 when still pending/failed (retried later). */
int mibr_v3_flush_due(struct mibr_v3_reader *r,int force);
/* Frame bytes include final LF. out receives entire framed result or a bounded error. */
int mibr_v3_handle(struct mibr_v3_reader *r, enum mibr_v3_role role,
                   const char *frame, size_t length, char *out, size_t capacity);
#endif
