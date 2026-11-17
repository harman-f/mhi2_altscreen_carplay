/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "wcp_wifi_reply.h"
#include "wcp_config.h"
#include "iap2_5703_encoder.h"
#include <string.h>

static void wipe(void *ptr, size_t length)
{
    volatile unsigned char *p = (volatile unsigned char *)ptr;
    while (length--) *p++ = 0;
}

int wcp_wifi_reply(const void *record, size_t record_length,
                   uint64_t before, uint64_t after, uint64_t current,
                   uint32_t snapshot_interface_index, uint32_t current_interface_index,
                   enum wcp_credential_kind credential_kind,
                   unsigned char *out, size_t capacity, size_t *out_length)
{
    struct wcp_ap ap;
    struct iap2_5703_config config;
    int result;
    if (out_length) *out_length = 0;
    if (!out || !out_length) return WCP_INVALID;
    if (!before || before != after || after != current) return WCP_STALE;
    if (!snapshot_interface_index || !current_interface_index ||
        snapshot_interface_index != current_interface_index) return WCP_STALE;
    memset(&ap, 0, sizeof(ap));
    memset(&config, 0, sizeof(config));
    result = wcp_ap_record(record, record_length, before, after, snapshot_interface_index, &ap);
    if (result != WCP_OK) goto done;
    if (ap.security == WCP_AP_OPEN && credential_kind == WCP_CREDENTIAL_NONE) {
        config.security_type = 0;
    } else if (ap.security == WCP_AP_WPA2 && credential_kind == WCP_CREDENTIAL_PASSPHRASE) {
        if (strlen(ap.psk) > 63u) {
            result = WCP_SECURITY;
            goto done;
        }
        config.security_type = 2;
        config.has_passphrase = 1;
        config.passphrase = (const uint8_t *)ap.psk;
        config.passphrase_len = strlen(ap.psk);
    } else {
        result = WCP_SECURITY;
        goto done;
    }
    config.ssid = (const uint8_t *)ap.ssid;
    config.ssid_len = strlen(ap.ssid);
    config.has_security_type = 1;
    config.has_channel = 1;
    config.channel = (uint8_t)ap.channel;
    result = iap2_5703_encode_body(&config, out, capacity, out_length) == 0 ? WCP_OK : WCP_INVALID;
done:
    wipe(&config, sizeof(config));
    wipe(&ap, sizeof(ap));
    return result;
}
