#ifndef MIBR_GPS_DEMO_MODE_H
#define MIBR_GPS_DEMO_MODE_H

#ifndef MIBR_GPS_DEMO_MODE_FILE
#define MIBR_GPS_DEMO_MODE_FILE "/tmp/mibr-gps-demo.choice"
#endif

/* Shared volatile operator choice. Missing file reads as OFF. */
int mibr_gps_demo_mode_read(char out[32]);
/* Requires effective uid 0; serializes with readers and writes a root-owned mode-0600 flat file. */
int mibr_gps_demo_mode_write(const char *mode);

#endif
