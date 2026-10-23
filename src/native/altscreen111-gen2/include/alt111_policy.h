#ifndef MIBR_ALT111_POLICY_H
#define MIBR_ALT111_POLICY_H
#include <stdint.h>

/* Pure producer policy. All calls are serialized by the adapter; no I/O. */
enum alt111_periodic_mode {
    ALT111_SOURCE_FRAMES, ALT111_SOURCE_TIME, ALT111_EVENT_ONLY, ALT111_PERIODIC_OFF
};
enum alt111_keyframe_reason {
    ALT111_KF_PERIODIC_FRAMES = 1u << 0,
    ALT111_KF_PERIODIC_TIME = 1u << 1,
    ALT111_KF_SHOWUI = 1u << 2,
    ALT111_KF_BRIDGE_READY = 1u << 3,
    ALT111_KF_SOURCE_GAP = 1u << 4,
    ALT111_KF_LATENCY_RECOVERY = 1u << 5,
    ALT111_KF_LIFECYCLE_RESET = 1u << 6,
    ALT111_KF_MANUAL = 1u << 7
};
#define ALT111_KF_ALL 255u
struct alt111_policy_config {
    unsigned mode, interval_frames, interval_ms;
    unsigned showui, gap_recovery, latency_recovery;
};
struct alt111_policy {
    struct alt111_policy_config config;
    uint64_t stream, previous_time, previous_arrival_us, phase;
    uint64_t frames_opportunities, time_opportunities, clock_resets;
    unsigned configured, have_time, source_time_available;
};
void alt111_policy_defaults(struct alt111_policy_config *config);
int alt111_policy_configure(struct alt111_policy *policy,
                           const struct alt111_policy_config *config);
unsigned alt111_policy_au(struct alt111_policy *policy, uint64_t stream,
                          uint64_t source_ordinal, const uint8_t raw[8],
                          unsigned time_present, uint64_t arrival_us);
unsigned alt111_policy_event(const struct alt111_policy_config *config,
                             unsigned reasons);
const char *alt111_keyframe_reason_name(unsigned single_reason);
#endif
