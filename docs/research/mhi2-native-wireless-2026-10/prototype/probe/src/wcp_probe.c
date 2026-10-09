#include "wcp_probe.h"

#include <stdio.h>
#include <string.h>

#define WCP_MAX_MESSAGE 4096u
#define WCP_MAX_AUTH_BLOB 2048u

static uint16_t read_be16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static void write_be16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)(value >> 8);
    p[1] = (uint8_t)(value & 0xff);
}

static int append_bytes(uint8_t *out, size_t cap, size_t *pos,
                        const void *data, size_t len)
{
    if (!out || !pos || (!data && len) || *pos > cap || len > cap - *pos)
        return -1;
    if (len)
        memcpy(out + *pos, data, len);
    *pos += len;
    return 0;
}

static int append_tlv_raw(uint8_t *out, size_t cap, size_t *pos,
                          uint16_t parameter_id,
                          const uint8_t *value, size_t value_len)
{
    uint8_t header[4];
    size_t total = value_len + sizeof(header);

    if (total > 0xffffu)
        return -1;

    write_be16(header, (uint16_t)total);
    write_be16(header + 2, parameter_id);
    if (append_bytes(out, cap, pos, header, sizeof(header)) != 0)
        return -1;
    return append_bytes(out, cap, pos, value, value_len);
}

static int append_tlv_empty(uint8_t *out, size_t cap, size_t *pos,
                            uint16_t parameter_id)
{
    return append_tlv_raw(out, cap, pos, parameter_id, NULL, 0);
}

static int append_tlv_u8(uint8_t *out, size_t cap, size_t *pos,
                         uint16_t parameter_id, uint8_t value)
{
    return append_tlv_raw(out, cap, pos, parameter_id, &value, 1);
}

static int append_tlv_u16(uint8_t *out, size_t cap, size_t *pos,
                          uint16_t parameter_id, uint16_t value)
{
    uint8_t bytes[2];
    write_be16(bytes, value);
    return append_tlv_raw(out, cap, pos, parameter_id, bytes, sizeof(bytes));
}

static int append_tlv_string(uint8_t *out, size_t cap, size_t *pos,
                             uint16_t parameter_id, const char *value)
{
    size_t len;

    if (!value)
        return -1;
    len = strlen(value) + 1;
    return append_tlv_raw(out, cap, pos, parameter_id,
                          (const uint8_t *)value, len);
}

static int begin_csm(uint8_t *out, size_t cap, uint16_t message_id, size_t *pos)
{
    if (!out || !pos || cap < 6)
        return -1;

    write_be16(out, WCP_CSM_MAGIC);
    write_be16(out + 2, 0);
    write_be16(out + 4, message_id);
    *pos = 6;
    return 0;
}

static int finish_csm(uint8_t *out, size_t cap, size_t pos, size_t *out_len)
{
    if (!out || !out_len || pos > cap || pos > 0xffffu)
        return -1;

    write_be16(out + 2, (uint16_t)pos);
    *out_len = pos;
    return 0;
}

static int build_single_blob_message(uint16_t message_id,
                                     const uint8_t *blob, size_t blob_len,
                                     uint8_t *out, size_t cap, size_t *out_len)
{
    size_t pos;

    if (begin_csm(out, cap, message_id, &pos) != 0)
        return -1;
    if (append_tlv_raw(out, cap, &pos, 0, blob, blob_len) != 0)
        return -1;
    return finish_csm(out, cap, pos, out_len);
}

static int find_tlv(const uint8_t *payload, size_t payload_len,
                    uint16_t wanted_id,
                    const uint8_t **value, size_t *value_len)
{
    size_t pos = 0;

    if (!payload || !value || !value_len)
        return -1;

    while (pos < payload_len) {
        uint16_t total;
        uint16_t parameter_id;

        if (payload_len - pos < 4)
            return -1;

        total = read_be16(payload + pos);
        parameter_id = read_be16(payload + pos + 2);
        if (total < 4 || total > payload_len - pos)
            return -1;

        if (parameter_id == wanted_id) {
            *value = payload + pos + 4;
            *value_len = total - 4;
            return 0;
        }

        pos += total;
    }

    return 1;
}

static void emit(struct wcp_probe *probe, enum wcp_probe_event event,
                 const char *detail)
{
    if (probe && probe->callbacks.event)
        probe->callbacks.event(probe->opaque, event, detail ? detail : "");
}

static int send_message(struct wcp_probe *probe,
                        const uint8_t *message, size_t message_len)
{
    if (!probe || !probe->callbacks.send_control_message)
        return -1;
    return probe->callbacks.send_control_message(probe->opaque,
                                                 message, message_len);
}

