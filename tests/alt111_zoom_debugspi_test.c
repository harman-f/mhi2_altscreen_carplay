#include "alt111_zoom_debugspi.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static void put32(unsigned char *p,uint32_t v) {
    p[0]=(unsigned char)(v>>24);p[1]=(unsigned char)(v>>16);
    p[2]=(unsigned char)(v>>8);p[3]=(unsigned char)v;
}
struct observed { int direction[20]; uint32_t stamp[20]; unsigned n; };
static void got(void *v,uint32_t stamp,int sign) {
    struct observed *o=v; assert(o->n<20);
    o->stamp[o->n]=stamp;o->direction[o->n++]=sign;
}
static size_t mkframe(unsigned char *f,size_t cap,int subtype,uint32_t t,
                      int id,int delta,int valid,int tag) {
    unsigned char *p;
    size_t pl=subtype==2?76u:61u,n=26u+pl;
    int i;
    assert(n<=cap);memset(f,0,n);put32(f,(uint32_t)n-4u);
    memcpy(f+4,"\x80""MLP",4);f[20]=1;put32(f+22,(uint32_t)pl);
    p=f+26;p[0]=255;p[1]=1;p[2]=16;p[5]=0xf9;p[6]=(unsigned char)subtype;
    put32(p+11,t);
    if(subtype==2) {
        int fields[5]={4,id,delta,0,valid};
        p[37]=0;p[38]=0x2e;put32(p+43,4);put32(p+47,5);
        for(i=0;i<5;i++) {p[51+5*i]=1;put32(p+52+5*i,(uint32_t)fields[i]);}
    } else put32(p+35,(uint32_t)tag);
    return n;
}
static void split(struct alt111_spi_zoom *s,const unsigned char *f,size_t n,
                  struct observed *o) {
    alt111_spi_zoom_feed(s,f,3,got,o);
    alt111_spi_zoom_feed(s,f+3,7,got,o);
    alt111_spi_zoom_feed(s,f+10,n-10,got,o);
}
int main(void) {
    static const int signs[11]={1,1,1,1,1,-1,-1,-1,-1,-1,-1};
    static const uint32_t wheel[11]={
      1000u,1500u,2000u,2500u,3000u,3500u,4000u,4500u,5000u,5500u,6000u};
    static const uint32_t tag[11]={
      1028u,1497u,2014u,2507u,3017u,3503u,4014u,4489u,5011u,5518u,6021u};
    struct alt111_spi_zoom s;struct observed o;unsigned char f[128];size_t n;int i;
    memset(&o,0,sizeof o);alt111_spi_zoom_init(&s);
    /* One left encoder, one wrong subtype/tag, one unmatched wheel,
     * none may emit. */
    n=mkframe(f,sizeof f,2,100,44,1,1,0);split(&s,f,n,&o);
    n=mkframe(f,sizeof f,4,105,40,1,1,7);split(&s,f,n,&o);
    n=mkframe(f,sizeof f,2,200,40,1,0,0);split(&s,f,n,&o);
    n=mkframe(f,sizeof f,2,300,40,1,1,0);split(&s,f,n,&o);
    assert(o.n==0);
    /* This tag is >40ms later than the unmatched wheel. */
    n=mkframe(f,sizeof f,4,400,40,1,1,56);split(&s,f,n,&o);
    assert(o.n==0);
    /* Drain outdated tag without accidentally pairing it with a later wheel. */
    n=mkframe(f,sizeof f,2,500,40,1,1,0);split(&s,f,n,&o);
    assert(o.n==0);
    /* Synthetic timestamp/sign pairs: one record can be
     * logged slightly before its wheel event, i.e. pairing is bidirectional.
     * No OEM payloads or private identifiers are used in the fixture. */
    for(i=0;i<11;i++) {
        if(tag[i]<wheel[i]) {
            n=mkframe(f,sizeof f,4,tag[i],40,1,1,56);split(&s,f,n,&o);
            n=mkframe(f,sizeof f,2,wheel[i],40,signs[i],1,0);split(&s,f,n,&o);
        } else {
            n=mkframe(f,sizeof f,2,wheel[i],40,signs[i],1,0);split(&s,f,n,&o);
            n=mkframe(f,sizeof f,4,tag[i],40,1,1,56);split(&s,f,n,&o);
        }
        assert(o.n==(unsigned)i+1u);
        assert(o.direction[i]==signs[i] && o.stamp[i]==wheel[i]);
    }
    assert(s.matches==11);
    /* Every event consumes both halves, so a duplicate tag cannot emit. */
    n=mkframe(f,sizeof f,4,tag[10],40,1,1,56);split(&s,f,n,&o);
    assert(o.n==11);
    /* A fresh source session near rollover must accept signed wraparound.
     * The preceding test left an intentionally unmatched stale Tag56; a real
     * read idle period / reconnect expires that incomplete pair. */
    alt111_spi_zoom_init(&s);
    n=mkframe(f,sizeof f,2,0xfffffffbu,40,1,1,0);split(&s,f,n,&o);
    n=mkframe(f,sizeof f,4,5u,40,1,1,56);split(&s,f,n,&o);
    assert(o.n==12 && o.direction[11]==1 && s.matches==1);
    puts("alt111_zoom_debugspi host PASS: eleven synthetic timestamp pairs, split MLP, negatives, wrap");
    return 0;
}
