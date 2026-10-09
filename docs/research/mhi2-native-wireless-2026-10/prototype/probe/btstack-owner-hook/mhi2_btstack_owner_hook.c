/*
 * MU1440 btstack owner-capture / servicegraph insertion interposer.
 *
 * LAB / COMPILE FIXTURE ONLY.
 *
 * Exact target:
 *   /eso/bin/apps/btstack
 *   SHA-256 d2b55046b8f22302c27811ab2070dc87f0408702c8764b43ad2ff135a66444a0
 *   ELF32 ARM ET_EXEC
 *
 * Proven target geometry:
 *   BluetoothServices ctor             0x0012c0f0
 *   Proxy::connect PLT call            0x0012c974
 *   return address in this interposer  0x0012c978
 *   embedded comm::Proxy offset        +0x0198
 *   service owner/list offset          +0x076c
 *   owner/list insert helper           0x0011d1e0
 *
 * The old MU1433 constructor inserted IapServices immediately before this
 * Proxy::connect phase. This interposer recreates only that placement seam.
 *
 * It is deliberately disabled unless:
 *   MHI2_IAP_SERVICEGRAPH_LAB=1
 *
 * RFCOMM activation has a second independent gate:
 *   MHI2_IAP_RFCOMM_LAB=1
 *
 * Deterministic first-vehicle activation may use a third independent gate:
 *   MHI2_IAP_FORCE_CONNECTABLE_LAB=1
 * This affects only the restored project-owned 0x4000 service node.
 *
 * A deployment wrapper must independently verify the exact target SHA before
 * setting either gate. The fixed-address provider is never called otherwise.
 */

#include "../servicegraph-adapter/mhi2_iap_servicegraph_adapter.h"
#include "../rfcomm-provider/mhi2_rfcomm_provider.h"

#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TARGET_CONNECT_RETURN ((uintptr_t)0x0012c978u)
#define TARGET_PROXY_OFFSET   ((uintptr_t)0x00000198u)
#define TARGET_LIST_OFFSET    ((uintptr_t)0x0000076cu)
#define TARGET_INSERT_ADDR    ((uintptr_t)0x0011d1e0u)

typedef int (*real_proxy_connect_fn)(void *proxy_this);

static real_proxy_connect_fn g_real_connect;
static struct mhi2_iap_service_node *g_node;
static struct mhi2_rfcomm_provider *g_provider;
static void *g_owner;
static int g_install_attempted;

static int env_gate_enabled(const char *name)
{
    const char *v = getenv(name);
    return v != NULL && strcmp(v, "1") == 0;
}

static int lab_enabled(void)
{
    return env_gate_enabled("MHI2_IAP_SERVICEGRAPH_LAB");
}

static int force_connectable_enabled(void)
{
    return env_gate_enabled("MHI2_IAP_FORCE_CONNECTABLE_LAB");
}

static int provider_start(void *ctx)
{
    return mhi2_rfcomm_provider_start(
        (struct mhi2_rfcomm_provider *)ctx);
}

static int provider_stop(void *ctx)
{
    return mhi2_rfcomm_provider_stop(
        (struct mhi2_rfcomm_provider *)ctx);
}

static int provider_event(void *ctx, uintptr_t event_arg, uintptr_t aux_arg)
{
    /*
     * The RFCOMM callback is installed directly into the generic target
     * descriptor. No BluetoothServiceBase event is required for data-plane
     * delivery. Keep this slot inert until a concrete stock caller is proven.
     */
    (void)ctx;
    (void)event_arg;
    (void)aux_arg;
    return 0;
}

static void provider_destroy(void *ctx)
{
    mhi2_rfcomm_provider_destroy(
        (struct mhi2_rfcomm_provider *)ctx);
    if (ctx == g_provider) {
        g_provider = NULL;
    }
}

static const struct mhi2_iap_provider_ops g_provider_ops = {
    provider_start,
    provider_stop,
    provider_event,
    provider_destroy
};

static real_proxy_connect_fn resolve_real_connect(void)
{
    void *p;
    const char *err;

    if (g_real_connect != NULL) {
        return g_real_connect;
    }

    dlerror();
    p = dlsym(RTLD_NEXT, "_ZN4comm5Proxy7connectEv");
    err = dlerror();
    if (err != NULL || p == NULL) {
        fprintf(stderr,
            "MHI2_IAP_OWNER_HOOK resolve_error symbol=_ZN4comm5Proxy7connectEv error=%s\n",
            err != NULL ? err : "not-found");
        return NULL;
    }

    memcpy(&g_real_connect, &p, sizeof(g_real_connect));
    return g_real_connect;
}

