#include "mvs_core.h"
#include <stdio.h>
#include <string.h>

/* Entire module is a pure formatter/state machine: NO CAN, no OS, no sockets. */
#define DAY_MS 86400000ull
#define MAX_SPEED_MMPS 100000u
#define STALE_MS 1000ull
#define BATCH_MS 800ull
#define GAP_MS 2000ull

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static uint64_t le64(const uint8_t *p) {
    return (uint64_t)le32(p) | ((uint64_t)le32(p+4)<<32);
}
static void put32(uint8_t *p, uint32_t v) {
    p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8);
    p[2]=(uint8_t)(v>>16); p[3]=(uint8_t)(v>>24);
}
static void put64(uint8_t *p, uint64_t v) {
    put32(p,(uint32_t)v); put32(p+4,(uint32_t)(v>>32));
}
static int valid(const mvs_sample *s) {
    if (!s || (s->flags & ~MVS_VALID_MASK)) return 0;
    if (!(s->flags & MVS_VALID_SPEED) && s->speed_mmps) return 0;
    if ((s->flags & MVS_STANDSTILL) &&
        (!(s->flags & MVS_VALID_SPEED) || s->speed_mmps)) return 0;
    if ((s->flags & MVS_REVERSE) && !(s->flags & MVS_GEAR_VALID)) return 0;
    return s->speed_mmps <= MAX_SPEED_MMPS;
}
int mvs_wire_encode(const mvs_sample *s, uint8_t *out, size_t cap) {
    if (!valid(s) || !out || cap < MVS_WIRE_BYTES) return -1;
    memset(out,0,MVS_WIRE_BYTES);
    memcpy(out,"MVS1",4);
    out[4]=1;
    out[5]=s->flags;
    put64(out+8,s->sample_ms);
    put32(out+16,s->speed_mmps);
    put32(out+20,s->source_seq);
    return 0;
}
int mvs_wire_decode(const uint8_t *p, size_t n, mvs_sample *out) {
    mvs_sample t;
    if (!p || !out || n != MVS_WIRE_BYTES || memcmp(p,"MVS1",4) ||
        p[4]!=1 || p[6]!=0 || p[7]!=0) return -1;
    t.flags=p[5];
    t.sample_ms=le64(p+8);
    t.speed_mmps=le32(p+16);
    t.source_seq=le32(p+20);
    if (!valid(&t)) return -1;
    *out=t;
    return 0;
}
void mvs_reset(mvs_engine *e) { if (e) memset(e,0,sizeof(*e)); }
void mvs_set_identify_speed(mvs_engine *e, int confirmed) {
    if (!e) return;
    e->identify_speed_advertised=(confirmed==1);
    e->phone_wants_speed=0;
    e->stock_pascd_seen=0;
    e->count=0;
    e->have_last=0;
}
int mvs_start_location(mvs_engine *e,const uint8_t *p,size_t n) {
    size_t off=0;
    int speed=0;
    if (!e) return -1;
    e->phone_wants_speed=0; e->count=0;
    if (!p || !n || !e->identify_speed_advertised || e->stock_pascd_seen)
        return 0;
    while (off<n) {
        unsigned len,id;
        if (n-off<4) return -1;
        len=((unsigned)p[off]<<8)|p[off+1];
        id=((unsigned)p[off+2]<<8)|p[off+3];
        if (len<4 || len>n-off) return -1;
        if (id==4) { /* StartLocationInformation VehicleSpeedData */
            if (speed || len!=4) return -1;
            speed=1;
        }
        off+=len;
    }
    e->phone_wants_speed=speed;
    return speed;
}
void mvs_stop_location(mvs_engine *e) {
    if (!e) return;
    e->phone_wants_speed=0; e->count=0;
}
void mvs_stock_pascd_observed(mvs_engine *e) {
    if (!e) return;
    e->stock_pascd_seen=1; e->phone_wants_speed=0;
    e->count=0;
}
static int sentence(const mvs_sample *s,unsigned n,char *out,size_t cap) {
    unsigned i; size_t used; int k; unsigned char crc=0;
    char gear='D';
    uint64_t ref;
    if (!n || n>MVS_BATCH || !out || !cap) return -1;
    for (i=0;i<n;i++) {
        if ((s[i].flags & (MVS_GEAR_VALID|MVS_REVERSE)) ==
            (MVS_GEAR_VALID|MVS_REVERSE)) gear='R';
        else if (!(s[i].flags & MVS_GEAR_VALID) && gear!='R') gear='U';
    }
    ref=s[0].sample_ms%DAY_MS;
    k=snprintf(out,cap,"$PASCD,%llu.%03u,C,%c,0,%u",
        (unsigned long long)(ref/1000ull),(unsigned)(ref%1000ull),gear,n);
    if (k<0 || (size_t)k>=cap) return -1;
    used=(size_t)k;
    for (i=0;i<n;i++) {
        uint64_t dt=s[i].sample_ms-s[0].sample_ms;
        uint64_t centis=(dt+5ull)/10ull;
        k=snprintf(out+used,cap-used,",%llu.%02u,%u.%03u",
            (unsigned long long)(centis/100ull),(unsigned)(centis%100ull),
            (unsigned)(s[i].speed_mmps/1000u),
            (unsigned)(s[i].speed_mmps%1000u));
        if (k<0 || (size_t)k>=cap-used) return -1;
        used+=(size_t)k;
    }
    for (i=1;i<used;i++) crc^=(unsigned char)out[i];
    k=snprintf(out+used,cap-used,"*%02X",(unsigned)crc);
    if (k!=3 || (size_t)k>=cap-used) return -1;
    return (int)(used+(size_t)k);
}
int mvs_ingest(mvs_engine *e,const uint8_t *wire,size_t n,uint64_t now_ms,
               char *out,size_t cap) {
    mvs_sample s;
    int result;
    if (!e || !out || !cap || mvs_wire_decode(wire,n,&s)) {
        if(e) e->count=0;
        return -1;
    }
    out[0]=0;
    if (e->have_last) {
        uint32_t seq_delta=(uint32_t)(s.source_seq-e->last_source_seq);
        /* Unsigned subtraction accepts the natural uint32 wrap for the next
         * event (delta=1), rejects duplicate/backward replay, and allows a
         * forward loss to start a fresh interval. Never roll back watermarks. */
        if (!seq_delta || (seq_delta & 0x80000000u) ||
            s.sample_ms<=e->last_sample_ms) return 0;
        if (s.sample_ms-e->last_sample_ms>GAP_MS || seq_delta!=1u)
            e->count=0;
    }
    e->last_source_seq=s.source_seq;
    e->last_sample_ms=s.sample_ms;
    e->have_last=1;
    /* Keep the source watermark for structurally valid but stale/invalid
     * events so replaying an older valid sample cannot revive a dead batch. */
    if (!(s.flags & MVS_VALID_SPEED) || now_ms<s.sample_ms ||
        now_ms-s.sample_ms>STALE_MS) {
        e->count=0; return 0;
    }
    if (!e->identify_speed_advertised || !e->phone_wants_speed ||
        e->stock_pascd_seen) { e->count=0; return 0; }
    /* The oldest buffered event must still be fresh when the batch is sent.
     * A fresh arrival can otherwise flush an expired pending interval. */
    if (e->count && now_ms-e->samples[0].sample_ms>STALE_MS) e->count=0;
    if (!e->count) { e->samples[e->count++]=s; return 0; }
    if (s.sample_ms-e->samples[0].sample_ms<BATCH_MS) {
        if (e->count<MVS_BATCH) e->samples[e->count++]=s;
        /* >5 very fast samples: retain earliest true 5, never synthesize. */
        return 0;
    }
    if (e->count<MVS_BATCH) e->samples[e->count++]=s;
    result=sentence(e->samples,e->count,out,cap);
    if (result<0) { e->count=0; return -1; }
    if (e->samples[e->count-1].source_seq==s.source_seq) e->count=0;
    else { e->samples[0]=s; e->count=1; }
    return result;
}
static int hex(unsigned char c) {
    if (c>='0'&&c<='9') return c-'0';
    if (c>='A'&&c<='F') return c-'A'+10;
    return -1;
}
size_t mvs_location_tlv(const char *s,uint8_t *out,size_t cap) {
    size_t n,i,star=0; unsigned char crc=0; unsigned len;
    if (!s || !out) return 0;
    /* Never make an unbounded strlen() walk across a malformed IPC buffer. */
    for (n=0;n<MVS_SENTENCE_BYTES && s[n];n++) { }
    if (n>=MVS_SENTENCE_BYTES || n<12 || n+5u>cap ||
        n+5u>65535u || strncmp(s,"$PASCD,",7)) return 0;
    for(i=1;i<n;i++) {
        if (s[i]=='*') { star=i; break; }
        if ((unsigned char)s[i]<32 || (unsigned char)s[i]>126) return 0;
        crc^=(unsigned char)s[i];
    }
    if (!star || star+3!=n || hex((unsigned char)s[star+1])<0 ||
        hex((unsigned char)s[star+2])<0 ||
        ((hex((unsigned char)s[star+1])<<4)|hex((unsigned char)s[star+2]))!=crc)
        return 0;
    len=(unsigned)(n+5u); /* TLV header 4 + sentence NUL */
    out[0]=(uint8_t)(len>>8); out[1]=(uint8_t)len;
    out[2]=0; out[3]=0; memcpy(out+4,s,n+1);
    return len;
}
