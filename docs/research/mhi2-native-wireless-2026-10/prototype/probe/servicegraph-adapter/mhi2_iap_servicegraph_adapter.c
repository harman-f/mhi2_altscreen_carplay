/*
 * Minimal MU1440 BluetoothServiceBase-compatible SC_IAP2_HOST node.
 *
 * This is a compile-only/lab ABI fixture. It is intentionally NOT a vehicle
 * install candidate and does not contain a fixed-address btstack hook.
 *
 * Static evidence:
 *   - MU1440 BluetoothServiceBase raw vtable has two Itanium ABI header words.
 *   - object vptr therefore points at raw slot 2.
 *   - object vptr + 0x30 -> raw slot 14: serviceType matcher.
 *   - object vptr + 0x14 -> raw slot 7: service-specific connectability hook.
 *   - old MU1433 IapServices uses serviceType 0x4000 (SC_IAP2_HOST).
 */

#include "mhi2_iap_servicegraph_adapter.h"

#include <stdlib.h>
#include <string.h>

typedef uintptr_t word_t;

struct mhi2_iap_service_node {
    word_t *vptr;              /* BluetoothServiceBase vptr */
    uint32_t service_type;     /* +0x04 */
    uint32_t base_state;       /* +0x08 */
    const struct mhi2_iap_provider_ops *ops;
    void *provider_ctx;
    int connectable;
    int inserted;
    int force_connectable_lab;
};

/*
 * Use a wide fixed ARM/EABI-compatible signature for unknown abstract hooks.
 * Stock callers may pass fewer arguments; unused register arguments are
 * ignored. All unknown hooks fail closed with zero.
 */
static word_t svc_noop(struct mhi2_iap_service_node *self,
                       word_t a1, word_t a2, word_t a3)
{
    (void)self;
    (void)a1;
    (void)a2;
    (void)a3;
    return 0;
}

static word_t svc_dtor(struct mhi2_iap_service_node *self,
                       word_t a1, word_t a2, word_t a3)
{
    (void)a1;
    (void)a2;
    (void)a3;

    if (self != NULL && self->connectable) {
        if (self->ops != NULL && self->ops->stop != NULL) {
            (void)self->ops->stop(self->provider_ctx);
        }
        self->connectable = 0;
    }

    if (self != NULL && self->ops != NULL && self->ops->destroy != NULL) {
        self->ops->destroy(self->provider_ctx);
        self->provider_ctx = NULL;
    }

    return (word_t)self;
}

static word_t svc_deleting_dtor(struct mhi2_iap_service_node *self,
                                word_t a1, word_t a2, word_t a3)
{
    (void)a1;
    (void)a2;
    (void)a3;
    (void)svc_dtor(self, 0, 0, 0);
    free(self);
    return 0;
}

/*
 * Raw slot 7 / object-vptr + 0x14.
 * This is the exact semantic position occupied by MU1433
 * IapServices::setConnectable-like hook 0x00237bfc.
 */
static word_t svc_set_connectable(struct mhi2_iap_service_node *self,
                                  word_t state, word_t a2, word_t a3)
{
    int want;
    int rc = 0;

    (void)a2;
    (void)a3;

    if (self == NULL) {
        return (word_t)-1;
    }

    want = state != 0;

    /*
     * Deterministic first-vehicle lab mode: stock production configuration
     * carries bluetooth.enableIap=false. Do not let that generic policy write
     * tear down the project-owned restored 0x4000 node while the explicit
     * force gate is active. This affects only this node, not stock state.
     */
    if (!want && self->force_connectable_lab) {
        return 0;
    }

    if (want == self->connectable) {
        return 0;
    }

    if (self->ops == NULL) {
        return (word_t)-1;
    }

    if (want) {
        if (self->ops->start == NULL) {
            return (word_t)-1;
        }
        rc = self->ops->start(self->provider_ctx);
        if (rc == 0) {
            self->connectable = 1;
        }
    } else {
        if (self->ops->stop != NULL) {
            rc = self->ops->stop(self->provider_ctx);
        }
        if (rc == 0) {
            self->connectable = 0;
        }
    }

    return (word_t)rc;
}

/*
 * Raw slot 14 / object-vptr + 0x30.
 * Exact MU1440 base implementation 0x0012d1c4 is:
 *     return this->serviceType == requestedService;
 */
static word_t svc_matches_type(struct mhi2_iap_service_node *self,
                               word_t requested_service,
                               word_t a2, word_t a3)
{
    (void)a2;
    (void)a3;
    return self != NULL && self->service_type == (uint32_t)requested_service;
}

