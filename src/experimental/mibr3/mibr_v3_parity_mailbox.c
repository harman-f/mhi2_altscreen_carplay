/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "mibr_v3_parity_mailbox.h"
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
static int safe_rid(const char *rid){
    size_t n=0;unsigned char x;
    if(!rid||!*rid)return 0;
    while(n<64&&(x=(unsigned char)rid[n])!=0){
        if(!((x>='a'&&x<='z')||(x>='A'&&x<='Z')||
           (x>='0'&&x<='9')||x=='_'||x=='-'))return 0;
        ++n;
    }
    return n>0&&n<65&&rid[n]==0;
}
static int send_request(struct mibr_v3_parity_mailbox *m,
    const char *rid,const char *verb){
    char temp[512],payload[256];size_t len,pos=0;ssize_t got;
    int fd,n,uncertain=0;
    struct stat st;
    if(!m||m->qualified!=1||!m->request_path||
       strncmp(m->request_path,"/tmp/",5)||!m->request_path[5]||
       strchr(m->request_path+5,'/')||!m->session||
       !m->stream_generation||!safe_rid(rid))return -1;
    n=snprintf(temp,sizeof(temp),"%s.%s.tmp",m->request_path,rid);
    if(n<0||(size_t)n>=sizeof(temp))return -1;
    n=snprintf(payload,sizeof(payload),"MIBR3|%s|%s|%" PRIu64 "|%" PRIu64 "\n",
        verb,rid,m->session,m->stream_generation);
    if(n<0||(size_t)n>=sizeof(payload))return -1;
    len=(size_t)n;
    /* Existence is deliberately not a queue: one unreconciled action means
     * no second owner command even if its author is unknown. */
    if(!lstat(m->request_path,&st)||errno!=ENOENT)return -2;
    fd=open(temp,O_WRONLY|O_CREAT|O_EXCL,0600);
    if(fd<0)return errno==EEXIST?-2:-1;
    if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_uid!=geteuid()||
       (st.st_mode&077)!=0){uncertain=-1;goto abort;}
    while(pos<len){
        got=write(fd,payload+pos,len-pos);
        if(got<0&&errno==EINTR)continue;
        if(got<=0){uncertain=-1;goto abort;}pos+=(size_t)got;
    }
    if(fsync(fd)){uncertain=-1;goto abort;}
    if(close(fd)){(void)unlink(temp);return -2;}
    /* An earlier lstat + rename was unsafe: POSIX rename REPLACES an
     * occupied destination if another producer wins between the calls.
     * Hard-link publication is atomic no-replace in the SAME /tmp FS:
     * EEXIST cannot overwrite a still-unconsumed owner command. */
    if(link(temp,m->request_path)){
        int saved_errno=errno;
        (void)unlink(temp);
        return saved_errno==EEXIST?-2:-1; /* no link = proven no handoff */
    }
    /* Once link succeeds, the sole owner may already have taken the request.
     * Losing cleanup does not justify a second dispatch with a fresh RID. */
    if(unlink(temp))return -2;
    return 0;
abort:
    (void)close(fd);(void)unlink(temp);return uncertain;
}
int mibr_v3_parity_mailbox_start(void *ctx,const char *rid){
    return send_request((struct mibr_v3_parity_mailbox*)ctx,rid,"START");
}
int mibr_v3_parity_mailbox_stop(void *ctx,const char *rid){
    return send_request((struct mibr_v3_parity_mailbox*)ctx,rid,"STOP");
}
