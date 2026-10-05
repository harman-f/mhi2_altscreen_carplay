/* Compile the actual implementation, with its CLI renamed, for boundary tests. */
#define main parity_cli_main
#include "../src/native/direct-ts-parity/direct_ts_parity.c"
#undef main
#include <assert.h>

static const uint8_t config[] = {0,0,0,1,0x67,0x42,0,0x1f,0,0,0,1,0x68,0xce};
static const uint8_t primed[] = {0,0,0,1,0x67,0x42,0,0x1f,0,0,0,1,0x68,0xce,
                               0,0,0,1,9,0xf0,0,0,0,1,0x65,0x88};
static const uint8_t partial[] = {0,0,0,1,0x68,0xcf,0,0,0,1,9,0xf0,0,0,0,1,0x65,0x89};

static void assert_types(const uint8_t *p,size_t n) {
    const int types[]={9,7,8,5};
    size_t sc=0,nal=0;unsigned count=0;int type;
    while((type=annexb_nal_type(p,n,&sc,&nal))>=0) {
        assert(count<4 && type==types[count++]);sc=nal+1;
    }
    assert(count==4);
}

int main(void) {
    uint8_t *cache=NULL,*out=NULL;size_t cn=0,on=0;struct clock_state c;
    uint64_t first,next,rebases;int rb;
    assert(extract_param_sets(config,sizeof(config),&cache,&cn)==0);
    assert(normalize_au(primed,sizeof(primed),1,&cache,&cn,&out,&on)==0);
    assert_types(out,on);free(out);
    assert(normalize_au(partial,sizeof(partial),1,&cache,&cn,&out,&on)==0);
    assert_types(out,on);assert(au_has_type(cache,cn,7));assert(au_has_type(cache,cn,8));free(out);free(cache);
    memset(&c,0,sizeof(c));pthread_mutex_init(&c.lock,NULL);c.transport_pcr90k=45000;
    first=assign_pts(&c,0xc0000000u,0xffffffffu,&rb);
    next=assign_pts(&c,0x40000000u,0u,&rb);
    assert(next-first==45000u);assert(c.source_rebases==0);
    c.have_origin=0;c.have_previous_source=0;
    first=assign_pts(&c,0xe0000000u,0xffffffffu,&rb);
    next=assign_pts(&c,0u,0u,&rb);
    assert(next-first==11250u); /* exact zero is valid at rollover */
    c.have_origin=0;c.have_previous_source=0;
    (void)assign_pts(&c,0,100,&rb);
    (void)assign_pts(&c,0x40000000u,100,&rb);
    rebases=c.source_rebases;
    (void)assign_pts(&c,0x20000000u,100,&rb);
    assert(c.source_rebases>rebases); /* rollback above the original origin */
    rebases=c.source_rebases;
    next=assign_pts(&c,0,3700,&rb);
    assert(c.source_rebases>rebases);assert(next<c.transport_pcr90k+90000u);
    pthread_mutex_destroy(&c.lock);
    puts("PARITY_BOUNDARY_REGRESSIONS=PASS AUD SPS_PPS borrow rollover rollback forward_jump");
    return 0;
}
