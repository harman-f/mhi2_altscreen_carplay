/* Shared write window on /mnt/app between the broker and helper scripts, so one writer cannot
 * remount the filesystem read-only during another writer's save. mibr-view.ksh takes the same file. */
#ifndef MIBR_APP_RW_LEASE_H
#define MIBR_APP_RW_LEASE_H
#define MIBR_APP_RW_LEASE_PATH "/tmp/mibr-app-rw.lock"
/* 0 = held, -1 = another live writer still holds it after wait_ms. */
int mibr_app_rw_lease_acquire(const char *path,unsigned wait_ms);
void mibr_app_rw_lease_release(const char *path);
#endif
