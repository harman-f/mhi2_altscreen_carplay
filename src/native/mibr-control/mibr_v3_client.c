/* SPDX-License-Identifier: GPL-3.0-or-later
 * Thin CLI over the SAME MIBR/3 loopback service as future IBM J9 UI.
 * This file does not link settings_core, access profile/TEMP, or issue OEM IO.
 */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>
#define INMAX 4096u
#define OUTMAX 16384u
static int read_secret(const char *p,char value[65]){
    struct stat a,b;int fd;size_t n=0;ssize_t r;char tail;
    if(lstat(p,&a)||!S_ISREG(a.st_mode)||a.st_uid!=geteuid()||
       (a.st_mode&077)||a.st_size!=65)return -1;
    fd=open(p,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&b)||a.st_dev!=b.st_dev||a.st_ino!=b.st_ino||
       b.st_uid!=geteuid()||(b.st_mode&077)){close(fd);return -1;}
    while(n<65){r=read(fd,value+n,65-n);if(r<0&&errno==EINTR)continue;
        if(r<=0){close(fd);return -1;}n+=(size_t)r;}
    r=read(fd,&tail,1);if(close(fd)||r!=0||value[64]!='\n')return -1;
    value[64]=0;
    for(n=0;n<64;n++)if(!((value[n]>='0'&&value[n]<='9')||
         (value[n]>='a'&&value[n]<='f')))return -1;
    return 0;
}
static int safe(char c){
    return (c>='A'&&c<='Z')||(c>='a'&&c<='z')||
      (c>='0'&&c<='9')||c=='-'||c=='_'||c=='.'||c=='~';
}
static int encoded(const char *value,char *out,size_t cap){
    static const char hex[]="0123456789ABCDEF";
    size_t n=0;const unsigned char *p=(const unsigned char*)value;
    if(!*p)return -1;
    while(*p){
        if(safe((char)*p)){if(n+1>=cap)return -1;out[n++]=(char)*p;}
        else {if(n+3>=cap)return -1;out[n++]='%';out[n++]=hex[*p>>4];out[n++]=hex[*p&15];}
        p++;
    }
    out[n]=0;return 0;
}
static int valid_rid(const char *s){
    unsigned n=0;unsigned char c;
    if(!s||!*s)return 0;
    while((c=(unsigned char)*s++)!=0){
        if(++n>64||!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
             (c>='0'&&c<='9')||c=='_'||c=='-'))return 0;
    }
    return 1;
}
static int send_all(int fd,const char *p,size_t n){
    size_t used=0;ssize_t r;
    while(used<n){r=send(fd,p+used,n-used,0);if(r<0&&errno==EINTR)continue;
        if(r<=0)return -1;
        used+=(size_t)r;}
    return 0;
}
int main(int argc,char **argv){
    char auth[65]={0},request[INMAX+1],reply[OUTMAX+1],key[600],value[600];
    const char *op,*rid="cli",*fields="";unsigned long port;char *end;
    int fd,used,n,rc;ssize_t readn;struct sockaddr_in address;struct timeval timeout;
    if(argc<6||strcmp(argv[1],"--port")||strcmp(argv[3],"--secret-file"))return 2;
    errno=0;port=strtoul(argv[2],&end,10);
    if(errno||!*argv[2]||*end||port<1024||port>65535||read_secret(argv[4],auth))return 2;
    op=argv[5];
    if(argc==6&&(!strcmp(op,"HELLO")||!strcmp(op,"CAPABILITIES")||!strcmp(op,"STATUS"))){}
    else if(argc==6&&!strcmp(op,"SNAPSHOT"))fields="scope=ui";
    else if(argc==7&&!strcmp(op,"GET")){
        if(encoded(argv[6],key,sizeof(key)))return 2;
        used=snprintf(request,sizeof(request),"key=%s",key);
        if(used<0||(size_t)used>=sizeof(request))return 2;
        fields=request;
    }else if(argc==7&&(!strcmp(op,"REQUEST_STATUS")||!strcmp(op,"ACTION_STATUS"))){
        if(!valid_rid(argv[6]))return 2;
        used=snprintf(request,sizeof(request),"request_id=%s",argv[6]);
        if(used<0||(size_t)used>=sizeof(request))return 2;
        fields=request;
    }else if(argc==10&&!strcmp(op,"SET")){
        rid=argv[9];if(!valid_rid(rid)||encoded(argv[6],key,sizeof(key))||
                            encoded(argv[7],value,sizeof(value)))return 2;
        {const char *r=argv[8];if(!*r||(*r=='0'&&r[1]))return 2;
         while(*r){if(*r<'0'||*r>'9')return 2;r++;}}
        used=snprintf(request,sizeof(request),
         "key=%s;value=%s;expected_revision=%s;activation=AUTO;request_id=%s",
         key,value,argv[8],rid);
        if(used<0||(size_t)used>=sizeof(request))return 2;
        fields=request;
    }else return 2;
    /* fields points at request in the branch above: build into separate frame. */
    {char frame[INMAX+1];
     used=snprintf(frame,sizeof(frame),"MIBR/3 %s %s%s%s%sauth=%s\n",
          rid,op,*fields?" ":"",fields,*fields?";":" ",auth);
     if(used<=0||(size_t)used>INMAX){memset(auth,0,sizeof(auth));return 2;}
     memcpy(request,frame,(size_t)used+1);
    }
    memset(auth,0,sizeof(auth));
    fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return 3;
    timeout.tv_sec=3;timeout.tv_usec=0;
    (void)setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
    (void)setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
    memset(&address,0,sizeof(address));address.sin_family=AF_INET;
    address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);address.sin_port=htons((unsigned short)port);
    if(connect(fd,(struct sockaddr*)&address,sizeof(address))||
       send_all(fd,request,(size_t)used)){close(fd);return 3;}
    n=0;rc=3;
    while((size_t)n<OUTMAX){
        readn=recv(fd,reply+n,1,0);
        if(readn<0&&errno==EINTR)continue;
        if(readn!=1)break;
        if(reply[n++]=='\n'){reply[n]=0;rc=0;break;}
    }
    close(fd);if(rc)return 3;
    fputs(reply,stdout);
    return strstr(reply," ERR ")?1:0;
}
