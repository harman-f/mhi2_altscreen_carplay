/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_SEAT_ZOOM_EPOCH_H
#define MIBR_SEAT_ZOOM_EPOCH_H
#include <stdint.h>
struct seat_zoom_epoch {
    uint64_t session,stream,codec,consumer;
    uint32_t since_ms;
    unsigned valid;
};
static int seat_zoom_epoch_update(struct seat_zoom_epoch *e,uint64_t session,
        uint64_t stream,uint64_t codec,uint64_t consumer,unsigned eligible,uint32_t now)
{
    int changed=!e->valid || !eligible || e->session!=session ||
        e->stream!=stream || e->codec!=codec || e->consumer!=consumer;
    if(changed){
        e->session=session;e->stream=stream;e->codec=codec;e->consumer=consumer;
        e->since_ms=now;e->valid=eligible?1u:0u;
    }
    return changed;
}
static unsigned seat_zoom_epoch_fresh(const struct seat_zoom_epoch *e,
                                      uint32_t source_ms,uint32_t now)
{
    int32_t age=(int32_t)(now-source_ms);
    return e->valid && age>=-40 && age<=500 &&
        (int32_t)(source_ms-e->since_ms)>=0;
}
#endif
