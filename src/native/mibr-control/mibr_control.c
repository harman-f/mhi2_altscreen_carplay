/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Experimental SINGLE Classic111 TEMP broker. No runtime-effective claim or SAVE.
 * Linked against the PINNED original alt111-settings core, not a duplicate registry.
 * OFFLINE/host qualified only; explicit standalone Unit approval required.
 */
#define _POSIX_C_SOURCE 200809L
#include "alt111_settings.h"
#include <arpa/inet.h>
#include <errno.h>
#include <inttypes.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#define REQ_CAP 512
#define REPLY_CAP 768
static const struct alt111_settings_paths production_paths={"/tmp","/mnt/app/root"};
static struct alt111_settings_paths paths;
static char auth[33];
static int enabled;
static void reply(char *out,size_t n,const char *msg){snprintf(out,n,"%s",msg);}
static int digits(const char *s,uint64_t *v){
    char *end;unsigned long long u;
    if(!s||!*s||(*s<'0'||*s>'9')||(s[0]=='0'&&s[1]))return -1;
    errno=0;u=strtoull(s,&end,10);
    if(errno||*end||u==0)return -1;
    *v=(uint64_t)u;return 0;
}
static int token_ok(const char *s){
    unsigned i,diff=0;
    if(!s||strlen(s)!=32)return 0;
    for(i=0;i<32;i++)diff|=(unsigned)(unsigned char)(s[i]^auth[i]);
    return diff==0;
}
/* UI presentation allowlist, NOT a second type/domain registry. CI verifies
 * exact membership against menu-definition.json (11 visible/37 hidden). */
