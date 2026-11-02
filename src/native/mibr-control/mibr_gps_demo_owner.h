/* Original DIO/iAP2 owner-scoped GPS demo control and current GNSS filter. */
#ifndef MIBR_GPS_DEMO_OWNER_H
#define MIBR_GPS_DEMO_OWNER_H
#include "mibr_gps_demo.h"
#include <stdint.h>
#include <pthread.h>
#include <sys/types.h>
struct mibr_gps_demo_owner {
    struct mibr_gps_demo state;
    int server_fd;
    int initialized;
    uint64_t last_send_ms;
    int last_send_ok;
    enum mibr_gps_demo_choice last_sent_choice;
    ino_t socket_ino;
    dev_t socket_dev;
    pthread_mutex_t mutex;
};
int mibr_gps_demo_owner_init(struct mibr_gps_demo_owner *owner);
/* Embed in the ORIGINAL trusted iAP2 owner process (not a second daemon). */
int mibr_gps_demo_owner_open(struct mibr_gps_demo_owner *owner);
void mibr_gps_demo_owner_close(struct mibr_gps_demo_owner *owner);
/* Nonblocking; service at most one low-rate control request per iteration. */
int mibr_gps_demo_owner_poll(struct mibr_gps_demo_owner *owner,uint64_t now_ms);
/* Calls are authorized ONLY from genuine original-owner lifecycle/DSI speed. */
void mibr_gps_demo_owner_session(struct mibr_gps_demo_owner *owner,
  uint64_t epoch,int connected,int identified,int location_requested);
void mibr_gps_demo_owner_speed(struct mibr_gps_demo_owner *owner,int mm_s,
  uint64_t observed_ms,int valid);
/* A second, independent, fresh genuine parking/park-brake observation is required. */
void mibr_gps_demo_owner_parking(struct mibr_gps_demo_owner *owner,int parked,
  uint64_t observed_ms,int valid);
/* Commit speed + independent parking from one authenticated typed record. */
void mibr_gps_demo_owner_vehicle(struct mibr_gps_demo_owner *owner,int mm_s,
  uint64_t speed_ms,int speed_valid,int parked,uint64_t park_ms,int park_valid);
/* Before ORIGINAL DIO NMEA send job: 0 unchanged, 1 modified, -1 drop. */
int mibr_gps_demo_owner_nmea(struct mibr_gps_demo_owner *owner,
 const char *original,size_t original_n,char *altered,size_t cap,uint64_t now_ms);
#endif
