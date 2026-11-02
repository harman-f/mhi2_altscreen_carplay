/* SPDX-License-Identifier: GPL-3.0-or-later
 * No second iAP2 owner, no altered OEM GNSS, no CAN/DSI writes.
 * Pure CarPlay accessory NMEA GGA/RMC transformer, called ONLY from the
 * exact original trusted DIO owner/worker location-send seam.
 */
#include "mibr_gps_demo.h"
#include <stdio.h>
#include <string.h>
/* Tourist/public landmarks rather than a residential address.
 * Decimal reference: Alexanderstrasse B2/B5 ~52.5220579,13.4162179;
 * Ballindamm coach stopping area ~53.552422,9.995430.
 * Standard NMEA ddmm.mmmm and dddmm.mmmm; static = parked demo.
 */
struct gps_point {const char *lat,*lon;};
/* No residential destinations; static public-centre WGS84 test points.
 * R2 valid-fix semantics stay identical; only coordinates differ by mode.
 * Mode OFF passes the entire original sentence unchanged.
 */
static const struct gps_point berlin={"5231.3235","01324.9731"};
static const struct gps_point hamburg={"5333.1453","00959.7258"};
static const struct gps_point schwalefeld={"5118.4746","00837.8102"}; /* Ortsmitte */
static const struct gps_point winterberg={"5111.6490","00831.9856"}; /* Untere Pforte */
const char *mibr_gps_demo_name(enum mibr_gps_demo_choice choice){
    switch(choice){
        case MIBR_GPS_OFF:return "OFF";
        case MIBR_GPS_BERLIN:return "BERLIN_DEMO";
        case MIBR_GPS_HAMBURG:return "HAMBURG_DEMO";
        case MIBR_GPS_SCHWALEFELD:return "SCHWALEFELD_DEMO";
        case MIBR_GPS_WINTERBERG:return "WINTERBERG_DEMO";
        default:return "OFF";
    }
}
static enum mibr_gps_demo_choice parse(const char *value){
    if(value&&!strcmp(value,"BERLIN_DEMO"))return MIBR_GPS_BERLIN;
    if(value&&!strcmp(value,"HAMBURG_DEMO"))return MIBR_GPS_HAMBURG;
    if(value&&!strcmp(value,"SCHWALEFELD_DEMO"))return MIBR_GPS_SCHWALEFELD;
    if(value&&!strcmp(value,"WINTERBERG_DEMO"))return MIBR_GPS_WINTERBERG;
    return MIBR_GPS_OFF;
}
void mibr_gps_demo_session(struct mibr_gps_demo *state,uint64_t epoch,int connected,
                          int identified,int location_requested){
    if(!state)return;
    /* Informational legacy observations only. The owner requested a manual
     * test mode independent of vehicle state and protocol/session admission.
     * HARMAN retains the actual iAP2 authentication and request filtering. */
    state->session_epoch=epoch;
    state->connected=!!connected;
    state->identify_accepted=!!identified;
    state->location_requested=!!location_requested;
}
void mibr_gps_demo_speed(struct mibr_gps_demo *state,int speed_mm_s,
                         uint64_t stamp,int valid){
    if(!state)return;
    state->trusted_stationary=!!valid&&speed_mm_s==0;
    state->speed_mm_s=speed_mm_s;state->speed_timestamp_ms=stamp;
}
void mibr_gps_demo_parking(struct mibr_gps_demo *state,int genuine_parked,
                           uint64_t stamp,int valid){
    if(!state)return;
    state->trusted_parked=!!valid&&genuine_parked==1;
    state->parking_timestamp_ms=stamp;
}
int mibr_gps_demo_select(struct mibr_gps_demo *state,const char *value,
                         uint64_t epoch,uint64_t now){
    if(!state||!value||(strcmp(value,"OFF")&&strcmp(value,"BERLIN_DEMO")&&
       strcmp(value,"HAMBURG_DEMO")&&strcmp(value,"SCHWALEFELD_DEMO")&&
       strcmp(value,"WINTERBERG_DEMO")))return -1;
    if(!strcmp(value,"OFF")){state->choice=MIBR_GPS_OFF;return 0;}
    (void)epoch;(void)now;
    state->choice=parse(value);return 0;
}
int mibr_gps_demo_active(const struct mibr_gps_demo *state,uint64_t now){
    (void)now;return state&&state->choice!=MIBR_GPS_OFF;
}
static int hex(char c){
    return c>='0'&&c<='9'?c-'0':c>='A'&&c<='F'?c-'A'+10:
           c>='a'&&c<='f'?c-'a'+10:-1;
}
static int check_nmea(const char *in,size_t n,size_t *star){
    size_t i;unsigned sum=0;
    if(!in||n<8||n>MIBR_GPS_DEMO_NMEA_MAX||in[0]!='$')return -1;
    for(i=1;i<n&&in[i]!='*';i++){
        if((unsigned char)in[i]<32||(unsigned char)in[i]>126)return -1;
        sum^=(unsigned char)in[i];
    }
    if(i+3>n||i<6||hex(in[i+1])<0||hex(in[i+2])<0||
       ((unsigned)(hex(in[i+1])<<4|hex(in[i+2]))!=sum))return -1;
    if(i+3<n&&!(i+5==n&&in[i+3]=='\r'&&in[i+4]=='\n')&&
       !(i+4==n&&in[i+3]=='\n'))return -1;
    *star=i;return 0;
}
int mibr_gps_demo_filter(struct mibr_gps_demo *state,const char *in,size_t n,
                        char *out,size_t cap,uint64_t now){
    char text[MIBR_GPS_DEMO_NMEA_MAX+1],*field[24];size_t star,start,i;
    unsigned count=0,checksum=0;int rmc,gga,lat,lon;
    const struct gps_point *point;
    if(!state||state->choice==MIBR_GPS_OFF)return 0;
    (void)now;
    if(check_nmea(in,n,&star))return -1;
    if(star>=sizeof(text))return -1;
    memcpy(text,in,star);text[star]=0;
    rmc=star>=6&&(!memcmp(text,"$GPRMC",6)||!memcmp(text,"$GNRMC",6));
    gga=star>=6&&(!memcmp(text,"$GPGGA",6)||!memcmp(text,"$GNGGA",6));
    /* Unknown NMEA sentence families may contain the genuine position.
     * When demo is selected, suppress rather than leak an unclassified frame. */
    if(!rmc&&!gga)return -1;
    field[count++]=text+1;start=1;
    for(i=1;i<star;i++)if(text[i]==','){
        if(count>=24)return -1;
        text[i]=0;field[count++]=text+i+1;start=i+1;
    }
    (void)start;
    /* GGA: time, lat, NS, lon, EW, fix quality.
     * RMC: time, status, lat, NS, lon, EW, speed, track ... */
    /* GGA quality output needs all three quality fields present. Refuse a
     * truncated sentence rather than inventing its missing structure. */
    if(count<(unsigned)(rmc?8:9))return -1;
    lat=rmc?3:2;lon=rmc?5:4;
    /* Original coordinates/hemispheres are replaced in full below, so empty
     * source position fields are safe and must not block the demo position. */
    switch(state->choice){
        case MIBR_GPS_BERLIN:point=&berlin;break;
        case MIBR_GPS_HAMBURG:point=&hamburg;break;
        case MIBR_GPS_SCHWALEFELD:point=&schwalefeld;break;
        case MIBR_GPS_WINTERBERG:point=&winterberg;break;
        default:return -1;
    }
    /* Assemble with bounded append operations, preserving other NMEA fields.
     * Reset RMC speed to 0.0 to avoid stale original speed alongside a static fix. */
    {
        size_t used=0;
        if(!out||cap<16)return -1;
        out[used++]='$';
        for(i=0;i<count;i++){
            const char *v=field[i];size_t len;
            if(i==(unsigned)lat)v=point->lat;
            else if(i==(unsigned)(lat+1))v="N";
            else if(i==(unsigned)lon)v=point->lon;
            else if(i==(unsigned)(lon+1))v="E";
            else if(gga&&i==6)v="1"; /* synthetic autonomous-fix profile */
            else if(gga&&i==7)v="12"; /* synthetic satellite count */
            else if(gga&&i==8)v="0.9"; /* synthetic HDOP; never measured */
            else if(rmc&&i==2)v="A"; /* valid RMC status */
            else if(rmc&&i==12)v="A"; /* optional mode field, when present */
            else if(rmc&&(i==7||i==8))v="0.0"; /* stationary speed and track */
            len=strlen(v);
            if(used+len+7>=cap)return -1;
            if(i)out[used++]=',';
            memcpy(out+used,v,len);used+=len;
        }
        for(i=1;i<used;i++)checksum^=(unsigned char)out[i];
        if(used+6>cap)return -1;
        sprintf(out+used,"*%02X\r\n",checksum);
    }
    return 1;
}
