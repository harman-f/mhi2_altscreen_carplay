/* Actual bridge functions with a deterministic nonblocking device stand-in. */
#include <sys/types.h>
#include <unistd.h>
#include <errno.h>
#include <assert.h>
static ssize_t simulated_write(int fd, const void *p, size_t n);
#define write simulated_write
#define main parity_cli_main
#include "../src/native/direct-ts-parity/direct_ts_parity.c"
#undef main
#undef write
static unsigned attempts, accepts;
static int fail_write;
static struct au_queue *active_queue;
static ssize_t simulated_write(int fd, const void *p, size_t n) {
    if(fd!=10000)return write(fd,p,n);
    assert(n==12032u);
    ++attempts;
    if(fail_write){errno=EIO;return -1;}
    if(attempts&1u){errno=EAGAIN;return -1;}
    usleep(9000);
    if(++accepts==4u){
        pthread_mutex_lock(&active_queue->lock);active_queue->input_done=1;
        pthread_mutex_unlock(&active_queue->lock);
    }
    return (ssize_t)n;
}
int main(void) {
    struct clock_state c;
    struct bridge_stats stats;
    struct au_queue q;
    struct writer_ctx w;
    int rebased;
    memset(&c,0,sizeof(c));pthread_mutex_init(&c.lock,NULL);c.transport_pcr90k=45000;
    memset(&stats,0,sizeof(stats));pthread_mutex_init(&stats.lock,NULL);
    queue_init(&q);active_queue=&q;
    memset(&w,0,sizeof(w));w.fd=10000;w.input_fd=-1;w.queue=&q;w.clock=&c;w.stats=&stats;
    g_status_enabled=0;
    assert(assign_pts_presence(&c,0x40000000u,100u,1,&rebased)==54000u);
    assert(c.assigned_sec==100u && c.assigned_frac==0x40000000u);
    assert(c.assigned_mono_us && c.assigned_source_present);
    c.emitted_pts90k=54000;
    writer_main(&w);
    assert(accepts==4u && attempts==8u && stats.write_eagain==4u && !stats.write_errors);
    assert(stats.bytes_written==48128u && c.physical_packets==256u);
    assert(c.transport_pcr90k==47820u && c.accepted_pts90k==54000u);
    assert(c.accepted_mono_us>=c.writer_epoch_us+36000u);
    assert(c.accepted_write_us_total>=36000u);
    /* Nominal packet time is only 31333 us: diagnostics expose the slower sink. */
    assert((c.accepted_mono_us-c.writer_epoch_us)*90000u>2820u*1000000ull);
    g_status_enabled=1;publish_status(&stats,&c,&q,"done");
    puts("PARITY_CLOCK_REVIEW=PASS slow_acceptance EAGAIN nominal_clock assigned_source coherent_snapshot");
    queue_destroy(&q);pthread_mutex_destroy(&c.lock);pthread_mutex_destroy(&stats.lock);
    memset(&c,0,sizeof(c));pthread_mutex_init(&c.lock,NULL);c.transport_pcr90k=45000;
    memset(&stats,0,sizeof(stats));pthread_mutex_init(&stats.lock,NULL);
    queue_init(&q);active_queue=&q;w.queue=&q;w.clock=&c;w.stats=&stats;
    fail_write=1;g_stop=0;g_status_enabled=0;
    writer_main(&w);
    assert(g_stop && stats.write_errors==1u && !c.physical_packets && !c.accepted_mono_us);
    queue_destroy(&q);pthread_mutex_destroy(&c.lock);pthread_mutex_destroy(&stats.lock);
    puts("PARITY_CLOCK_FAILURE=PASS failed_write_does_not_advance_acceptance");
    return 0;
}
