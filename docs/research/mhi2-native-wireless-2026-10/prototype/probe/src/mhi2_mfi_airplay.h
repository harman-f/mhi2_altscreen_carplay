#ifndef MIB_MHI2_MFI_AIRPLAY_H
#define MIB_MHI2_MFI_AIRPLAY_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

struct mhi2_mfi_airplay {
    void *dl_handle;
    int initialized;

    int32_t (*platform_initialize)(void);
    void (*platform_finalize)(void);
    int32_t (*copy_certificate)(uint8_t **out_certificate,
                                size_t *out_certificate_len);
    int32_t (*create_signature)(const void *digest,
                                size_t digest_len,
                                uint8_t **out_signature,
                                size_t *out_signature_len);
};

int mhi2_mfi_airplay_open(struct mhi2_mfi_airplay *ctx,
                          const char *libairplay_path);

void mhi2_mfi_airplay_close(struct mhi2_mfi_airplay *ctx);

int mhi2_mfi_airplay_copy_certificate(void *opaque,
                                      uint8_t *out,
                                      size_t cap,
                                      size_t *out_len);

int mhi2_mfi_airplay_sign_challenge(void *opaque,
                                    const uint8_t *challenge,
                                    size_t challenge_len,
                                    uint8_t *out,
                                    size_t cap,
                                    size_t *out_len);

#ifdef __cplusplus
}
#endif

#endif
