/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef WCP_WIFI_REPLY_H
#define WCP_WIFI_REPLY_H
#include <stddef.h>
#include <stdint.h>
#include "wcp_control.h"

enum wcp_credential_kind { WCP_CREDENTIAL_NONE = 0, WCP_CREDENTIAL_PASSPHRASE = 1, WCP_CREDENTIAL_RAW_PSK = 2 };

/* Encode a normalized project record, not a raw driver file. The caller must
 * independently obtain the snapshot and current interface/generation. Both
 * interface indices must be nonzero and equal; equality cannot establish that
 * the radio actually matches the snapshot.
 * All input, output and output-length storage must be disjoint. On failure the
 * output bytes are unchanged and *out_length is zero. The caller owns and must
 * clear the input record and successful output, which can contain credentials. */
int wcp_wifi_reply(const void *record, size_t record_length,
                   uint64_t before, uint64_t after, uint64_t current,
                   uint32_t snapshot_interface_index, uint32_t current_interface_index,
                   enum wcp_credential_kind credential_kind,
                   unsigned char *out, size_t capacity, size_t *out_length);
#endif
