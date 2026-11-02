/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "mibr_gps_demo_mode.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

static int valid_mode(const char *mode) {
    return mode && (!strcmp(mode,"OFF") || !strcmp(mode,"BERLIN_DEMO") ||
                    !strcmp(mode,"HAMBURG_DEMO") ||
                    !strcmp(mode,"SCHWALEFELD_DEMO") ||
                    !strcmp(mode,"WINTERBERG_DEMO"));
}

static int secure_regular(int fd, struct stat *st) {
    if (fstat(fd,st) || !S_ISREG(st->st_mode) || st->st_uid != 0 ||
        (st->st_mode & 0777) != 0600) return -1;
    return 0;
}

static int make_path(char *out,size_t cap,const char *suffix) {
    int n=snprintf(out,cap,"%s%s",MIBR_GPS_DEMO_MODE_FILE,suffix);
    return n>0&&(size_t)n<cap?0:-1;
}

/* QNX 6.5 /tmp is /dev/shmem: no fcntl lock and rename() can fail EXDEV.
 * Use the proven shared O_EXCL lock-file pattern for both readers and writers. */
static int stale_lock_owner_gone(const char *path) {
    struct stat st; char owner[48],*end; size_t used=0; long pid; ssize_t n; int fd;
    if(lstat(path,&st)||!S_ISREG(st.st_mode)||st.st_uid!=0||
       (st.st_mode&0777)!=0600)return 0;
    fd=open(path,O_RDONLY);
    if(fd<0)return 0;
    while(used<sizeof(owner)-1){
        n=read(fd,owner+used,sizeof(owner)-1-used);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)break;
        used+=(size_t)n;
    }
    close(fd);
    if(!used||used==sizeof(owner)-1)return 0;
    owner[used]=0;errno=0;pid=strtol(owner,&end,10);
    if(errno||pid<=1||end==owner||(*end!='\n'&&*end!=0)||
       (*end=='\n'&&end[1]!=0))return 0;
    errno=0;
    return kill((pid_t)pid,0)==-1&&errno==ESRCH;
}

static int lock_mode(char lock[512]) {
    unsigned attempt; int fd,n; char owner[48]; struct stat st;
    if(make_path(lock,512,".lock"))return -1;
    for(attempt=0;attempt<100u;attempt++){
        fd=open(lock,O_WRONLY|O_CREAT|O_EXCL,0600);
        if(fd>=0){
            n=snprintf(owner,sizeof(owner),"%ld\n",(long)getpid());
            if(n<=0||(size_t)n>=sizeof(owner)||write(fd,owner,(size_t)n)!=n){
                close(fd);unlink(lock);return -1;
            }
            if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_uid!=0||
               fchmod(fd,0600)){close(fd);unlink(lock);return -1;}
            return fd;
        }
        if(errno!=EEXIST)return -1;
        if(lstat(lock,&st)){
            if(errno==ENOENT)continue;
            return -1;
        }
        if(!S_ISREG(st.st_mode)||st.st_uid!=0||(st.st_mode&0777)!=0600)return -1;
        if(stale_lock_owner_gone(lock)){
            struct stat current;
            if(lstat(lock,&current)){
                if(errno==ENOENT)continue;
                return -1;
            }
            if(current.st_dev==st.st_dev&&current.st_ino==st.st_ino){
                if(!unlink(lock)||errno==ENOENT)continue;
                return -1;
            }
        }
        if(attempt+1u<100u){struct timespec pause={0,1000000L};(void)nanosleep(&pause,NULL);}
    }
    errno=EBUSY;return -1;
}

static void unlock_mode(const char *path,int fd) {
    struct stat held,current;
    if(fd<0)return;
    if(fstat(fd,&held)){close(fd);return;}
    close(fd);
    if(!lstat(path,&current)&&held.st_dev==current.st_dev&&held.st_ino==current.st_ino)
        (void)unlink(path);
}

