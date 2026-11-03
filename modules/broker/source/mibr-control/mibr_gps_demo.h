/* Original DIO/iAP2-owned CarPlay-only GNSS demo filter. */
#ifndef MIBR_GPS_DEMO_H
#define MIBR_GPS_DEMO_H
#include <stddef.h>
#include <stdint.h>
#define MIBR_GPS_DEMO_NMEA_MAX 255
enum mibr_gps_demo_choice {
    MIBR_GPS_OFF=0,MIBR_GPS_BERLIN=1,MIBR_GPS_HAMBURG=2,
    MIBR_GPS_SCHWALEFELD=3,MIBR_GPS_WINTERBERG=4
};
struct mibr_gps_demo {
    uint64_t session_epoch;
    uint64_t speed_timestamp_ms;
    uint64_t parking_timestamp_ms;
    int connected,identify_accepted,location_requested;
    int trusted_stationary,speed_mm_s;
    int trusted_parked;
    enum mibr_gps_demo_choice choice;
};
/* Legacy observations retained for source ABI compatibility. None is a manual
 * demo admission condition; no vehicle data is queried by the product path. */
void mibr_gps_demo_session(struct mibr_gps_demo *,uint64_t epoch,int connected,
                          int identify_accepted,int location_requested);
void mibr_gps_demo_speed(struct mibr_gps_demo *,int genuine_mm_s,
                         uint64_t source_monotonic_ms,int valid);
/* Informational only; does not arm/disarm the manual test mode. */
void mibr_gps_demo_parking(struct mibr_gps_demo *,int genuine_parked,
                           uint64_t source_monotonic_ms,int valid);
int mibr_gps_demo_select(struct mibr_gps_demo *,const char *value,uint64_t epoch,
                         uint64_t now_monotonic_ms);
const char *mibr_gps_demo_name(enum mibr_gps_demo_choice);
int mibr_gps_demo_active(const struct mibr_gps_demo *,uint64_t now_monotonic_ms);
/* 0: pass original NMEA bytes, 1: send out altered NMEA, -1: DROP
 * (never forward a possibly identifying original sentence while spoofing).
 * Caller must use exact original iap2_gps_data_send/current-session owner.
 */
int mibr_gps_demo_filter(struct mibr_gps_demo *,const char *in,size_t in_n,
                        char *out,size_t out_cap,uint64_t now_monotonic_ms);
#endif
