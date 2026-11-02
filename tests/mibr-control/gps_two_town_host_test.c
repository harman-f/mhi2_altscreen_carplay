/* Two additional public-centre choices via the existing iAP2 sender.
 * Berlin and Hamburg remain unchanged; no compile-time aliases.
 */
#include "mibr_gps_demo.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void frame(char *dest,size_t cap,const char *body){
    unsigned sum=0;size_t i;
    for(i=0;body[i];i++)sum^=(unsigned char)body[i];
    assert(snprintf(dest,cap,"$%s*%02X\r\n",body,sum)>0);
}
static int valid_crc(const char *frame){
    unsigned sum=0,got=256;size_t i;
    if(!frame||frame[0]!='$')return 0;
    for(i=1;frame[i]&&frame[i]!='*';i++)sum^=(unsigned char)frame[i];
    return frame[i]=='*'&&sscanf(frame+i+1,"%2x",&got)==1&&got==sum;
}
int main(void){
    struct mibr_gps_demo st={0};
    char in[256],out[256],expected[256];
    frame(in,sizeof(in),"GPGGA,194702.51,5118.738097,N,00837.790068,E,6,13,0.9,524.9,M,0.0,M,,");
    strcpy(out,"OFF_UNTOUCHED");
    assert(mibr_gps_demo_filter(&st,in,strlen(in),out,sizeof(out),0)==0);
    assert(!strcmp(out,"OFF_UNTOUCHED"));

    assert(mibr_gps_demo_select(&st,"SCHWALEFELD_DEMO",1,0)==0);
    frame(expected,sizeof(expected),"GPGGA,194702.51,5118.4746,N,00837.8102,E,1,12,0.9,524.9,M,0.0,M,,");
    assert(mibr_gps_demo_filter(&st,in,strlen(in),out,sizeof(out),0)==1);
    assert(!strcmp(out,expected)&&valid_crc(out));
    frame(in,sizeof(in),"GPRMC,194702.51,A,5118.738097,N,00837.790068,E,0.0,273.9,271026,,,E");
    frame(expected,sizeof(expected),"GPRMC,194702.51,A,5118.4746,N,00837.8102,E,0.0,0.0,271026,,,A");
    assert(mibr_gps_demo_filter(&st,in,strlen(in),out,sizeof(out),0)==1);
    assert(!strcmp(out,expected)&&valid_crc(out));

    assert(mibr_gps_demo_select(&st,"WINTERBERG_DEMO",2,0)==0);
    frame(expected,sizeof(expected),"GPRMC,194702.51,A,5111.6490,N,00831.9856,E,0.0,0.0,271026,,,A");
    assert(mibr_gps_demo_filter(&st,in,strlen(in),out,sizeof(out),0)==1);
    assert(!strcmp(out,expected)&&valid_crc(out));
    frame(in,sizeof(in),"GPGGA,194702.51,5118.738097,N,00837.790068,E,6,13,0.9,524.9,M,0.0,M,,");
    frame(expected,sizeof(expected),"GPGGA,194702.51,5111.6490,N,00831.9856,E,1,12,0.9,524.9,M,0.0,M,,");
    assert(mibr_gps_demo_filter(&st,in,strlen(in),out,sizeof(out),0)==1);
    assert(!strcmp(out,expected)&&valid_crc(out));

    /* Fail closed while active: unknown families/suspicious input never pass. */
    frame(in,sizeof(in),"GPGSV,1,1,00");
    assert(mibr_gps_demo_filter(&st,in,strlen(in),out,sizeof(out),0)==-1);
    assert(mibr_gps_demo_filter(&st,"$GPGGA,broken*00",17,out,sizeof(out),0)==-1);

    assert(mibr_gps_demo_select(&st,"OFF",0,0)==0);
    assert(mibr_gps_demo_filter(&st,in,strlen(in),out,sizeof(out),0)==0);
    puts("GPS_TWO_TOWN_MENU_OPTIONS_HOST_PASS");
    return 0;
}
