/*
 * MIBR R2 DSI client receive-only probe; QNX 6.5 ARMv7 or POSIX host.
 * Captures exact received TCP bytes; DOES NOT presume client protocol framing.
 * CLOCK_MONOTONIC times are comparable to mibr-keypanel-native combined.log
 * on the same QNX kernel. A chunk timestamp is not an individual DSI event time.
 * No socket sends, process signals, OEM edits, /tmp use, or autostart.
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
static void help(const char *name) {
    fprintf(stderr,"Usage: %s --capture --out EXISTING_SD_DIR --seconds 10..1800 [--port 1800]\n",name);
}
int main(int argc,char **argv) {
    int sec=0,port=1800,s=-1,raw=-1,indexfd=-1,rc=2,connected=0,truncated=0;
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
    signal(SIGINT,on_signal);signal(SIGTERM,on_signal);
    begin=mono_ms();if(begin<0)goto finish;
    s=socket(AF_INET,SOCK_STREAM,0);if(s<0){perror("socket");goto finish;}
    memset(&addr,0,sizeof addr);addr.sin_family=AF_INET;addr.sin_port=htons((unsigned short)port);
    addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if(connect(s,(struct sockaddr*)&addr,sizeof addr)!=0){perror("connect 127.0.0.1");goto finish;}
    connected=1;connected_at=mono_ms();
    printf("DSI_RX connected loopback_port=%d mono_ms=%lld; no bytes sent\n",port,connected_at);fflush(stdout);
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
        if(!n){fprintf(stderr,"DSI_RX peer_closed (does not prove zero DSI traffic)\n");break;}
        now=mono_ms();if(first_at<0)first_at=now;last_at=now;
        if(bytes+(unsigned long)n>RAW_CAP){truncated=1;fprintf(stderr,"DSI_RX bounded raw cap reached\n");rc=4;break;}
        snprintf(row,sizeof row,"%lld\t%lu\t%ld\n",now,bytes,(long)n);
        if(write_all(raw,buf,(size_t)n)||write_all(indexfd,row,strlen(row))){perror("capture write");rc=3;break;}
        bytes+=(unsigned long)n;chunks++;
    }
finish:
    end=mono_ms();if(s>=0)close(s);if(raw>=0)close(raw);if(indexfd>=0)close(indexfd);
    FILE *f=fopen(reportpath,"w");if(f) {
        fprintf(f,"VC_DSI_RX_R2=1\nreceive_only=YES\nprotocol_decoded=NO\nport=%d\nconnected=%d\n",port,connected);
        fprintf(f,"start_mono_ms=%lld\nconnected_mono_ms=%lld\nfirst_chunk_mono_ms=%lld\nlast_chunk_mono_ms=%lld\nend_mono_ms=%lld\n",begin,connected_at,first_at,last_at,end);
        fprintf(f,"raw_bytes=%lu\nchunks=%lu\ntruncated=%d\nexit_rc=%d\n",bytes,chunks,truncated,rc);
        fclose(f);
    }
    printf("DSI_RX_RESULT connected=%d bytes=%lu chunks=%lu truncated=%d rc=%d\n",connected,bytes,chunks,truncated,rc);
    return rc;
}
