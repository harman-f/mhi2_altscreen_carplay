#include "../servicegraph-adapter/mhi2_iap_servicegraph_adapter.h"

#include <assert.h>
#include <stdint.h>
#include <stdlib.h>

struct fake_provider {
    int starts;
    int stops;
    int destroys;
};

static int fake_start(void *ctx)
{
    struct fake_provider *p = ctx;
    ++p->starts;
    return 0;
}

static int fake_stop(void *ctx)
{
    struct fake_provider *p = ctx;
    ++p->stops;
    return 0;
}

static int fake_event(void *ctx, uintptr_t a, uintptr_t b)
{
    (void)ctx;
    return (int)(a ^ b);
}

static void fake_destroy(void *ctx)
{
    struct fake_provider *p = ctx;
    ++p->destroys;
}

int main(void)
{
    struct fake_provider p = {0, 0, 0};
    const struct mhi2_iap_provider_ops ops = {
        fake_start, fake_stop, fake_event, fake_destroy
    };
    struct mhi2_iap_service_node *node =
        mhi2_iap_service_node_create(&ops, &p);

    assert(node != NULL);
    assert(mhi2_iap_service_node_service_type(node) ==
           MHI2_BT_SERVICE_IAP2_HOST);
    assert(mhi2_iap_service_node_is_connectable(node) == 0);

    assert(mhi2_iap_service_node_force_connectable_for_lab(node, 1) == 0);
    assert(mhi2_iap_service_node_is_connectable(node) == 1);
    assert(p.starts == 1);

    /* Idempotent force-on must not start the provider twice. */
    assert(mhi2_iap_service_node_force_connectable_for_lab(node, 1) == 0);
    assert(p.starts == 1);

    assert(mhi2_iap_service_node_force_connectable_for_lab(node, 0) == 0);
    assert(mhi2_iap_service_node_is_connectable(node) == 0);
    assert(p.stops == 1);

    mhi2_iap_service_node_destroy(node);
    assert(p.destroys == 1);
    return 0;
}
