#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#define PROVIDER_READY_PATH "build/test-dispatch-provider.ready"

typedef struct { struct { int rcvid; } message_context; } dispatch_context_t;
struct mhi2_rfcomm_provider {
    pthread_mutex_t lock;
    pthread_cond_t cond;
    void *ep_dispatch;
    int ep_ready, ep_stop, stopping, started, registered, sdp_published;
    unsigned channel;
};
static struct mhi2_rfcomm_provider *provider;
static dispatch_context_t *current;
static unsigned calls, handled, freed;
static int fatal;
static dispatch_context_t *dispatch_context_alloc(void *d)
{ (void)d; current = calloc(1, sizeof(*current)); assert(current); return current; }
static dispatch_context_t *dispatch_block(dispatch_context_t *p)
{
    assert(p == current); /* EINTR must reuse the old valid context. */
    calls++;
    if (calls == 1) { errno = EINTR; return NULL; }
    if (calls == 2) {
        dispatch_context_t *next = calloc(1, sizeof(*next)); assert(next);
        free(current); current = next; /* documented successful reallocation */
        current->message_context.rcvid = -1; return current;
    }
    if (calls == 3) { current->message_context.rcvid = 5; return current; }
    if (!fatal) provider->ep_stop = 1;
    errno = fatal ? ENOMEM : EINTR;
    return NULL;
}
static void dispatch_handler(dispatch_context_t *p)
{ assert(p == current); handled++; }
static void dispatch_context_free(dispatch_context_t *p)
{ assert(p == current); free(p); current = NULL; freed++; }
#include "../build/qnx_dispatch.inc"

int main(void)
{
    struct mhi2_rfcomm_provider p = {0};
    provider = &p;
    assert(pthread_mutex_init(&p.lock, NULL) == 0);
    assert(pthread_cond_init(&p.cond, NULL) == 0);
    p.started = p.registered = p.sdp_published = p.ep_ready = p.channel = 1;
    assert(access(PROVIDER_READY_PATH, F_OK) == -1);
    assert(endpoint_publish_ready(&p) == 0);
    endpoint_thread_main(&p);
    assert(p.ep_ready == -1 && handled == 1 && freed == 1);
    assert(access(PROVIDER_READY_PATH, F_OK) == -1);
    assert(endpoint_publish_ready(&p) == -1); /* exited dispatch cannot republish */
    fatal = 1; calls = 0; p.ep_stop = 0;
    endpoint_thread_main(&p);
    assert(handled == 2 && freed == 2 && p.ep_ready == -1);
    pthread_cond_destroy(&p.cond); pthread_mutex_destroy(&p.lock);
    puts("QNX dispatch regression: PASS (EINTR/reallocation/timeout/stop/fatal/ready health)");
    return 0;
}
