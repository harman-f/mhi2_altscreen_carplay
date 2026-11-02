/* SPDX-License-Identifier: GPL-3.0-or-later
 * One manual demo owner in the original DIO process. No vehicle-data query,
 * new iAP2 client, protocol sender, or session-admission layer is introduced.
 * The volatile choice file is authoritative for both UI control and filtering.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_gps_dio_runtime.h"
#include "mibr_gps_demo_owner.h"
#include "mibr_gps_demo_mode.h"
#include <pthread.h>
#include <signal.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static pthread_mutex_t lifecycle=PTHREAD_MUTEX_INITIALIZER;
static struct mibr_gps_demo_owner owner;
static pthread_t worker;
static int stopping,thread_started;
static uint64_t now_ms(void){struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return (uint64_t)t.tv_sec*1000u+(uint64_t)t.tv_nsec/1000000u;
}
static int should_stop(void){int value;
    pthread_mutex_lock(&owner.mutex);value=stopping;
    pthread_mutex_unlock(&owner.mutex);return value;
}
static void *control_loop(void *unused){sigset_t blocked;(void)unused;
    sigemptyset(&blocked);sigaddset(&blocked,SIGPIPE);
    (void)pthread_sigmask(SIG_BLOCK,&blocked,NULL);
    while(!should_stop()){
        (void)mibr_gps_demo_owner_poll(&owner,now_ms());
        {struct timespec pause={0,20000000};nanosleep(&pause,NULL);}
    }
    return NULL;
}
static void initialize_locked(void){
    if(owner.initialized)return;
    stopping=0;
    if(mibr_gps_demo_owner_open(&owner))return;
    if(!pthread_create(&worker,NULL,control_loop,NULL))thread_started=1;
}
static void stop_locked(void){
    if(!owner.initialized)return;
    pthread_mutex_lock(&owner.mutex);stopping=1;
    pthread_mutex_unlock(&owner.mutex);
    if(thread_started)pthread_join(worker,NULL);
    thread_started=0;mibr_gps_demo_owner_close(&owner);
}
static void __attribute__((destructor)) finish(void){
    pthread_mutex_lock(&lifecycle);stop_locked();pthread_mutex_unlock(&lifecycle);
}
int mibr_gps_dio_owner_send(void *handle,const char *nmea,mibr_gps_vendor_send send){
    char changed[MIBR_GPS_DEMO_NMEA_MAX+8],choice[32];size_t n=0;int edit=0,result;
    if(!send)return -1;
    pthread_mutex_lock(&lifecycle);initialize_locked();
    if(!owner.initialized){pthread_mutex_unlock(&lifecycle);return send(handle,nmea);}
    pthread_mutex_lock(&owner.mutex);
    /* Read the same atomic choice used by MIBR/3. A malformed/racing control
     * read suppresses this frame rather than leaking stock coordinates. */
    if(mibr_gps_demo_mode_read(choice))edit=-1;
    else (void)mibr_gps_demo_select(&owner.state,choice,0,0);
    if(edit==0&&nmea&&owner.state.choice!=MIBR_GPS_OFF){
        while(n<=MIBR_GPS_DEMO_NMEA_MAX&&nmea[n])++n;
        edit=n>MIBR_GPS_DEMO_NMEA_MAX?-1:
            mibr_gps_demo_filter(&owner.state,nmea,n,changed,sizeof(changed),0);
    }
    result=edit<0?0:send(handle,edit?changed:nmea);
    owner.last_send_ok=edit>0&&result==0;
    owner.last_sent_choice=owner.state.choice;
    owner.last_send_ms=now_ms();
    pthread_mutex_unlock(&owner.mutex);pthread_mutex_unlock(&lifecycle);return result;
}
