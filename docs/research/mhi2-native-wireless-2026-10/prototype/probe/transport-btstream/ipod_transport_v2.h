#ifndef MIB_IPOD_TRANSPORT_V2_H
#define MIB_IPOD_TRANSPORT_V2_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

#if UINTPTR_MAX != 0xffffffffu
#error "The stock MHI2 ipod_transport ABI is 32-bit ARM; compile this target with a 32-bit ABI."
#endif

struct ipod_transport_v2;

typedef int (*ipod_transport_init_fn)(struct ipod_transport_v2 *self,
                                      const char *mount_base,
                                      const char *options);
typedef int (*ipod_transport_link_params_fn)(struct ipod_transport_v2 *self,
                                             void *out_12_bytes);
typedef int (*ipod_transport_type_fn)(struct ipod_transport_v2 *self,
                                      uint8_t *out_type);
typedef int (*ipod_transport_caps_fn)(struct ipod_transport_v2 *self,
                                      int capability,
                                      void *out_value);
typedef int (*ipod_transport_audiopath_fn)(struct ipod_transport_v2 *self);
typedef ssize_t (*ipod_transport_send_fn)(struct ipod_transport_v2 *self,
                                          const void *buffer,
                                          size_t length);
typedef ssize_t (*ipod_transport_recv_fn)(struct ipod_transport_v2 *self,
                                          void *buffer,
                                          size_t length,
                                          int timeout_ms);

/*
 * Exact callback-prefix layout recovered from MU1440
 * ipod-transport-usbdevice.so. The trailing 0x78 bytes are transport-private
 * state. mm-ipod writes its host/device context at +0x0c before calling init.
 */
struct ipod_transport_v2 {
    const char *interface_name;                   /* +0x00 */
    uint32_t reserved_04;                         /* +0x04 */
    uint32_t reserved_08;                         /* +0x08 */
    void *host_context;                           /* +0x0c */
    uint32_t reserved_10;                         /* +0x10 */
    ipod_transport_init_fn init;                  /* +0x14 */
    ipod_transport_link_params_fn link_params;    /* +0x18 */
    ipod_transport_type_fn type_get;              /* +0x1c */
    ipod_transport_caps_fn caps_get;              /* +0x20 */
    ipod_transport_audiopath_fn audiopath_get;    /* +0x24 */
    ipod_transport_send_fn data_send;             /* +0x28 */
    ipod_transport_recv_fn data_recv;             /* +0x2c */
    uint32_t private_words[30];                   /* +0x30 .. +0xa7 */
};

/*
 * Exact 36-byte ipod_module prefix used by stock mm-ipod:
 * +0x00 module name pointer
 * +0x04 interface version 0x0200
 * +0x20 interface pointer
 */
struct ipod_module_v2 {
    const char *module_name;                      /* +0x00 */
    uint32_t interface_version;                   /* +0x04 */
    uint32_t reserved[6];                         /* +0x08 .. +0x1f */
    struct ipod_transport_v2 *transport;          /* +0x20 */
};

#define IPOD_TRANSPORT_V2_VERSION 0x0200u
#define IPOD_TRANSPORT_TYPE_BLUETOOTH 3u
#define IPOD_LINK_PARAMS_SIZE 12u

#define ABI_ASSERT(name, expr) typedef char abi_assert_##name[(expr) ? 1 : -1]
ABI_ASSERT(transport_size, sizeof(struct ipod_transport_v2) == 168);
ABI_ASSERT(transport_host_offset, offsetof(struct ipod_transport_v2, host_context) == 0x0c);
ABI_ASSERT(transport_init_offset, offsetof(struct ipod_transport_v2, init) == 0x14);
ABI_ASSERT(transport_link_offset, offsetof(struct ipod_transport_v2, link_params) == 0x18);
ABI_ASSERT(transport_type_offset, offsetof(struct ipod_transport_v2, type_get) == 0x1c);
ABI_ASSERT(transport_caps_offset, offsetof(struct ipod_transport_v2, caps_get) == 0x20);
ABI_ASSERT(transport_audio_offset, offsetof(struct ipod_transport_v2, audiopath_get) == 0x24);
ABI_ASSERT(transport_send_offset, offsetof(struct ipod_transport_v2, data_send) == 0x28);
ABI_ASSERT(transport_recv_offset, offsetof(struct ipod_transport_v2, data_recv) == 0x2c);
ABI_ASSERT(module_size, sizeof(struct ipod_module_v2) == 36);
ABI_ASSERT(module_transport_offset, offsetof(struct ipod_module_v2, transport) == 0x20);

#endif
