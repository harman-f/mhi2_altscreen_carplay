#ifndef MHI2_IAP_SERVICEGRAPH_ADAPTER_H
#define MHI2_IAP_SERVICEGRAPH_ADAPTER_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MHI2_BT_SERVICE_IAP2_HOST 0x4000u

struct mhi2_iap_provider_ops {
    int (*start)(void *ctx);
    int (*stop)(void *ctx);
    int (*event)(void *ctx, uintptr_t event_arg, uintptr_t aux_arg);
    void (*destroy)(void *ctx);
};

struct mhi2_iap_service_node;

/*
 * Allocate and initialize the minimal BluetoothServiceBase-compatible object.
 * This does NOT insert the object into btstack by itself.
 */
struct mhi2_iap_service_node *
mhi2_iap_service_node_create(const struct mhi2_iap_provider_ops *ops,
                             void *provider_ctx);

/*
 * Idempotently force the provider to non-connectable and release it.
 * Call only after the object has been detached from the stock owner graph.
 */
void mhi2_iap_service_node_destroy(struct mhi2_iap_service_node *node);

/* Test/introspection helpers. */
uint32_t mhi2_iap_service_node_service_type(
    const struct mhi2_iap_service_node *node);
int mhi2_iap_service_node_is_connectable(
    const struct mhi2_iap_service_node *node);

/*
 * Lab-only deterministic activation gate.
 *
 * When enabled, starts the provider immediately and suppresses later stock
 * "connectable=false" policy writes for this restored node only. Destruction
 * still stops the provider unconditionally. Disabling the force gate stops
 * the provider and returns the node to ordinary stock-policy behavior.
 */
int mhi2_iap_service_node_force_connectable_for_lab(
    struct mhi2_iap_service_node *node,
    int enabled);

/*
 * Compile-time/lab install seam.
 *
 * The exact MU1440 owner/list helper is known statically, but the production
 * owner-binding mechanism is deliberately kept out of this ABI until the
 * constructor/Proxy::connect seam is fully SHA-gated.
 */
typedef void (*mhi2_servicegraph_insert_fn)(void *owner_list,
                                            void *service_ptr_address);

int mhi2_iap_servicegraph_insert_for_lab(
    struct mhi2_iap_service_node *node,
    void *owner_list,
    mhi2_servicegraph_insert_fn insert_fn);

#ifdef __cplusplus
}
#endif

#endif
