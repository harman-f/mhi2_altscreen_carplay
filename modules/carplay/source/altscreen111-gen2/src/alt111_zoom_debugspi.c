#include "alt111_zoom_debugspi.h"
#include <string.h>
#include <stdint.h>
static uint32_t be32(const unsigned char *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
}
static uint32_t diff_abs(uint32_t a, uint32_t b) {
    int32_t d=(int32_t)(a-b);
    return d<0 ? (uint32_t)(-(int64_t)d) : (uint32_t)d;
}
void alt111_spi_zoom_init(struct alt111_spi_zoom *s) {
    if(s) memset(s,0,sizeof(*s));
}
static void try_pair(struct alt111_spi_zoom *s, alt111_spi_zoom_cb cb, void *ctx) {
    if(!s->have_wheel || !s->have_tag) return;
    if(diff_abs(s->wheel_ms,s->tag_ms)<=ALT111_SPI_MATCH_WINDOW_MS) {
        /* One Tag56 AND one wheel record consumed per emitted event. */
        ++s->matches;
        if(cb) cb(ctx,s->wheel_ms,s->wheel_delta);
        s->have_wheel=s->have_tag=0;
        return;
    }
    /* Timestamps come from a single monotonic DebugSPI domain, though
     * trace records may be placed a few milliseconds out of order. */
    if((int32_t)(s->wheel_ms-s->tag_ms)>0) s->have_tag=0;
    else s->have_wheel=0;
}
static void frame(struct alt111_spi_zoom *s,const unsigned char *f,size_t n,
                  alt111_spi_zoom_cb cb,void *ctx) {
    const unsigned char *p;
    size_t pl;
    uint32_t timestamp,tag;
    int fields[5],i;
    ++s->frames;
    if(n<26 || memcmp(f+4,"\x80""MLP",4) ||
       be32(f+22)!=n-26 || f[20]!=1) return;
    p=f+26;pl=n-26;
    if(pl<39 || p[0]!=255 || p[1]!=1 || p[2]!=16) return;
    timestamp=be32(p+11);
    if(p[5]==0xf9 && p[6]==0x02 && pl==76 &&
       p[37]==0 && p[38]==0x2e &&
       be32(p+43)==4 && be32(p+47)==5) {
        for(i=0;i<5;i++) {
            if(p[51+5*i]!=1) return;
            fields[i]=(int32_t)be32(p+52+5*i);
        }
        if(fields[0]!=4 || fields[1]!=40 || fields[3]!=0 ||
           fields[4]!=1 || (fields[2]!=1 && fields[2]!=-1)) return;
        ++s->wheel_count;
        s->wheel_ms=timestamp;
        s->wheel_delta=fields[2];
        s->have_wheel=1;
        try_pair(s,cb,ctx);
    } else if(p[5]==0xf9 && p[6]==0x04 && pl==61) {
        tag=be32(p+35);
        if(tag!=56) return;
        ++s->tag_count;
        s->tag_ms=timestamp;
        s->have_tag=1;
        try_pair(s,cb,ctx);
    }
}
void alt111_spi_zoom_feed(struct alt111_spi_zoom *s,const void *bytes,size_t n,
                         alt111_spi_zoom_cb cb,void *ctx) {
    const unsigned char *p=(const unsigned char*)bytes;
    if(!s || (!p && n)) return;
    while(n) {
        size_t room=sizeof(s->buf)-s->used, chunk=n<room?n:room, need;
        if(!room) {s->used=0;++s->bad_frames;continue;}
        memcpy(s->buf+s->used,p,chunk);
        s->used+=chunk;p+=chunk;n-=chunk;
        while(s->used>=8) {
            if(memcmp(s->buf+4,"\x80""MLP",4)) {
                size_t i,at=0;
                for(i=5;i+4<=s->used;i++)
                    if(!memcmp(s->buf+i,"\x80""MLP",4)){at=i;break;}
                if(at>=4) {
                    memmove(s->buf,s->buf+at-4,s->used-(at-4));
                    s->used-=at-4;
                } else if(s->used>16) {
                    memmove(s->buf,s->buf+s->used-7,7);s->used=7;
                } else break;
                ++s->bad_frames;
                continue;
            }
            need=(size_t)be32(s->buf)+4u;
            if(need<26 || need>ALT111_SPI_FRAME_MAX) {
                memmove(s->buf,s->buf+1,--s->used);
                ++s->bad_frames;continue;
            }
            if(s->used<need) break;
            frame(s,s->buf,need,cb,ctx);
            memmove(s->buf,s->buf+need,s->used-need);
            s->used-=need;
        }
    }
}
