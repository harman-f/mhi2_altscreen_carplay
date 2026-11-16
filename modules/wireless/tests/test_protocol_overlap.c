/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../source/wcp_protocol.h"
#include <assert.h>
#include <string.h>

static void stream(unsigned char *p) {
    size_t i;
    p[0] = 7; p[1] = 255;
    for (i = 0; i < 255; ++i) p[2+i] = (unsigned char)i;
    p[257] = 7; p[258] = 3; p[259] = 9; p[260] = 8; p[261] = 7;
}
static void reject_overlap(size_t input, size_t output) {
    unsigned char b[800], before[800]; size_t n = 77;
    memset(b, 0xa5, sizeof b); stream(b + input); memcpy(before, b, sizeof b);
    assert(wcp_tlv_value(b + input, 262, 7, b + output, 258, &n) == WCP_PARSE_ERROR);
    assert(n == 0); assert(memcmp(b, before, sizeof b) == 0);
}
int main(void) {
    unsigned char b[800]; size_t n;
    reject_overlap(100, 104); reject_overlap(300, 100);
    memset(b, 0, sizeof b); stream(b + 10); n = 99;
    assert(wcp_tlv_value(b + 10, 262, 7, b + 272, 258, &n) == WCP_PARSE_OK && n == 258);
    assert(b[272] == 0 && b[526] == 254 && b[527] == 9 && b[529] == 7);
    memset(b, 0, sizeof b); stream(b + 300); n = 99;
    assert(wcp_tlv_value(b + 300, 262, 7, b + 42, 258, &n) == WCP_PARSE_OK && n == 258);
    b[0] = 7; b[1] = 0; n = 99;
    assert(wcp_tlv_value(b, 2, 7, NULL, 0, &n) == WCP_PARSE_OK && n == 0);
    n = 99; assert(wcp_tlv_value(b, 2, 7, b, 1, &n) == WCP_PARSE_OK && n == 0);
    n = 99; assert(wcp_tlv_value(NULL, 0, 7, NULL, 0, &n) == WCP_PARSE_MORE && n == 0);
    n = 99; assert(wcp_tlv_value(NULL, 1, 7, NULL, 0, &n) == WCP_PARSE_ERROR && n == 0);
    n = 99; assert(wcp_tlv_value(b, 2, 7, NULL, 1, &n) == WCP_PARSE_ERROR && n == 0);
    return 0;
}