int wcp_csm_parse(const uint8_t *message,
                  size_t message_len,
                  struct wcp_csm_view *view)
{
    uint16_t declared_length;

    if (!message || !view || message_len < 6)
        return -1;
    if (read_be16(message) != WCP_CSM_MAGIC)
        return -2;

    declared_length = read_be16(message + 2);
    if (declared_length < 6 || declared_length != message_len)
        return -3;

    view->message_id = read_be16(message + 4);
    view->payload = message + 6;
    view->payload_len = message_len - 6;
    return 0;
}

int wcp_build_wifi_config_message(const struct wcp_wifi_config *wifi,
                                  uint8_t *out,
                                  size_t cap,
                                  size_t *out_len)
{
    size_t pos;

    if (!wifi || !wifi->ssid || !wifi->passphrase || !out || !out_len)
        return -1;
    if (wifi->channel == 0)
        return -1;

    if (begin_csm(out, cap, WCP_MSG_ACCESSORY_WIFI_CONFIGURATION, &pos) != 0)
        return -1;
    if (append_tlv_string(out, cap, &pos, 1, wifi->ssid) != 0)
        return -1;
    if (append_tlv_string(out, cap, &pos, 2, wifi->passphrase) != 0)
        return -1;
    if (append_tlv_u8(out, cap, &pos, 3, wifi->security_type) != 0)
        return -1;
    if (append_tlv_u8(out, cap, &pos, 4, wifi->channel) != 0)
        return -1;

    return finish_csm(out, cap, pos, out_len);
}

static int append_transport_component(uint8_t *out, size_t cap, size_t *pos,
                                      uint16_t outer_parameter_id,
                                      uint16_t component_id,
                                      const char *component_name,
                                      const uint8_t *mac,
                                      int supports_carplay)
{
    uint8_t nested[256];
    size_t nested_pos = 0;

    if (append_tlv_u16(nested, sizeof(nested), &nested_pos, 0, component_id) != 0)
        return -1;
    if (append_tlv_string(nested, sizeof(nested), &nested_pos, 1,
                          component_name) != 0)
        return -1;
    if (append_tlv_empty(nested, sizeof(nested), &nested_pos, 2) != 0)
        return -1;

    if (mac) {
        if (append_tlv_raw(nested, sizeof(nested), &nested_pos, 3, mac, 6) != 0)
            return -1;
    }

    if (supports_carplay) {
        if (append_tlv_empty(nested, sizeof(nested), &nested_pos, 4) != 0)
            return -1;
    }

    return append_tlv_raw(out, cap, pos, outer_parameter_id,
                          nested, nested_pos);
}

int wcp_build_identification_message(const struct wcp_identity *identity,
                                     uint8_t *out,
                                     size_t cap,
                                     size_t *out_len)
{
    static const uint8_t accessory_sent_messages[] = {
        0x57, 0x03
    };
    static const uint8_t accessory_received_messages[] = {
        0x57, 0x02, 0x4e, 0x0d, 0x4e, 0x0e
    };
    const char *language;
    size_t pos;

    if (!identity || !identity->name || !identity->model_identifier ||
        !identity->manufacturer || !identity->serial_number ||
        !identity->firmware_version || !identity->hardware_version ||
        !identity->bluetooth_mac || !out || !out_len)
        return -1;

    language = identity->language ? identity->language : "en";

    if (begin_csm(out, cap, WCP_MSG_IDENTIFICATION_INFORMATION, &pos) != 0)
        return -1;

    /*
     * Parameter numbering follows the iAP2 Identification information layout
     * observed in the MH2P implementation and independent protocol fixtures.
     * This is a probe fixture, not a claim of a complete MFi identification
     * descriptor.
     */
    if (append_tlv_string(out, cap, &pos, 0, identity->name) != 0 ||
        append_tlv_string(out, cap, &pos, 1, identity->model_identifier) != 0 ||
        append_tlv_string(out, cap, &pos, 2, identity->manufacturer) != 0 ||
        append_tlv_string(out, cap, &pos, 3, identity->serial_number) != 0 ||
        append_tlv_string(out, cap, &pos, 4, identity->firmware_version) != 0 ||
        append_tlv_string(out, cap, &pos, 5, identity->hardware_version) != 0 ||
        append_tlv_raw(out, cap, &pos, 6, accessory_sent_messages,
                       sizeof(accessory_sent_messages)) != 0 ||
        append_tlv_raw(out, cap, &pos, 7, accessory_received_messages,
                       sizeof(accessory_received_messages)) != 0 ||
        append_tlv_u8(out, cap, &pos, 8, 0) != 0 ||
        append_tlv_u16(out, cap, &pos, 9, 0) != 0 ||
        append_tlv_string(out, cap, &pos, 12, language) != 0 ||
        append_tlv_string(out, cap, &pos, 13, language) != 0)
        return -1;

    if (append_transport_component(out, cap, &pos, 17,
                                   identity->bluetooth_transport_id,
                                   "Bluetooth",
                                   identity->bluetooth_mac, 0) != 0)
        return -1;

    if (append_transport_component(out, cap, &pos, 24,
                                   identity->wireless_carplay_transport_id,
                                   "WirelessCarPlay",
                                   NULL, 1) != 0)
        return -1;

    return finish_csm(out, cap, pos, out_len);
}

