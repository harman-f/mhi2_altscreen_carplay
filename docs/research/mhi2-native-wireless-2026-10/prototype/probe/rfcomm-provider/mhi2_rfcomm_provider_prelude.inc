#define _POSIX_C_SOURCE 200809L

#include "mhi2_rfcomm_provider.h"

#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#ifdef __QNXNTO__
#include <sys/dispatch.h>
#include <sys/iofunc.h>
#include <sys/resmgr.h>
#include <sys/stat.h>
#endif

#define TARGET_REGISTER_SERVER  ((uintptr_t)0x00277a30u)
#define TARGET_PUBLISH_SDP      ((uintptr_t)0x0020725cu)
#define TARGET_ACCEPT           ((uintptr_t)0x00277354u)
#define TARGET_ADD_CREDIT       ((uintptr_t)0x00277174u)
#define TARGET_TX_CAPACITY      ((uintptr_t)0x0027708cu)
#define TARGET_SEND             ((uintptr_t)0x00277210u)
#define TARGET_DISCONNECT       ((uintptr_t)0x00277410u)
#define TARGET_DEREGISTER       ((uintptr_t)0x002779ccu)
#define TARGET_REMOVE_SDP       ((uintptr_t)0x002071dcu)

#define RX_CAPACITY (256u * 1024u)
#define TX_QUEUE_LIMIT 64u
#define ENDPOINT_READ_CHUNK 8192u
#define STOP_WAIT_SECONDS 2

#define RF_EVENT_INBOUND     1u
#define RF_EVENT_ESTABLISHED 2u
#define RF_EVENT_CONTROL     3u
#define RF_EVENT_CLOSED      4u
#define RF_EVENT_RX          5u
#define RF_EVENT_TX_DONE     6u

#define RF_RC_QUEUED 2
#define RF_TX_CANCELLED 0x11u

struct tx_packet {
    struct tx_packet *next;
    size_t length;
    int in_call;
    int event_done;
    uint64_t generation;
    uint8_t raw[0x18];
    uint8_t data[MHI2_IAP_RFCOMM_MTU];
};

struct mhi2_rfcomm_provider {
    struct mhi2_rfcomm_stack_ops stack;
    void *stack_opaque;
    int target_mode;

    pthread_mutex_t lock;
    pthread_mutex_t lifecycle_lock;
    pthread_cond_t cond;
    pthread_t tx_thread;
    int tx_thread_started;
    int tx_stop;
    int tx_wake;
    unsigned stack_calls;
    unsigned callbacks_active;
    int pending_accept;
    int session_ready;
    uint64_t generation;

    uint8_t descriptor[MHI2_RFCOMM_DESC_SIZE];
    uint8_t channel;
    int registered;
    int sdp_published;
    int started;
    int stopping;
    int connected;

    uint8_t peer_mac[6];

    uint8_t sdp_service_class[19];
    uint8_t sdp_protocol[14];
    uint8_t sdp_attrs[24];
    uint8_t sdp_record[24];

    uint8_t rx[RX_CAPACITY];
    size_t rx_head;
    size_t rx_tail;
    size_t rx_count;

    struct tx_packet *tx_head;
    struct tx_packet *tx_tail;
    struct tx_packet *tx_inflight;
    size_t tx_queued;

    char endpoint_path[96];

#ifdef __QNXNTO__
    dispatch_t *ep_dispatch;
    int ep_attach_id;
    pthread_t ep_thread;
    int ep_thread_started;
    int ep_ready;
    int ep_stop;
    iofunc_attr_t ep_attr;
    resmgr_connect_funcs_t ep_connect;
    resmgr_io_funcs_t ep_io;
    iofunc_notify_t ep_notify[3];
    uint8_t ep_readbuf[ENDPOINT_READ_CHUNK];
#endif
};

static struct mhi2_rfcomm_provider *g_target_provider;
#ifdef __QNXNTO__
static struct mhi2_rfcomm_provider *g_endpoint_provider;
#endif

