/* Host shim for only the real ep_io_write body. No QNX endpoint/SDK calls. */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#define EOK 0
typedef struct { size_t written; } resmgr_context_t;
typedef struct { struct { size_t nbytes; } i; } io_write_t;
typedef int RESMGR_OCB_T;
struct mhi2_rfcomm_provider { int connected; };
static struct mhi2_rfcomm_provider provider = {1};
static struct mhi2_rfcomm_provider *g_endpoint_provider = &provider;
static ssize_t mock_received;
static size_t observed_length;
static unsigned queue_calls;
#define _IO_SET_WRITE_NBYTES(ctx, n) ((ctx)->written = (n))
static int iofunc_write_verify(resmgr_context_t *c, io_write_t *m, RESMGR_OCB_T *o, void *x)
{ (void)c; (void)m; (void)o; (void)x; return EOK; }
static int mhi2_rfcomm_provider_is_connected(struct mhi2_rfcomm_provider *p)
{ return p->connected; }
static ssize_t resmgr_msgread(resmgr_context_t *c, void *buf, size_t requested, size_t offset)
{
    (void)c; (void)offset;
    memset(buf, 0xcd, requested);
    if (mock_received > 0) memset(buf, 'A', (size_t)mock_received);
    if (mock_received == -1) errno = EIO;
    return mock_received;
}
static size_t mhi2_rfcomm_provider_queue_tx(struct mhi2_rfcomm_provider *p, const void *buf, size_t n)
{
    size_t i;
    (void)p;
    queue_calls++;
    observed_length = n;
    for (i = 0; i < n; i++) assert(((const uint8_t *)buf)[i] == 'A');
    return n;
}
#include "../build/qnx_ep_write.inc"
int main(void)
{
    resmgr_context_t ctx = {0};
    io_write_t msg = {{8}};
    RESMGR_OCB_T ocb = 0;
    mock_received = 3;
    assert(ep_io_write(&ctx, &msg, &ocb) == EOK);
    assert(observed_length == 3 && ctx.written == 3 && queue_calls == 1);
    mock_received = 0;
    assert(ep_io_write(&ctx, &msg, &ocb) == EOK);
    assert(ctx.written == 0 && queue_calls == 1);
    mock_received = -1;
    assert(ep_io_write(&ctx, &msg, &ocb) == EIO && queue_calls == 1);
    mock_received = 8;
    assert(ep_io_write(&ctx, &msg, &ocb) == EOK);
    assert(observed_length == 8 && ctx.written == 8 && queue_calls == 2);
    provider.connected = 0;
    assert(ep_io_write(&ctx, &msg, &ocb) == ENOTCONN && queue_calls == 2);
    puts("QNX write length shim regression: ok (short, zero, error, full, disconnected)");
    return 0;
}
