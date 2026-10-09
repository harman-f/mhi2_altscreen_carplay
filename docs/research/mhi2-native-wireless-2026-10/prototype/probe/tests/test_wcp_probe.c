#include "wcp_probe.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

struct fixture {
    uint8_t sent[4096];
    size_t sent_len;
    unsigned events[32];
    size_t event_count;
};

static int send_control(void *opaque, const uint8_t *buf, size_t len)
{
    struct fixture *fx = (struct fixture *)opaque;
    assert(len <= sizeof(fx->sent));
    memcpy(fx->sent, buf, len);
    fx->sent_len = len;
    return 0;
}

static int copy_certificate(void *opaque, uint8_t *out, size_t cap, size_t *out_len)
{
    static const uint8_t cert[] = { 0x30, 0x03, 0x01, 0x02, 0x03 };
    (void)opaque;
    assert(cap >= sizeof(cert));
    memcpy(out, cert, sizeof(cert));
    *out_len = sizeof(cert);
    return 0;
}

static int sign_challenge(void *opaque,
                          const uint8_t *challenge, size_t challenge_len,
                          uint8_t *out, size_t cap, size_t *out_len)
{
    size_t i;
    (void)opaque;
    assert(challenge_len > 0);
    assert(cap >= challenge_len);

    for (i = 0; i < challenge_len; ++i)
        out[i] = (uint8_t)(challenge[challenge_len - 1 - i] ^ 0x5a);

    *out_len = challenge_len;
    return 0;
}

static void event_cb(void *opaque, enum wcp_probe_event event, const char *detail)
{
    struct fixture *fx = (struct fixture *)opaque;
    (void)detail;
    assert(fx->event_count < sizeof(fx->events) / sizeof(fx->events[0]));
    fx->events[fx->event_count++] = (unsigned)event;
}

static size_t make_empty_csm(uint16_t id, uint8_t *out)
{
    out[0] = 0x40;
    out[1] = 0x40;
    out[2] = 0x00;
    out[3] = 0x06;
    out[4] = (uint8_t)(id >> 8);
    out[5] = (uint8_t)id;
    return 6;
}

static size_t make_blob_csm(uint16_t id, const uint8_t *blob, size_t blob_len,
                            uint8_t *out)
{
    size_t total = 6 + 4 + blob_len;
    out[0] = 0x40;
    out[1] = 0x40;
    out[2] = (uint8_t)(total >> 8);
    out[3] = (uint8_t)total;
    out[4] = (uint8_t)(id >> 8);
    out[5] = (uint8_t)id;
    out[6] = (uint8_t)((blob_len + 4) >> 8);
    out[7] = (uint8_t)(blob_len + 4);
    out[8] = 0;
    out[9] = 0;
    memcpy(out + 10, blob, blob_len);
    return total;
}

static int contains_bytes(const uint8_t *buf, size_t len,
                          const uint8_t *needle, size_t needle_len)
{
    size_t i;
    if (needle_len > len)
        return 0;
    for (i = 0; i + needle_len <= len; ++i) {
        if (memcmp(buf + i, needle, needle_len) == 0)
            return 1;
    }
    return 0;
}

static void test_wifi_builder(void)
{
    static const uint8_t ssid_tlv[] = {
        0x00, 0x0c, 0x00, 0x01,
        'M','I','B','-','W','C','P',0x00
    };
    static const uint8_t security_tlv[] = {
        0x00, 0x05, 0x00, 0x03, 0x02
    };
    static const uint8_t channel_tlv[] = {
        0x00, 0x05, 0x00, 0x04, 0x06
    };
    struct wcp_wifi_config wifi = {
        "MIB-WCP", "12345678", WCP_SECURITY_WPA_WPA2, 6
    };
    struct wcp_csm_view view;
    uint8_t out[512];
    size_t out_len = 0;

    assert(wcp_build_wifi_config_message(&wifi, out, sizeof(out), &out_len) == 0);
    assert(wcp_csm_parse(out, out_len, &view) == 0);
    assert(view.message_id == WCP_MSG_ACCESSORY_WIFI_CONFIGURATION);
    assert(contains_bytes(out, out_len, ssid_tlv, sizeof(ssid_tlv)));
    assert(contains_bytes(out, out_len, security_tlv, sizeof(security_tlv)));
    assert(contains_bytes(out, out_len, channel_tlv, sizeof(channel_tlv)));
}

