/* SPDX-License-Identifier: GPL-3.0-or-later
 * MIBR KEY40 long-press route toggle (r21).
 *
 * Passive receiver on the existing Java DebugSPI socket 127.0.0.1:15001 (same family the
 * GEN2 zoom parser and the keypanel logger use). The stream carries the original ASCII line
 *   HK Received: KBD[4] KEY[40] KST[1]
 * for every physical key state. One classifier (mibr_v3_key40.c: 1 press, 3 long armed,
 * 4 fired, 5 held, 0 release) turns the right roller PUSH into SHORT (left to the OEM, nothing
 * done here) or ROUTE_LONG (exactly once per press). KEY41 and every other key are ignored.
 *
 * ROUTE_LONG toggles the pause file read by parity_drive_supervisor.sh:
 *   no pause file  -> create it and stop the running Parity owner with SIGTERM (graceful,
 *                     the owner restores the stock route on exit: native navigation is visible)
 *   pause file     -> remove it (the supervisor reopens the CarPlay route on the live stream)
 * Nothing is written to OEM state, no DebugSPI byte is ever sent.
 */
#include "mibr_v3_key40.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#define PAUSE_PATH "/tmp/mibr-parity-drive.pause"
#define OWNER_PID_PATH "/tmp/mibr-parity-session.pid"
#define OWNER_LOCK_PATH "/tmp/mibr-parity-session.lock"
#define VIEW_SCRIPT "/mnt/app/root/altscreen-u2/scripts/mibr-view.ksh"
#define VIEW_WAIT_MS 3000
#define BUF_CAP 8192u
#define NEEDLE "HK Received: KBD["
#define DEBOUNCE_MS 1500LL

struct key40d_scan {
    char buf[BUF_CAP];
    size_t n;
    struct mibr_key40 key;
    struct mibr_key40 key44;
};

typedef void (*key40d_event_fn)(void *context,enum mibr_key40_event event);
/* r55: called once for every KEY40 press start (KST 1), short or long: the virtual cockpit steps its view then. */
typedef void (*key40d_step_fn)(void *context);
/* r57: KEY40 (right roller push) held long = resync of the view counter. */
typedef void (*key40d_resync_fn)(void *context);
static void (*g_trace)(int kbd,int key,int kst);

static void key40d_init(struct key40d_scan *s){
    memset(s,0,sizeof(*s));
    mibr_key40_reset(&s->key);
    mibr_key40_reset(&s->key44);
}

/* Consumes a chunk of the DebugSPI byte stream. A key line may be split across chunks. */
static void key40d_feed(struct key40d_scan *s,const char *data,size_t len,
                        key40d_event_fn fn,key40d_step_fn step,key40d_resync_fn resync,void *context){
    size_t pos=0,needle=strlen(NEEDLE);
    while(len>0){
        size_t room=BUF_CAP-s->n,take=len<room?len:room,k;
        /* The DebugSPI text messages are UTF-16LE on the wire (car capture 2026-10-19: no contiguous ASCII needle).
         * Dropping NUL bytes turns both UTF-16LE and plain ASCII text into the same ASCII stream. */
        for(k=0;k<take;++k)if(data[k])s->buf[s->n++]=data[k];
        data+=take;len-=take;
        for(;;){
            char *p=NULL;size_t i;int kbd,key,kst;
            for(i=pos;i+needle<=s->n;i++)if(!memcmp(s->buf+i,NEEDLE,needle)){p=s->buf+i;break;}
            if(!p){
                /* keep only a tail that could still start a needle */
                size_t keep=needle>1?needle-1:0;
                pos=s->n>keep?s->n-keep:0;
                break;
            }
            if((size_t)(p-s->buf)+48>s->n){pos=(size_t)(p-s->buf);break;} /* line incomplete */
            if(sscanf(p,"HK Received: KBD[%d] KEY[%d] KST[%d]",&kbd,&key,&kst)==3){
                enum mibr_key40_event e;
                if(g_trace)g_trace(kbd,key,kst);
                if(step&&kbd==4&&key==40&&kst==1)step(context);
                /* r57: left roller push (KEY44) held long = CarPlay/native route toggle (was KEY40);
                 * right roller push (KEY40) held long = resync of the view counter. */
                e=mibr_key40_feed_key(&s->key44,kbd,key,kst,44);
                if(e==MIBR_KEY40_ROUTE_LONG&&fn)fn(context,e);
                e=mibr_key40_feed(&s->key,kbd,key,kst);
                if(e==MIBR_KEY40_ROUTE_LONG&&resync)resync(context);
            }
            pos=(size_t)(p-s->buf)+needle;
        }
        if(pos>0){memmove(s->buf,s->buf+pos,s->n-pos);s->n-=pos;pos=0;}
        if(s->n>=BUF_CAP-1u){s->n=0;pos=0;} /* defensive: never wedge on junk */
    }
}

