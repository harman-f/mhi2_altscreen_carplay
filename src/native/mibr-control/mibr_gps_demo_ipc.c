/* SPDX-License-Identifier: GPL-3.0-or-later
 * MIBR/3 forwards low-rate user mode choice through one authoritative volatile
 * file. An attached original-DIO owner may report its current send-active state.
 * SET grammar: SET MODE [legacy-epoch]; the epoch argument is ignored.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_gps_demo_ipc.h"
#include "mibr_gps_demo_mode.h"
#include <errno.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>

static int valid_mode(const char *mode) {
    return mode && (!strcmp(mode,"OFF") || !strcmp(mode,"BERLIN_DEMO") ||
                    !strcmp(mode,"HAMBURG_DEMO") ||
                    !strcmp(mode,"SCHWALEFELD_DEMO") ||
                    !strcmp(mode,"WINTERBERG_DEMO"));
}

static int owner_get(char *result,size_t size) {
    int fd=-1,n; struct sockaddr_un addr; struct stat file;
    struct timeval tv={2,0}; char reply[128]; size_t used=0; ssize_t got;
    if(lstat(MIBR_GPS_DEMO_SOCKET,&file)||!S_ISSOCK(file.st_mode)||
       file.st_uid!=geteuid()||(file.st_mode&077)!=0)return -1;
    fd=socket(AF_UNIX,SOCK_STREAM,0);if(fd<0)return -1;
    memset(&addr,0,sizeof(addr));addr.sun_family=AF_UNIX;
    snprintf(addr.sun_path,sizeof(addr.sun_path),"%s",MIBR_GPS_DEMO_SOCKET);
    (void)setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));
    (void)setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof(tv));
    if(connect(fd,(struct sockaddr *)&addr,sizeof(addr))||send(fd,"GET\n",4,0)!=4){close(fd);return -1;}
    while(used<sizeof(reply)-1){
        got=recv(fd,reply+used,1,0);
        if(got!=1)break;
        if(reply[used++]=='\n')break;
    }
    close(fd);
    if(!used||reply[used-1]!='\n')return -1;
    reply[used-1]=0;
    if(strncmp(reply,"OK ",3))return -1;
    if(strlen(reply)>=size)return -1;
    strcpy(result,reply);n=(int)strlen(result);return n>0?0:-1;
}

int mibr_gps_demo_ipc(void *unused,const char *op,const char *value,
                      const char *epoch,char *result,size_t size){
    char mode[32]; int n;
    (void)unused;(void)epoch;
    if(!op||!result||size<64)return -1;
    if(!strcmp(op,"SET")){
        if(!valid_mode(value)||mibr_gps_demo_mode_write(value))return -1;
        n=snprintf(result,size,"OK %s 0 0 0",value);
        return n>0&&(size_t)n<size?0:-1;
    }
    if(strcmp(op,"GET"))return -1;
    /* Preserve actual attached-worker status when available; otherwise report
       the shared manual choice, which is usable without a DIO owner process. */
    if(!owner_get(result,size))return 0;
    if(mibr_gps_demo_mode_read(mode))return -1;
    n=snprintf(result,size,"OK %s 0 0 0",mode);
    return n>0&&(size_t)n<size?0:-1;
}
