/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host-only in-process wire harness. A command-line role switch is NOT authentication;
 * never link this file into a product executable or deploy it.
 */
#ifndef ALT111_SETTINGS_TEST
#error MIBR_V3_HOST_ONLY
#endif
#include "mibr_v3_readonly.h"
#include "mibr_v3_input_bridge.h"
#include "mibr_v3_route_gateway.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct mock_route {struct mibr_v3_route_observation state;unsigned calls;};
static int mock_observe(void *ctx,struct mibr_v3_route_observation *out){
    struct mock_route *m=(struct mock_route*)ctx;*out=m->state;return 0;
}
static int mock_apply(void *ctx,enum mibr_v3_visible_route target,
    const struct mibr_v3_route_observation *expected,const char *rid,
    struct mibr_v3_route_observation *out){
    struct mock_route *m=(struct mock_route*)ctx;
    if(m->state.visible!=expected->visible||
       m->state.session!=expected->session||m->state.generation!=expected->generation)
       return -1;
    m->calls++;
    if(getenv("MIBR_V3_HOST_ROUTE_FAIL"))return -1;
    if(getenv("MIBR_V3_HOST_ROUTE_UNCERTAIN"))return -2;
    if(getenv("MIBR_V3_HOST_ROUTE_PENDING")){*out=m->state;return 1;}
    m->state.visible=target;m->state.generation++;
    if(!getenv("MIBR_V3_HOST_ROUTE_NO_ACK"))
        snprintf(m->state.ack_request_id,sizeof(m->state.ack_request_id),"%s",rid);
    *out=m->state;return 0;
}
/* Independent synthetic owner/AID are HOST-ONLY. No target has these sources. */
struct host_gateway_scene {
    uint64_t now;
    struct mibr_v3_owner_sample owner;
    struct mibr_v3_aid_sample aid;
    unsigned calls;
};
static int host_now(void *ctx,uint64_t *p){
    *p=((struct host_gateway_scene*)ctx)->now;return 0;
}
static int host_owner(void *ctx,struct mibr_v3_owner_sample *p){
    *p=((struct host_gateway_scene*)ctx)->owner;return 0;
}
static int host_aid(void *ctx,struct mibr_v3_aid_sample *p){
    *p=((struct host_gateway_scene*)ctx)->aid;return 0;
}
static int host_owner_request(void *ctx,enum mibr_v3_visible_route target,
                              const struct mibr_v3_route_observation *expected,
                              const char *rid){
    struct host_gateway_scene *s=(struct host_gateway_scene*)ctx;
    if(s->owner.visible!=expected->visible||s->owner.session!=expected->session||
       s->owner.generation!=expected->generation)return -1;
    ++s->calls;
    if(getenv("MIBR_V3_HOST_GATEWAY_UNCERTAIN"))return -2;
    s->owner.visible=target;s->owner.generation++;s->owner.observed_ms=s->now;
    snprintf(s->owner.ack_request_id,sizeof(s->owner.ack_request_id),"%s",rid);
    if(!getenv("MIBR_V3_HOST_GATEWAY_AID_LAG")){
        s->aid.visible=target;s->aid.observed_ms=s->now;
    }
    return 0;
}
int main(int argc,char **argv){
    struct mock_route mock={0};
    struct host_gateway_scene gs={0};
    struct mibr_v3_route_gateway gateway;
    const struct mibr_v3_route_gateway_ops gateway_ops={
        host_now,host_owner,host_aid,host_owner_request};
    struct mibr_v3_input_bridge input;
    struct mibr_v3_reader reader;
    struct alt111_settings_paths paths;
    enum mibr_v3_role role;
    char line[4098],out[16384];size_t n;
    if(argc!=2)return 2;
    if(!strcmp(argv[1],"--ui"))role=MIBR_V3_UI;
    else if(!strcmp(argv[1],"--shell"))role=MIBR_V3_SHELL;
    else if(!strcmp(argv[1],"--input"))role=MIBR_V3_INPUT;
    else return 2;
    paths.temp=getenv("ALT111_SETTINGS_TEMP_ROOT");
    paths.persistent=getenv("ALT111_SETTINGS_PERSISTENT_ROOT");
    if(!paths.temp||!paths.persistent)return 3;
    if(mibr_v3_open(&reader,&paths))return 4;
    if(getenv("MIBR_V3_HOST_ROUTE_TEST")){
        mock.state.visible=MIBR_ROUTE_STOCK110;
        mock.state.session=7;mock.state.generation=9;mock.state.confirmed=1;
        reader.route_read=mock_observe;reader.route_set=mock_apply;
        reader.route_context=&mock;
        reader.route_qualified=getenv("MIBR_V3_HOST_ROUTE_UNQUALIFIED")?0:1;
    }
    if(getenv("MIBR_V3_HOST_GATEWAY_TEST")){
        if(reader.route_read||reader.route_set||reader.route_qualified)return 6;
        gs.now=10000;gs.owner.visible=MIBR_ROUTE_STOCK110;
        gs.owner.session=7;gs.owner.generation=9;gs.owner.observed_ms=9999;
        gs.owner.confirmed=1;gs.owner.control_authority_verified=1;
        gs.aid.visible=MIBR_ROUTE_STOCK110;gs.aid.observed_ms=9998;
        gs.aid.confirmed=1;
        mibr_v3_gateway_init(&gateway,&gateway_ops,&gs);
        if(mibr_v3_gateway_attach(&gateway,&reader,1))return 7;
    }
    mibr_v3_input_init(&input,4711u);
    if(getenv("MIBR_V3_HOST_INPUT_TEST"))(void)mibr_v3_input_arm(&input,1);
    puts("MIBR_V3_HOST_READY");fflush(stdout);
    while(fgets(line,sizeof(line),stdin)){
        /* Test-only KEY40 input injection: no physical DSI or OEM bypass. */
        if(!strncmp(line,"#HOST_KEY40 ",12)){
            char outkey[16384];int state;enum mibr_v3_input_result res;
            if(sscanf(line+12,"%d",&state)!=1){puts("HOST_KEY40_INVALID");fflush(stdout);continue;}
            res=mibr_v3_input_key2(&input,&reader,4,40,state,outkey,sizeof(outkey));
            if(res==MIBR_INPUT_ACTION)fputs(outkey,stdout);
            else puts(res==MIBR_INPUT_NONE?"HOST_KEY40_NONE":
                      res==MIBR_INPUT_OEM_SHORT?"HOST_KEY40_OEM_SHORT":
                      res==MIBR_INPUT_UNQUALIFIED?"HOST_KEY40_UNQUALIFIED":"HOST_KEY40_INVALID");
            fflush(stdout);continue;
        }
        /* Host-only AID catchup/loss exercises the actual broker plus gateway;
         * no DSI, owner ticket or vehicle activation is provided. */
        if(!strcmp(line,"#HOST_AID_CATCHUP\n")){
            if(!getenv("MIBR_V3_HOST_GATEWAY_TEST"))puts("HOST_GATEWAY_UNAVAILABLE");
            else {
                gs.aid.visible=gs.owner.visible;gs.aid.observed_ms=gs.now;
                puts("HOST_AID_CATCHUP_OK");
            }
            fflush(stdout);continue;
        }
        if(!strcmp(line,"#HOST_GATEWAY_REVOKE\n")){
            if(!getenv("MIBR_V3_HOST_GATEWAY_TEST"))puts("HOST_GATEWAY_UNAVAILABLE");
            else {
                mibr_v3_gateway_revoke(&gateway,&reader);
                puts("HOST_GATEWAY_REVOKED");
            }
            fflush(stdout);continue;
        }
        /* Test-only explicit invalidation hooks; never part of the MIBR/3 wire. */
        /* Test-only deferred owner event, NOT a product API or owner bridge. */
        if(!strncmp(line,"#HOST_ROUTE_COMPLETE ",21)){
            char *rid=line+21;unsigned i;int found=0;size_t n=strlen(rid);
            if(n&&rid[n-1]=='\n')rid[n-1]=0;
            for(i=0;i<8;i++)if(reader.route_receipts[i].rid[0]&&
               !strcmp(reader.route_receipts[i].rid,rid)&&
               reader.route_receipts[i].expected_session==mock.state.session&&
               reader.route_receipts[i].expected_generation==mock.state.generation){
                mock.state.visible=reader.route_receipts[i].target;
                mock.state.generation++;
                snprintf(mock.state.ack_request_id,
                    sizeof(mock.state.ack_request_id),"%s",rid);
                found=1;break;
            }
            puts(found?"HOST_ROUTE_COMPLETE_OK":"HOST_ROUTE_COMPLETE_REJECTED");
            fflush(stdout);continue;
        }
        if(!strcmp(line,"#HOST_ROUTE_CALLS\n")){
            printf("HOST_ROUTE_CALLS=%u\n",getenv("MIBR_V3_HOST_GATEWAY_TEST")?gs.calls:mock.calls);fflush(stdout);continue;
        }
        if(!strcmp(line,"#HOST_REFRESH\n")){
            puts(mibr_v3_refresh(&reader,&paths)?"HOST_REFRESH_FAILED":"HOST_REFRESH_OK");
            fflush(stdout);continue;
        }
        if(!strcmp(line,"#HOST_REFRESH_BAD_PATHS\n")){
            puts(mibr_v3_refresh(&reader,NULL)?"HOST_REFRESH_FAILED":"HOST_REFRESH_UNEXPECTED_OK");
            fflush(stdout);continue;
        }
        n=strlen(line);
        (void)mibr_v3_handle(&reader,role,line,n,out,sizeof(out));
        fputs(out,stdout);fflush(stdout);
    }
    return 0;
}