#ifndef KEY40D_TEST
static long long mono_ms(void){
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return (long long)t.tv_sec*1000LL+t.tv_nsec/1000000L;
}

static void say(const char *what){
    fprintf(stderr,"[%lldms] MIBR_KEY40D %s\n",mono_ms(),what);
    fflush(stderr);
}

static void trace_state(int kbd,int key,int kst){
    static int lines;
    if(lines++>=4000)return;
    /* r28: every key is traced so a second toggle key can be picked from the log. */
    if(kbd==4&&key==40)fprintf(stderr,"[%lldms] MIBR_KEY40D KEY40 KST=%d\n",mono_ms(),kst);
    else fprintf(stderr,"[%lldms] MIBR_KEY40D OTHER KBD=%d KEY=%d KST=%d\n",mono_ms(),kbd,key,kst);
    fflush(stderr);
}

static void stop_owner(void){
    FILE *f;long pid=0;
    if(access(OWNER_LOCK_PATH,F_OK)){say("STOP_SKIPPED no_owner_lock");return;}
    f=fopen(OWNER_PID_PATH,"r");
    if(!f){say("STOP_SKIPPED no_owner_pid");return;}
    if(fscanf(f,"%ld",&pid)!=1)pid=0;
    fclose(f);
    if(pid<=1){say("STOP_SKIPPED bad_owner_pid");return;}
    if(kill((pid_t)pid,0)){say("STOP_SKIPPED owner_not_running");return;}
    if(kill((pid_t)pid,SIGTERM)){say("STOP_FAILED");return;}
    fprintf(stderr,"[%lldms] MIBR_KEY40D STOP_SIGTERM owner=%ld\n",mono_ms(),pid);
    fflush(stderr);
}

static void toggle(void *context,enum mibr_key40_event event){
    static long long last;
    long long now=mono_ms();
    int fd;
    (void)context;(void)event;
    if(last&&now-last<DEBOUNCE_MS){say("TOGGLE_DEBOUNCED");return;}
    last=now;
    if(!access(PAUSE_PATH,F_OK)){
        if(unlink(PAUSE_PATH))say("RESUME_FAILED");else say("RESUME route requested (pause removed)");
        return;
    }
    fd=open(PAUSE_PATH,O_WRONLY|O_CREAT|O_EXCL,0644);
    if(fd<0){say("PAUSE_FAILED");return;}
    close(fd);
    say("PAUSE route requested (native navigation)");
    stop_owner();
}

/* r55: one cockpit view step per KEY40 press start. The helper keeps the position and, when the owner switched
 * "follow" on, sets the live safe area. It is run to completion (bounded) so quick presses never overlap. */
static void view_run(const char *verb){
    pid_t p;int st=0,waited=0;
    if(access(VIEW_SCRIPT,R_OK)){return;}
    p=fork();
    if(p<0){say("VIEW_FORK_FAILED");return;}
    if(p==0){
        execl("/bin/ksh","ksh",VIEW_SCRIPT,verb,(char *)NULL);
        _exit(127);
    }
    while(waited<VIEW_WAIT_MS){
        pid_t w=waitpid(p,&st,WNOHANG);
        if(w==p)return;
        if(w<0&&errno!=EINTR)return;
        usleep(10000);waited+=10;
    }
    kill(p,SIGKILL);
    (void)waitpid(p,&st,0);
    say("VIEW_STEP_TIMEOUT");
}
static void view_step(void *context){(void)context;view_run("step");}
static void view_resync(void *context){(void)context;say("RESYNC view counter (KEY40 long)");view_run("resync");}

/* r30: passive raw capture of the DebugSPI byte stream for offline key/encoder identification.
 * Record = u32 LE monotonic ms, u16 LE length, payload. Capped so /tmp (RAM) cannot fill up. */
