#ifndef MIBR_GPS_DIO_RUNTIME_H
#define MIBR_GPS_DIO_RUNTIME_H
typedef int (*mibr_gps_vendor_send)(void *,const char *);
int mibr_gps_dio_owner_send(void *handle,const char *nmea,mibr_gps_vendor_send send);
#endif
