/* SPDX-License-Identifier: GPL-3.0-or-later
 * Pure mathematics only. No vendor send callback, no worker timer, no iAP2
 * session handle. Never pretend buffered interpolation can produce real-time
 * 250ms values from a FUTURE GNSS fix that has not arrived.
 */
#include "mibr_gps_4hz.h"
#include <stddef.h>
#define MAX_LAT_E7 900000000
#define MAX_LON_E7 1800000000
#define MAX_CHANGE_E7 300000 /* 3.3km: stale/unrelated source is not a track */
static int safe_sample(const struct mibr_gps_sample *s) {
    return s && s->latitude_e7>=-MAX_LAT_E7 &&
        s->latitude_e7<=MAX_LAT_E7 &&
        s->longitude_e7>=-MAX_LON_E7 &&
        s->longitude_e7<=MAX_LON_E7;
}
static int64_t absolute64(int64_t v){return v<0?-v:v;}
int mibr_gps_4hz_stationary(const struct mibr_gps_sample *current,
                            struct mibr_gps_sample subfix[3]){
    int i;
    if(!safe_sample(current)||!subfix||
       current->monotonic_ms>UINT64_MAX-750u)return -1;
    for(i=0;i<3;i++){
        subfix[i]=*current;
        subfix[i].monotonic_ms=current->monotonic_ms+(uint64_t)(i+1)*250u;
    }
    return 0;
}
int mibr_gps_4hz_interpolate(const struct mibr_gps_sample *before,
                             const struct mibr_gps_sample *after,
                             struct mibr_gps_sample intermediate[3]) {
    uint64_t period;
    int64_t lat_delta,lon_delta;
    int i;
    if(!safe_sample(before)||!safe_sample(after)||!intermediate||
       after->monotonic_ms<=before->monotonic_ms)return -1;
    period=after->monotonic_ms-before->monotonic_ms;
    if(period<750||period>2000)return -1;
    lat_delta=(int64_t)after->latitude_e7-before->latitude_e7;
    lon_delta=(int64_t)after->longitude_e7-before->longitude_e7;
    if(absolute64(lat_delta)>MAX_CHANGE_E7||
       absolute64(lon_delta)>MAX_CHANGE_E7)return -1;
    for(i=1;i<=3;i++){
        intermediate[i-1].latitude_e7=(int32_t)
             ((int64_t)before->latitude_e7+(lat_delta*i)/4);
        intermediate[i-1].longitude_e7=(int32_t)
             ((int64_t)before->longitude_e7+(lon_delta*i)/4);
        intermediate[i-1].monotonic_ms=before->monotonic_ms+(period*i)/4;
    }
    return 0;
}
