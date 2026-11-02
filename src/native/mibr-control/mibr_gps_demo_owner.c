/* SPDX-License-Identifier: GPL-3.0-or-later
 * Embedded, original-DIO/iAP2-owner-only AF_UNIX control. No second iAP2
 * connection, no GNSS device or vehicle navigation modification.
 * The original DIO worker calls owner_nmea() before its existing vendor send.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_gps_demo_owner.h"
#include "mibr_gps_demo_ipc.h"
#include "mibr_gps_demo_mode.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>
static int digits(const char *s,uint64_t *v){
    uint64_t value=0;size_t i;
    if(!s||!*s||(s[0]=='0'&&s[1]))return -1;
    for(i=0;s[i];i++){
        unsigned d;
        if(i>19||s[i]<'0'||s[i]>'9')return -1;
        d=(unsigned)(s[i]-'0');
        if(value>(UINT64_MAX-d)/10u)return -1;
        value=value*10u+d;
    }
    *v=value;return 0;
}
int mibr_gps_demo_owner_init(struct mibr_gps_demo_owner *owner){
    if(!owner)return -1;
    memset(owner,0,sizeof(*owner));owner->server_fd=-1;
    if(pthread_mutex_init(&owner->mutex,NULL))return -1;
    owner->initialized=1;return 0;
}
int mibr_gps_demo_owner_open(struct mibr_gps_demo_owner *owner){
    struct sockaddr_un addr;int fd,oldmask,flags;
    struct stat oldfile;
    if(mibr_gps_demo_owner_init(owner))return -1;
    /* Refuse any existing socket/file; never unlink an unknown owner. */
    if(!lstat(MIBR_GPS_DEMO_SOCKET,&oldfile))return -1;
    if(errno!=ENOENT)return -1;
    fd=socket(AF_UNIX,SOCK_STREAM,0);if(fd<0)return -1;
    memset(&addr,0,sizeof(addr));addr.sun_family=AF_UNIX;
    snprintf(addr.sun_path,sizeof(addr.sun_path),"%s",MIBR_GPS_DEMO_SOCKET);
    oldmask=umask(0177);
    flags=bind(fd,(struct sockaddr*)&addr,sizeof(addr));
    umask(oldmask);
    if(flags){close(fd);return -1;}
    if(lstat(MIBR_GPS_DEMO_SOCKET,&oldfile)){close(fd);return -1;}
    owner->socket_ino=oldfile.st_ino;owner->socket_dev=oldfile.st_dev;
    if(listen(fd,3)){close(fd);unlink(MIBR_GPS_DEMO_SOCKET);return -1;}
    flags=fcntl(fd,F_GETFL,0);
    if(flags<0||fcntl(fd,F_SETFL,flags|O_NONBLOCK)){
        close(fd);unlink(MIBR_GPS_DEMO_SOCKET);return -1;
    }
    owner->server_fd=fd;owner->state.choice=MIBR_GPS_OFF;
    return 0;
}
void mibr_gps_demo_owner_close(struct mibr_gps_demo_owner *owner){
    if(!owner||!owner->initialized)return;
    pthread_mutex_lock(&owner->mutex);
    owner->state.choice=MIBR_GPS_OFF;
    if(owner->server_fd>=0){
        struct stat current;
        close(owner->server_fd);
        /* Only the owner that created the socket may remove it. */
        if(!lstat(MIBR_GPS_DEMO_SOCKET,&current)&&current.st_ino==owner->socket_ino&&
           current.st_dev==owner->socket_dev)unlink(MIBR_GPS_DEMO_SOCKET);
    }
    owner->server_fd=-1;
    pthread_mutex_unlock(&owner->mutex);
    pthread_mutex_destroy(&owner->mutex);
    owner->initialized=0;
}
void mibr_gps_demo_owner_session(struct mibr_gps_demo_owner *owner,
 uint64_t epoch,int connected,int identified,int location_requested){
    if(owner){pthread_mutex_lock(&owner->mutex);
        mibr_gps_demo_session(&owner->state,epoch,connected,identified,location_requested);
        pthread_mutex_unlock(&owner->mutex);}
}
void mibr_gps_demo_owner_speed(struct mibr_gps_demo_owner *owner,int mm_s,
 uint64_t timestamp,int valid){
    if(owner){pthread_mutex_lock(&owner->mutex);
        mibr_gps_demo_speed(&owner->state,mm_s,timestamp,valid);
        pthread_mutex_unlock(&owner->mutex);}
}
void mibr_gps_demo_owner_parking(struct mibr_gps_demo_owner *owner,int parked,
 uint64_t timestamp,int valid){
    if(owner){pthread_mutex_lock(&owner->mutex);
        mibr_gps_demo_parking(&owner->state,parked,timestamp,valid);
        pthread_mutex_unlock(&owner->mutex);}
}
void mibr_gps_demo_owner_vehicle(struct mibr_gps_demo_owner *owner,int mm_s,
 uint64_t speed_ms,int speed_valid,int parked,uint64_t park_ms,int park_valid){
    if(!owner)return;
    pthread_mutex_lock(&owner->mutex);
    mibr_gps_demo_speed(&owner->state,mm_s,speed_ms,speed_valid);
    mibr_gps_demo_parking(&owner->state,parked,park_ms,park_valid);
    pthread_mutex_unlock(&owner->mutex);
}
int mibr_gps_demo_owner_nmea(struct mibr_gps_demo_owner *owner,const char *in,
 size_t in_n,char *out,size_t cap,uint64_t now){
    int result;
    if(!owner)return 0;
    pthread_mutex_lock(&owner->mutex);
    result=mibr_gps_demo_filter(&owner->state,in,in_n,out,cap,now);
    pthread_mutex_unlock(&owner->mutex);return result;
}
static int cmd(struct mibr_gps_demo_owner *owner,const char *request,
 uint64_t now,char *reply,size_t cap){
    char value[32],rev[32],extra[8],selected[32];uint64_t epoch;
    int result;
    if(!strcmp(request,"GET\n"))result=0;
    else if(sscanf(request,"SET %31s %31s %7s",value,rev,extra)==2&&
            !digits(rev,&epoch)){
        (void)epoch;
        if(mibr_gps_demo_mode_write(value))return snprintf(reply,cap,"ERR MODE_WRITE_FAILED\n");
        result=0;
    }else return snprintf(reply,cap,"ERR INVALID_REQUEST\n");
    (void)result;
    if(mibr_gps_demo_mode_read(selected))return snprintf(reply,cap,"ERR MODE_READ_FAILED\n");
    if(mibr_gps_demo_select(&owner->state,selected,0,now))return snprintf(reply,cap,"ERR INVALID_MODE\n");
    return snprintf(reply,cap,"OK %s 0 %d 0\n",
        mibr_gps_demo_name(owner->state.choice),
        owner->state.choice!=MIBR_GPS_OFF&&owner->last_send_ok&&
            owner->last_sent_choice==owner->state.choice&&now>=owner->last_send_ms&&
            now-owner->last_send_ms<=2000?1:0);
}
int mibr_gps_demo_owner_poll(struct mibr_gps_demo_owner *owner,uint64_t now){
    int client;char req[96],reply[128];size_t count=0;ssize_t read_n;
    struct timeval tv={0,100000};
    if(!owner||owner->server_fd<0)return -1;
    client=accept(owner->server_fd,NULL,NULL);
    if(client<0)return errno==EAGAIN||errno==EWOULDBLOCK||errno==EINTR?0:-1;
    (void)setsockopt(client,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));
    (void)setsockopt(client,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof(tv));
    while(count+1<sizeof(req)){
        read_n=recv(client,req+count,1,0);
        if(read_n!=1)break;
        if(req[count++]=='\n')break;
    }
    if(!count||req[count-1]!='\n'){
        close(client);return -1;
    }
    req[count]=0;
    {
        int n;
        pthread_mutex_lock(&owner->mutex);
        n=cmd(owner,req,now,reply,sizeof(reply));
        pthread_mutex_unlock(&owner->mutex);
        if(n>0&&(size_t)n<sizeof(reply))(void)send(client,reply,(size_t)n,0);
    }
    close(client);return 1;
}
