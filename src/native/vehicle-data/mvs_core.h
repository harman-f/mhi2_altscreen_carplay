/* MU1440 MVS1 portable source-to-iAP2 core. HOST ONLY until gated target port.
 * Independently authored interface (not a copy of Audi/Cinemo hook code).
 * This API NEVER transmits or modifies a car process. C99, no dynamic allocation.
 */
#ifndef MVS_CORE_H
#define MVS_CORE_H
#include <stddef.h>
#include <stdint.h>

#define MVS_WIRE_BYTES 24u
#define MVS_BATCH 5u
#define MVS_SENTENCE_BYTES 192u
#define MVS_VALID_SPEED 0x01u
#define MVS_STANDSTILL  0x02u
#define MVS_GEAR_VALID  0x04u
#define MVS_REVERSE     0x08u
#define MVS_VALID_MASK  0x0fu

/* MVS1 wire v1 LE: 0..3 "MVS1"; 4 version=1; 5 flags;
 * 6..7 reserved=0; 8..15 source monotonic milliseconds (LE64);
 * 16..19 speed in millimetres/second (LE32); 20..23 source DSI event sequence
 * (LE32). Sequence increments ONLY for a fresh real DSI event; do not
 * invent 5 Hz samples by replaying the last DSI speed from a timer.
 * All timestamps belong to ONE monotonic clock domain; reset on reconnect.
 */
typedef struct {
    uint64_t sample_ms;
    uint32_t speed_mmps;
    uint32_t source_seq;
    uint8_t flags;
} mvs_sample;

typedef struct {
    mvs_sample samples[MVS_BATCH];
    unsigned count;
    uint64_t last_sample_ms;
    uint32_t last_source_seq;
    int have_last;
    int identify_speed_advertised; /* from verified CURRENT session Identify */
    int phone_wants_speed;         /* from valid CURRENT 0xFFFA param id 4 */
    int stock_pascd_seen;          /* latched until Identify/session reset */
} mvs_engine;

/* 0=valid/success, -1=invalid. Decoder rejects unknown flags, bad reserved
 * bits, nonzero invalid speed, and impossible speeds (>100 m/s). */
int mvs_wire_encode(const mvs_sample *s, uint8_t *out, size_t cap);
int mvs_wire_decode(const uint8_t *p, size_t n, mvs_sample *out);
void mvs_reset(mvs_engine *e);
void mvs_set_identify_speed(mvs_engine *e, int confirmed); /* resets phone request/batch */
int mvs_start_location(mvs_engine *e, const uint8_t *tlv, size_t n);
/* TLV is JUST the authenticated iAP2 StartLocationInformation parameter
 * payload: big endian length incl. 4 byte header and id, id 4=VehicleSpeedData.
 * Return 1=valid request, 0=no request, -1=malformed (fail closed). */
void mvs_stop_location(mvs_engine *e);
void mvs_stock_pascd_observed(mvs_engine *e); /* externally verified stock only */
/* Returns >0 NUL-terminated PASCD chars in out; 0 no sentence; -1 invalid
 * input/buffer. Engine never performs iAP2 IO, hooks Identify or sends GPS. */
int mvs_ingest(mvs_engine *e, const uint8_t *wire, size_t n, uint64_t now_ms,
               char *out, size_t cap);
/* Wrap NUL-terminated PASCD in iAP2 LocationInformation parameter 0 TLV.
 * Returns length incl. TLV+NUL, or 0. Caller must pass to a separately
 * qualified EXISTING current-session DIO send worker, never a second owner. */
size_t mvs_location_tlv(const char *sentence, uint8_t *out, size_t cap);
#endif
