/* SPDX-License-Identifier: GPL-3.0-or-later
 * clang's armv7a-none-eabi target lowers struct copies and zeroing to the ARM EABI helpers below;
 * the QNX 6.5 libc does not export them. Hidden, so they never interpose anything in the process.
 */
#include <stddef.h>
#include <string.h>

#define HIDDEN __attribute__((visibility("hidden")))

HIDDEN void __aeabi_memcpy(void *d, const void *s, size_t n) { memcpy(d, s, n); }
HIDDEN void __aeabi_memcpy4(void *d, const void *s, size_t n) { memcpy(d, s, n); }
HIDDEN void __aeabi_memcpy8(void *d, const void *s, size_t n) { memcpy(d, s, n); }
HIDDEN void __aeabi_memclr(void *d, size_t n) { memset(d, 0, n); }
HIDDEN void __aeabi_memclr4(void *d, size_t n) { memset(d, 0, n); }
HIDDEN void __aeabi_memclr8(void *d, size_t n) { memset(d, 0, n); }
