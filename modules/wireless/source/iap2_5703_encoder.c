/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "iap2_5703_encoder.h"

#include <string.h>

#define IAP2_5703_MESSAGE_ID 0x5703u
#define IAP2_5703_PARAMETER_HEADER_BYTES 4u

static int contains_nul(const uint8_t *value, size_t length)
{
    size_t i;
    for (i = 0; i < length; ++i) {
        if (value[i] == 0u) {
            return 1;
        }
    }
    return 0;
}

static int is_unverified_64_hex_psk(const uint8_t *value, size_t length)
{
    size_t i;
    if (length != 64u) {
        return 0;
    }
    for (i = 0; i < length; ++i) {
        if (!((value[i] >= (uint8_t)'0' && value[i] <= (uint8_t)'9') ||
              (value[i] >= (uint8_t)'a' && value[i] <= (uint8_t)'f') ||
              (value[i] >= (uint8_t)'A' && value[i] <= (uint8_t)'F'))) {
            return 0;
        }
    }
    return 1;
}

static void secure_wipe(void *memory, size_t length)
{
    volatile uint8_t *bytes = (volatile uint8_t *)memory;
    while (length != 0u) {
        *bytes++ = 0u;
        --length;
    }
}

static int append_parameter(uint8_t *body,
                            size_t body_capacity,
                            size_t *body_length,
                            uint16_t parameter_id,
                            const uint8_t *value,
                            size_t value_length)
{
    size_t encoded_length;
    size_t required;
    size_t offset;

    if (value_length > (size_t)0xffffu - IAP2_5703_PARAMETER_HEADER_BYTES) {
        return -1;
    }
    encoded_length = value_length + IAP2_5703_PARAMETER_HEADER_BYTES;
    if (*body_length > body_capacity ||
        encoded_length > body_capacity - *body_length) {
        return -1;
    }
    required = *body_length + encoded_length;
    if (required > IAP2_5703_MAX_BODY_BYTES) {
        return -1;
    }

    offset = *body_length;
    body[offset++] = (uint8_t)(encoded_length >> 8);
    body[offset++] = (uint8_t)encoded_length;
    body[offset++] = (uint8_t)(parameter_id >> 8);
    body[offset++] = (uint8_t)parameter_id;
    if (value_length != 0u) {
        memcpy(body + offset, value, value_length);
    }
    *body_length = required;
    return 0;
}

int iap2_5703_encode_body(const struct iap2_5703_config *config,
                          uint8_t *out,
                          size_t out_capacity,
                          size_t *out_len)
{
    uint8_t body[IAP2_5703_MAX_BODY_BYTES];
    uint8_t string_value[IAP2_5703_MAX_BODY_BYTES];
    size_t body_length = 2u;
    size_t ssid_value_length;
    size_t passphrase_value_length;
    const uint8_t *one_byte;
    int result = -1;

    if (out_len != NULL) {
        *out_len = 0u;
    }
    if (config == NULL || out == NULL || out_len == NULL || config->ssid == NULL) {
        goto cleanup;
    }
    if (config->has_passphrase && config->passphrase == NULL) {
        goto cleanup;
    }
    if ((config->has_security_type != 0 && config->security_type > 2u) ||
        (config->has_security_type != 0 && config->has_security_type != 1) ||
        (config->has_channel != 0 && config->has_channel != 1) ||
        (config->has_passphrase != 0 && config->has_passphrase != 1)) {
        goto cleanup;
    }
    if (config->ssid_len >= sizeof(string_value) ||
        (config->has_passphrase &&
         config->passphrase_len >= sizeof(string_value))) {
        goto cleanup;
    }
    if (contains_nul(config->ssid, config->ssid_len) ||
        (config->has_passphrase &&
         (contains_nul(config->passphrase, config->passphrase_len) ||
          is_unverified_64_hex_psk(config->passphrase,
                                   config->passphrase_len)))) {
        goto cleanup;
    }

    ssid_value_length = config->ssid_len + 1u;
    if (config->ssid_len != 0u) {
        memcpy(string_value, config->ssid, config->ssid_len);
    }
    string_value[config->ssid_len] = 0u;

    body[0] = (uint8_t)(IAP2_5703_MESSAGE_ID >> 8);
    body[1] = (uint8_t)IAP2_5703_MESSAGE_ID;
    if (append_parameter(body, sizeof(body), &body_length, 1u,
                         string_value, ssid_value_length) != 0) {
        goto cleanup;
    }

    if (config->has_passphrase) {
        passphrase_value_length = config->passphrase_len + 1u;
        if (config->passphrase_len != 0u) {
            memcpy(string_value, config->passphrase,
                   config->passphrase_len);
        }
        string_value[config->passphrase_len] = 0u;
        if (append_parameter(body, sizeof(body), &body_length, 2u,
                             string_value, passphrase_value_length) != 0) {
            goto cleanup;
        }
    }

    if (config->has_security_type) {
        one_byte = &config->security_type;
        if (append_parameter(body, sizeof(body), &body_length, 3u,
                             one_byte, 1u) != 0) {
            goto cleanup;
        }
    }
    if (config->has_channel) {
        one_byte = &config->channel;
        if (append_parameter(body, sizeof(body), &body_length, 4u,
                             one_byte, 1u) != 0) {
            goto cleanup;
        }
    }

    if (body_length > out_capacity) {
        goto cleanup;
    }
    memcpy(out, body, body_length);
    *out_len = body_length;
    result = 0;

cleanup:
    secure_wipe(string_value, sizeof(string_value));
    secure_wipe(body, sizeof(body));
    return result;
}
