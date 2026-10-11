/*
 * MIBR R2.1 OEM ClientAppender 1.3.17 trace reader; QNX 6.5 or POSIX host.
 * Only sends mandatory VersionInfo / >OK< handshake (not DSI commands).
 * Discards OEM client library; captures byte-exact POST-HANDSHAKE stream.
 * CLOCK_MONOTONIC times are comparable to mibr-keypanel-native combined.log
 * on the same QNX kernel. A chunk timestamp is not an individual DSI event time.
 * No emulator, process signals, OEM edits, /tmp use, or autostart.
 */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define RAW_CAP (16u*1024u*1024u)
#define CHUNK_SIZE 4096u
#define LIB_CAP (16u*1024u*1024u)
#define HANDSHAKE_MS 45000LL
static volatile sig_atomic_t stop_requested;
static void on_signal(int sig) {(void)sig; stop_requested=1;}
static long long mono_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC,&ts)!=0) return -1;
    return (long long)ts.tv_sec*1000LL+ts.tv_nsec/1000000LL;
}
static int write_all(int fd,const void *b,size_t n) {
    const unsigned char *p=(const unsigned char*)b;
    while(n) {ssize_t w=write(fd,p,n);if(w<0 && errno==EINTR)continue;
        if(w<=0)return -1;
        p+=(size_t)w;
        n-=(size_t)w;
    }
    return 0;
}
/* Bounded, segmentation-safe OEM protocol IO; never use host printf shell utility. */
static int ready(int fd,int writing,long long until) {
    while(!stop_requested) {
        if(mono_ms()<0 || mono_ms()>=until)return -1;
        fd_set rd,wr;struct timeval tv;FD_ZERO(&rd);FD_ZERO(&wr);
        FD_SET(fd,writing?&wr:&rd);tv.tv_sec=0;tv.tv_usec=250000;
        int n=select(fd+1,writing?NULL:&rd,writing?&wr:NULL,NULL,&tv);
        if(n<0 && errno==EINTR)continue;
        if(n<0)return -1;
        if(n)return 0;
    }
    return -1;
}
static int recv_exact(int fd,unsigned char *b,size_t n,long long until) {
    while(n) {
        if(ready(fd,0,until))return -1;
        ssize_t m=recv(fd,b,n,0);
        if(m<0 && (errno==EINTR||errno==EAGAIN))continue;
        if(m<=0)return -1;
        b+=(size_t)m;n-=(size_t)m;
    }
    return 0;
}
static int send_exact(int fd,const unsigned char *b,size_t n,long long until) {
    while(n) {
        if(ready(fd,1,until))return -1;
        ssize_t m=send(fd,b,n,0);
        if(m<0 && (errno==EINTR||errno==EAGAIN))continue;
        if(m<=0)return -1;
        b+=(size_t)m;n-=(size_t)m;
    }
    return 0;
}
static int send_utf(int fd,const char *s,long long until) {
    size_t n=strlen(s);unsigned char b[128];
    if(n>125)return -1;
    b[0]=(unsigned char)(n>>8);b[1]=(unsigned char)n;
    memcpy(b+2,s,n); /* ASCII is Java modified-UTF-8 compatible */
    return send_exact(fd,b,n+2,until);
}
static void help(const char *name) {
    fprintf(stderr,"Usage: %s --capture --out EXISTING_SD_DIR --seconds 10..1800 [--port 1800]\n",name);
}
int main(int argc,char **argv) {
    int sec=0,port=1800,s=-1,raw=-1,indexfd=-1,rc=2,connected=0,truncated=0;
    int version_sent=0,lib_header=0,lib_magic_ok=0,ok_sent=0,peer_closed=0;
    unsigned long lib_bytes=0;const char *phase="init";unsigned char head[11];
    long long handshake_at=-1,until=0;
    char *out=NULL,rawpath[768],indexpath[768],reportpath[768],row[256];
    unsigned char buf[CHUNK_SIZE]; unsigned long bytes=0,chunks=0;
    long long begin=-1,connected_at=-1,end,first_at=-1,last_at=-1;
    struct sockaddr_in addr;
    for(int i=1;i<argc;i++) {
        if(!strcmp(argv[i],"--capture"))continue;
        if(!strcmp(argv[i],"--out")&&i+1<argc){out=argv[++i];continue;}
        if(!strcmp(argv[i],"--seconds")&&i+1<argc){char*e;long n=strtol(argv[++i],&e,10);if(*e||n<10||n>1800){help(argv[0]);return 2;}sec=(int)n;continue;}
        if(!strcmp(argv[i],"--port")&&i+1<argc){char*e;long n=strtol(argv[++i],&e,10);if(*e||n<1||n>65535){help(argv[0]);return 2;}port=(int)n;continue;}
        help(argv[0]);return 2;
    }
    if(!out||!sec||out[0]!='/') {help(argv[0]);return 2;}
    /* Production: SD only. Host CI uses an explicit compile-time switch. */
#ifndef MIBR_HOST_TEST
    if(strncmp(out,"/net/mmx/fs/sda0/",17)!=0 &&
       strncmp(out,"/net/mmx.mibhigh.net/fs/sda0/",29)!=0) {fprintf(stderr,"Output path is not approved SD location\n");return 2;}
#endif
    struct stat st;if(stat(out,&st)||!S_ISDIR(st.st_mode)){perror("output directory");return 2;}
    if(snprintf(rawpath,sizeof rawpath,"%s/dsi-client-original.bin",out)>=(int)sizeof rawpath ||
       snprintf(indexpath,sizeof indexpath,"%s/dsi-chunks.tsv",out)>=(int)sizeof indexpath ||
       snprintf(reportpath,sizeof reportpath,"%s/dsi-report.txt",out)>=(int)sizeof reportpath) return 2;
    raw=open(rawpath,O_CREAT|O_EXCL|O_WRONLY,0644);
    if(raw<0){perror("raw create");return 2;}
    indexfd=open(indexpath,O_CREAT|O_EXCL|O_WRONLY,0644);
    if(indexfd<0){perror("index create");goto finish;}
    if(write_all(indexfd,"mono_ms\toffset\tbytes\n",21))goto finish;
    signal(SIGINT,on_signal);signal(SIGTERM,on_signal);signal(SIGPIPE,SIG_IGN);
    begin=mono_ms();if(begin<0)goto finish;
    s=socket(AF_INET,SOCK_STREAM,0);if(s<0){perror("socket");goto finish;}
    memset(&addr,0,sizeof addr);addr.sin_family=AF_INET;addr.sin_port=htons((unsigned short)port);
    addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    phase="connect";
    if(connect(s,(struct sockaddr*)&addr,sizeof addr)!=0){perror("connect 127.0.0.1");goto finish;}
    connected=1;connected_at=mono_ms();until=connected_at+HANDSHAKE_MS;
    printf("DSI_RX connected loopback_port=%d mono_ms=%lld\n",port,connected_at);fflush(stdout);
    phase="version_sent";
    if(send_utf(s,"VersionInfo client=1.3.17",until)){rc=5;goto finish;}
    version_sent=1;phase="lib_header";
    if(recv_exact(s,head,sizeof head,until)){rc=5;goto finish;}
    if(head[0]!='@'||head[1]!='d'||head[10]!='\n'){rc=5;goto finish;}
    uint64_t nlib=0;for(int j=2;j<10;j++)nlib=(nlib<<8)|head[j];
    if(nlib<3||nlib>LIB_CAP){rc=5;goto finish;}
    lib_header=1;lib_bytes=(unsigned long)nlib;
    phase="lib_transfer";
    uint64_t remain=nlib;unsigned char magic[3];size_t checked=0;
    while(remain) {
        size_t take=remain>CHUNK_SIZE?CHUNK_SIZE:(size_t)remain;
        if(recv_exact(s,buf,take,until)){rc=5;goto finish;}
        for(size_t j=0;j<take && checked<3;j++)magic[checked++]=buf[j];
        remain-=take; /* OEM binary transferred only in RAM; never written to SD */
    }
    if(checked!=3||magic[0]!='B'||magic[1]!='Z'||magic[2]!='h'){rc=5;goto finish;}
    lib_magic_ok=1;phase="ok_sent";
    if(send_utf(s,">OK<",until)){rc=5;goto finish;}
    ok_sent=1;handshake_at=mono_ms();phase="trace_capture";
    printf("DSI_RX HANDSHAKE=PASS lib_bytes=%lu mono_ms=%lld\n",lib_bytes,handshake_at);fflush(stdout);
    rc=0;
    while(!stop_requested) {
        long long now=mono_ms();if(now<0){rc=3;break;}
        if(now-begin>=(long long)sec*1000)break;
        fd_set set;struct timeval tv;FD_ZERO(&set);FD_SET(s,&set);tv.tv_sec=0;tv.tv_usec=250000;
        int sel=select(s+1,&set,NULL,NULL,&tv);
        if(sel<0){if(errno==EINTR)continue;perror("select");rc=3;break;}
        if(!sel)continue;
        ssize_t n=recv(s,buf,sizeof buf,0);
        if(n<0){if(errno==EINTR)continue;perror("recv");rc=3;break;}
        if(!n){fprintf(stderr,"DSI_RX peer_closed AFTER handshake\n");peer_closed=1;break;}
        now=mono_ms();if(first_at<0)first_at=now;last_at=now;
        if(bytes+(unsigned long)n>RAW_CAP){truncated=1;fprintf(stderr,"DSI_RX bounded raw cap reached\n");rc=4;break;}
        snprintf(row,sizeof row,"%lld\t%lu\t%ld\n",now,bytes,(long)n);
        if(write_all(raw,buf,(size_t)n)||write_all(indexfd,row,strlen(row))){perror("capture write");rc=3;break;}
        bytes+=(unsigned long)n;chunks++;
    }
finish:
    end=mono_ms();if(s>=0)close(s);if(raw>=0)close(raw);if(indexfd>=0)close(indexfd);
    FILE *f=fopen(reportpath,"w");if(f) {
        fprintf(f,"VC_DSI_RX_R2_1=1\nprotocol=OEM_ClientAppender_1.3.17\noutput=POST_HANDSHAKE_RAW_TRANSPORT\noem_library_saved=NO\nport=%d\nconnected=%d\n",port,connected);
        fprintf(f,"version_sent=%d\nlib_header=%d\nlib_bytes=%lu\nlib_bzip2_magic=%d\nok_sent=%d\nphase=%s\npeer_closed=%d\nhandshake_mono_ms=%lld\n",version_sent,lib_header,lib_bytes,lib_magic_ok,ok_sent,phase,peer_closed,handshake_at);
        fprintf(f,"start_mono_ms=%lld\nconnected_mono_ms=%lld\nfirst_chunk_mono_ms=%lld\nlast_chunk_mono_ms=%lld\nend_mono_ms=%lld\n",begin,connected_at,first_at,last_at,end);
        fprintf(f,"raw_bytes=%lu\nchunks=%lu\ntruncated=%d\nexit_rc=%d\n",bytes,chunks,truncated,rc);
        fclose(f);
    }
    printf("DSI_RX_RESULT handshake=%s post_handshake_bytes=%lu chunks=%lu truncated=%d rc=%d\n",ok_sent?"PASS":"FAIL",bytes,chunks,truncated,rc);
    return rc;
}
