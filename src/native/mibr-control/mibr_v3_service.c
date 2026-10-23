/* SPDX-License-Identifier: GPL-3.0-or-later
 * MIBR/3 local service; read-only by default, qualified storage opt-in.
 * Target write/stream capabilities intentionally remain unadvertised.
 * The production secret is provisioned out of band, never passed in argv.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_v3_readonly.h"
#include "mibr_v3_runtime_observer.h"
#include "mibr_v3_recovery_gate.h"
#include <stdlib.h>
#if defined(__QNXNTO__) && defined(MIBR_V3_TARGET_STORAGE_QUALIFIED)
#include "mibr_v3_qnx_mount.h"
#endif
#ifdef ALT111_SETTINGS_TEST
#include "mibr_v3_profile_store.h"
#include <stdio.h>
struct host_store {const char *profile;};
struct mock_route {struct mibr_v3_route_observation state;unsigned calls;};
static int route_read(void *ctx,struct mibr_v3_route_observation *out){
    *out=((struct mock_route*)ctx)->state;return 0;
}
static int route_set(void *ctx,enum mibr_v3_visible_route target,
    const struct mibr_v3_route_observation *expected,const char *rid,
    struct mibr_v3_route_observation *out){
    struct mock_route *m=(struct mock_route*)ctx;
    if(m->state.visible!=expected->visible||m->state.session!=expected->session||
       m->state.generation!=expected->generation)return -1;
    m->calls++;
    if(getenv("MIBR_V3_HOST_ROUTE_FAIL"))return -1;
    if(getenv("MIBR_V3_HOST_ROUTE_UNCERTAIN"))return -2;
    if(getenv("MIBR_V3_HOST_ROUTE_PENDING")){*out=m->state;return 1;}
    m->state.visible=target;m->state.generation++;
    if(!getenv("MIBR_V3_HOST_ROUTE_NO_ACK"))
        snprintf(m->state.ack_request_id,sizeof(m->state.ack_request_id),"%s",rid);
    *out=m->state;return 0;
}
static int host_rw(void *ctx){(void)ctx;return getenv("MIBR_V3_HOST_FAIL_RW")?-1:0;}
static int host_ro(void *ctx){(void)ctx;return getenv("MIBR_V3_HOST_FAIL_RO")?-1:0;}
static int host_set(void *ctx,const struct alt111_settings_paths *paths,
    const struct alt111_settings *observed,unsigned id,const char *value,
    uint64_t revision,char *error,size_t cap){
    struct host_store *s=(struct host_store*)ctx;
    struct mibr_v3_mount_guard guard={host_rw,host_ro,ctx};
    return mibr_v3_profile_set(paths,s->profile,observed,id,value,revision,&guard,error,cap);
}
#endif
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#define REQUEST_CAP 4096u
#define RESPONSE_CAP 16384u
#define TOKEN_LENGTH 64u
static volatile sig_atomic_t stopped;
static void stop_service(int sig){(void)sig;stopped=1;}
static int hex_lower(char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}
static int secret_read(const char *path,char value[TOKEN_LENGTH+1]){
    struct stat link,opened;int fd;size_t used=0;ssize_t n;char tail;
    if(!path||lstat(path,&link)||!S_ISREG(link.st_mode)||
       link.st_uid!=geteuid()||(link.st_mode&077)!=0||link.st_size!=TOKEN_LENGTH+1)return -1;
    fd=open(path,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&opened)||!S_ISREG(opened.st_mode)||
       opened.st_dev!=link.st_dev||opened.st_ino!=link.st_ino||
       opened.st_uid!=geteuid()||(opened.st_mode&077)!=0){close(fd);return -1;}
    while(used<TOKEN_LENGTH+1){
        n=read(fd,value+used,TOKEN_LENGTH+1-used);
        if(n<0&&errno==EINTR)continue;
        if(n<=0){close(fd);return -1;}used+=(size_t)n;
    }
    n=read(fd,&tail,1);
    if(close(fd)||n!=0||value[TOKEN_LENGTH]!='\n')return -1;
    value[TOKEN_LENGTH]=0;
    for(used=0;used<TOKEN_LENGTH;used++)if(!hex_lower(value[used]))return -1;
    return 0;
}
static int read_line(int fd,char line[REQUEST_CAP+1],size_t *length){
    size_t n=0;char c;ssize_t k;
    while(n<REQUEST_CAP){
        k=recv(fd,&c,1,0);
        if(k<0&&errno==EINTR)continue;
        if(k!=1)return -1;
        if(c=='\n'){line[n++]='\n';line[n]=0;*length=n;return 0;}
        if((unsigned char)c<32||(unsigned char)c>126)return -1;
        line[n++]=c;
    }
    return -1;
}
static int authenticate_and_strip(char *line,size_t *length,const char *secret,
                                  const char *input_secret,
                                  enum mibr_v3_role *role){
    char *p=line,*marker=NULL;size_t at,i;unsigned diff=0,input_diff=0;
    /* Authentication is a required LAST field, not a new Java-only verb.
     * Search every field delimiter; malformed duplicate auth is rejected by
     * the original strict MIBR/3 parser after stripping only the last token. */
    while((p=strstr(p,"auth="))!=NULL){
        if(p>line&&(p[-1]==' '||p[-1]==';'))marker=p-1;
        p+=5;
    }
    if(!marker)return -1;
    at=(size_t)(marker-line);
    if(at+1+5+TOKEN_LENGTH+1!=*length||
       memcmp(marker+1,"auth=",5)||line[*length-1]!='\n')return -1;
    for(i=0;i<TOKEN_LENGTH;i++){
        diff|=(unsigned char)(marker[6+i]^secret[i]);
        if(input_secret)input_diff|=(unsigned char)(marker[6+i]^input_secret[i]);
    }
    if(diff&&(!input_secret||input_diff))return -1;
    *role=!diff?MIBR_V3_UI:MIBR_V3_INPUT;
    line[at]='\n';line[at+1]=0;*length=at+1;
    return 0;
}
static int send_full(int fd,const char *p,size_t count){
    size_t used=0;ssize_t n;
    while(used<count){
        n=send(fd,p+used,count-used,0);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)return -1;
        used+=(size_t)n;
    }
    return 0;
}
/* r23: cockpit confirmation of the last presentation request. GEN2 consumes the marker, dispatches one
 * SHOW and reports its completion in the status counters; SHOWN only after a completion newer than the
 * baseline taken when the request was written (never from the request alone). */