#define RAW_PATH "/tmp/mibr-debugspi-raw.bin"
#define RAW_CAP (12L*1024L*1024L)
static FILE *g_raw;
static long g_raw_bytes;
static void raw_record(const char *data,size_t n){
    unsigned char h[6];long long t=mono_ms();
    if(!g_raw){
        if(g_raw_bytes>=RAW_CAP)return;
        g_raw=fopen(RAW_PATH,"ab");
        if(!g_raw){g_raw_bytes=RAW_CAP;return;}
    }
    if(g_raw_bytes+(long)n+6>RAW_CAP){
        if(g_raw){fclose(g_raw);g_raw=NULL;}
        g_raw_bytes=RAW_CAP;
        say("RAW_CAPTURE_FULL");
        return;
    }
    h[0]=(unsigned char)(t&0xff);h[1]=(unsigned char)((t>>8)&0xff);
    h[2]=(unsigned char)((t>>16)&0xff);h[3]=(unsigned char)((t>>24)&0xff);
    h[4]=(unsigned char)(n&0xff);h[5]=(unsigned char)((n>>8)&0xff);
    if(fwrite(h,1,6,g_raw)==6&&fwrite(data,1,n,g_raw)==n){g_raw_bytes+=(long)n+6;fflush(g_raw);}
}

static volatile sig_atomic_t stopped;
static void on_stop(int sig){(void)sig;stopped=1;}

int main(void){
    struct key40d_scan *scan=(struct key40d_scan *)calloc(1,sizeof(*scan));
    if(!scan)return 2;
    key40d_init(scan);
    signal(SIGPIPE,SIG_IGN);signal(SIGTERM,on_stop);signal(SIGINT,on_stop);
    g_trace=trace_state;
    say("START passive receiver 127.0.0.1:15001");
    while(!stopped){
        int fd=socket(AF_INET,SOCK_STREAM,0);
        struct sockaddr_in a;
        if(fd<0){sleep(2);continue;}
        memset(&a,0,sizeof(a));a.sin_family=AF_INET;
        a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);a.sin_port=htons(15001);
        if(connect(fd,(struct sockaddr*)&a,sizeof(a))){close(fd);sleep(2);continue;}
        say("CONNECTED");
        key40d_init(scan);
        while(!stopped){
            fd_set rs;struct timeval tv;char chunk[2048];ssize_t n;int r;
            FD_ZERO(&rs);FD_SET(fd,&rs);tv.tv_sec=1;tv.tv_usec=0;
            r=select(fd+1,&rs,NULL,NULL,&tv);
            if(r<0){if(errno==EINTR)continue;break;}
            if(r==0)continue;
            n=recv(fd,chunk,sizeof(chunk),0);
            if(n<=0)break;
            raw_record(chunk,(size_t)n);
            key40d_feed(scan,chunk,(size_t)n,toggle,view_step,view_resync,NULL);
        }
        close(fd);
        say("DISCONNECTED retry");
        if(!stopped)sleep(2);
    }
    say("STOP");
    free(scan);
    return 0;
}
#else
/* Host test: stdin is the byte stream, argv[1] the chunk size. Prints one ROUTE_LONG per toggle. */
static int count,steps,resyncs;
static void on_event(void *context,enum mibr_key40_event event){
    (void)context;(void)event;count++;printf("ROUTE_LONG %d\n",count);
}
static void on_step(void *context){(void)context;steps++;}
static void on_resync(void *context){(void)context;resyncs++;}
int main(int argc,char **argv){
    struct key40d_scan *scan=(struct key40d_scan *)calloc(1,sizeof(*scan));
    size_t chunk=argc>1?(size_t)atoi(argv[1]):4096u;
    char *buf;size_t n;
    if(!scan||chunk==0||chunk>BUF_CAP)return 2;
    buf=(char *)malloc(chunk);
    if(!buf)return 2;
    key40d_init(scan);
    while((n=fread(buf,1,chunk,stdin))>0)key40d_feed(scan,buf,n,on_event,on_step,on_resync,NULL);
    printf("STEPS %d\n",steps);
    printf("RESYNCS %d\n",resyncs);
    printf("TOTAL %d\n",count);
    free(buf);free(scan);
    return 0;
}
#endif