static word_t svc_event_forward(struct mhi2_iap_service_node *self,
                                word_t event_arg, word_t aux_arg, word_t a3)
{
    (void)a3;
    if (self == NULL || self->ops == NULL || self->ops->event == NULL) {
        return 0;
    }
    return (word_t)self->ops->event(self->provider_ctx, event_arg, aux_arg);
}

/*
 * Itanium ARM vtable image, raw slots 0..17.
 * The object vptr is &g_iap_vtable[2].
 *
 * Only the proven semantic slots are specialized:
 *   raw 2  destructor
 *   raw 3  deleting destructor
 *   raw 7  connectability
 *   raw 14 service-type matcher
 *
 * Abstract/service-specific hooks are kept fail-closed/no-op until their
 * exact iAP semantics are needed. raw slot 5 is routed to provider event()
 * as a bounded extension point; this can be tightened after live evidence.
 */
static word_t g_iap_vtable[18] = {
    0,                                  /* 0 offset-to-top */
    0,                                  /* 1 RTTI: deliberately absent in C fixture */
    (word_t)(void *)&svc_dtor,           /* 2 */
    (word_t)(void *)&svc_deleting_dtor,  /* 3 */
    (word_t)(void *)&svc_noop,           /* 4 */
    (word_t)(void *)&svc_event_forward,  /* 5 */
    (word_t)(void *)&svc_noop,           /* 6 */
    (word_t)(void *)&svc_set_connectable,/* 7 */
    (word_t)(void *)&svc_noop,           /* 8 */
    (word_t)(void *)&svc_noop,           /* 9 */
    (word_t)(void *)&svc_noop,           /* 10 */
    (word_t)(void *)&svc_noop,           /* 11 */
    (word_t)(void *)&svc_noop,           /* 12 */
    (word_t)(void *)&svc_noop,           /* 13 */
    (word_t)(void *)&svc_matches_type,   /* 14 */
    (word_t)(void *)&svc_noop,           /* 15 */
    (word_t)(void *)&svc_noop,           /* 16 */
    (word_t)(void *)&svc_noop            /* 17 */
};

struct mhi2_iap_service_node *
mhi2_iap_service_node_create(const struct mhi2_iap_provider_ops *ops,
                             void *provider_ctx)
{
    struct mhi2_iap_service_node *node;

    if (ops == NULL || ops->start == NULL) {
        return NULL;
    }

    node = (struct mhi2_iap_service_node *)calloc(1, sizeof(*node));
    if (node == NULL) {
        return NULL;
    }

    node->vptr = &g_iap_vtable[2];
    node->service_type = MHI2_BT_SERVICE_IAP2_HOST;
    node->base_state = 0;
    node->ops = ops;
    node->provider_ctx = provider_ctx;
    return node;
}

void mhi2_iap_service_node_destroy(struct mhi2_iap_service_node *node)
{
    if (node == NULL) {
        return;
    }

    /*
     * Never free an object while the stock graph may still own its pointer.
     * The vehicle integration layer must detach it first.
     */
    if (node->inserted) {
        return;
    }

    (void)svc_deleting_dtor(node, 0, 0, 0);
}

uint32_t mhi2_iap_service_node_service_type(
    const struct mhi2_iap_service_node *node)
{
    return node != NULL ? node->service_type : 0;
}

int mhi2_iap_service_node_is_connectable(
    const struct mhi2_iap_service_node *node)
{
    return node != NULL ? node->connectable : 0;
}

int mhi2_iap_service_node_force_connectable_for_lab(
    struct mhi2_iap_service_node *node,
    int enabled)
{
    word_t rc;

    if (node == NULL) {
        return -1;
    }

    if (enabled) {
        node->force_connectable_lab = 1;
        rc = svc_set_connectable(node, 1, 0, 0);
        if ((intptr_t)rc != 0) {
            node->force_connectable_lab = 0;
        }
        return (int)(intptr_t)rc;
    }

    node->force_connectable_lab = 0;
    rc = svc_set_connectable(node, 0, 0, 0);
    return (int)(intptr_t)rc;
}

int mhi2_iap_servicegraph_insert_for_lab(
    struct mhi2_iap_service_node *node,
    void *owner_list,
    mhi2_servicegraph_insert_fn insert_fn)
{
    void *service_ptr;
    if (node == NULL || owner_list == NULL || insert_fn == NULL
            || node->inserted) {
        return -1;
    }

    service_ptr = node;
    insert_fn(owner_list, &service_ptr);
    node->inserted = 1;
    return 0;
}
