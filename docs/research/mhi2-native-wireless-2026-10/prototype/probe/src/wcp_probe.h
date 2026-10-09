#ifndef MIB_WCP_PROBE_H
#define MIB_WCP_PROBE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WCP_CSM_MAGIC 0x4040u

enum wcp_message_id {
    WCP_MSG_START_IDENTIFICATION = 0x1D00,
    WCP_MSG_IDENTIFICATION_INFORMATION = 0x1D01,
    WCP_MSG_IDENTIFICATION_ACCEPTED = 0x1D02,
    WCP_MSG_IDENTIFICATION_REJECTED = 0x1D03,

    WCP_MSG_WIRELESS_CARPLAY_UPDATE = 0x4E0D,
    WCP_MSG_DEVICE_TRANSPORT_IDENTIFIER = 0x4E0E,

    WCP_MSG_REQUEST_WIFI_INFORMATION = 0x5700,
    WCP_MSG_WIFI_INFORMATION = 0x5701,
    WCP_MSG_REQUEST_ACCESSORY_WIFI_CONFIGURATION = 0x5702,
    WCP_MSG_ACCESSORY_WIFI_CONFIGURATION = 0x5703,

    WCP_MSG_REQUEST_AUTH_CERTIFICATE = 0xAA00,
    WCP_MSG_AUTH_CERTIFICATE = 0xAA01,
    WCP_MSG_REQUEST_AUTH_CHALLENGE_RESPONSE = 0xAA02,
    WCP_MSG_AUTH_RESPONSE = 0xAA03,
    WCP_MSG_AUTH_FAILED = 0xAA04,
    WCP_MSG_AUTH_SUCCEEDED = 0xAA05
};

enum wcp_security_type {
    WCP_SECURITY_NONE = 0,
    WCP_SECURITY_WEP = 1,
    WCP_SECURITY_WPA_WPA2 = 2
};

enum wcp_probe_state {
    WCP_STATE_IDLE = 0,
    WCP_STATE_IDENTIFICATION_SENT,
    WCP_STATE_IDENTIFICATION_ACCEPTED,
    WCP_STATE_AUTHENTICATING,
    WCP_STATE_AUTHENTICATED,
    WCP_STATE_WIFI_CREDENTIALS_SENT,
    WCP_STATE_FAILED
};

enum wcp_probe_event {
    WCP_EVENT_START_IDENTIFICATION = 1,
    WCP_EVENT_IDENTIFICATION_SENT,
    WCP_EVENT_IDENTIFICATION_ACCEPTED,
    WCP_EVENT_IDENTIFICATION_REJECTED,
    WCP_EVENT_AUTH_CERT_REQUEST,
    WCP_EVENT_AUTH_CHALLENGE,
    WCP_EVENT_AUTH_SUCCEEDED,
    WCP_EVENT_AUTH_FAILED,
    WCP_EVENT_WIFI_CONFIG_REQUEST,
    WCP_EVENT_WIFI_CONFIG_SENT,
    WCP_EVENT_BT_2P4_RESTRICT_REQUIRED,
    WCP_EVENT_BT_DISCONNECT_AFTER_WIFI_ARMED,
    WCP_EVENT_PROBE_COMPLETE,
    WCP_EVENT_PROTOCOL_ERROR
};

struct wcp_wifi_config {
    const char *ssid;
    const char *passphrase;
    uint8_t security_type;
    uint8_t channel;
};

struct wcp_identity {
    const char *name;
    const char *model_identifier;
    const char *manufacturer;
    const char *serial_number;
    const char *firmware_version;
    const char *hardware_version;
    const char *language;
    const uint8_t *bluetooth_mac;
    uint16_t bluetooth_transport_id;
    uint16_t wireless_carplay_transport_id;
};

struct wcp_probe_callbacks {
    int (*send_control_message)(void *opaque, const uint8_t *buf, size_t len);
    int (*mfi_copy_certificate)(void *opaque, uint8_t *out, size_t cap, size_t *out_len);
    int (*mfi_sign_challenge)(void *opaque,
                              const uint8_t *challenge,
                              size_t challenge_len,
                              uint8_t *out,
                              size_t cap,
                              size_t *out_len);
    void (*event)(void *opaque, enum wcp_probe_event event, const char *detail);
};

struct wcp_probe {
    enum wcp_probe_state state;
    struct wcp_wifi_config wifi;
    struct wcp_identity identity;
    struct wcp_probe_callbacks callbacks;
    void *opaque;
};

struct wcp_csm_view {
    uint16_t message_id;
    const uint8_t *payload;
    size_t payload_len;
};

int wcp_probe_init(struct wcp_probe *probe,
                   const struct wcp_wifi_config *wifi,
                   const struct wcp_identity *identity,
                   const struct wcp_probe_callbacks *callbacks,
                   void *opaque);

int wcp_probe_handle_control_message(struct wcp_probe *probe,
                                     const uint8_t *message,
                                     size_t message_len);

int wcp_csm_parse(const uint8_t *message,
                  size_t message_len,
                  struct wcp_csm_view *view);

int wcp_build_wifi_config_message(const struct wcp_wifi_config *wifi,
                                  uint8_t *out,
                                  size_t cap,
                                  size_t *out_len);

int wcp_build_identification_message(const struct wcp_identity *identity,
                                     uint8_t *out,
                                     size_t cap,
                                     size_t *out_len);

const char *wcp_probe_state_name(enum wcp_probe_state state);
const char *wcp_probe_event_name(enum wcp_probe_event event);

#ifdef __cplusplus
}
#endif

#endif