static struct {char dir[256];unsigned long long baseline;int pending;long long since;int final_set;char final_state[16];} show_track;
static long long show_now_ms(void){
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return (long long)t.tv_sec*1000LL+t.tv_nsec/1000000L;
}
static int gen2_counters(const char *dir,unsigned long long *completed,int *status){
    char path[300],buf[4096],*p;ssize_t n;int fd;
    if(snprintf(path,sizeof(path),"%s/mibr-alt111-gen2.status",dir)>=(int)sizeof(path))return -1;
    fd=open(path,O_RDONLY);if(fd<0)return -1;
    n=read(fd,buf,sizeof(buf)-1);(void)close(fd);
    if(n<=0)return -1;
    buf[n]=0;*completed=0;*status=-1;
    p=strstr(buf,"last_completed_request=");if(!p)return -1;
    *completed=strtoull(p+23,NULL,10);
    p=strstr(buf,"last_completion_status=");if(p)*status=atoi(p+23);
    return 0;
}
static int show_state(void *context,char *out,size_t cap){
    unsigned long long completed;int status;long long age;
    (void)context;
    if(!show_track.pending){snprintf(out,cap,"%s",show_track.final_set?show_track.final_state:"NONE");return 0;}
    age=show_now_ms()-show_track.since;
    if(!gen2_counters(show_track.dir,&completed,&status)){
        if(completed>show_track.baseline){
            snprintf(show_track.final_state,sizeof(show_track.final_state),"%s",status==0?"SHOWN":"FAILED");
            show_track.final_set=1;show_track.pending=0;
            snprintf(out,cap,"%s",show_track.final_state);return 0;
        }
    }else if(age>2500){
        snprintf(show_track.final_state,sizeof(show_track.final_state),"NO_SESSION");
        show_track.final_set=1;show_track.pending=0;
        snprintf(out,cap,"NO_SESSION");return 0;
    }
    if(age>12000){
        snprintf(show_track.final_state,sizeof(show_track.final_state),"TIMEOUT");
        show_track.final_set=1;show_track.pending=0;
        snprintf(out,cap,"TIMEOUT");return 0;
    }
    snprintf(out,cap,"PENDING");return 0;
}
/* r23: "CarPlay im Cockpit" = the same pause the KEY40 long press toggles (pause file read by the
 * supervisor). Pausing also stops the Parity owner gracefully (SIGTERM): it restores the stock route. */
