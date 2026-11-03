/* Offline NMEA coordinate interpolation primitive; NEVER sends iAP2 packets.
 * It requires TWO real, timestamped fixes. Produces quarter-time intermediate
 * samples for a 1-second-delayed 4 Hz pipeline, not predictions of the future.
 * No change to DIO/iAP2 owner or original 1 Hz stream in normal builds.
 */
#ifndef MIBR_GPS_4HZ_H
#define MIBR_GPS_4HZ_H
#include <stdint.h>
struct mibr_gps_sample {
    int32_t latitude_e7,longitude_e7;
    uint64_t monotonic_ms;
};
/* Stationary DEMO: no next sample needed; three 250ms subfix placeholders. */
int mibr_gps_4hz_stationary(const struct mibr_gps_sample *current,
                            struct mibr_gps_sample subfix[3]);
int mibr_gps_4hz_interpolate(const struct mibr_gps_sample *before,
                             const struct mibr_gps_sample *after,
                             struct mibr_gps_sample intermediate[3]);
#endif