int mibr_gps_demo_mode_read(char out[32]) {
    int fd,lockfd; char lock[512],buf[64]; struct stat path_st,file_st;
    size_t used=0; ssize_t n;
    if(!out||geteuid()!=0)return -1;
    out[0]=0;lockfd=lock_mode(lock);if(lockfd<0)return -1;
    if(lstat(MIBR_GPS_DEMO_MODE_FILE,&path_st)){
        int missing=errno==ENOENT;unlock_mode(lock,lockfd);
        if(missing){strcpy(out,"OFF");return 0;}return -1;
    }
    if(!S_ISREG(path_st.st_mode)||path_st.st_uid!=0||(path_st.st_mode&0777)!=0600){
        unlock_mode(lock,lockfd);return -1;
    }
#ifdef O_NOFOLLOW
    fd=open(MIBR_GPS_DEMO_MODE_FILE,O_RDONLY|O_NOFOLLOW);
#else
    fd=open(MIBR_GPS_DEMO_MODE_FILE,O_RDONLY);
#endif
    if(fd<0){unlock_mode(lock,lockfd);return -1;}
    if(secure_regular(fd,&file_st)||file_st.st_dev!=path_st.st_dev||file_st.st_ino!=path_st.st_ino){
        close(fd);unlock_mode(lock,lockfd);return -1;
    }
    while(used<sizeof(buf)){
        n=read(fd,buf+used,sizeof(buf)-used);
        if(n<0&&errno==EINTR)continue;
        if(n<0){close(fd);unlock_mode(lock,lockfd);return -1;}
        if(n==0)break;
        used+=(size_t)n;
    }
    close(fd);unlock_mode(lock,lockfd);
    if(used>=sizeof(buf))return -1;
    buf[used]=0;
    if(used<sizeof("MIBR_GPS_DEMO/1\nOFF\n")-1||memcmp(buf,"MIBR_GPS_DEMO/1\n",16))return -1;
    {
        char *mode=buf+16;size_t len=used-16;
        if(len<2||mode[len-1]!='\n')return -1;
        mode[len-1]=0;
        if(!valid_mode(mode)||strlen(mode)+17!=used)return -1;
        strcpy(out,mode);
    }
    return 0;
}

int mibr_gps_demo_mode_write(const char *mode) {
    char lock[512],data[64]; int lockfd,fd=-1,n,rc=-1; struct stat before,opened;
    int existed=0; size_t len,off=0; ssize_t wrote;
    if(geteuid()!=0||!valid_mode(mode))return -1;
    n=snprintf(data,sizeof(data),"MIBR_GPS_DEMO/1\n%s\n",mode);
    if(n<=0||(size_t)n>=sizeof(data))return -1;
    len=(size_t)n;
    lockfd=lock_mode(lock);if(lockfd<0)return -1;
    if(!lstat(MIBR_GPS_DEMO_MODE_FILE,&before)){
        if(!S_ISREG(before.st_mode)||before.st_uid!=0||(before.st_mode&0777)!=0600)goto done;
        existed=1;
    }else if(errno!=ENOENT)goto done;
#ifdef O_NOFOLLOW
    fd=open(MIBR_GPS_DEMO_MODE_FILE,O_WRONLY|O_CREAT|O_TRUNC|O_NOFOLLOW,0600);
#else
    fd=open(MIBR_GPS_DEMO_MODE_FILE,O_WRONLY|O_CREAT|O_TRUNC,0600);
#endif
    if(fd<0)goto done;
    if(fchmod(fd,0600)||fstat(fd,&opened)||!S_ISREG(opened.st_mode)||opened.st_uid!=0||
       (opened.st_mode&0777)!=0600||(existed&&(opened.st_dev!=before.st_dev||opened.st_ino!=before.st_ino)))goto done;
    while(off<len){
        wrote=write(fd,data+off,len-off);
        if(wrote<0&&errno==EINTR)continue;
        if(wrote<=0)goto done;
        off+=(size_t)wrote;
    }
    rc=0;
done:
    if(fd>=0&&close(fd))rc=-1;
    unlock_mode(lock,lockfd);
    return rc;
}
