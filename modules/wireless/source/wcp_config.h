/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_WCP_CONFIG_H
#define MIBR_WCP_CONFIG_H
#include "wcp_control.h"

/* Project-owned normalized record formats, NOT a driver configuration parser.
 * Caller owns the bounded input and must clear it after credential use. The
 * caller must also clear a successful wcp_ap_record output after credential
 * use; on error the output is zeroed. Input and output storage must not overlap.
 * No files, settings stores or radio configuration are read/written. */
int wcp_config_parse(const void *, size_t, struct wcp_config *);
/* Require equal nonzero producer generations around the caller's snapshot.
 * Equality is a consistency check, not independent proof of a live/fresh AP. */
int wcp_ap_record(const void *, size_t, uint64_t before, uint64_t after,
                   uint32_t interface_index, struct wcp_ap *);
#endif