static int carplay_paused_state(void *context){
    char path[300];
    if(!context||snprintf(path,sizeof(path),"%s/mibr-parity-drive.pause",(const char *)context)>=(int)sizeof(path))return 0;
    return access(path,F_OK)==0;
}
static int carplay_pause(void *context,int enabled){
    char path[300],lock[300],pidp[300];FILE *f;long pid=0;int fd;
    if(!context)return -1;
    if(snprintf(path,sizeof(path),"%s/mibr-parity-drive.pause",(const char *)context)>=(int)sizeof(path))return -1;
    if(enabled){
        if(access(path,F_OK)==0&&unlink(path))return -1;
        return 0;
    }
    if(access(path,F_OK)!=0){
        fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0644);
        if(fd<0)return -1;
        (void)close(fd);
    }
    if(snprintf(lock,sizeof(lock),"%s/mibr-parity-session.lock",(const char *)context)>=(int)sizeof(lock)||
       snprintf(pidp,sizeof(pidp),"%s/mibr-parity-session.pid",(const char *)context)>=(int)sizeof(pidp))return 0;
    if(access(lock,F_OK)!=0)return 0;
    f=fopen(pidp,"r");if(!f)return 0;
    if(fscanf(f,"%ld",&pid)!=1)pid=0;
    (void)fclose(f);
    if(pid>1&&kill((pid_t)pid,0)==0)(void)kill((pid_t)pid,SIGTERM);
    return 0;
}
/* Presentation refresh through the existing GEN2 owner: the proven operator path
 * (`echo request > /tmp/mibr-alt111-gen2-reacquire`) that GEN2 consumes and turns
 * into one serialized SHOW for the current session. Best effort, bounded, no ACK. */
