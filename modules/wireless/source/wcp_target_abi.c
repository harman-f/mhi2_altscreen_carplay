/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Build-time assertions for the project C boundary, never an OEM vtable. */
#include "wcp_control.h"
#if defined(MIBR_WCP_TARGET_QNX)
#if !defined(__QNXNTO__) || !defined(__arm__)
#error Expected QNX ARM target compiler
#endif
typedef char pointer_width_must_be_32[(sizeof(void *) == 4) ? 1 : -1];
typedef char callback_width_must_be_32[(sizeof(((struct wcp_ops *)0)->begin) == 4) ? 1 : -1];
typedef char request_width_must_be_64[(sizeof(uint64_t) == 8) ? 1 : -1];
typedef char abi_header_offset[(offsetof(struct wcp_ops, context) == 12) ? 1 : -1];
#endif
/* A nonempty translation unit also builds with strict host C99 compilers. */
const uint32_t mibr_wcp_abi_version = WCP_ABI;