static void test_state_machine(void)
{
    static const uint8_t bt_mac[6] = {0x02,0x11,0x22,0x33,0x44,0x55};
    static const uint8_t challenge[20] = {
        0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19
    };
    struct wcp_wifi_config wifi = {
        "MIB-WCP", "12345678", WCP_SECURITY_WPA_WPA2, 6
    };
    struct wcp_identity identity = {
        "MIB Wireless Probe",
        "MHI2-WCP-PROBE",
        "M.I.B. Research",
        "probe-0001",
        "0.1",
        "MHI2",
        "en",
        bt_mac,
        1,
        2
    };
    struct wcp_probe_callbacks callbacks = {
        send_control,
        copy_certificate,
        sign_challenge,
        event_cb
    };
    struct fixture fx;
    struct wcp_probe probe;
    struct wcp_csm_view view;
    uint8_t in[256];
    size_t in_len;
    int rc;

    memset(&fx, 0, sizeof(fx));
    assert(wcp_probe_init(&probe, &wifi, &identity, &callbacks, &fx) == 0);

    in_len = make_empty_csm(WCP_MSG_START_IDENTIFICATION, in);
    assert(wcp_probe_handle_control_message(&probe, in, in_len) == 0);
    assert(probe.state == WCP_STATE_IDENTIFICATION_SENT);
    assert(wcp_csm_parse(fx.sent, fx.sent_len, &view) == 0);
    assert(view.message_id == WCP_MSG_IDENTIFICATION_INFORMATION);

    in_len = make_empty_csm(WCP_MSG_IDENTIFICATION_ACCEPTED, in);
    assert(wcp_probe_handle_control_message(&probe, in, in_len) == 0);
    assert(probe.state == WCP_STATE_IDENTIFICATION_ACCEPTED);

    in_len = make_empty_csm(WCP_MSG_REQUEST_AUTH_CERTIFICATE, in);
    assert(wcp_probe_handle_control_message(&probe, in, in_len) == 0);
    assert(wcp_csm_parse(fx.sent, fx.sent_len, &view) == 0);
    assert(view.message_id == WCP_MSG_AUTH_CERTIFICATE);

    in_len = make_blob_csm(WCP_MSG_REQUEST_AUTH_CHALLENGE_RESPONSE,
                           challenge, sizeof(challenge), in);
    assert(wcp_probe_handle_control_message(&probe, in, in_len) == 0);
    assert(wcp_csm_parse(fx.sent, fx.sent_len, &view) == 0);
    assert(view.message_id == WCP_MSG_AUTH_RESPONSE);

    in_len = make_empty_csm(WCP_MSG_AUTH_SUCCEEDED, in);
    assert(wcp_probe_handle_control_message(&probe, in, in_len) == 0);
    assert(probe.state == WCP_STATE_AUTHENTICATED);

    in_len = make_empty_csm(WCP_MSG_REQUEST_ACCESSORY_WIFI_CONFIGURATION, in);
    rc = wcp_probe_handle_control_message(&probe, in, in_len);
    assert(rc == 1);
    assert(probe.state == WCP_STATE_WIFI_CREDENTIALS_SENT);
    assert(wcp_csm_parse(fx.sent, fx.sent_len, &view) == 0);
    assert(view.message_id == WCP_MSG_ACCESSORY_WIFI_CONFIGURATION);

    assert(fx.event_count >= 8);
    assert(fx.events[fx.event_count - 1] == WCP_EVENT_PROBE_COMPLETE);
}

static void test_reject_early_wifi_request(void)
{
    static const uint8_t bt_mac[6] = {0,1,2,3,4,5};
    struct wcp_wifi_config wifi = {
        "MIB-WCP", "12345678", WCP_SECURITY_WPA_WPA2, 11
    };
    struct wcp_identity identity = {
        "MIB Wireless Probe", "MHI2-WCP-PROBE", "M.I.B. Research",
        "probe-0002", "0.1", "MHI2", "en", bt_mac, 1, 2
    };
    struct wcp_probe_callbacks callbacks = {
        send_control, copy_certificate, sign_challenge, event_cb
    };
    struct fixture fx;
    struct wcp_probe probe;
    uint8_t in[16];
    size_t in_len;

    memset(&fx, 0, sizeof(fx));
    assert(wcp_probe_init(&probe, &wifi, &identity, &callbacks, &fx) == 0);
    in_len = make_empty_csm(WCP_MSG_REQUEST_ACCESSORY_WIFI_CONFIGURATION, in);
    assert(wcp_probe_handle_control_message(&probe, in, in_len) < 0);
    assert(probe.state == WCP_STATE_FAILED);
}

int main(void)
{
    test_wifi_builder();
    test_state_machine();
    test_reject_early_wifi_request();
    puts("wcp_probe tests: PASS");
    return 0;
}