static int request_show(void *context,unsigned id){
    char path[256];int fd;
    (void)id;
    /* r13: GEN2 re-reads the settings files only every 250 ms but checks this
     * marker every loop. Written at once, the SHOW often carried the OLD values
     * and the change appeared only with a later SHOW (field: large delay).
     * Wait one settings poll period plus margin so the SHOW sees the new TEMP. */
    {struct timespec wait={0,300000000L};(void)nanosleep(&wait,NULL);}
    if(!context||snprintf(path,sizeof(path),"%s/mibr-alt111-gen2-reacquire",
                          (const char *)context)>=(int)sizeof(path))return -1;
    fd=open(path,O_WRONLY|O_CREAT|O_TRUNC,0644);if(fd<0)return -1;
    if(write(fd,"request\n",8)!=8){(void)close(fd);return -1;}
    {int rc=close(fd);
     /* r23: remember what to wait for: any GEN2 completion newer than now confirms this SHOW. */
     {unsigned long long completed=0;int status=-1;
      snprintf(show_track.dir,sizeof(show_track.dir),"%s",(const char *)context);
      show_track.baseline=gen2_counters(show_track.dir,&completed,&status)?0ULL:completed;
      show_track.pending=1;show_track.final_set=0;show_track.since=show_now_ms();}
     return rc;}
}
/* r46: engine type helper. Fixed script path, fixed argv (no shell string), enum-validated value, 12 s bound. */
static int engine_op(void *context,const char *op,const char *value,char *out,size_t cap){
    int fds[2],status=0,rc=-1,w;pid_t pid;size_t n=0;long long t0;
    const char *script,*shell="/bin/ksh";
    (void)context;
    if(!out||cap<16||!op||(strcmp(op,"get")&&strcmp(op,"set")))return -1;
    if(!strcmp(op,"set")&&(!value||(strcmp(value,"gas")&&strcmp(value,"diesel")&&
                                      strcmp(value,"electric")&&strcmp(value,"cng"))))return -1;
    script="/mnt/app/root/altscreen-u2/scripts/mibr-engine.ksh";
#ifdef ALT111_SETTINGS_TEST
    if(getenv("MIBR_ENGINE_SCRIPT"))script=getenv("MIBR_ENGINE_SCRIPT");
    if(getenv("MIBR_ENGINE_SHELL"))shell=getenv("MIBR_ENGINE_SHELL");
#endif
    out[0]=0;
    if(pipe(fds))return -1;
    pid=fork();
    if(pid<0){(void)close(fds[0]);(void)close(fds[1]);return -1;}
    if(pid==0){
        (void)close(fds[0]);
        if(dup2(fds[1],1)<0)_exit(126);
        (void)close(fds[1]);
        if(!strcmp(op,"set"))(void)execl(shell,"ksh",script,"set",value,(char *)NULL);
        else (void)execl(shell,"ksh",script,"get",(char *)NULL);
        _exit(127);
    }
    (void)close(fds[1]);
    t0=show_now_ms();
    for(;;){
        fd_set rs;struct timeval tv;ssize_t k;
        if(show_now_ms()-t0>12000)break;
        FD_ZERO(&rs);FD_SET(fds[0],&rs);tv.tv_sec=0;tv.tv_usec=200000;
        if(select(fds[0]+1,&rs,NULL,NULL,&tv)>0){
            k=read(fds[0],out+n,cap-1-n);
            if(k<=0)break;
            n+=(size_t)k;if(n>=cap-1)break;
        }
    }
    out[n]=0;(void)close(fds[0]);
    for(w=0;w<20;w++){
        pid_t got=waitpid(pid,&status,WNOHANG);
        if(got==pid){rc=(WIFEXITED(status)&&WEXITSTATUS(status)==0)?0:-1;pid=-1;break;}
        {struct timespec d={0,100000000L};(void)nanosleep(&d,NULL);}
    }
    if(pid>0){(void)kill(pid,SIGKILL);(void)waitpid(pid,&status,0);rc=-1;}
    return rc;
}
/* Audit of mutating/failed requests (never the credential: it is stripped before). */
static unsigned long now_ms(void){
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return (unsigned long)t.tv_sec*1000ul+(unsigned long)(t.tv_nsec/1000000L);
}
static void audit(int role,const char *in,const char *out,unsigned long t0){
    char req[200],rep[160];size_t i;const char *op=strchr(in,' ');
    int mutating=0;
    if(op){op=strchr(op+1,' ');
        if(op){op++;
            mutating=!strncmp(op,"SET",3)||!strncmp(op,"ACTION",6)||!strncmp(op,"REQUEST_STATUS",14)||!strncmp(op,"ENGINE_SET",10);}}
    if(!mutating&&!strstr(out," ERR "))return;
    for(i=0;i<sizeof(req)-1&&in[i]&&in[i]!='\n';i++){req[i]=in[i];}
    req[i]=0;
    for(i=0;i<sizeof(rep)-1&&out[i]&&out[i]!='\n';i++){rep[i]=out[i];}
    rep[i]=0;
    /* r13: monotonic start and duration, to locate delays between tap, flash and SHOW. */
    fprintf(stderr,"MIBR_V3_AUDIT t_ms=%lu dur_ms=%lu role=%d req=\"%s\" rep=\"%s\"\n",
            t0,now_ms()-t0,role,req,rep);
    fflush(stderr);
}
static void serve(int fd,struct mibr_v3_reader *reader,const char *secret,
                  const char *input_secret){
    char in[REQUEST_CAP+1],out[RESPONSE_CAP];size_t n=0;
    enum mibr_v3_role role=MIBR_V3_UI;unsigned long t0;
    struct timeval tv;tv.tv_sec=3;tv.tv_usec=0;
    (void)setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));
    (void)setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof(tv));
    if(read_line(fd,in,&n)||authenticate_and_strip(in,&n,secret,input_secret,&role)){
        (void)send_full(fd,"MIBR/3 invalid ERR AUTH_REQUIRED\n",
                        sizeof("MIBR/3 invalid ERR AUTH_REQUIRED\n")-1);return;
    }
    /* One passive fresh owner-file observation per serviced request; never
     * a second sender, persistent writer or implied same-session key ACK. */
    if(mibr_v3_runtime_read("/tmp/mibr-alt111-gen2.status",&reader->runtime))
        memset(&reader->runtime,0,sizeof(reader->runtime));
    t0=now_ms();
    (void)mibr_v3_handle(reader,role,in,n,out,sizeof(out));
    audit((int)role,in,out,t0);
    (void)send_full(fd,out,strlen(out));
}
int main(int argc,char **argv){
    struct alt111_settings_paths paths={"/tmp","/mnt/app/root"};
    struct mibr_v3_reader *reader=NULL;
    struct sockaddr_in local,peer;struct timeval tv;char secret[TOKEN_LENGTH+1]={0};
    unsigned long port;char *end;int server=-1,fd,one=1; socklen_t peerlen;
    char input_secret[TOKEN_LENGTH+1]={0};
    int input_enabled=0,qualify_durable=0;
#ifdef ALT111_SETTINGS_TEST
    struct host_store store;
    struct mock_route mock={0};
#endif
#if defined(__QNXNTO__) && defined(MIBR_V3_TARGET_STORAGE_QUALIFIED)
    struct mibr_v3_qnx_store target_store;
#endif
    if(argc<5||argc>8||strcmp(argv[1],"--port")||strcmp(argv[3],"--secret-file"))return 2;
    if(argc>=7&&!strcmp(argv[5],"--input-secret-file")){
        input_enabled=1;
        if(argc==8){if(strcmp(argv[7],"--qualify-durable"))return 2;qualify_durable=1;}
        else if(argc!=7)return 2;
    }else if(argc==6&&!strcmp(argv[5],"--qualify-durable"))qualify_durable=1;
    else if(argc!=5)return 2;
#if !(defined(__QNXNTO__) && defined(MIBR_V3_TARGET_STORAGE_QUALIFIED))
    if(qualify_durable)return 2;
#endif
    errno=0;port=strtoul(argv[2],&end,10);
    if(errno||!*argv[2]||*end||port>65535||port<1024){
#ifdef ALT111_SETTINGS_TEST
        if(port!=0)return 2;
#else
        return 2;
#endif
    }
#ifdef ALT111_SETTINGS_TEST
    paths.temp=getenv("ALT111_SETTINGS_TEMP_ROOT");
    paths.persistent=getenv("ALT111_SETTINGS_PERSISTENT_ROOT");
    if(!paths.temp||!paths.persistent)return 3;
#endif
    if(secret_read(argv[4],secret))return 3;
    if(input_enabled){
        if(secret_read(argv[6],input_secret)||!strcmp(secret,input_secret)){
            memset(secret,0,sizeof(secret));memset(input_secret,0,sizeof(input_secret));
            return 3;
        }
    }
    reader=(struct mibr_v3_reader*)calloc(1,sizeof(*reader));
    if(!reader){memset(secret,0,sizeof(secret));return 3;}
    if(mibr_v3_open(reader,&paths)){free(reader);memset(secret,0,sizeof(secret));return 4;}
    reader->presentation_request=request_show;
    reader->presentation_context=(void *)paths.temp;
    reader->live_apply=mibr_v3_live_apply;reader->live_revert=mibr_v3_live_revert;
    reader->carplay_pause=carplay_pause;reader->carplay_paused=carplay_paused_state;
    reader->carplay_context=(void *)paths.temp;
    reader->show_state=show_state;reader->show_context=NULL;
    reader->engine_op=engine_op;reader->engine_context=NULL;
    {
        /* r14 write-behind. Target default: flush 25 s after the last change, at the latest 90 s
         * after the first. 0 = synchronous durable SET. Host tests stay synchronous unless set. */
        const char *d=getenv("MIBR_V3_PERSIST_DELAY_MS"),*m=getenv("MIBR_V3_PERSIST_MAX_MS");
#ifdef ALT111_SETTINGS_TEST
        reader->persist_delay_ms=d?atoi(d):0;
#else
        reader->persist_delay_ms=d?atoi(d):25000;
#endif
        reader->persist_max_ms=m?atoi(m):90000;
        if(reader->persist_delay_ms<0||reader->persist_delay_ms>60000)reader->persist_delay_ms=0;
        if(reader->persist_max_ms<reader->persist_delay_ms)reader->persist_max_ms=reader->persist_delay_ms;
    }
#ifdef ALT111_SETTINGS_TEST
    if(getenv("MIBR_V3_HOST_ROUTE_TEST")){
        mock.state.visible=MIBR_ROUTE_STOCK110;
        mock.state.session=7;mock.state.generation=9;mock.state.confirmed=1;
        reader->route_read=route_read;reader->route_set=route_set;
        reader->route_context=&mock;
        reader->route_qualified=getenv("MIBR_V3_HOST_ROUTE_UNQUALIFIED")?0:1;
    }
    store.profile=getenv("MIBR_V3_HOST_PROFILE_PATH");
    if(store.profile&&*store.profile&&
       !mibr_v3_recovery_check(store.profile)&&
       !mibr_v3_profile_parity(store.profile,&reader->cached)){
        reader->durable_set=host_set;reader->storage_context=&store;
    }
#endif
#if defined(__QNXNTO__) && defined(MIBR_V3_TARGET_STORAGE_QUALIFIED)
    if(qualify_durable){
        if(mibr_v3_qnx_preflight(&target_store,
              "/mnt/app/root/altscreen-u2/config/cpvc-r5.profile",&reader->cached)){
            free(reader);memset(secret,0,sizeof(secret));return 4;
        }
        reader->durable_set=mibr_v3_qnx_set;reader->storage_context=&target_store;
    }
#endif
    signal(SIGPIPE,SIG_IGN);signal(SIGTERM,stop_service);signal(SIGINT,stop_service);
    server=socket(AF_INET,SOCK_STREAM,0);if(server<0)goto fail;
    (void)setsockopt(server,SOL_SOCKET,SO_REUSEADDR,&one,sizeof(one));
    memset(&local,0,sizeof(local));local.sin_family=AF_INET;
    local.sin_addr.s_addr=htonl(INADDR_LOOPBACK);local.sin_port=htons((unsigned short)port);
    if(bind(server,(struct sockaddr*)&local,sizeof(local))||listen(server,4))goto fail;
    tv.tv_sec=1;tv.tv_usec=0;
    (void)setsockopt(server,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));