int wcp_probe_init(struct wcp_probe *probe,
                   const struct wcp_wifi_config *wifi,
                   const struct wcp_identity *identity,
                   const struct wcp_probe_callbacks *callbacks,
                   void *opaque)
{
    if (!probe || !wifi || !identity || !callbacks ||
        !callbacks->send_control_message)
        return -1;

    memset(probe, 0, sizeof(*probe));
    probe->wifi = *wifi;
    probe->identity = *identity;
    probe->callbacks = *callbacks;
    probe->opaque = opaque;
    probe->state = WCP_STATE_IDLE;
    return 0;
}

int wcp_probe_handle_control_message(struct wcp_probe *probe,
                                     const uint8_t *message,
                                     size_t message_len)
{
    struct wcp_csm_view view;
    uint8_t out[WCP_MAX_MESSAGE];
    size_t out_len = 0;
    int rc;

    if (!probe)
        return -1;

    rc = wcp_csm_parse(message, message_len, &view);
    if (rc != 0) {
        probe->state = WCP_STATE_FAILED;
        emit(probe, WCP_EVENT_PROTOCOL_ERROR, "invalid CSM frame");
        return rc;
    }

    switch (view.message_id) {
    case WCP_MSG_START_IDENTIFICATION:
        emit(probe, WCP_EVENT_START_IDENTIFICATION, "0x1D00 received");
        emit(probe, WCP_EVENT_BT_2P4_RESTRICT_REQUIRED,
             "2.4GHz probe: keep only bootstrap Bluetooth/iAP2; no extra BT profiles/scanning");
        if (wcp_build_identification_message(&probe->identity,
                                             out, sizeof(out), &out_len) != 0 ||
            send_message(probe, out, out_len) != 0) {
            probe->state = WCP_STATE_FAILED;
            return -1;
        }
        probe->state = WCP_STATE_IDENTIFICATION_SENT;
        emit(probe, WCP_EVENT_IDENTIFICATION_SENT, "0x1D01 sent");
        return 0;

    case WCP_MSG_IDENTIFICATION_ACCEPTED:
        probe->state = WCP_STATE_IDENTIFICATION_ACCEPTED;
        emit(probe, WCP_EVENT_IDENTIFICATION_ACCEPTED, "0x1D02 received");
        return 0;

    case WCP_MSG_IDENTIFICATION_REJECTED:
        probe->state = WCP_STATE_FAILED;
        emit(probe, WCP_EVENT_IDENTIFICATION_REJECTED, "0x1D03 received");
        return -1;

    case WCP_MSG_REQUEST_AUTH_CERTIFICATE: {
        uint8_t certificate[WCP_MAX_AUTH_BLOB];
        size_t certificate_len = 0;

        emit(probe, WCP_EVENT_AUTH_CERT_REQUEST, "0xAA00 received");
        if (!probe->callbacks.mfi_copy_certificate ||
            probe->callbacks.mfi_copy_certificate(probe->opaque,
                                                  certificate,
                                                  sizeof(certificate),
                                                  &certificate_len) != 0 ||
            certificate_len == 0 ||
            build_single_blob_message(WCP_MSG_AUTH_CERTIFICATE,
                                      certificate, certificate_len,
                                      out, sizeof(out), &out_len) != 0 ||
            send_message(probe, out, out_len) != 0) {
            probe->state = WCP_STATE_FAILED;
            return -1;
        }
        probe->state = WCP_STATE_AUTHENTICATING;
        return 0;
    }

    case WCP_MSG_REQUEST_AUTH_CHALLENGE_RESPONSE: {
        const uint8_t *challenge = NULL;
        size_t challenge_len = 0;
        uint8_t signature[WCP_MAX_AUTH_BLOB];
        size_t signature_len = 0;

        emit(probe, WCP_EVENT_AUTH_CHALLENGE, "0xAA02 received");
        if (find_tlv(view.payload, view.payload_len, 0,
                     &challenge, &challenge_len) != 0 ||
            challenge_len == 0 ||
            !probe->callbacks.mfi_sign_challenge ||
            probe->callbacks.mfi_sign_challenge(probe->opaque,
                                                challenge, challenge_len,
                                                signature, sizeof(signature),
                                                &signature_len) != 0 ||
            signature_len == 0 ||
            build_single_blob_message(WCP_MSG_AUTH_RESPONSE,
                                      signature, signature_len,
                                      out, sizeof(out), &out_len) != 0 ||
            send_message(probe, out, out_len) != 0) {
            probe->state = WCP_STATE_FAILED;
            return -1;
        }
        probe->state = WCP_STATE_AUTHENTICATING;
        return 0;
    }

    case WCP_MSG_AUTH_SUCCEEDED:
        probe->state = WCP_STATE_AUTHENTICATED;
        emit(probe, WCP_EVENT_AUTH_SUCCEEDED, "0xAA05 received");
        return 0;

    case WCP_MSG_AUTH_FAILED:
        probe->state = WCP_STATE_FAILED;
        emit(probe, WCP_EVENT_AUTH_FAILED, "0xAA04 received");
        return -1;

    case WCP_MSG_REQUEST_ACCESSORY_WIFI_CONFIGURATION:
        emit(probe, WCP_EVENT_WIFI_CONFIG_REQUEST, "0x5702 received");
        if (probe->state != WCP_STATE_AUTHENTICATED) {
            emit(probe, WCP_EVENT_PROTOCOL_ERROR,
                 "0x5702 received before MFi authentication completed");
            probe->state = WCP_STATE_FAILED;
            return -1;
        }
        if (wcp_build_wifi_config_message(&probe->wifi,
                                          out, sizeof(out), &out_len) != 0 ||
            send_message(probe, out, out_len) != 0) {
            probe->state = WCP_STATE_FAILED;
            return -1;
        }

        probe->state = WCP_STATE_WIFI_CREDENTIALS_SENT;
        emit(probe, WCP_EVENT_WIFI_CONFIG_SENT,
             "0x5703 sent; credential handoff boundary reached");
        emit(probe, WCP_EVENT_BT_DISCONNECT_AFTER_WIFI_ARMED,
             "do not tear down bootstrap link yet; disconnect Bluetooth after Wi-Fi/CarPlay handoff");
        emit(probe, WCP_EVENT_PROBE_COMPLETE,
             "bounded Track B probe complete at Wi-Fi credential handoff");
        return 1;

    default:
        return 0;
    }
}