static void maybe_install(void *proxy_this, uintptr_t return_address)
{
    uintptr_t proxy;
    uintptr_t owner_addr;
    uintptr_t list_addr;
    mhi2_servicegraph_insert_fn insert_fn;
    void *insert_raw = (void *)TARGET_INSERT_ADDR;

    if (!lab_enabled()) {
        return;
    }

    if (return_address != TARGET_CONNECT_RETURN) {
        return;
    }

    if (g_install_attempted) {
        return;
    }
    g_install_attempted = 1;

    if (proxy_this == NULL) {
        fprintf(stderr,
            "MHI2_IAP_OWNER_HOOK install=blocked reason=null_proxy\n");
        return;
    }

    proxy = (uintptr_t)proxy_this;
    if (proxy < TARGET_PROXY_OFFSET) {
        fprintf(stderr,
            "MHI2_IAP_OWNER_HOOK install=blocked reason=invalid_proxy\n");
        return;
    }

    owner_addr = proxy - TARGET_PROXY_OFFSET;
    list_addr = owner_addr + TARGET_LIST_OFFSET;

    g_provider = mhi2_rfcomm_provider_create_target();
    if (g_provider == NULL) {
        fprintf(stderr,
            "MHI2_IAP_OWNER_HOOK install=blocked reason=provider_alloc_failed errno=%d\n",
            errno);
        return;
    }

    g_node = mhi2_iap_service_node_create(&g_provider_ops, g_provider);
    if (g_node == NULL) {
        fprintf(stderr,
            "MHI2_IAP_OWNER_HOOK install=blocked reason=node_alloc_failed\n");
        mhi2_rfcomm_provider_destroy(g_provider);
        g_provider = NULL;
        return;
    }

    memcpy(&insert_fn, &insert_raw, sizeof(insert_fn));

    if (mhi2_iap_servicegraph_insert_for_lab(
            g_node, (void *)list_addr, insert_fn) != 0) {
        fprintf(stderr,
            "MHI2_IAP_OWNER_HOOK install=blocked reason=insert_failed\n");
        mhi2_iap_service_node_destroy(g_node);
        g_node = NULL;
        g_provider = NULL;
        return;
    }

    g_owner = (void *)owner_addr;

    if (force_connectable_enabled()) {
        int rc = mhi2_iap_service_node_force_connectable_for_lab(g_node, 1);
        if (rc != 0) {
            fprintf(stderr,
                "MHI2_IAP_OWNER_HOOK force_connectable=failed service=0x%04x rc=%d\n",
                (unsigned)mhi2_iap_service_node_service_type(g_node), rc);
        } else {
            fprintf(stderr,
                "MHI2_IAP_OWNER_HOOK force_connectable=ok service=0x%04x\n",
                (unsigned)mhi2_iap_service_node_service_type(g_node));
        }
    }

    fprintf(stderr,
        "MHI2_IAP_OWNER_HOOK install=ok owner=%p proxy=%p list=%p service=0x%04x endpoint=%s\n",
        g_owner,
        proxy_this,
        (void *)list_addr,
        (unsigned)mhi2_iap_service_node_service_type(g_node),
        mhi2_rfcomm_provider_endpoint_path(g_provider));
}

/*
 * Exact dynamic symbol imported by target btstack.
 * ARM C++ non-static member call ABI passes the object pointer in r0.
 */
__attribute__((visibility("default")))
int mhi2_interposed_comm_proxy_connect(void *proxy_this)
    __asm__("_ZN4comm5Proxy7connectEv");

int mhi2_interposed_comm_proxy_connect(void *proxy_this)
{
    real_proxy_connect_fn real_connect;
    uintptr_t ra =
        (uintptr_t)__builtin_extract_return_addr(__builtin_return_address(0));

    real_connect = resolve_real_connect();
    if (real_connect == NULL) {
        errno = ENOSYS;
        return -1;
    }

    /*
     * Match stock ordering: the old iAP service node existed before this
     * Proxy::connect call. Install first, then delegate.
     */
    maybe_install(proxy_this, ra);

    return real_connect(proxy_this);
}
