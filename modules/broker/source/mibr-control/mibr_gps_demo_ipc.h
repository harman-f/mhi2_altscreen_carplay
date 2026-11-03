/* Manual choice is always available; GET reports live worker state when attached. */
#ifndef MIBR_GPS_DEMO_IPC_H
#define MIBR_GPS_DEMO_IPC_H
#include <stddef.h>
#ifndef MIBR_GPS_DEMO_SOCKET
#define MIBR_GPS_DEMO_SOCKET "/tmp/mibr-gps-demo-owner.sock"
#endif
int mibr_gps_demo_ipc(void *ctx,const char *op,const char *value,
                      const char *epoch,char *result,size_t result_size);
#endif