const char *wcp_probe_state_name(enum wcp_probe_state state)
{
    switch (state) {
    case WCP_STATE_IDLE: return "IDLE";
    case WCP_STATE_IDENTIFICATION_SENT: return "IDENTIFICATION_SENT";
    case WCP_STATE_IDENTIFICATION_ACCEPTED: return "IDENTIFICATION_ACCEPTED";
    case WCP_STATE_AUTHENTICATING: return "AUTHENTICATING";
    case WCP_STATE_AUTHENTICATED: return "AUTHENTICATED";
    case WCP_STATE_WIFI_CREDENTIALS_SENT: return "WIFI_CREDENTIALS_SENT";
    case WCP_STATE_FAILED: return "FAILED";
    default: return "UNKNOWN";
    }
}

const char *wcp_probe_event_name(enum wcp_probe_event event)
{
    switch (event) {
    case WCP_EVENT_START_IDENTIFICATION: return "START_IDENTIFICATION";
    case WCP_EVENT_IDENTIFICATION_SENT: return "IDENTIFICATION_SENT";
    case WCP_EVENT_IDENTIFICATION_ACCEPTED: return "IDENTIFICATION_ACCEPTED";
    case WCP_EVENT_IDENTIFICATION_REJECTED: return "IDENTIFICATION_REJECTED";
    case WCP_EVENT_AUTH_CERT_REQUEST: return "AUTH_CERT_REQUEST";
    case WCP_EVENT_AUTH_CHALLENGE: return "AUTH_CHALLENGE";
    case WCP_EVENT_AUTH_SUCCEEDED: return "AUTH_SUCCEEDED";
    case WCP_EVENT_AUTH_FAILED: return "AUTH_FAILED";
    case WCP_EVENT_WIFI_CONFIG_REQUEST: return "WIFI_CONFIG_REQUEST";
    case WCP_EVENT_WIFI_CONFIG_SENT: return "WIFI_CONFIG_SENT";
    case WCP_EVENT_BT_2P4_RESTRICT_REQUIRED: return "BT_2P4_RESTRICT_REQUIRED";
    case WCP_EVENT_BT_DISCONNECT_AFTER_WIFI_ARMED: return "BT_DISCONNECT_AFTER_WIFI_ARMED";
    case WCP_EVENT_PROBE_COMPLETE: return "PROBE_COMPLETE";
    case WCP_EVENT_PROTOCOL_ERROR: return "PROTOCOL_ERROR";
    default: return "UNKNOWN";
    }
}
