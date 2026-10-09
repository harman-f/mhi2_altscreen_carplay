/* Host shim of the actual QNX notify/close/trigger bodies; no QNX device. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#define EOK 0
#define _NOTIFY_COND_INPUT 1
#define IOFUNC_NOTIFY_INPUT 0
#define _NOTIFY_COND_OUTPUT 2

typedef int resmgr_context_t;
typedef int io_notify_t;
typedef int io_close_t;
typedef int RESMGR_OCB_T;
struct mhi2_rfcomm_provider { int target_mode, ep_attr, ep_notify[3], ep_ready; pthread_mutex_t lock; };
static struct mhi2_rfcomm_provider provider = {1, 0, {0}, 1, PTHREAD_MUTEX_INITIALIZER};
static struct mhi2_rfcomm_provider *g_endpoint_provider = &provider;
static pthread_mutex_t attr = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t barrier = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
static int attr_depth, lock_fail, pending, armed, triggers, producer_entered;
static int removing_client, ready_removed;
static pthread_t producer;
static void endpoint_rx_ready(struct mhi2_rfcomm_provider *p);
static void *arrival(void *opaque)
{
    pthread_mutex_lock(&barrier);
    producer_entered = 1;
    pthread_cond_signal(&cond);
    pthread_mutex_unlock(&barrier);
    endpoint_rx_ready(opaque); /* must wait until check/arm releases attr */
    return NULL;
}
static int iofunc_attr_lock(int *a)
{
    (void)a;
    if (lock_fail) { lock_fail = 0; return EAGAIN; }
    pthread_mutex_lock(&attr);
    attr_depth++;
    return 0;
}
static void iofunc_attr_unlock(int *a)
{ (void)a; assert(attr_depth == 1); attr_depth--; pthread_mutex_unlock(&attr); }
static int mhi2_rfcomm_provider_rx_pending(struct mhi2_rfcomm_provider *p)
{ (void)p; return pending; }
static int mhi2_rfcomm_provider_is_connected(struct mhi2_rfcomm_provider *p)
{ (void)p; return 1; }
static int iofunc_notify(resmgr_context_t *c, io_notify_t *m, int *n,
                         int trigger, void *f, void *d)
{
    (void)c; (void)m; (void)n; (void)f; (void)d;
    assert(attr_depth == 1 && trigger == 0);
    pthread_mutex_lock(&barrier);
    assert(pthread_create(&producer, NULL, arrival, &provider) == 0);
    while (!producer_entered) pthread_cond_wait(&cond, &barrier);
    pthread_mutex_unlock(&barrier);
    assert(triggers == 0);
    armed = 1;
    return 0;
}
static void iofunc_notify_trigger(int *n, int count, int condition)
{
    (void)n; (void)count; (void)condition;
    assert(attr_depth == 1 && armed);
    triggers++;
}
static void iofunc_notify_remove(resmgr_context_t *c, int *n)
{ (void)n; assert(attr_depth == 1); assert(c != NULL); removing_client = *c; }
static int iofunc_close_dup_default(resmgr_context_t *c, io_close_t *m, RESMGR_OCB_T *o)
{ (void)c; (void)m; (void)o; return 42; }
static void endpoint_remove_ready(struct mhi2_rfcomm_provider *p)
{ (void)p; ready_removed++; }
#include "../build/qnx_notify.inc"
int main(void)
{
    resmgr_context_t ctx = 17;
    io_notify_t notify = 0;
    io_close_t close_msg = 0;
    RESMGR_OCB_T ocb = 0;
    assert(ep_io_notify(&ctx, &notify, &ocb) == 0);
    pthread_join(producer, NULL);
    assert(triggers == 1 && attr_depth == 0);
    assert(ep_io_close_dup(&ctx, &close_msg, &ocb) == 42);
    assert(removing_client == 17); /* retain other clients' entries */
    lock_fail = 1;
    assert(ep_io_notify(&ctx, &notify, &ocb) == EAGAIN);
    lock_fail = 1;
    endpoint_rx_ready(&provider);
    assert(ready_removed == 1 && triggers == 1 && provider.ep_ready == -1);
    puts("QNX notify shim regression: ok (check/arm race, trigger lock, client close, lock failure)");
    return 0;
}