static uint16_t get_u16(const uint8_t *p)
{
    uint16_t value;
    memcpy(&value, p, sizeof(value));
    return value;
}

static void put_u16(uint8_t *p, uint16_t value)
{
    memcpy(p, &value, sizeof(value));
}

static void put_u32(uint8_t *p, uint32_t value)
{
    memcpy(p, &value, sizeof(value));
}

static void put_target_ptr(uint8_t *p, const void *value)
{
    uintptr_t raw = (uintptr_t)value;
    put_u32(p, (uint32_t)raw);
}

static void *get_target_ptr(const uint8_t *p)
{
    uint32_t raw;
    memcpy(&raw, p, sizeof(raw));
    return (void *)(uintptr_t)raw;
}

static int env_enabled(const char *name)
{
    const char *v = getenv(name);
    return v != NULL && strcmp(v, "1") == 0;
}

static void fixed_function(uintptr_t address, void *dst, size_t size)
{
    void *raw = (void *)address;
    memcpy(dst, &raw, size);
}

static int target_register_server(void *opaque, void *descriptor,
                                  uint8_t *channel, unsigned credits)
{
    typedef int (*fn_t)(void *, uint8_t *, unsigned);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_REGISTER_SERVER, &fn, sizeof(fn));
    return fn(descriptor, channel, credits);
}

static int target_publish_sdp(void *opaque, void *record)
{
    typedef int (*fn_t)(void *);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_PUBLISH_SDP, &fn, sizeof(fn));
    return fn(record);
}

static int target_accept(void *opaque, void *descriptor, int accept)
{
    typedef int (*fn_t)(void *, int);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_ACCEPT, &fn, sizeof(fn));
    return fn(descriptor, accept);
}

static int target_add_credit(void *opaque, void *descriptor, unsigned credits)
{
    typedef int (*fn_t)(void *, unsigned);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_ADD_CREDIT, &fn, sizeof(fn));
    return fn(descriptor, credits);
}

static unsigned target_tx_capacity(void *opaque, void *descriptor)
{
    typedef unsigned (*fn_t)(void *);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_TX_CAPACITY, &fn, sizeof(fn));
    return fn(descriptor);
}

static int target_send(void *opaque, void *descriptor, void *packet)
{
    typedef int (*fn_t)(void *, void *);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_SEND, &fn, sizeof(fn));
    return fn(descriptor, packet);
}

static int target_disconnect(void *opaque, void *descriptor)
{
    typedef int (*fn_t)(void *);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_DISCONNECT, &fn, sizeof(fn));
    return fn(descriptor);
}

static int target_deregister_server(void *opaque, void *descriptor,
                                    uint8_t *channel)
{
    typedef int (*fn_t)(void *, uint8_t *);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_DEREGISTER, &fn, sizeof(fn));
    return fn(descriptor, channel);
}

static int target_remove_sdp(void *opaque, void *record)
{
    typedef int (*fn_t)(void *);
    fn_t fn = NULL;
    (void)opaque;
    fixed_function(TARGET_REMOVE_SDP, &fn, sizeof(fn));
    return fn(record);
}

static const struct mhi2_rfcomm_stack_ops g_target_ops = {
    target_register_server,
    target_publish_sdp,
    target_accept,
    target_add_credit,
    target_tx_capacity,
    target_send,
    target_disconnect,
    target_deregister_server,
    target_remove_sdp
};

static void prepare_descriptor(struct mhi2_rfcomm_provider *p);
static void prepare_sdp(struct mhi2_rfcomm_provider *p);
static void kick_tx(struct mhi2_rfcomm_provider *p);
static void *tx_thread_main(void *opaque);
static int endpoint_start(struct mhi2_rfcomm_provider *p);
static void endpoint_stop(struct mhi2_rfcomm_provider *p);
static void endpoint_rx_ready(struct mhi2_rfcomm_provider *p);
static int endpoint_publish_ready(struct mhi2_rfcomm_provider *p);
static void endpoint_remove_ready(struct mhi2_rfcomm_provider *p);