#ifdef ALT111_SETTINGS_TEST
    {socklen_t len=sizeof(local);
     if(getsockname(server,(struct sockaddr*)&local,&len))goto fail;
     printf("MIBR_V3_HOST_SERVICE_PORT=%u\n",(unsigned)ntohs(local.sin_port));fflush(stdout);}
#endif
    while(!stopped){
        {
            /* accept() ignores SO_RCVTIMEO on QNX: wake once a second for the write-behind flush. */
            fd_set rs;struct timeval wait;int ready;
            FD_ZERO(&rs);FD_SET(server,&rs);wait.tv_sec=1;wait.tv_usec=0;
            ready=select(server+1,&rs,NULL,NULL,&wait);
            if(ready<=0){(void)mibr_v3_flush_due(reader,0);continue;}
        }
        peerlen=sizeof(peer);fd=accept(server,(struct sockaddr*)&peer,&peerlen);
        if(fd<0){
            if(errno==EINTR||errno==EAGAIN||errno==EWOULDBLOCK){(void)mibr_v3_flush_due(reader,0);continue;}
            break;
        }
        if(peerlen>=sizeof(peer)&&peer.sin_family==AF_INET&&
           peer.sin_addr.s_addr==htonl(INADDR_LOOPBACK))serve(fd,reader,secret,input_enabled?input_secret:NULL);
        close(fd);
        (void)mibr_v3_flush_due(reader,0);
    }
    (void)mibr_v3_flush_due(reader,1);
    close(server);memset(secret,0,sizeof(secret));
    memset(input_secret,0,sizeof(input_secret));free(reader);return stopped?0:7;
fail:
    if(server>=0)close(server);
    memset(secret,0,sizeof(secret));
    memset(input_secret,0,sizeof(input_secret));free(reader);return 5;
}
