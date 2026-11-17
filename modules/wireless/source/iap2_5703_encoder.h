/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef IAP2_5703_ENCODER_H
#define IAP2_5703_ENCODER_H

#include <stddef.h>
#include <stdint.h>

#define IAP2_5703_MAX_BODY_BYTES 4096u

struct iap2_5703_config {
    const uint8_t *ssid;
    size_t ssid_len;

    int has_passphrase;
    const uint8_t *passphrase;
    size_t passphrase_len;

    int has_security_type;
    uint8_t security_type; /* observed values: None=0, WEP=1, WPA-family=2 */

    int has_channel;
    uint8_t channel;
};

/*
 * Encode only the 0x5703 control-message body, not a link packet or transport
 * frame. Returns 0 on success and -1 for invalid input or insufficient output
 * capacity. out_len is set to zero on failure when it is non-NULL. The caller
 * must provide non-overlapping storage for config, out, out_len, and the SSID /
 * passphrase byte ranges. On failure, out is unchanged. Internal body and
 * string scratch buffers are wiped on every return; caller-owned inputs and
 * successful output are not wiped.
 */
int iap2_5703_encode_body(const struct iap2_5703_config *config,
                          uint8_t *out,
                          size_t out_capacity,
                          size_t *out_len);

#endif