static const char *const UI_VISIBLE_KEYS[]={
    "carplay.enabled","viewarea.selected","navigation.surface",
    "navigation.ETA","navigation.speedLimit","navigation.compass",
    "navigation.maneuver","navigation.url","preset.id","maxFPS",
    "sourceVersion"
};
static int ui_visible(const char *key){
    unsigned i;
    for(i=0;i<sizeof(UI_VISIBLE_KEYS)/sizeof(UI_VISIBLE_KEYS[0]);i++)
        if(!strcmp(key,UI_VISIBLE_KEYS[i]))return 1;
    return 0;
}
static const char *layer(unsigned n){return n==ALT111_TEMP?"temp":n==ALT111_PERSISTENT?"persistent":"profile";}
static const char *result_apply(const char *a){
    if(!strcmp(a,"reconnect"))return "RECONNECT_REQUIRED";
    if(!strcmp(a,"session"))return "SESSION_TRANSITION_REQUIRED";
    if(!strcmp(a,"presentation"))return "PRESENTATION_REFRESH_REQUIRED";
    return "QUEUED";
}
static int printable(const char *p){
    while(*p){if((unsigned char)*p<33||(unsigned char)*p>126)return 0;p++;}return 1;
}
static void command(char *input,char out[REPLY_CAP]){
    char *save=0,*verb,*token,*a,*b,*c,*extra;
    struct alt111_settings *snap=0,*after=0;
    char err[256]={0};int id;uint64_t rev;unsigned setting;
    verb=strtok_r(input," ",&save);token=strtok_r(NULL," ",&save);
    if(!verb||!token||!token_ok(token)){reply(out,REPLY_CAP,"ERROR AUTH_REQUIRED");return;}
    if(!strcmp(verb,"HELLO")){
        a=strtok_r(NULL," ",&save);
        if(!a||strcmp(a,"MIBR/2")||strtok_r(NULL," ",&save))reply(out,REPLY_CAP,"ERROR INVALID_REQUEST");
        else reply(out,REPLY_CAP,"HELLO MIBR/2 mode=TEMP_NATIVE mutations=TEMP_ONLY keys=48 effective=UNCONFIRMED");
        return;
    }
    snap=(struct alt111_settings *)malloc(sizeof(*snap));
    if(!snap){reply(out,REPLY_CAP,"ERROR ALLOCATION");return;}
    if(alt111_settings_load(&paths,snap,err,sizeof(err))){
        /* Never leak error paths or an unverified snapshot over the protocol. */
        reply(out,REPLY_CAP,"ERROR CORE_LOAD_FAILED");goto done;
    }
    if(!strcmp(verb,"STATUS")&&!strtok_r(NULL," ",&save)){
        snprintf(out,REPLY_CAP,"STATUS mode=TEMP_NATIVE revision=%" PRIu64
          " session=NONE effective=UNCONFIRMED stored=UNCONFIRMED",
          snap->revision);goto done;
    }
    if(!strcmp(verb,"GET")){
        a=strtok_r(NULL," ",&save);
        if(!a||strtok_r(NULL," ",&save)){reply(out,REPLY_CAP,"ERROR INVALID_REQUEST");goto done;}
        id=alt111_setting_find(a);
        if(id<0){reply(out,REPLY_CAP,"ERROR INVALID_KEY");goto done;}
        snprintf(out,REPLY_CAP,"VALUE key=%s desired=%s source=%s revision=%" PRIu64
          " effective=UNCONFIRMED session=NONE",a,snap->value[id],
          layer(snap->layer[id]),snap->revision);goto done;
    }
    if(!strcmp(verb,"TEMPBATCH")){
        unsigned ids[11],count=0,i,j;const char *values[11];
        char *part,*next,*equals;int priority=0;
        a=strtok_r(NULL," ",&save);b=strtok_r(NULL," ",&save);
        extra=strtok_r(NULL," ",&save);
        if(!enabled){reply(out,REPLY_CAP,"ERROR POLICY_BLOCKED");goto done;}
        if(!a||!b||extra||digits(a,&rev)||!printable(b)){
            reply(out,REPLY_CAP,"ERROR INVALID_REQUEST");goto done;
        }
        if(rev!=snap->revision){reply(out,REPLY_CAP,"ERROR STALE_REVISION");goto done;}
        part=b;
        while(part&&*part){
            if(count==11){reply(out,REPLY_CAP,"ERROR INVALID_BATCH");goto done;}
            next=strchr(part,';');if(next)*next=0;
            equals=strchr(part,'=');
            if(!equals||equals==part||!equals[1]){
                reply(out,REPLY_CAP,"ERROR INVALID_BATCH");goto done;
            }
            *equals=0;values[count]=equals+1;
            id=alt111_setting_find(part);
            if(id<0){reply(out,REPLY_CAP,"ERROR INVALID_KEY");goto done;}
            for(j=0;j<count;j++)if(ids[j]==(unsigned)id){
                reply(out,REPLY_CAP,"ERROR DUPLICATE_KEY");goto done;
            }
            if(!ui_visible(part)||alt111_setting((unsigned)id)->read_only||
               alt111_setting_validate((unsigned)id,values[count])){
                reply(out,REPLY_CAP,"ERROR INVALID_OR_LOCKED_VALUE");goto done;
            }
            ids[count++]=(unsigned)id;
            if(!next)break;
            part=next+1;if(!*part){reply(out,REPLY_CAP,"ERROR INVALID_BATCH");goto done;}
        }
        if(!count){reply(out,REPLY_CAP,"ERROR INVALID_BATCH");goto done;}
        after=(struct alt111_settings *)malloc(sizeof(*after));
        if(!after){reply(out,REPLY_CAP,"ERROR ALLOCATION");goto done;}
        if(alt111_settings_mutate(&paths,ALT111_TEMP,ids,values,count,rev,after,err,sizeof(err))){
            reply(out,REPLY_CAP,strstr(err,"STALE_REVISION")?"ERROR STALE_REVISION":"ERROR CORE_MUTATION_FAILED");
            goto done;
        }
        if(alt111_settings_load(&paths,snap,err,sizeof(err))){
            reply(out,REPLY_CAP,"ERROR TEMP_READBACK_UNCONFIRMED");goto done;
        }
        for(i=0;i<count;i++){
            const char *apply=alt111_setting(ids[i])->apply;
            int rank=!strcmp(apply,"reconnect")?4:!strcmp(apply,"session")?3:
                     !strcmp(apply,"presentation")?2:1;
            if(strcmp(snap->value[ids[i]],values[i])||snap->layer[ids[i]]!=ALT111_TEMP){
                reply(out,REPLY_CAP,"ERROR TEMP_READBACK_UNCONFIRMED");goto done;
            }
            if(rank>priority)priority=rank;
        }
        snprintf(out,REPLY_CAP,"RESULT state=%s count=%u revision=%" PRIu64
          " desired=TEMP_READBACK effective=UNCONFIRMED session=NONE",
          priority==4?"RECONNECT_REQUIRED":priority==3?"SESSION_TRANSITION_REQUIRED":
          priority==2?"PRESENTATION_REFRESH_REQUIRED":"QUEUED",
          count,snap->revision);
        goto done;
    }
    if(!strcmp(verb,"TEMP")){
        a=strtok_r(NULL," ",&save);b=strtok_r(NULL," ",&save);
        c=strtok_r(NULL," ",&save);extra=strtok_r(NULL," ",&save);
        if(!enabled){reply(out,REPLY_CAP,"ERROR POLICY_BLOCKED");goto done;}
        if(!a||!b||!c||extra||digits(a,&rev)||!printable(c)){
            reply(out,REPLY_CAP,"ERROR INVALID_REQUEST");goto done;
        }
        if(rev!=snap->revision){reply(out,REPLY_CAP,"ERROR STALE_REVISION");goto done;}
        id=alt111_setting_find(b);
        if(id<0){reply(out,REPLY_CAP,"ERROR INVALID_KEY");goto done;}
        setting=(unsigned)id;
        /* Only approved visible keys in this interim HMI product surface. */
        if(!ui_visible(b) || alt111_setting(setting)->read_only ||
           alt111_setting_validate(setting,c)){
            reply(out,REPLY_CAP,"ERROR INVALID_OR_LOCKED_VALUE");goto done;
        }
        after=(struct alt111_settings *)malloc(sizeof(*after));
        if(!after){reply(out,REPLY_CAP,"ERROR ALLOCATION");goto done;}
        {
            const char *values[1]={c};
            if(alt111_settings_mutate(&paths,ALT111_TEMP,&setting,values,1,rev,after,err,sizeof(err))){
                reply(out,REPLY_CAP,strstr(err,"STALE_REVISION")?"ERROR STALE_REVISION":"ERROR CORE_MUTATION_FAILED");
                goto done;
            }
        }
        /* The native transaction result is not equivalent to a fresh readback. */
        if(alt111_settings_load(&paths,snap,err,sizeof(err)) ||
           strcmp(snap->value[setting],c) || snap->layer[setting]!=ALT111_TEMP){
            reply(out,REPLY_CAP,"ERROR TEMP_READBACK_UNCONFIRMED");goto done;
        }
        snprintf(out,REPLY_CAP,"RESULT state=%s key=%s desired=%s source=temp revision=%" PRIu64
          " effective=UNCONFIRMED session=NONE",result_apply(alt111_setting(setting)->apply),
          b,c,snap->revision);
        goto done;
    }
    reply(out,REPLY_CAP,"ERROR POLICY_BLOCKED");
done:
    free(after);free(snap);
}
static int line_read(int fd,char out[REQ_CAP+1]){
    unsigned n=0;char c;ssize_t got;
    while(n<REQ_CAP){
        got=recv(fd,&c,1,0);
        if(got<=0)return -1;
        if(c=='\n'){out[n]=0;return n?0:-1;}
        if((unsigned char)c<32||(unsigned char)c>126)return -1;
        out[n++]=c;
    }
    return -1;
}
int main(int argc,char **argv){
    int i,s,client;unsigned long port=0;char *end=0;struct sockaddr_in address;
    char line[REQ_CAP+1],result[REPLY_CAP];struct timeval timeout;
    paths=production_paths;
    if(argc!=6||strcmp(argv[1],"--port")||strcmp(argv[3],"--token")||strcmp(argv[5],"--enable-temp")){
        fputs("MIBR_CONTROL_EXPLICIT_ARGS_REQUIRED\n",stderr);return 2;
    }
    errno=0;port=strtoul(argv[2],&end,10);
    if(errno||*end||port>65535||port<1024){
#ifdef ALT111_SETTINGS_TEST
        if(port!=0){fputs("INVALID_PORT\n",stderr);return 2;}
#else
        fputs("INVALID_PORT\n",stderr);return 2;
#endif
    }
    if(strlen(argv[4])!=32){fputs("INVALID_TOKEN\n",stderr);return 2;}
    for(i=0;i<32;i++)if(!((argv[4][i]>='a'&&argv[4][i]<='f')||
                         (argv[4][i]>='0'&&argv[4][i]<='9'))){
        fputs("INVALID_TOKEN\n",stderr);return 2;
    }
    memcpy(auth,argv[4],32);auth[32]=0;enabled=1;
#ifdef ALT111_SETTINGS_TEST
    paths.temp=getenv("ALT111_SETTINGS_TEMP_ROOT");
    paths.persistent=getenv("ALT111_SETTINGS_PERSISTENT_ROOT");
    if(!paths.temp||!paths.persistent)return 3;
#endif
    signal(SIGPIPE,SIG_IGN);
    s=socket(AF_INET,SOCK_STREAM,0);if(s<0)return 4;
    memset(&address,0,sizeof(address));address.sin_family=AF_INET;
    address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);address.sin_port=htons((unsigned short)port);
    if(bind(s,(struct sockaddr *)&address,sizeof(address))||listen(s,4)){close(s);return 5;}
#ifdef ALT111_SETTINGS_TEST
    {socklen_t len=sizeof(address);if(getsockname(s,(struct sockaddr *)&address,&len))return 6;
     printf("MIBR_CONTROL_HOST_TEST_PORT=%u\n",(unsigned)ntohs(address.sin_port));fflush(stdout);}
#endif
    for(;;){
        client=accept(s,0,0);if(client<0){if(errno==EINTR)continue;break;}
        timeout.tv_sec=3;timeout.tv_usec=0;
        setsockopt(client,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
        setsockopt(client,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
        if(line_read(client,line))reply(result,sizeof(result),"ERROR INVALID_FRAME");
        else command(line,result);
        {size_t n=strlen(result);result[n++]='\n';(void)send(client,result,n,0);}
        close(client);
    }
    close(s);memset(auth,0,sizeof(auth));return 7;
}
