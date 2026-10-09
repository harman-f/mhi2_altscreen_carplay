#include "mhi2_mfi_airplay.h"

#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>

#define MHI2_DEFAULT_LIBAIRPLAY "/eso/lib/libairplay.so"
#define MHI2_MFI_DIGEST_LEN 20u

typedef int32_t (*mfi_initialize_fn)(void);
typedef void (*mfi_finalize_fn)(void);
typedef int32_t (*mfi_copy_certificate_fn)(uint8_t **, size_t *);
typedef int32_t (*mfi_create_signature_fn)(const void *, size_t,
                                           uint8_t **, size_t *);

static int resolve_required(void *handle, const char *name, void **out)
{
    void *symbol;

    if (!handle || !name || !out)
        return -1;

    dlerror();
    symbol = dlsym(handle, name);
    if (dlerror() != NULL || !symbol)
        return -1;

    *out = symbol;
    return 0;
}

int mhi2_mfi_airplay_open(struct mhi2_mfi_airplay *ctx,
                          const char *libairplay_path)
{
    void *p;
    int32_t status;

    if (!ctx)
        return -1;

    memset(ctx, 0, sizeof(*ctx));
    if (!libairplay_path || !*libairplay_path)
        libairplay_path = MHI2_DEFAULT_LIBAIRPLAY;

    ctx->dl_handle = dlopen(libairplay_path, RTLD_NOW | RTLD_LOCAL);
    if (!ctx->dl_handle)
        return -2;

    p = NULL;
    if (resolve_required(ctx->dl_handle, "APSMFiPlatform_Initialize", &p) != 0)
        goto fail;
    ctx->platform_initialize = (mfi_initialize_fn)p;

    p = NULL;
    if (resolve_required(ctx->dl_handle, "APSMFiPlatform_Finalize", &p) != 0)
        goto fail;
    ctx->platform_finalize = (mfi_finalize_fn)p;

    p = NULL;
    if (resolve_required(ctx->dl_handle, "APSMFiPlatform_CopyCertificate", &p) != 0)
        goto fail;
    ctx->copy_certificate = (mfi_copy_certificate_fn)p;

    p = NULL;
    if (resolve_required(ctx->dl_handle, "APSMFiPlatform_CreateSignature", &p) != 0)
        goto fail;
    ctx->create_signature = (mfi_create_signature_fn)p;

    status = ctx->platform_initialize();
    if (status != 0)
        goto fail;

    ctx->initialized = 1;
    return 0;

fail:
    if (ctx->dl_handle)
        dlclose(ctx->dl_handle);
    memset(ctx, 0, sizeof(*ctx));
    return -3;
}

void mhi2_mfi_airplay_close(struct mhi2_mfi_airplay *ctx)
{
    if (!ctx)
        return;

    if (ctx->initialized && ctx->platform_finalize)
        ctx->platform_finalize();

    if (ctx->dl_handle)
        dlclose(ctx->dl_handle);

    memset(ctx, 0, sizeof(*ctx));
}

int mhi2_mfi_airplay_copy_certificate(void *opaque,
                                      uint8_t *out,
                                      size_t cap,
                                      size_t *out_len)
{
    struct mhi2_mfi_airplay *ctx = (struct mhi2_mfi_airplay *)opaque;
    uint8_t *allocated = NULL;
    size_t len = 0;
    int32_t status;

    if (!ctx || !ctx->initialized || !ctx->copy_certificate ||
        !out || !out_len)
        return -1;

    status = ctx->copy_certificate(&allocated, &len);
    if (status != 0 || !allocated || len == 0) {
        free(allocated);
        return -2;
    }

    if (len > cap) {
        free(allocated);
        return -3;
    }

    memcpy(out, allocated, len);
    free(allocated);
    *out_len = len;
    return 0;
}

int mhi2_mfi_airplay_sign_challenge(void *opaque,
                                    const uint8_t *challenge,
                                    size_t challenge_len,
                                    uint8_t *out,
                                    size_t cap,
                                    size_t *out_len)
{
    struct mhi2_mfi_airplay *ctx = (struct mhi2_mfi_airplay *)opaque;
    uint8_t *allocated = NULL;
    size_t len = 0;
    int32_t status;

    if (!ctx || !ctx->initialized || !ctx->create_signature ||
        !challenge || !out || !out_len)
        return -1;

    /*
     * Apple CarPlay Communication Plug-in 210.81 declares the platform API
     * input as a 20-byte SHA-1 digest. The iAP2 authentication challenge at
     * this boundary is exactly 20 bytes; refuse any other size rather than
     * guessing or hashing again.
     */
    if (challenge_len != MHI2_MFI_DIGEST_LEN)
        return -2;

    status = ctx->create_signature(challenge, challenge_len, &allocated, &len);
    if (status != 0 || !allocated || len == 0) {
        free(allocated);
        return -3;
    }

    if (len > cap) {
        free(allocated);
        return -4;
    }

    memcpy(out, allocated, len);
    free(allocated);
    *out_len = len;
    return 0;
}
