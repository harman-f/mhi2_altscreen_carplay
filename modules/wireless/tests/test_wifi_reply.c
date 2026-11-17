/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "wcp_wifi_reply.h"
#include <assert.h>
#include <string.h>

static int reply(const char *record, uint64_t before, uint64_t after,
                 uint64_t current, enum wcp_credential_kind kind,
                 unsigned char *out, size_t cap, size_t *len)
{
    return wcp_wifi_reply(record, strlen(record), before, after, current,
                          2, 2, kind, out, cap, len);
}
int main(void)
{
    const char *wpa = "ssid=DemoAP\npsk=abcdefgh\nchannel=36,secondary\nsecurity=wpa2\ncipher=ccmp\n";
    const char *open = "ssid=DemoAP\npsk=\nchannel=11,secondary\nsecurity=open\ncipher=none\n";
    const char *raw = "ssid=DemoAP\npsk=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nchannel=36,secondary\nsecurity=wpa2\ncipher=ccmp\n";
    const char *invalid = "ssid=DemoAP\npsk=abcdefgh\nchannel=36,secondary\nsecurity=wpa2\ncipher=none\n";
    const unsigned char expected[] = {0x57,0x03,0x00,0x0b,0x00,0x01,'D','e','m','o','A','P',0,0x00,0x0d,0x00,0x02,'a','b','c','d','e','f','g','h',0,0x00,0x05,0x00,0x03,0x02,0x00,0x05,0x00,0x04,0x24};
    unsigned char out[128], saved[128]; size_t len;
    memset(out, 0xa5, sizeof(out)); memcpy(saved, out, sizeof(out));
    assert(reply(wpa, 7, 7, 7, WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_OK);
    assert(len == sizeof(expected) && !memcmp(out, expected, len));
    memset(out, 0xa5, sizeof(out));
    assert(wcp_wifi_reply(NULL, 1, 7, 7, 7, 2, 2,
                          WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_INVALID && !len && !memcmp(out, saved, sizeof(out)));
    assert(wcp_wifi_reply(wpa, strlen(wpa), 7, 7, 7, 2, 2,
                          WCP_CREDENTIAL_PASSPHRASE, NULL, sizeof(out), &len) == WCP_INVALID && !len);
    assert(wcp_wifi_reply(wpa, strlen(wpa), 7, 7, 7, 2, 2,
                          WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), NULL) == WCP_INVALID && !memcmp(out, saved, sizeof(out)));
    assert(reply(wpa, 7, 8, 8, WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_STALE && !len && !memcmp(out, saved, sizeof(out)));
    assert(reply(wpa, 7, 7, 8, WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_STALE && !len);
    assert(wcp_wifi_reply(wpa, strlen(wpa), 7, 7, 7, 2, 3,
                          WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_STALE && !len && !memcmp(out, saved, sizeof(out)));
    assert(wcp_wifi_reply(wpa, strlen(wpa), 7, 7, 7, 2, 0,
                          WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_STALE && !len);
    assert(reply(raw, 7, 7, 7, WCP_CREDENTIAL_RAW_PSK, out, sizeof(out), &len) == WCP_SECURITY && !len);
    assert(reply(raw, 7, 7, 7, WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_SECURITY && !len);
    assert(reply(invalid, 7, 7, 7, WCP_CREDENTIAL_PASSPHRASE, out, sizeof(out), &len) == WCP_SECURITY && !len);
    assert(reply(wpa, 7, 7, 7, WCP_CREDENTIAL_NONE, out, sizeof(out), &len) == WCP_SECURITY && !len);
    assert(reply(wpa, 7, 7, 7, WCP_CREDENTIAL_PASSPHRASE, out, 3, &len) == WCP_INVALID && !len && !memcmp(out, saved, sizeof(out)));
    assert(reply(open, 7, 7, 7, WCP_CREDENTIAL_NONE, out, sizeof(out), &len) == WCP_OK && len == 23);
    return 0;
}
