/* SPDX-License-Identifier: GPL-3.0-or-later
 * Original Classic111 schema2/48 core, explicitly refreshed immutable RAM snapshot.
 * OFFLINE READ-ONLY LIBRARY: not a daemon, peer authenticator or installed service.
 */
#include "mibr_v3_readonly.h"
#include <inttypes.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#define INPUT_MAX 4096u
#define OUTPUT_MAX 16384u
#define VALUE_MAX 512u
#define FIELDS_MAX 64u
#define UI_COUNT 11u
static const char *const ui_keys[UI_COUNT] = {
    "carplay.enabled","viewarea.selected","navigation.surface",
    "navigation.ETA","navigation.speedLimit","navigation.compass",
    "navigation.maneuver","navigation.url","preset.id","maxFPS","sourceVersion"
};
struct field { char key[65]; char value[VALUE_MAX+1u]; };
struct request { char rid[65]; char op[32]; struct field f[FIELDS_MAX]; unsigned count; };
struct writer { char *s; size_t n,cap; int failed; unsigned fields; };
static int alnum_(unsigned char c){
    return (c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9');
}
static int name_first(unsigned char c){return (c>='A'&&c<='Z')||(c>='a'&&c<='z');}
static int unreserved(unsigned char c){
    return alnum_(c)||c=='_'||c=='.'||c=='~'||c=='-';
}
static int hexdigit(unsigned char c){return c>='0'&&c<='9'?c-'0':
        c>='A'&&c<='F'?c-'A'+10:-1;}
static int valid_utf8(const unsigned char *p, size_t n){
    size_t i=0;unsigned c,k,min,cp;
    while(i<n){
        c=p[i++];
        if(c<32||c==127)return 0;
        if(c<128)continue;
        if(c>=0xc2&&c<=0xdf){k=1;cp=c&31;min=128;}
        else if(c>=0xe0&&c<=0xef){k=2;cp=c&15;min=2048;}
        else if(c>=0xf0&&c<=0xf4){k=3;cp=c&7;min=65536;}
        else return 0;
        if(i+k>n)return 0;
        while(k--){c=p[i++];if((c&0xc0)!=0x80)return 0;cp=(cp<<6)|(c&63);}
        if(cp<min||cp>0x10ffff||(cp>=0xd800&&cp<=0xdfff))return 0;
    }
    return 1;
}
static int decode(const char *p,size_t n,char out[VALUE_MAX+1u]){
    size_t i=0,j=0;int a,b;unsigned char c;
    if(!n)return -1;
    while(i<n){
        c=(unsigned char)p[i++];
        if(c=='%'){
            if(i+1>=n||(a=hexdigit((unsigned char)p[i]))<0||
               (b=hexdigit((unsigned char)p[i+1]))<0)return -1;
            c=(unsigned char)((a<<4)|b);i+=2;
            if(unreserved(c))return -1; /* canonical: never escape safe bytes */
        }else if(!unreserved(c))return -1;
        if(j==VALUE_MAX)return -1;
        out[j++]=(char)c;
    }
    out[j]=0;
    return valid_utf8((const unsigned char*)out,j)?0:-1;
}
static int parse(const char *p,size_t n,struct request *q){
    size_t i=0,b,part,j,k;unsigned char c; unsigned a;
    memset(q,0,sizeof(*q));
    if(!p||n<12||n>INPUT_MAX||p[n-1]!='\n')return -1;
    for(i=0;i<n-1;i++)if((unsigned char)p[i]<32||(unsigned char)p[i]>126)return -1;
    if(memcmp(p,"MIBR/3 ",7))return -2;
    i=7;b=i;
    while(i<n-1&&p[i]!=' ')i++;
    if(i==b||i-b>64||i>=n-1)return -1;
    for(j=b;j<i;j++){c=(unsigned char)p[j];if(!alnum_(c)&&c!='_'&&c!='-')return -1;}
    memcpy(q->rid,p+b,i-b);q->rid[i-b]=0;i++;
    b=i;while(i<n-1&&p[i]!=' ')i++;
    if(i==b||i-b>=sizeof(q->op))return -1;
    memcpy(q->op,p+b,i-b);q->op[i-b]=0;
    if(i==n-1)return 0;
    i++;if(i==n-1)return -1;
    while(i<n-1){
        if(q->count==FIELDS_MAX)return -1;
        part=i;while(i<n-1&&p[i]!=';')i++;
        b=part;while(b<i&&p[b]!='=')b++;
        if(b==part||b==i||b-part>64||!name_first((unsigned char)p[part]))return -1;
        for(j=part+1;j<b;j++){
            c=(unsigned char)p[j];if(!alnum_(c)&&c!='_'&&c!='.'&&c!='-')return -1;
        }
        a=q->count;
        memcpy(q->f[a].key,p+part,b-part);q->f[a].key[b-part]=0;
        for(k=0;k<a;k++)if(!strcmp(q->f[k].key,q->f[a].key))return -1;
        if(decode(p+b+1,i-b-1,q->f[a].value))return -1;
        q->count++;
        if(i==n-1)break;
        i++;if(i==n-1)return -1;
    }
    return 0;
}
static void put(struct writer *w,const char *s){
    size_t n=strlen(s);
    if(w->failed||n>=w->cap-w->n){w->failed=1;return;}
    memcpy(w->s+w->n,s,n);w->n+=n;w->s[w->n]=0;
}
static void field(struct writer *w,const char *key,const char *value){
    static const char hex[]="0123456789ABCDEF";
    const unsigned char *p=(const unsigned char*)value;char one[4];
    if(!value||!*value||strlen(value)>VALUE_MAX||
       !valid_utf8(p,strlen(value))){w->failed=1;return;}
    put(w,w->fields++?";":" ");put(w,key);put(w,"=");
    while(*p&&!w->failed){
        if(unreserved(*p)){one[0]=(char)*p;one[1]=0;}
        else {one[0]='%';one[1]=hex[*p>>4];one[2]=hex[*p&15];one[3]=0;}
        put(w,one);p++;
    }
}
static void numeric(struct writer *w,const char *name,uint64_t n){
    char b[32];snprintf(b,sizeof(b),"%" PRIu64,n);field(w,name,b);
}
static void response_start(struct writer *w,const char *rid,const char *status){
    put(w,"MIBR/3 ");put(w,rid);put(w," ");put(w,status);
}
static void finish(struct writer *w){put(w,"\n");}
/* key=value line out of a small helper output; 0 on success, value must be 1..cap-1 lowercase/digit characters. */
static int kv_line(const char *text,const char *key,char *out,size_t cap){
    size_t kn=strlen(key),i;const char *p=text;
    while(p&&*p){
        if(!strncmp(p,key,kn)&&p[kn]=='='){
            p+=kn+1;
            for(i=0;p[i]&&p[i]!='\n';i++){
                if(i+1>=cap||!((p[i]>='a'&&p[i]<='z')||(p[i]>='0'&&p[i]<='9')))return -1;
                out[i]=p[i];
            }
            out[i]=0;return i?0:-1;
        }
        p=strchr(p,'\n');if(p)p++;
    }
    return -1;
}
static void error_frame(char *out,size_t cap,const char *rid,const char *code){
    snprintf(out,cap,"MIBR/3 %s ERR %s\n",rid&&*rid?rid:"invalid",code);
}
static long long mono_ms(void){
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return (long long)t.tv_sec*1000LL+t.tv_nsec/1000000L;
}
int mibr_v3_flush_due(struct mibr_v3_reader *r,int force){
    unsigned id;int failed=0;long long now;
    if(!r||!r->persist_pending)return 0;
    now=mono_ms();
    if(!force&&now-r->persist_last_ms<r->persist_delay_ms&&
       now-r->persist_first_ms<r->persist_max_ms)return 1;
    if(!r->durable_set||!r->ready||mibr_v3_refresh(r,&r->paths))return 1;
    for(id=0;id<ALTSET_COUNT;id++){
        struct alt111_settings obs;char err[80]={0};int rc;
        if(!r->persist_dirty[id])continue;
        obs=r->cached;
        snprintf(obs.value[id],sizeof(obs.value[id]),"%s",r->persist_old[id]);
        rc=r->durable_set(r->storage_context,&r->paths,&obs,id,r->cached.value[id],
                          obs.revision,err,sizeof(err));
        if(rc>=0){r->persist_dirty[id]=0;continue;}
        failed=1;
        fprintf(stderr,"MIBR_V3_PERSIST_FAILED id=%u rc=%d err=%s\n",id,rc,err);
        if(rc==-2||!strcmp(err,"RO_RESTORE_FAILED")){r->durable_set=NULL;r->ready=0;break;}
    }
    (void)mibr_v3_refresh(r,&r->paths);
    if(failed){r->persist_last_ms=mono_ms();r->persist_first_ms=r->persist_last_ms;return 1;}
    r->persist_pending=0;
    fprintf(stderr,"MIBR_V3_PERSIST_OK\n");
    return 0;
}
int mibr_v3_refresh(struct mibr_v3_reader *r,const struct alt111_settings_paths *paths){
    struct alt111_settings staged;
    char err[256]={0};
    if(!r)return -1;
    /* Fail closed until a complete original-core snapshot has been loaded.
     * Caller serializes refresh and handle, including on QNX. */
    r->ready=0;r->stored_verified=0;r->stored_pending=0;
    if(!paths||ALTSET_COUNT!=48u||
       alt111_settings_load(paths,&staged,err,sizeof(err)))return -1;
    r->cached=staged;
    r->ready=1;
    return 0;
}
int mibr_v3_open(struct mibr_v3_reader *r,const struct alt111_settings_paths *paths){
    if(!r)return -1;
    memset(r,0,sizeof(*r));
    if(paths)r->paths=*paths;
    return mibr_v3_refresh(r,paths);
}
static int is_visible(const char *key){
    unsigned i;for(i=0;i<UI_COUNT;i++)if(!strcmp(ui_keys[i],key))return 1;
    return 0;
}
static const char *activation_kind(const char *apply){
    if(!strcmp(apply,"live"))return "LIVE";
    if(!strcmp(apply,"presentation"))return "PRESENTATION";
    if(!strcmp(apply,"session"))return "SESSION";
    if(!strcmp(apply,"reconnect"))return "RECONNECT";
    return "UNKNOWN";
}
static const char *layer(unsigned n){
    return n==ALT111_TEMP?"temp":n==ALT111_PERSISTENT?"persistent":"profile";
}
static void row(struct writer *w,const struct alt111_settings *s,unsigned index,unsigned id){
    char key[48];const struct alt111_setting_descriptor *d=alt111_setting(id);
    if(!d){w->failed=1;return;}
#define ROW(fieldname,value) do {snprintf(key,sizeof(key),"row.%u." fieldname,index);field(w,key,value);}while(0)
    ROW("key",d->key);ROW("value",s->value[id]);ROW("source",layer(s->layer[id]));
    ROW("apply",d->apply);ROW("active","UNKNOWN");ROW("advertised","UNKNOWN");
#undef ROW
}
static const char *route_name(enum mibr_v3_visible_route v){
    return v==MIBR_ROUTE_STOCK110?"STOCK110":v==MIBR_ROUTE_DIRECT111?"DIRECT111":"UNKNOWN";
}
static int route_value(const char *s,enum mibr_v3_visible_route *v){
    if(!strcmp(s,"STOCK110")){*v=MIBR_ROUTE_STOCK110;return 0;}
    if(!strcmp(s,"DIRECT111")){*v=MIBR_ROUTE_DIRECT111;return 0;}
    return -1;
}
static int decimal_u64(const char *s,uint64_t *v){
    size_t i;uint64_t n=0;unsigned d;
    if(!s||!*s||(s[0]=='0'&&s[1]))return -1;
    for(i=0;s[i];i++){
        if(s[i]<'0'||s[i]>'9')return -1;
        d=(unsigned)(s[i]-'0');
        if(n>(UINT64_MAX-d)/10u)return -1;
        n=n*10u+d;
    }
    if(!n)return -1;
    *v=n;return 0;
}
static int route_observe(struct mibr_v3_reader *r,struct mibr_v3_route_observation *o){
    memset(o,0,sizeof(*o));
    if(!r||!r->route_qualified||!r->route_read||r->route_read(r->route_context,o)||
       !o->confirmed||!o->session||!o->generation||
       !memchr(o->ack_request_id,0,sizeof(o->ack_request_id))||
       (o->visible!=MIBR_ROUTE_STOCK110&&o->visible!=MIBR_ROUTE_DIRECT111)){
        memset(o,0,sizeof(*o));return -1;
    }
    return 0;
}
/* A pending route request owns the transition slot even if a later observer
 * shows a different generation or the original response was lost. Reconcile
 * ONLY with the original owner/session/RID and verified target. A timeout,
 * receipt eviction, stale telemetry or unrelated ACK cannot release it. */
static int route_reconcile_inflight(struct mibr_v3_reader *r){
    struct mibr_v3_route_observation current;
    struct mibr_v3_route_receipt *saved=NULL;
    unsigned i;
    if(!r||!r->route_inflight)return 0;
    for(i=0;i<8;i++)if(!strcmp(r->route_receipts[i].rid,r->route_inflight_rid)){
        saved=&r->route_receipts[i];break;
    }
    if(!saved)return -1;
    if(!saved->active && !route_observe(r,&current) &&
       current.visible==saved->target &&
       current.session==saved->expected_session &&
       current.generation>=saved->expected_generation &&
       !strcmp(current.ack_request_id,saved->rid))saved->active=1;
    if(!saved->active)return -1;
    r->route_inflight=0;r->route_inflight_rid[0]=0;
    return 0;
}
int mibr_v3_handle(struct mibr_v3_reader *r,enum mibr_v3_role role,
                   const char *frame,size_t length,char *out,size_t cap){
    struct request req;struct writer w;unsigned i;int rc,id;
    const char *scope="ui";
    enum mibr_v3_visible_route action_target=MIBR_ROUTE_UNKNOWN;
    uint64_t action_session=0,action_generation=0;
    if(!out||cap<80)return -1;
    out[0]=0;rc=parse(frame,length,&req);
    if(rc){error_frame(out,cap,rc==-2?"invalid":req.rid,rc==-2?"UNSUPPORTED_VERSION":"INVALID_FRAME");return -1;}
    /* Dedicated physical-input credential cannot read/write preferences, inspect
     * arbitrary keys or invoke future diagnostic verbs. Only route control. */
    if(role==MIBR_V3_INPUT && strcmp(req.op,"HELLO") &&
       strcmp(req.op,"CAPABILITIES") && strcmp(req.op,"STATUS") &&
       strcmp(req.op,"ACTION") && strcmp(req.op,"ACTION_STATUS")){
        error_frame(out,cap,req.rid,"FORBIDDEN");return -1;
    }
    w.s=out;w.n=0;w.cap=cap<OUTPUT_MAX?cap:OUTPUT_MAX;w.failed=0;w.fields=0;
    if(!strcmp(req.op,"HELLO")||!strcmp(req.op,"CAPABILITIES")||
       !strcmp(req.op,"STATUS")||!strcmp(req.op,"SHOW_STATUS")){
        if(req.count){error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;}
        response_start(&w,req.rid,"OK");
        if(!strcmp(req.op,"HELLO")){
            field(&w,"version","MIBR/3");field(&w,"schema","2");
            field(&w,"registry_keys","48");field(&w,"phase",r&&r->durable_set?"NATIVE_PROFILE_GUARDED":"NATIVE_READONLY_OFFLINE");
        }else if(!strcmp(req.op,"CAPABILITIES")){
            field(&w,"snapshot","1");field(&w,"durable_set",r&&r->durable_set?"1":"0");
            field(&w,"test_override","0");field(&w,"presentation_refresh","0");
            field(&w,"reconnect","0");field(&w,"session_control","0");
            {struct mibr_v3_route_observation current;
             field(&w,"route_action",r&&r->route_set&&!r->route_inflight&&
                   !route_observe(r,&current)?"1":"0");
             field(&w,"key40_input","0");field(&w,"zoom_exec_owner","GEN2");}
            field(&w,"phase",r&&r->durable_set?"NATIVE_PROFILE_GUARDED":"NATIVE_READONLY_OFFLINE");
        }else if(!strcmp(req.op,"SHOW_STATUS")){
            /* r23: did the cockpit confirm the last presentation request (GEN2 completion counters)? */
            char state[24]="UNKNOWN";
            if(r&&r->show_state)r->show_state(r->show_context,state,sizeof(state));
            field(&w,"state",state);
        }else {
            field(&w,"ready",r&&r->ready?(r->durable_set?"READY":"READ_ONLY"):"NOT_READY");
            field(&w,"stored",r&&r->stored_verified?"VERIFIED":"UNCONFIRMED");field(&w,"durable_generation","UNKNOWN");
            field(&w,"runtime_correlated","0");field(&w,"connected","UNKNOWN");
            field(&w,"session","NONE");field(&w,"pending","UNKNOWN");
            {struct mibr_v3_route_observation current;
             int observed=!route_observe(r,&current);
             field(&w,"route_correlated",observed?"1":"0");
             field(&w,"visible_route",observed?route_name(current.visible):"UNKNOWN");
             if(observed){numeric(&w,"route_session",current.session);
                          numeric(&w,"route_generation",current.generation);}
            }
            /* Separate passive observed GEN2 report, NOT per-key verified ACTIVE.
             * Never set runtime_correlated=1 merely from this aggregate snapshot. */
            field(&w,"runtime_observed",r&&r->runtime.observed?"1":"0");
            if(r&&r->runtime.observed){
                numeric(&w,"owner_session",r->runtime.session);
                numeric(&w,"owner_stream_gen",r->runtime.stream_gen);
                numeric(&w,"owner_desired_revision",r->runtime.desired_revision);
                numeric(&w,"owner_active_revision",r->runtime.active_revision);
                field(&w,"owner_confirmed",r->runtime.confirmed?"1":"0");
            }
            field(&w,"persistent_safety",r&&r->durable_set?"GUARDED":"UNQUALIFIED");
            if(r&&r->ready)numeric(&w,"revision",r->cached.revision);
        }
    }else if(!strcmp(req.op,"ENGINE_GET")||!strcmp(req.op,"ENGINE_SET")){
        /* r46: engine type of the CarPlay Identify. The value is validated here AND by the helper script. */
        char res[256],engine[16],announced[16],pending[4];
        int set=!strcmp(req.op,"ENGINE_SET");
        if(set?(req.count!=1||strcmp(req.f[0].key,"value")||
                (strcmp(req.f[0].value,"gas")&&strcmp(req.f[0].value,"diesel")&&
                 strcmp(req.f[0].value,"electric")&&strcmp(req.f[0].value,"cng"))):req.count){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if(!r||!r->engine_op){error_frame(out,cap,req.rid,"POLICY_BLOCKED");return -1;}
        res[0]=0;
        if(r->engine_op(r->engine_context,set?"set":"get",set?req.f[0].value:NULL,res,sizeof(res))){
            error_frame(out,cap,req.rid,"ENGINE_FAILED");return -1;
        }
        if(kv_line(res,"engine",engine,sizeof(engine))||kv_line(res,"announced",announced,sizeof(announced))||
           kv_line(res,"pending",pending,sizeof(pending))){
            error_frame(out,cap,req.rid,"ENGINE_FAILED");return -1;
        }
        response_start(&w,req.rid,"OK");
        field(&w,"engine",engine);field(&w,"announced",announced);field(&w,"pending",pending);
    }else if(!strcmp(req.op,"VIEW_GET")||!strcmp(req.op,"VIEW_SET")){
        /* r55: cockpit view follow. Key and value are allowlisted here AND validated by the helper script. */
        char res[256],follow[4],sport[4],m0[4],m1[4],m4[4],rs[4],pos[4];
        int set=!strcmp(req.op,"VIEW_SET");
        if(set){
            const char *k,*v;
            if(req.count!=2||strcmp(req.f[0].key,"name")||strcmp(req.f[1].key,"value")){
                error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
            }
            k=req.f[0].value;v=req.f[1].value;
            if(!v[0]||v[1]||
               !(((!strcmp(k,"follow")||!strcmp(k,"sport"))&&(v[0]=='0'||v[0]=='1'))||
                 ((!strcmp(k,"m0")||!strcmp(k,"m1")||!strcmp(k,"m4"))&&v[0]>='0'&&v[0]<='2')||
                 ((!strcmp(k,"pos")||!strcmp(k,"rs"))&&v[0]>='0'&&v[0]<='4'))){
                error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
            }
        }else if(req.count){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if(!r||!r->view_op){error_frame(out,cap,req.rid,"POLICY_BLOCKED");return -1;}
        res[0]=0;
        if(r->view_op(r->view_context,set?"set":"get",set?req.f[0].value:NULL,set?req.f[1].value:NULL,res,sizeof(res))){
            error_frame(out,cap,req.rid,"VIEW_FAILED");return -1;
        }
        if(kv_line(res,"follow",follow,sizeof(follow))||kv_line(res,"sport",sport,sizeof(sport))||
           kv_line(res,"m0",m0,sizeof(m0))||kv_line(res,"m1",m1,sizeof(m1))||kv_line(res,"m4",m4,sizeof(m4))||
           kv_line(res,"rs",rs,sizeof(rs))||kv_line(res,"pos",pos,sizeof(pos))){
            error_frame(out,cap,req.rid,"VIEW_FAILED");return -1;
        }
        response_start(&w,req.rid,"OK");
        field(&w,"follow",follow);field(&w,"sport",sport);field(&w,"m0",m0);field(&w,"m1",m1);field(&w,"m4",m4);
        field(&w,"rs",rs);field(&w,"pos",pos);
    }else if(!strcmp(req.op,"SNAPSHOT")){
        if(req.count>1||(req.count==1&&strcmp(req.f[0].key,"scope"))){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if(req.count)scope=req.f[0].value;
        if(strcmp(scope,"ui")&&strcmp(scope,"all")){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if(!strcmp(scope,"all")&&role!=MIBR_V3_SHELL){
            error_frame(out,cap,req.rid,"FORBIDDEN");return -1;
        }
        if(!r||!r->ready){error_frame(out,cap,req.rid,"NOT_READY");return -1;}
        response_start(&w,req.rid,"OK");
        numeric(&w,"row_count",!strcmp(scope,"ui")?UI_COUNT:ALTSET_COUNT);
        numeric(&w,"revision",r->cached.revision);
        field(&w,"stored",r&&r->stored_verified?"VERIFIED":"UNCONFIRMED");field(&w,"durable_generation","UNKNOWN");
        field(&w,"runtime_correlated","0");field(&w,"connected","UNKNOWN");
        field(&w,"session","NONE");field(&w,"session_generation","UNKNOWN");
        field(&w,"pending","UNKNOWN");field(&w,"phase",r->durable_set?"NATIVE_PROFILE_GUARDED":"NATIVE_READONLY_OFFLINE");
        {
            /* r23: the carplay.enabled row shows the live pause state (value 0 while paused). */
            struct alt111_settings shown=r->cached;
            if(r->carplay_paused&&r->carplay_paused(r->carplay_context))
                snprintf(shown.value[ALTSET_CARPLAY_ENABLED],sizeof(shown.value[ALTSET_CARPLAY_ENABLED]),"0");
            if(!strcmp(scope,"ui")){
                for(i=0;i<UI_COUNT;i++){
                    id=alt111_setting_find(ui_keys[i]);if(id<0){w.failed=1;break;}
                    row(&w,&shown,i,(unsigned)id);
                }
            }else for(i=0;i<ALTSET_COUNT;i++)row(&w,&shown,i,i);
        }
    }else if(!strcmp(req.op,"GET")){
        if(req.count!=1||strcmp(req.f[0].key,"key")){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        id=alt111_setting_find(req.f[0].value);
        if(id<0){error_frame(out,cap,req.rid,"INVALID_KEY");return -1;}
        if(role!=MIBR_V3_SHELL&&!is_visible(req.f[0].value)){
            error_frame(out,cap,req.rid,"FORBIDDEN");return -1;
        }
        if(!r||!r->ready){error_frame(out,cap,req.rid,"NOT_READY");return -1;}
        response_start(&w,req.rid,"OK");numeric(&w,"revision",r->cached.revision);
        field(&w,"stored",r&&r->stored_verified?"VERIFIED":"UNCONFIRMED");field(&w,"runtime_correlated","0");
        field(&w,"key",req.f[0].value);
        field(&w,"value",((unsigned)id==ALTSET_CARPLAY_ENABLED&&r->carplay_paused&&
                          r->carplay_paused(r->carplay_context))?"0":r->cached.value[id]);
        field(&w,"source",layer(r->cached.layer[id]));
        field(&w,"apply",alt111_setting((unsigned)id)->apply);field(&w,"active","UNKNOWN");
    }else if(!strcmp(req.op,"SET")){
        if(r)for(i=0;i<8;i++)if(!strcmp(req.rid,r->route_receipts[i].rid)){
            error_frame(out,cap,req.rid,"IDEMPOTENCY_COLLISION");return -1;
        }
        if(!r||!r->durable_set){error_frame(out,cap,req.rid,"POLICY_BLOCKED");return -1;}
        for(i=0;i<8;i++)if(!strcmp(req.rid,r->receipts[i].rid)){
            if(length!=r->receipts[i].n||memcmp(frame,r->receipts[i].frame,length)){
                error_frame(out,cap,req.rid,"IDEMPOTENCY_COLLISION");return -1;
            }
            if(strlen(r->receipts[i].response)+1>cap){
                error_frame(out,cap,req.rid,"SNAPSHOT_TOO_LARGE");return -1;
            }
            strcpy(out,r->receipts[i].response);return 0;
        }
        const char *key=NULL,*value=NULL,*revtext=NULL,*activation=NULL,*request_id=NULL;
        uint64_t revision=0;char storage_error[80]={0};int live_done=0;uint64_t live_revision=0;
        for(i=0;i<req.count;i++){
            if(!strcmp(req.f[i].key,"key"))key=req.f[i].value;
            else if(!strcmp(req.f[i].key,"value"))value=req.f[i].value;
            else if(!strcmp(req.f[i].key,"expected_revision"))revtext=req.f[i].value;
            else if(!strcmp(req.f[i].key,"activation"))activation=req.f[i].value;
            else if(!strcmp(req.f[i].key,"request_id"))request_id=req.f[i].value;
            else {error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;}
        }
        if(req.count!=5||!key||!value||!revtext||!activation||!request_id||
           strcmp(activation,"AUTO")||strcmp(request_id,req.rid)){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if(!*revtext||(*revtext=='0'&&revtext[1])){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        for(i=0;revtext[i];i++){
            if(revtext[i]<'0'||revtext[i]>'9'){
                error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
            }
            if(revision>(UINT64_MAX-(unsigned)(revtext[i]-'0'))/10u){
                error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
            }
            revision=revision*10u+(unsigned)(revtext[i]-'0');
        }
        if(!revision){error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;}
        id=alt111_setting_find(key);
        if(id<0){error_frame(out,cap,req.rid,"INVALID_KEY");return -1;}
        if(role!=MIBR_V3_SHELL&&!is_visible(key)){
            error_frame(out,cap,req.rid,"FORBIDDEN");return -1;
        }
        if(alt111_setting((unsigned)id)->read_only){error_frame(out,cap,req.rid,"READ_ONLY");return -1;}
        if(alt111_setting_validate((unsigned)id,value)){
            error_frame(out,cap,req.rid,"INVALID_VALUE");return -1;
        }
        if(!r||!r->ready){error_frame(out,cap,req.rid,"NOT_READY");return -1;}
        if(revision!=r->cached.revision){error_frame(out,cap,req.rid,"STALE_REVISION");return -1;}
        if(!r->durable_set){error_frame(out,cap,req.rid,"POLICY_BLOCKED");return -1;}
        if((unsigned)id==ALTSET_CARPLAY_ENABLED){
            /* r23: "CarPlay im Cockpit" is the runtime pause of the VC route, not a durable setting. */
            if(!r->carplay_pause){error_frame(out,cap,req.rid,"POLICY_BLOCKED");return -1;}
            if(r->carplay_pause(r->carplay_context,!strcmp(value,"1"))){
                error_frame(out,cap,req.rid,"STORAGE_UNAVAILABLE");return -1;
            }
            response_start(&w,req.rid,"OK");field(&w,"stored","RUNTIME_ONLY");
            field(&w,"apply","UNCHANGED");field(&w,"active","UNKNOWN");
            field(&w,"activation",activation_kind(alt111_setting((unsigned)id)->apply));
            numeric(&w,"revision",r->cached.revision);
            field(&w,"materialized","1");
            goto set_done;
        }
        /* A stale boot cache must never authorize a flash transaction after
         * an external legacy TEMP/profile writer changed the original core.
         * Recheck only at mutation time, not for every menu/status read.
         * r13 (field 2026-10-20): a drift is answered with STALE_REVISION and a
         * refreshed cache. The client re-reads and may retry against the new
         * revision; the profile edit stays CAS-guarded and touches one key.
         * Revoking the write capability here locked every save until restart
         * after an ordinary outside TEMP rewrite (iPhone reconnect). */
        {
            struct alt111_settings fresh;
            char load_error[128]={0};int drift=0;
            if(alt111_settings_load(&r->paths,&fresh,load_error,sizeof(load_error))){
                r->durable_set=NULL;r->ready=0;
                error_frame(out,cap,req.rid,"NOT_READY");return -1;
            }
            if(fresh.revision!=r->cached.revision)drift=1;
            else for(i=0;i<ALTSET_COUNT;i++)
                if(fresh.layer[i]!=r->cached.layer[i]||
                   strcmp(fresh.value[i],r->cached.value[i])){drift=1;break;}
            if(drift){
                if(mibr_v3_refresh(r,&r->paths)){
                    r->durable_set=NULL;r->ready=0;
                    error_frame(out,cap,req.rid,"NOT_READY");return -1;
                }
                error_frame(out,cap,req.rid,"STALE_REVISION");return -1;
            }
        }
        /* r13: live first. The slow flash transaction (remount rw, fsync, sync,
         * remount ro) took seconds before the cockpit saw anything. Write the
         * volatile TEMP layer and request the presentation first, then persist.
         * A verified durable failure reverts TEMP to the previous value. */
        if(r->live_apply&&strcmp(r->cached.value[id],value)&&
           !r->live_apply(&r->paths,&r->cached,(unsigned)id,value,&live_revision)){
            live_done=1;
            if(r->presentation_request&&
               !strcmp(alt111_setting((unsigned)id)->apply,"presentation"))
                (void)r->presentation_request(r->presentation_context,(unsigned)id);
        }
        if(live_done&&r->persist_delay_ms>0&&r->durable_set&&
           strlen(r->cached.value[id])<sizeof(r->persist_old[0])){
            long long now=mono_ms();
            if(!r->persist_dirty[id]){
                memcpy(r->persist_old[id],r->cached.value[id],strlen(r->cached.value[id])+1u);
                r->persist_dirty[id]=1;
            }
            if(!r->persist_pending)r->persist_first_ms=now;
            r->persist_pending=1;r->persist_last_ms=now;
            if(mibr_v3_refresh(r,&r->paths)||strcmp(r->cached.value[id],value)){
                r->ready=0;error_frame(out,cap,req.rid,"UNKNOWN_COMMIT");return -1;
            }
            response_start(&w,req.rid,"OK");field(&w,"stored","PENDING_PERSIST");
            field(&w,"apply","PENDING");field(&w,"active","UNKNOWN");
            field(&w,"activation",activation_kind(alt111_setting((unsigned)id)->apply));
            numeric(&w,"revision",r->cached.revision);
            field(&w,"materialized","1");
            goto set_done;
        }
        rc=r->durable_set(r->storage_context,&r->paths,&r->cached,(unsigned)id,
                          value,revision,storage_error,sizeof(storage_error));
        if(live_done&&rc==2){
            /* Durable profile verified; the final TEMP step saw the live revision and
             * stood down. Accept it only if the reloaded core really holds the value. */
            if(!mibr_v3_refresh(r,&r->paths)&&!strcmp(r->cached.value[id],value))rc=1;
        }
        if(live_done&&rc==-1){
            /* Nothing was committed: put the previous volatile value back and re-present it. */
            if(r->live_revert)(void)r->live_revert(&r->paths,(unsigned)id,r->cached.value[id],live_revision);
            if(r->presentation_request&&
               !strcmp(alt111_setting((unsigned)id)->apply,"presentation"))
                (void)r->presentation_request(r->presentation_context,(unsigned)id);
        }
        if(rc<0){
            if(!strcmp(storage_error,"RO_RESTORE_FAILED")){
                r->durable_set=NULL;r->stored_verified=0;r->ready=0;
            }
            const char *code=rc==-2?"UNKNOWN_COMMIT":"STORAGE_UNAVAILABLE";
            if(!strcmp(storage_error,"RO_RESTORE_FAILED"))code="RO_RESTORE_FAILED";
            else if(!strcmp(storage_error,"DEPENDENCY_CONFLICT"))code="DEPENDENCY_CONFLICT";
            else if(!strcmp(storage_error,"STALE_REVISION"))code="STALE_REVISION";
            else if(!strcmp(storage_error,"INVALID_VALUE"))code="INVALID_VALUE";
            else if(!strcmp(storage_error,"DURABILITY_UNCONFIRMED"))code="DURABILITY_UNCONFIRMED";
            error_frame(out,cap,req.rid,code);return -1;
        }
        if(rc==1&&mibr_v3_refresh(r,&r->paths)){
            error_frame(out,cap,req.rid,"UNKNOWN_COMMIT");return -1;
        }
        if(rc==1&&strcmp(r->cached.value[id],value)){
            r->ready=0;error_frame(out,cap,req.rid,"UNKNOWN_COMMIT");return -1;
        }
        if(rc==1&&!live_done&&r->presentation_request&&
           !strcmp(alt111_setting((unsigned)id)->apply,"presentation"))
            (void)r->presentation_request(r->presentation_context,(unsigned)id);
        r->stored_pending=(rc==2);r->stored_verified=1;
        /* Profile verified, but the old resolved TEMP must never be served
         * as the new desired snapshot when compatibility materialization fails. */
        if(rc==2)r->ready=0;
        response_start(&w,req.rid,"OK");field(&w,"stored","VERIFIED");
        field(&w,"apply",rc==0?"UNCHANGED":"PENDING");
        field(&w,"active","UNKNOWN");
        field(&w,"activation",activation_kind(alt111_setting((unsigned)id)->apply));
        numeric(&w,"revision",r->cached.revision);
        field(&w,"materialized",rc==2?"0":"1");
     set_done:;
     }else if(!strcmp(req.op,"ACTION")){
        const char *kind=NULL,*target_name=NULL,*expect_name=NULL,*session_name=NULL;
        const char *generation_name=NULL,*origin=NULL,*request_id=NULL;
        struct mibr_v3_route_observation previous,after;
        enum mibr_v3_visible_route target,expected;
        struct mibr_v3_route_receipt *saved;
        uint64_t session,generation;
        int action_result;
        /* Retry of a verified original request must never actuate the owner a second time.
         * An identical ID with different bytes is a collision even between SET/ACTION. */
        for(i=0;i<8;i++)if(r&&!strcmp(req.rid,r->route_receipts[i].rid)){
            saved=&r->route_receipts[i];
            if(saved->role!=(unsigned)role||saved->n!=length||
               memcmp(saved->frame,frame,length)){
                error_frame(out,cap,req.rid,"IDEMPOTENCY_COLLISION");return -1;
            }
            if(strlen(saved->response)+1>cap){
                error_frame(out,cap,req.rid,"SNAPSHOT_TOO_LARGE");return -1;
            }
            strcpy(out,saved->response);return 0;
        }
        if(r)for(i=0;i<8;i++)if(!strcmp(req.rid,r->receipts[i].rid)){
            error_frame(out,cap,req.rid,"IDEMPOTENCY_COLLISION");return -1;
        }
        for(i=0;i<req.count;i++){
            if(!strcmp(req.f[i].key,"kind"))kind=req.f[i].value;
            else if(!strcmp(req.f[i].key,"target"))target_name=req.f[i].value;
            else if(!strcmp(req.f[i].key,"expected_route"))expect_name=req.f[i].value;
            else if(!strcmp(req.f[i].key,"expected_session"))session_name=req.f[i].value;
            else if(!strcmp(req.f[i].key,"expected_generation"))generation_name=req.f[i].value;
            else if(!strcmp(req.f[i].key,"origin"))origin=req.f[i].value;
            else if(!strcmp(req.f[i].key,"request_id"))request_id=req.f[i].value;
            else {error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;}
        }
        if(req.count!=7||!kind||strcmp(kind,"SET_VISIBLE_ROUTE")||!target_name||
           !expect_name||route_value(target_name,&target)||route_value(expect_name,&expected)||
           !session_name||decimal_u64(session_name,&session)||!generation_name||
           decimal_u64(generation_name,&generation)||!origin||!request_id||
           strcmp(request_id,req.rid)){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if((role==MIBR_V3_UI&&strcmp(origin,"HMI"))||
           (role==MIBR_V3_INPUT&&strcmp(origin,"KEY40_LONG"))||
           (role!=MIBR_V3_UI&&role!=MIBR_V3_INPUT)){
            error_frame(out,cap,req.rid,"FORBIDDEN");return -1;
        }
        if(!r||!r->route_qualified||!r->route_set||!r->route_read){
            error_frame(out,cap,req.rid,"ACTIVATION_UNSUPPORTED");return -1;
        }
        if(route_reconcile_inflight(r)||route_observe(r,&previous)){
            error_frame(out,cap,req.rid,"NOT_READY");return -1;
        }
        if(previous.visible!=expected||previous.session!=session||
           previous.generation!=generation){
            error_frame(out,cap,req.rid,"SESSION_STALE");return -1;
        }
        action_target=target;action_session=session;action_generation=generation;
        after=previous;
        /* Reserve BEFORE entering the owner callback: synchronous callback
         * reentry must not dispatch a competing request. The owner may report
         * -1 only when it proves NO dispatch; -2 means dispatch outcome is
         * uncertain, including a lost reply after side effects. */
        if(target!=previous.visible){
            r->route_inflight=1;
            strcpy(r->route_inflight_rid,req.rid);
        }
        action_result=target==previous.visible?0:
            r->route_set(r->route_context,target,&previous,req.rid,&after);
        if(action_result==-1){
            r->route_inflight=0;r->route_inflight_rid[0]=0;
            error_frame(out,cap,req.rid,"ACTIVATION_FAILED");return -1;
        }
        /* Every uncertain negative result remains PENDING and retains its
         * original RID until independently observed original-RID ACK.
         * Never retry the owner merely because transport returned an error. */
        if(action_result<0)action_result=1;
        /* An owner callback's return code is NOT an ACTIVE assertion:
         * independently re-observe its real current visible route. */
        if(action_result==0&&!route_observe(r,&after)&&after.visible==target&&
           after.session==session&&after.generation>=generation&&
           (target==previous.visible||!strcmp(after.ack_request_id,req.rid)))
            action_result=0;
        else action_result=1;
        if(target!=previous.visible && !action_result){
            r->route_inflight=0;r->route_inflight_rid[0]=0;
        }
        response_start(&w,req.rid,"OK");
        field(&w,"kind","SET_VISIBLE_ROUTE");field(&w,"target",route_name(target));
        field(&w,"apply",action_result?"PENDING":"ACTIVE");
        field(&w,"visible_route",action_result?"UNKNOWN":route_name(after.visible));
        field(&w,"stored","UNCHANGED");
        if(!action_result){numeric(&w,"owner_session",after.session);
                           numeric(&w,"owner_generation",after.generation);}
    }else if(!strcmp(req.op,"ACTION_STATUS")){
        struct mibr_v3_route_receipt *saved=NULL;
        struct mibr_v3_route_observation observed;
        if(req.count!=1||strcmp(req.f[0].key,"request_id")||
           !req.f[0].value[0]){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if(!r||role==MIBR_V3_SHELL){
            error_frame(out,cap,req.rid,"FORBIDDEN");return -1;
        }
        for(i=0;i<8;i++)if(!strcmp(r->route_receipts[i].rid,req.f[0].value)){
            saved=&r->route_receipts[i];break;
        }
        if(!saved){error_frame(out,cap,req.rid,"UNKNOWN_COMMIT");return -1;}
        if(saved->role!=(unsigned)role){
            error_frame(out,cap,req.rid,"FORBIDDEN");return -1;
        }
        /* A historical success stays ACKED, but callers MUST fetch fresh STATUS
         * to know what is visible now. A later verified ACK may resolve PENDING
         * only if it binds EXACT original id, owner session, generation and target.
         * No re-execution of the owner under a status request. */
        if(!saved->active&&!route_observe(r,&observed)&&
           observed.visible==saved->target&&
           observed.session==saved->expected_session&&
           observed.generation>=saved->expected_generation&&
           !strcmp(observed.ack_request_id,saved->rid))saved->active=1;
        if(saved->active && r->route_inflight &&
           !strcmp(r->route_inflight_rid,saved->rid)){
            r->route_inflight=0;r->route_inflight_rid[0]=0;
        }
        response_start(&w,req.rid,"OK");
        field(&w,"original_request_id",saved->rid);
        field(&w,"kind","SET_VISIBLE_ROUTE");
        field(&w,"target",route_name(saved->target));
        field(&w,"apply",saved->active?"ACTIVE":"PENDING");
        field(&w,"receipt_scope","HISTORICAL");
        field(&w,"stored","UNCHANGED");
    }else if(!strcmp(req.op,"REQUEST_STATUS")){
        struct mibr_v3_receipt *saved=NULL;
        if(req.count!=1||strcmp(req.f[0].key,"request_id")){
            error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;
        }
        if(!r||!r->durable_set){error_frame(out,cap,req.rid,"POLICY_BLOCKED");return -1;}
        for(i=0;i<8;i++)if(!strcmp(r->receipts[i].rid,req.f[0].value)){
            saved=&r->receipts[i];break;
        }
        if(!saved){error_frame(out,cap,req.rid,"UNKNOWN_COMMIT");return -1;}
        response_start(&w,req.rid,"OK");
        field(&w,"original_request_id",saved->rid);
        field(&w,"stored","VERIFIED");field(&w,"active","UNKNOWN");
        field(&w,"apply",saved->unchanged?"UNCHANGED":"PENDING");
        field(&w,"materialized",saved->materialized?"1":"0");
    }else if(!strcmp(req.op,"BATCH")||
              !strcmp(req.op,"RESET")||!strcmp(req.op,"TEST_SET")||
              !strcmp(req.op,"TEST_CLEAR")||!strcmp(req.op,"TEST_LIST")||
              !strcmp(req.op,"ACTIVATE")||!strcmp(req.op,"REQUEST_STATUS")){
        error_frame(out,cap,req.rid,"POLICY_BLOCKED");return -1;
    }else {error_frame(out,cap,req.rid,"INVALID_REQUEST");return -1;}
    finish(&w);
    if(w.failed){error_frame(out,cap,req.rid,"SNAPSHOT_TOO_LARGE");return -1;}
    if(r&&!strcmp(req.op,"ACTION")){
        struct mibr_v3_route_receipt *saved=&r->route_receipts[r->route_receipt_cursor++%8];
        strcpy(saved->rid,req.rid);
        memcpy(saved->frame,frame,length);saved->frame[length]=0;saved->n=length;
        saved->target=action_target;saved->expected_session=action_session;
        saved->expected_generation=action_generation;saved->role=(unsigned)role;
        saved->active=strstr(out,"apply=ACTIVE")!=NULL;
        if(strlen(out)<sizeof(saved->response))strcpy(saved->response,out);
        else saved->rid[0]=0;
    }
    if(r&&!strcmp(req.op,"SET")){
        struct mibr_v3_receipt *saved=&r->receipts[r->receipt_cursor++%8];
        strcpy(saved->rid,req.rid);
        memcpy(saved->frame,frame,length);saved->frame[length]=0;saved->n=length;
        strcpy(saved->response,out);
        saved->materialized=!r->stored_pending;
        saved->unchanged=strstr(out,"apply=UNCHANGED")!=NULL;
    }
    return 0;
}
