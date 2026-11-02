#include "mibr_gps_demo.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void frame(char *to,size_t cap,const char *body){unsigned c=0;size_t i;
 for(i=0;body[i];i++)c^=(unsigned char)body[i];
 assert(snprintf(to,cap,"$%s*%02X\r\n",body,c)>0);}
static int crc_ok(const char *s){unsigned c=0,e=0;size_t i;
 for(i=1;s[i]&&s[i]!='*';i++)c^=(unsigned char)s[i];
 return s[i]=='*'&&sscanf(s+i+1,"%2x",&e)==1&&c==e;}
int main(void){struct mibr_gps_demo state={0};char input[256],out[256],expected[256];
 frame(input,sizeof(input),"GPRMC,120000.00,A,5111.0000,N,01122.0000,E,5.5,123.4,261026,,,A");
 strcpy(out,"unchanged");
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==0);
 assert(!strcmp(out,"unchanged")); /* OFF leaves the output and input bytes untouched */
 /* Manual test mode works without a vehicle signal, phone Identify or epoch. */
 assert(mibr_gps_demo_select(&state,"BERLIN_DEMO",999,0)==0);
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==1);
 assert(strstr(out,"5231.3235,N,01324.9731,E,0.0,0.0")&&crc_ok(out));
 assert(strstr(out,"123.4")==NULL&&strstr(out,"5.5")==NULL);
 mibr_gps_demo_speed(&state,6000,0,0);mibr_gps_demo_parking(&state,0,0,0);
 mibr_gps_demo_session(&state,3,0,0,0);
 assert(mibr_gps_demo_active(&state,UINT64_MAX)); /* no TTL, motion or session reset */
 assert(mibr_gps_demo_select(&state,"HAMBURG_DEMO",123,0)==0);
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==1);
 assert(strstr(out,"5333.1453,N,00959.7258,E")&&crc_ok(out));
 frame(input,sizeof(input),"GPGGA,120000.00,5111.0000,N,01122.0000,E,6,08,0.9,540.0,M,0.0,M,,");
 frame(expected,sizeof(expected),"GPGGA,120000.00,5333.1453,N,00959.7258,E,1,12,0.9,540.0,M,0.0,M,,");
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==1);
 assert(!strcmp(out,expected)&&crc_ok(out));
 frame(input,sizeof(input),"GPRMC,190455.64,V,,,,,5.5,123.4,271026,,,E");
 frame(expected,sizeof(expected),"GPRMC,190455.64,A,5333.1453,N,00959.7258,E,0.0,0.0,271026,,,A");
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==1);
 assert(!strcmp(out,expected)&&crc_ok(out));
 /* A source with empty original coordinate/hemisphere fields is still usable. */
 frame(input,sizeof(input),"GPGGA,190455.64,,,,,0,0,,540.0,M,,M,,");
 frame(expected,sizeof(expected),"GPGGA,190455.64,5333.1453,N,00959.7258,E,1,12,0.9,540.0,M,,M,,");
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==1);
 assert(!strcmp(out,expected)&&crc_ok(out));
 /* A checksum-valid but structurally short GGA is rejected. */
 frame(input,sizeof(input),"GPGGA,190455.64,,,,,0,0");
 strcpy(out,"short-gga-sentinel");
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==-1);
 assert(!strcmp(out,"short-gga-sentinel"));
 frame(input,sizeof(input),"GPGLL,5111.0000,N,01122.0000,E,120000.00,A");
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==-1);
 assert(mibr_gps_demo_filter(&state,"$GPRMC,bad*00",13,out,sizeof(out),0)==-1);
 assert(mibr_gps_demo_select(&state,"OFF",0,0)==0);
 assert(mibr_gps_demo_filter(&state,input,strlen(input),out,sizeof(out),0)==0);
 assert(mibr_gps_demo_select(&state,"BAD",0,0)!=0);
 puts("GPS_DEMO_HOST_TEST_PASS");return 0;}
