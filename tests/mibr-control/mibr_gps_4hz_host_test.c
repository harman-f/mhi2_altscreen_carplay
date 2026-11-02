#include "mibr_gps_4hz.h"
#include <assert.h>
#include <stdio.h>
int main(void){
    struct mibr_gps_sample a={510000000,80000000,10000};
    struct mibr_gps_sample b={510004000,80008000,11000};
    struct mibr_gps_sample steps[3];
    int i;
    assert(mibr_gps_4hz_interpolate(&a,&b,steps)==0);
    for(i=0;i<3;i++){
        assert(steps[i].monotonic_ms==10250+(uint64_t)i*250);
        assert(steps[i].latitude_e7==510001000+(int32_t)i*1000);
        assert(steps[i].longitude_e7==80002000+(int32_t)i*2000);
    }
    b.latitude_e7=a.latitude_e7;
    b.longitude_e7=a.longitude_e7;
    assert(mibr_gps_4hz_interpolate(&a,&b,steps)==0);
    for(i=0;i<3;i++)assert(steps[i].latitude_e7==a.latitude_e7&&
                             steps[i].longitude_e7==a.longitude_e7);
    assert(mibr_gps_4hz_stationary(&a,steps)==0);
    for(i=0;i<3;i++){
        assert(steps[i].latitude_e7==a.latitude_e7&&
               steps[i].longitude_e7==a.longitude_e7&&
               steps[i].monotonic_ms==a.monotonic_ms+(uint64_t)(i+1)*250u);
    }
    b.monotonic_ms=10000;
    assert(mibr_gps_4hz_interpolate(&a,&b,steps)==-1);
    b.monotonic_ms=20000;
    assert(mibr_gps_4hz_interpolate(&a,&b,steps)==-1);
    b.monotonic_ms=11000;b.latitude_e7=510400000;
    assert(mibr_gps_4hz_interpolate(&a,&b,steps)==-1);
    b.latitude_e7=510000000;b.longitude_e7=1900000000;
    assert(mibr_gps_4hz_interpolate(&a,&b,steps)==-1);
    assert(mibr_gps_4hz_interpolate(&a,&b,NULL)==-1);
    puts("GPS_INTERPOLATION_MATH_ONLY_PASS");
    return 0;
}
