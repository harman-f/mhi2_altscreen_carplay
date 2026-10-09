#ifndef MHI2_RFCOMM_PROVIDER_H
#define MHI2_RFCOMM_PROVIDER_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MHI2_RFCOMM_DESC_SIZE 0xb0u
#define MHI2_IAP_RFCOMM_MTU 0x13abu
#define MHI2_IAP_RFCOMM_INITIAL_CREDITS 100u
#define MHI2_IAP_ENDPOINT_DEFAULT "/dev/mhi2-iap2-rfcomm"

struct mhi2_rfcomm_stack_ops {
    int (*register_server)(void *opaque, void *descriptor,
                           uint8_t *channel, unsigned initial_credits);
    int (*publish_sdp)(void *opaque, void *record);
    int (*accept)(void *opaque, void *descriptor, int accept);
    int (*add_credit)(void *opaque, void *descriptor, unsigned credits);
    unsigned (*tx_capacity)(void *opaque, void *descriptor);
    int (*send)(void *opaque, void *descriptor, void *packet);
    int (*disconnect)(void *opaque, void *descriptor);
    int (*deregister_server)(void *opaque, void *descriptor, uint8_t *channel);
    int (*remove_sdp)(void *opaque, void *record);
};

struct mhi2_rfcomm_provider;

struct mhi2_rfcomm_provider *
mhi2_rfcomm_provider_create_target(void);

struct mhi2_rfcomm_provider *
mhi2_rfcomm_provider_create_test(const struct mhi2_rfcomm_stack_ops *ops,
                                 void *opaque);

void mhi2_rfcomm_provider_destroy(struct mhi2_rfcomm_provider *provider);

int mhi2_rfcomm_provider_start(struct mhi2_rfcomm_provider *provider);
int mhi2_rfcomm_provider_stop(struct mhi2_rfcomm_provider *provider);

/*
 * Public only so host tests can feed exact callback-shaped events.
 * The target callback installed at descriptor +0x08 calls this function.
 */
void mhi2_rfcomm_provider_handle_event(struct mhi2_rfcomm_provider *provider,
                                       const void *event_record);

size_t mhi2_rfcomm_provider_rx_pending(struct mhi2_rfcomm_provider *provider);
size_t mhi2_rfcomm_provider_read_rx(struct mhi2_rfcomm_provider *provider,
                                    void *dst, size_t length);
size_t mhi2_rfcomm_provider_queue_tx(struct mhi2_rfcomm_provider *provider,
                                     const void *src, size_t length);

uint8_t mhi2_rfcomm_provider_channel(const struct mhi2_rfcomm_provider *provider);
int mhi2_rfcomm_provider_is_started(const struct mhi2_rfcomm_provider *provider);
int mhi2_rfcomm_provider_is_connected(const struct mhi2_rfcomm_provider *provider);
const char *mhi2_rfcomm_provider_endpoint_path(
    const struct mhi2_rfcomm_provider *provider);

#ifdef __cplusplus
}
#endif

#endif
